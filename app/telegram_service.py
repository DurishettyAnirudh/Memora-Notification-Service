"""Telegram Bot API message sender."""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def send_telegram_message(chat_id: str, text: str) -> bool:
    """Send a Telegram message via Bot API. Returns True on success."""
    if not settings.telegram_bot_token:
        logger.warning("Telegram bot token not configured")
        return False
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                url,
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            )
            if r.status_code == 200:
                return True
            logger.error("Telegram API error %d: %s", r.status_code, r.text)
            return False
    except Exception as e:
        logger.error("Telegram send error: %s", e)
        return False
