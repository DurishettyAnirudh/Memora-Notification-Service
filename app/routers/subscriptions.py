"""Subscriptions stub — browser push subscriptions removed."""
# Push subscription management removed: users now receive Telegram messages.

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import verify_api_key
from app.models import PushSubscription, get_db

router = APIRouter(prefix="/subscribe", tags=["subscriptions"])


class SubscriptionRequest(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


class SubscriptionResponse(BaseModel):
    id: int
    endpoint: str


@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
def create_subscription(
    body: SubscriptionRequest,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Store or update a push subscription."""
    existing = db.query(PushSubscription).filter(PushSubscription.endpoint == body.endpoint).first()
    if existing:
        existing.p256dh = body.p256dh
        existing.auth = body.auth
        db.commit()
        db.refresh(existing)
        return SubscriptionResponse(id=existing.id, endpoint=existing.endpoint)

    sub = PushSubscription(endpoint=body.endpoint, p256dh=body.p256dh, auth=body.auth)
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return SubscriptionResponse(id=sub.id, endpoint=sub.endpoint)
