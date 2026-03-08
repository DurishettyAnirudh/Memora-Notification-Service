"""Models stub — notification service is now stateless (no database)."""
# SQLAlchemy removed: service uses QStash for scheduling, no local DB needed.

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    endpoint = Column(Text, nullable=False, unique=True)
    p256dh = Column(Text, nullable=False)
    auth = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    notifications = relationship(
        "ScheduledNotification", back_populates="subscription", cascade="all, delete-orphan"
    )


class ScheduledNotification(Base):
    __tablename__ = "scheduled_notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subscription_id = Column(Integer, ForeignKey("push_subscriptions.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(100), nullable=False)
    body = Column(String(300), nullable=False)
    trigger_at = Column(DateTime, nullable=False)
    is_fired = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    api_key_hash = Column(String(64), nullable=False)

    subscription = relationship("PushSubscription", back_populates="notifications")

    __table_args__ = (Index("ix_trigger_fired", "trigger_at", "is_fired"),)


# Database setup
engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
    echo=False,
)
SessionLocal = sessionmaker(bind=engine, class_=Session)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
