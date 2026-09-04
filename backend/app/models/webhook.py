"""Webhook events ORM model."""

from sqlalchemy import Column, String, Integer, DateTime, Boolean, JSON
from sqlalchemy import func
from app.database import Base


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(100), unique=True, nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    payload = Column(JSON, nullable=True)
    processed = Column(Boolean, default=False)
    processing_result = Column(String(30), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
