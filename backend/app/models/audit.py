"""Audit log ORM model."""

from sqlalchemy import Column, String, Float, Integer, DateTime, Text, JSON
from sqlalchemy import func
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(50), nullable=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    details = Column(Text, nullable=True)
    amount = Column(Float, nullable=True)
    amount_recovered = Column(Float, nullable=True)
    ai_recommendation = Column(String(100), nullable=True)
    ml_probability = Column(Float, nullable=True)
    policy_decision = Column(String(30), nullable=True)
    action = Column(String(50), nullable=True)
    action_result = Column(String(30), nullable=True)
    rules_triggered = Column(JSON, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
