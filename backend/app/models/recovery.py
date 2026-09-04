"""Recovery-related ORM models."""

from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Text, JSON
from sqlalchemy import func
from app.database import Base


class ModelPrediction(Base):
    __tablename__ = "model_predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(50), nullable=False, index=True)
    recovery_probability = Column(Float, nullable=False)
    confidence = Column(Float, nullable=True)
    feature_importances = Column(JSON, nullable=True)
    model_version = Column(String(30), default="xgb_v1")
    created_at = Column(DateTime, server_default=func.now())


class RecoveryDecision(Base):
    __tablename__ = "recovery_decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(50), nullable=False, index=True)
    diagnosis = Column(String(100), nullable=True)
    recommended_action = Column(String(50), nullable=False)
    reasoning = Column(JSON, nullable=True)  # list of reason strings
    ai_confidence = Column(Float, nullable=True)
    retry_delay_minutes = Column(Integer, nullable=True)
    customer_message = Column(Text, nullable=True)

    # Policy decision
    policy_decision = Column(String(30), nullable=True)  # ALLOW, BLOCK, ESCALATE, STOP
    policy_reason = Column(Text, nullable=True)
    rules_triggered = Column(JSON, nullable=True)

    # Final outcome
    final_action = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class RecoveryAction(Base):
    __tablename__ = "recovery_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action_id = Column(String(50), unique=True, nullable=False, index=True)
    transaction_id = Column(String(50), nullable=False, index=True)
    action_type = Column(String(50), nullable=False)
    status = Column(String(30), nullable=False)  # success, failed, pending, skipped
    amount_recovered = Column(Float, default=0.0)
    execution_details = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class PaymentLink(Base):
    __tablename__ = "payment_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(50), nullable=False, index=True)
    link_id = Column(String(100), nullable=True)
    link_url = Column(String(500), nullable=True)
    short_url = Column(String(200), nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")
    status = Column(String(30), default="created")  # created, paid, expired
    provider = Column(String(30), default="mock")  # mock or razorpay
    created_at = Column(DateTime, server_default=func.now())


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(50), unique=True, nullable=False, index=True)
    total_transactions = Column(Integer, default=0)
    failed_transactions = Column(Integer, default=0)
    revenue_at_risk = Column(Float, default=0.0)
    eligible_for_recovery = Column(Integer, default=0)
    recovery_attempts = Column(Integer, default=0)
    successful_recoveries = Column(Integer, default=0)
    revenue_recovered = Column(Float, default=0.0)
    recovery_rate = Column(Float, default=0.0)
    avg_recovery_amount = Column(Float, default=0.0)
    automated_action_rate = Column(Float, default=0.0)
    human_escalation_rate = Column(Float, default=0.0)
    policy_block_rate = Column(Float, default=0.0)
    baseline_recovered = Column(Float, default=0.0)
    baseline_recovery_rate = Column(Float, default=0.0)
    improvement_pct = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())


class PolicyDecision(Base):
    __tablename__ = "policy_decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(50), nullable=False, index=True)
    requested_action = Column(String(50), nullable=False)
    decision = Column(String(30), nullable=False)  # ALLOW, BLOCK, ESCALATE, STOP
    reason = Column(Text, nullable=True)
    rules_triggered = Column(JSON, nullable=True)
    amount = Column(Float, nullable=True)
    recovery_probability = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
