"""Tests for Policy Engine deterministic guardrails."""

import pytest
from app.policies.policy_engine import PolicyEngine
from app.schemas import PolicyVerdict, RecoveryAction


@pytest.fixture
def policy():
    return PolicyEngine(
        max_automated_amount=10000.0,
        automated_retry_limit=2,
        min_auto_recovery_prob=0.80,
        min_nudge_prob=0.55,
        min_confidence=0.60,
        max_escalation_amount=50000.0,
    )


def test_high_value_transaction_is_escalated(policy):
    """Transactions exceeding MAX_ESCALATION_AMOUNT (>₹50,000) must always escalate."""
    result = policy.evaluate(
        requested_action="retry",
        amount=65000.0,
        recovery_probability=0.95,
        confidence=0.92,
        failure_code="temporary_bank_failure",
        retry_count=0,
    )
    assert result.decision == PolicyVerdict.ESCALATE
    assert result.allowed is False
    assert "HIGH_VALUE_ESCALATION" in result.rules_triggered
    assert result.final_action == "human_review"


def test_expired_card_is_not_retried(policy):
    """Expired card failure must NEVER be automatically retried."""
    result = policy.evaluate(
        requested_action="retry",
        amount=2500.0,
        recovery_probability=0.70,
        confidence=0.85,
        failure_code="expired_card",
        retry_count=0,
    )
    assert result.decision == PolicyVerdict.BLOCK
    assert result.allowed is False
    assert "NON_RETRYABLE_FAILURE" in result.rules_triggered
    assert result.final_action == "customer_nudge"  # Downgrades to nudge since prob >= 0.55


def test_retry_limit_is_enforced(policy):
    """When retry count >= limit (2), retry requests must STOP."""
    result = policy.evaluate(
        requested_action="retry",
        amount=1500.0,
        recovery_probability=0.90,
        confidence=0.90,
        failure_code="temporary_bank_failure",
        retry_count=2,
    )
    assert result.decision == PolicyVerdict.STOP
    assert result.allowed is False
    assert "RETRY_LIMIT_REACHED" in result.rules_triggered
    assert result.final_action == "stop"


def test_low_confidence_is_escalated(policy):
    """Low AI/ML confidence (<0.60) must escalate to human review."""
    result = policy.evaluate(
        requested_action="retry",
        amount=1200.0,
        recovery_probability=0.85,
        confidence=0.52,
        failure_code="temporary_bank_failure",
        retry_count=0,
    )
    assert result.decision == PolicyVerdict.ESCALATE
    assert result.allowed is False
    assert "LOW_CONFIDENCE" in result.rules_triggered
    assert result.final_action == "human_review"


def test_valid_retry_is_allowed(policy):
    """Valid conditions (high prob, reasonable amount, retryable failure) ALLOW auto-retry."""
    result = policy.evaluate(
        requested_action="retry",
        amount=4500.0,
        recovery_probability=0.91,
        confidence=0.94,
        failure_code="temporary_bank_failure",
        retry_count=0,
    )
    assert result.decision == PolicyVerdict.ALLOW
    assert result.allowed is True
    assert "AMOUNT_CHECK_PASSED" in result.rules_triggered
    assert "PROBABILITY_CHECK_PASSED" in result.rules_triggered
    assert result.final_action == "retry"


def test_payment_link_allowed_within_probability_band(policy):
    """Payment link action with recovery probability between 55% and 80% is ALLOWED."""
    result = policy.evaluate(
        requested_action="payment_link",
        amount=8500.0,
        recovery_probability=0.68,
        confidence=0.75,
        failure_code="insufficient_funds",
        retry_count=0,
    )
    assert result.decision == PolicyVerdict.ALLOW
    assert result.allowed is True
    assert "NUDGE_PROBABILITY_CHECK_PASSED" in result.rules_triggered
    assert result.final_action == "payment_link"


def test_insufficient_funds_never_retried(policy):
    """insufficient_funds requested with retry MUST be blocked from retry and routed to payment_link."""
    result = policy.evaluate(
        requested_action="retry",
        amount=3500.0,
        recovery_probability=0.85,
        confidence=0.90,
        failure_code="insufficient_funds",
        retry_count=0,
    )
    assert result.decision == PolicyVerdict.BLOCK
    assert result.allowed is False
    assert "NON_RETRYABLE_FAILURE" in result.rules_triggered
    assert result.final_action == "payment_link"


def test_authentication_failure_never_retried(policy):
    """authentication_failure requested with retry MUST be blocked from retry and routed to customer_nudge."""
    result = policy.evaluate(
        requested_action="retry",
        amount=2200.0,
        recovery_probability=0.82,
        confidence=0.88,
        failure_code="authentication_failure",
        retry_count=0,
    )
    assert result.decision == PolicyVerdict.BLOCK
    assert result.allowed is False
    assert "NON_RETRYABLE_FAILURE" in result.rules_triggered
    assert result.final_action == "customer_nudge"


def test_risk_decline_routed_to_human_review(policy):
    """risk_decline requested with retry MUST be blocked from retry and routed to human_review."""
    result = policy.evaluate(
        requested_action="retry",
        amount=4000.0,
        recovery_probability=0.75,
        confidence=0.80,
        failure_code="risk_decline",
        retry_count=0,
    )
    assert result.decision == PolicyVerdict.BLOCK
    assert result.allowed is False
    assert "NON_RETRYABLE_FAILURE" in result.rules_triggered
    assert result.final_action == "human_review"


def test_low_recovery_probability_stops(policy):
    """Recovery probability below min_nudge_prob (<0.55) must trigger STOP."""
    result = policy.evaluate(
        requested_action="retry",
        amount=1500.0,
        recovery_probability=0.35,
        confidence=0.80,
        failure_code="temporary_bank_failure",
        retry_count=0,
    )
    assert result.decision == PolicyVerdict.STOP
    assert result.allowed is False
    assert "LOW_RECOVERY_PROBABILITY" in result.rules_triggered
    assert result.final_action == "stop"


def test_retry_amount_exceeding_auto_limit_is_escalated(policy):
    """Retry for amount above max_automated_amount (₹10,000) but below max_escalation (₹50,000) must ESCALATE."""
    result = policy.evaluate(
        requested_action="retry",
        amount=25000.0,
        recovery_probability=0.92,
        confidence=0.90,
        failure_code="temporary_bank_failure",
        retry_count=0,
    )
    assert result.decision == PolicyVerdict.ESCALATE
    assert result.allowed is False
    assert "AMOUNT_EXCEEDS_AUTO_LIMIT" in result.rules_triggered
    assert result.final_action == "human_review"

