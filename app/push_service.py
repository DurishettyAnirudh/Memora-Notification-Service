"""Push service stub — replaced by Telegram Bot API delivery."""
# pywebpush removed: notifications are sent via Telegram.

import json
import logging

from pywebpush import webpush, WebPushException

from app.config import settings

logger = logging.getLogger(__name__)


def send_push(endpoint: str, p256dh: str, auth: str, title: str, body: str) -> bool:
    """Send a Web Push notification. Returns True on success."""
    payload = json.dumps({"title": title, "body": body})
    try:
        webpush(
            subscription_info={"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}},
            data=payload,
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_claims_email},
        )
        return True
    except WebPushException as e:
        logger.error("Push failed for %s: %s", endpoint[:60], e)
        return False
    except Exception as e:
        logger.error("Unexpected push error: %s", e)
        return False
