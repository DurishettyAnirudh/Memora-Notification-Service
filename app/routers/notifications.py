"""Notification scheduling via QStash and delivery via Telegram."""

import json
import logging
from datetime import datetime, timezone

from qstash import QStash
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.config import settings
from app.telegram_service import send_telegram_message

logger = logging.getLogger(__name__)

router = APIRouter()


class ScheduleRequest(BaseModel):
    id: str
    telegram_chat_id: str
    title: str
    body: str
    trigger_at: str  # ISO 8601


@router.post("/notify/schedule", status_code=202)
async def schedule_notification(
    payload: ScheduleRequest,
    request: Request,
):
    """Enqueue a Telegram notification to be delivered at trigger_at via QStash."""
    if request.headers.get("x-api-key") != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    trigger = datetime.fromisoformat(payload.trigger_at.replace("Z", "+00:00"))
    # If the trigger has no tzinfo (naive), assume UTC
    if trigger.tzinfo is None:
        trigger = trigger.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    delay_seconds = max(0, int((trigger - now).total_seconds()))

    if not settings.qstash_token:
        logger.warning("QStash not configured — notification %s not scheduled", payload.id)
        return {"scheduled": False, "reason": "QStash not configured"}

    try:
        client = QStash(token=settings.qstash_token)
        callback_url = f"{settings.service_url}/webhook/fire"
        client.message.publish_json(
            url=callback_url,
            body={
                "telegram_chat_id": payload.telegram_chat_id,
                "title": payload.title,
                "body": payload.body,
            },
            delay=delay_seconds,
            headers={"x-notification-id": payload.id},
        )
    except Exception as exc:
        logger.error("QStash publish failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))

    logger.info("Scheduled notification %s in %ds via QStash", payload.id, delay_seconds)
    return {"scheduled": True, "delay_seconds": delay_seconds, "mode": "qstash"}


@router.post("/webhook/fire")
async def fire_notification(request: Request):
    """Called by QStash at trigger time — sends Telegram message."""
    signature = request.headers.get("upstash-signature", "")
    body_bytes = await request.body()

    # Verify QStash signature (skipped in local dev when keys not set)
    if settings.qstash_current_signing_key:
        from qstash.receiver import Receiver

        receiver = Receiver(
            current_signing_key=settings.qstash_current_signing_key,
            next_signing_key=settings.qstash_next_signing_key,
        )
        try:
            receiver.verify(
                signature=signature,
                body=body_bytes.decode(),
                url=f"{settings.service_url}/webhook/fire",
            )
        except Exception as e:
            logger.warning("QStash signature verification failed: %s", e)
            raise HTTPException(status_code=401, detail="Invalid signature")

    data = json.loads(body_bytes)
    chat_id = data.get("telegram_chat_id", "")
    title = data.get("title", "Reminder")
    body = data.get("body", "")

    if not chat_id:
        raise HTTPException(status_code=400, detail="Missing telegram_chat_id")

    text = f"<b>⏰ {title}</b>\n{body}"
    success = await send_telegram_message(chat_id, text)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to send Telegram message")

    return {"fired": True}


@router.get("/telegram/chat-id")
async def get_telegram_chat_id(request: Request):
    """Helper: returns the most recent chat ID from bot updates.
    User must send any message to the bot before calling this."""
    if request.headers.get("x-api-key") != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not settings.telegram_bot_token:
        raise HTTPException(status_code=503, detail="Telegram bot token not configured")

    import httpx

    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/getUpdates",
            params={"limit": 1, "offset": -1},
        )
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail="Telegram API error")

    updates = r.json().get("result", [])
    if not updates:
        raise HTTPException(
            status_code=404,
            detail="No messages found. Send any message to your Telegram bot first.",
        )

    msg = updates[-1].get("message") or updates[-1].get("channel_post")
    if not msg:
        raise HTTPException(status_code=404, detail="No message in update")

    return {"chat_id": str(msg["chat"]["id"]), "name": msg["chat"].get("first_name", "")}
