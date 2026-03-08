"""Scheduler stub — replaced by QStash for serverless scheduling."""
# APScheduler removed: scheduling is delegated to Upstash QStash.

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, delete

from app.models import SessionLocal, ScheduledNotification
from app.push_service import send_push
from app.config import settings

logger = logging.getLogger(__name__)


def fire_due_notifications() -> None:
    """Check for due notifications and send them via Web Push."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        due = (
            db.query(ScheduledNotification)
            .filter(
                and_(
                    ScheduledNotification.trigger_at <= now,
                    ScheduledNotification.is_fired == False,  # noqa: E712
                )
            )
            .all()
        )

        for notif in due:
            sub = notif.subscription
            if not sub:
                notif.is_fired = True
                continue

            success = send_push(
                endpoint=sub.endpoint,
                p256dh=sub.p256dh,
                auth=sub.auth,
                title=notif.title,
                body=notif.body,
            )
            notif.is_fired = True
            if success:
                logger.info("Fired notification %s", notif.id)
            else:
                logger.warning("Failed to fire notification %s", notif.id)

        db.commit()
    except Exception as e:
        logger.error("Scheduler error: %s", e)
        db.rollback()
    finally:
        db.close()


def cleanup_old_notifications() -> None:
    """Delete fired notifications older than cleanup_days."""
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.cleanup_days)
        db.execute(
            delete(ScheduledNotification).where(
                and_(
                    ScheduledNotification.is_fired == True,  # noqa: E712
                    ScheduledNotification.created_at < cutoff,
                )
            )
        )
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
