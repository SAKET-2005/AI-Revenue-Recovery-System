"""Tests for ML Predictor, Agent reasoning, and Action Executor."""

import pytest
from app.ml.predictor import RecoveryPredictor
from app.agents.recovery_agent import RecoveryAgent
from app.executors.action_executor import ActionExecutor
from app.integrations.payment_provider import MockPaymentProvider
from app.schemas import ActionStatus, RecoveryAction


def test_ml_predictor_inference():
    """Predictor provides valid probability and confidence bounds [0, 1]."""
    predictor = RecoveryPredictor()
    predictor.load()

    features = {
        "amount": 3500.0,
        "payment_method": "upi",
        "failure_code": "temporary_bank_failure",
        "retry_count": 0,
        "device_type": "mobile",
        "checkout_duration": 90.0,
        "cart_value": 3500.0,
        "is_returning_customer": 1,
        "transaction_frequency": 5.0,
        "merchant_category": "ecommerce",
    }

    pred = predictor.predict(features)
    assert "recovery_probability" in pred
    assert 0.0 <= pred["recovery_probability"] <= 1.0
    assert 0.0 <= pred["confidence"] <= 1.0
    assert "feature_importances" in pred


@pytest.mark.asyncio
async def test_agent_deterministic_reasoning():
    """RecoveryAgent produces structured decision with reasoning without LLM API key."""
    agent = RecoveryAgent()
    txn = {
        "transaction_id": "TXN_TEST_01",
        "amount": 4200.0,
        "payment_method": "upi",
        "failure_code": "temporary_bank_failure",
        "failure_reason": "Bank timeout",
        "retry_count": 0,
        "is_returning_customer": True,
    }
    customer = {
        "customer_id": "CUST_TEST_01",
        "previous_transactions": 8,
        "success_rate": 0.88,
        "previous_failures": 1,
        "lifetime_value": 15000.0,
    }
    prediction = {
        "recovery_probability": 0.91,
        "confidence": 0.94,
    }

    decision = await agent.analyze(txn, customer, prediction)
    assert decision.transaction_id == "TXN_TEST_01"
    assert decision.recommended_action == RecoveryAction.RETRY
    assert len(decision.reasoning) >= 3
    assert decision.recovery_probability == 0.91


@pytest.mark.asyncio
async def test_action_executor_mock_retry():
    """ActionExecutor executes retry action and yields valid status."""
    mock_provider = MockPaymentProvider(seed=42)
    executor = ActionExecutor(provider=mock_provider)

    result = await executor.execute(
        transaction_id="TXN_TEST_02",
        action="retry",
        amount=1500.0,
        recovery_probability=1.0,  # Ensure success
    )
    assert result.transaction_id == "TXN_TEST_02"
    assert result.action == "retry"
    assert result.status == ActionStatus.SUCCESS
    assert result.amount_recovered == 1500.0


@pytest.mark.asyncio
async def test_action_executor_payment_link_creation():
    """ActionExecutor creates mock payment link with valid URLs."""
    mock_provider = MockPaymentProvider(seed=42)
    executor = ActionExecutor(provider=mock_provider)

    result = await executor.execute(
        transaction_id="TXN_TEST_03",
        action="payment_link",
        amount=2499.0,
    )
    assert result.action == "payment_link"
    assert result.status == ActionStatus.PENDING
    assert "link_url" in result.details
    assert "plink_" in result.details["link_id"]
