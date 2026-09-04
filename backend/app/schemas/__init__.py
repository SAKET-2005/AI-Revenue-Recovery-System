"""Pydantic schemas for API request/response validation."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ─── Enums ────────────────────────────────────────────────

class PaymentMethod(str, Enum):
    UPI = "upi"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    NET_BANKING = "net_banking"
    WALLET = "wallet"


class PaymentStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    RECOVERED = "recovered"
    PENDING = "pending"


class FailureCategory(str, Enum):
    TEMPORARY_BANK_FAILURE = "temporary_bank_failure"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    AUTHENTICATION_FAILURE = "authentication_failure"
    NETWORK_TIMEOUT = "network_timeout"
    EXPIRED_CARD = "expired_card"
    RISK_DECLINE = "risk_decline"
    INVALID_DETAILS = "invalid_details"
    UNKNOWN = "unknown"


class RecoveryAction(str, Enum):
    RETRY = "retry"
    CUSTOMER_NUDGE = "customer_nudge"
    PAYMENT_LINK = "payment_link"
    HUMAN_REVIEW = "human_review"
    STOP = "stop"


class PolicyVerdict(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"
    STOP = "STOP"


class ActionStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    SKIPPED = "skipped"


# ─── Transaction Schemas ──────────────────────────────────

class TransactionBase(BaseModel):
    transaction_id: str
    customer_id: str
    amount: float
    currency: str = "INR"
    payment_method: str
    payment_status: str
    failure_code: Optional[str] = None
    failure_reason: Optional[str] = None


class TransactionDetail(TransactionBase):
    id: int
    merchant_id: str
    retry_count: int = 0
    device_type: Optional[str] = None
    location: Optional[str] = None
    merchant_category: Optional[str] = None
    checkout_duration: Optional[float] = None
    cart_value: Optional[float] = None
    is_returning_customer: bool = False
    transaction_frequency: Optional[float] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CustomerDetail(BaseModel):
    customer_id: str
    previous_transactions: int = 0
    success_rate: float = 0.0
    previous_failures: int = 0
    lifetime_value: float = 0.0
    last_transaction_time: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── ML Schemas ───────────────────────────────────────────

class MLPrediction(BaseModel):
    transaction_id: str
    recovery_probability: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    feature_importances: Optional[dict] = None
    model_version: str = "xgb_v1"


# ─── AI Agent Schemas ─────────────────────────────────────

class AgentDecision(BaseModel):
    """Structured output from the AI recovery agent."""
    transaction_id: str
    diagnosis: str
    recovery_probability: float = Field(ge=0, le=1)
    recommended_action: RecoveryAction
    retry_delay_minutes: Optional[int] = 15
    customer_message: Optional[str] = None
    reasoning: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


# ─── Policy Schemas ───────────────────────────────────────

class PolicyResult(BaseModel):
    """Output from the deterministic policy engine."""
    allowed: bool
    decision: PolicyVerdict
    reason: str
    rules_triggered: List[str] = Field(default_factory=list)
    original_action: str
    final_action: Optional[str] = None


# ─── Action Schemas ───────────────────────────────────────

class ActionResult(BaseModel):
    action_id: str
    transaction_id: str
    action: str
    status: ActionStatus
    timestamp: datetime
    amount_recovered: float = 0.0
    details: Optional[dict] = None


# ─── Dashboard Schemas ────────────────────────────────────

class DashboardMetrics(BaseModel):
    total_transactions: int = 0
    revenue_processed: float = 0.0
    failed_transactions: int = 0
    revenue_at_risk: float = 0.0
    revenue_recovered: float = 0.0
    recovery_rate: float = 0.0
    automated_recoveries: int = 0
    human_escalations: int = 0
    policy_blocks: int = 0
    avg_recovery_probability: float = 0.0
    recovery_by_failure_type: dict = Field(default_factory=dict)
    recovery_by_payment_method: dict = Field(default_factory=dict)
    recovery_action_distribution: dict = Field(default_factory=dict)
    recovery_funnel: dict = Field(default_factory=dict)


# ─── Audit Schemas ────────────────────────────────────────

class AuditEntry(BaseModel):
    id: int
    transaction_id: Optional[str] = None
    event_type: str
    details: Optional[str] = None
    amount: Optional[float] = None
    amount_recovered: Optional[float] = None
    ai_recommendation: Optional[str] = None
    ml_probability: Optional[float] = None
    policy_decision: Optional[str] = None
    action: Optional[str] = None
    action_result: Optional[str] = None
    rules_triggered: Optional[list] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── Evaluation Schemas ───────────────────────────────────

class EvaluationResult(BaseModel):
    run_id: str
    total_transactions: int = 0
    failed_transactions: int = 0
    revenue_at_risk: float = 0.0
    eligible_for_recovery: int = 0
    recovery_attempts: int = 0
    successful_recoveries: int = 0
    revenue_recovered: float = 0.0
    recovery_rate: float = 0.0
    avg_recovery_amount: float = 0.0
    automated_action_rate: float = 0.0
    human_escalation_rate: float = 0.0
    policy_block_rate: float = 0.0
    escalations: int = 0
    policy_blocks: int = 0
    baseline_recovered: float = 0.0
    baseline_recovery_rate: float = 0.0
    improvement_pct: float = 0.0

    model_config = {"from_attributes": True}


# ─── Payment Link Schemas ─────────────────────────────────

class PaymentLinkCreate(BaseModel):
    transaction_id: str
    amount: float
    currency: str = "INR"
    description: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None


class PaymentLinkResponse(BaseModel):
    link_id: str
    link_url: str
    short_url: Optional[str] = None
    amount: float
    currency: str = "INR"
    status: str = "created"
    provider: str = "mock"

    model_config = {"from_attributes": True}


# ─── Request Schemas ──────────────────────────────────────

class GenerateRequest(BaseModel):
    count: int = Field(default=1000, ge=1, le=50000)


class BatchRecoveryRequest(BaseModel):
    limit: Optional[int] = None  # None = process all failed


class SimulatePaymentRequest(BaseModel):
    amount: Optional[float] = None
    payment_method: Optional[str] = None
    failure_type: Optional[str] = None


# ─── Transaction Analysis Response ────────────────────────

class TransactionAnalysis(BaseModel):
    transaction: TransactionDetail
    customer: Optional[CustomerDetail] = None
    prediction: Optional[MLPrediction] = None
    agent_decision: Optional[AgentDecision] = None
    policy_result: Optional[PolicyResult] = None
    action_result: Optional[ActionResult] = None
    audit_trail: List[AuditEntry] = Field(default_factory=list)


# ─── ML Metrics ──────────────────────────────────────────

class MLMetrics(BaseModel):
    model_version: str = "xgb_v1"
    roc_auc: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1: Optional[float] = None
    accuracy: Optional[float] = None
    feature_importances: Optional[dict] = None
    confusion_matrix: Optional[list] = None
    train_size: Optional[int] = None
    test_size: Optional[int] = None


# ─── Health ───────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    mode: str = "demo"
    llm_available: bool = False
    razorpay_available: bool = False
    ml_model_loaded: bool = False
    database: str = "connected"
    version: str = "1.0.0"
