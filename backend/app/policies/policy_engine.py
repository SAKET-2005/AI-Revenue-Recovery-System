"""
Deterministic Policy / Guardrail Engine for ReviveAI.

This engine does NOT use an LLM. All decisions are rule-based.
It enforces financial and operational guardrails on AI recommendations.
"""

from typing import Dict, List, Optional
from app.schemas import PolicyResult, PolicyVerdict, RecoveryAction
from app.config import settings


# Non-retryable failure types — automated retry must NEVER happen
NON_RETRYABLE = {"expired_card", "invalid_details", "risk_decline"}

# Failure types that are safe for automated retry
RETRYABLE = {"temporary_bank_failure", "network_timeout"}


class PolicyEngine:
    """
    Deterministic guardrail engine.

    Evaluates AI recommendations against financial/operational rules
    and returns an ALLOW / BLOCK / ESCALATE / STOP verdict.
    """

    def __init__(
        self,
        max_automated_amount: float = None,
        automated_retry_limit: int = None,
        min_auto_recovery_prob: float = None,
        min_nudge_prob: float = None,
        min_confidence: float = None,
        max_escalation_amount: float = None,
    ):
        self.max_automated_amount = max_automated_amount or settings.max_automated_amount
        self.automated_retry_limit = automated_retry_limit or settings.automated_retry_limit
        self.min_auto_recovery_prob = min_auto_recovery_prob or settings.min_auto_recovery_probability
        self.min_nudge_prob = min_nudge_prob or settings.min_nudge_probability
        self.min_confidence = min_confidence or settings.min_confidence
        self.max_escalation_amount = max_escalation_amount or settings.max_escalation_amount

    def evaluate(
        self,
        requested_action: str,
        amount: float,
        recovery_probability: float,
        confidence: float,
        failure_code: Optional[str] = None,
        retry_count: int = 0,
    ) -> PolicyResult:
        """
        Evaluate a requested action against all policy rules.

        Returns PolicyResult with verdict and triggered rules.
        """
        rules_triggered: List[str] = []
        reasons: List[str] = []

        # ── Rule 1: Low confidence → HUMAN_REVIEW ──────────────
        if confidence < self.min_confidence:
            rules_triggered.append("LOW_CONFIDENCE")
            reasons.append(
                f"Confidence {confidence:.0%} is below minimum threshold {self.min_confidence:.0%}"
            )
            return PolicyResult(
                allowed=False,
                decision=PolicyVerdict.ESCALATE,
                reason="; ".join(reasons),
                rules_triggered=rules_triggered,
                original_action=requested_action,
                final_action="human_review",
            )

        # ── Rule 2: Very high amount → always ESCALATE ─────────
        if amount > self.max_escalation_amount:
            rules_triggered.append("HIGH_VALUE_ESCALATION")
            reasons.append(
                f"Amount ₹{amount:,.0f} exceeds escalation threshold ₹{self.max_escalation_amount:,.0f}"
            )
            return PolicyResult(
                allowed=False,
                decision=PolicyVerdict.ESCALATE,
                reason="; ".join(reasons),
                rules_triggered=rules_triggered,
                original_action=requested_action,
                final_action="human_review",
            )

        # ── Rule 3: Expired card → NEVER retry ─────────────────
        if failure_code in NON_RETRYABLE and requested_action == RecoveryAction.RETRY.value:
            rules_triggered.append("NON_RETRYABLE_FAILURE")
            reasons.append(
                f"Failure type '{failure_code}' cannot be automatically retried"
            )
            return PolicyResult(
                allowed=False,
                decision=PolicyVerdict.BLOCK,
                reason="; ".join(reasons),
                rules_triggered=rules_triggered,
                original_action=requested_action,
                final_action="customer_nudge" if recovery_probability >= self.min_nudge_prob else "stop",
            )

        # ── Rule 4: Retry limit reached → STOP retrying ────────
        if requested_action == RecoveryAction.RETRY.value and retry_count >= self.automated_retry_limit:
            rules_triggered.append("RETRY_LIMIT_REACHED")
            reasons.append(
                f"Retry count {retry_count} has reached limit of {self.automated_retry_limit}"
            )
            return PolicyResult(
                allowed=False,
                decision=PolicyVerdict.STOP,
                reason="; ".join(reasons),
                rules_triggered=rules_triggered,
                original_action=requested_action,
                final_action="stop",
            )

        # ── Evaluate specific action type ──────────────────────

        if requested_action == RecoveryAction.RETRY.value:
            return self._evaluate_retry(
                amount, recovery_probability, confidence,
                failure_code, retry_count, rules_triggered, reasons
            )
        elif requested_action in (RecoveryAction.CUSTOMER_NUDGE.value, RecoveryAction.PAYMENT_LINK.value):
            return self._evaluate_nudge(
                requested_action, amount, recovery_probability,
                confidence, rules_triggered, reasons
            )
        elif requested_action == RecoveryAction.HUMAN_REVIEW.value:
            rules_triggered.append("HUMAN_REVIEW_REQUESTED")
            reasons.append("Action is human review — always allowed")
            return PolicyResult(
                allowed=True,
                decision=PolicyVerdict.ALLOW,
                reason="; ".join(reasons),
                rules_triggered=rules_triggered,
                original_action=requested_action,
                final_action="human_review",
            )
        elif requested_action == RecoveryAction.STOP.value:
            rules_triggered.append("STOP_REQUESTED")
            reasons.append("Stop action — always allowed")
            return PolicyResult(
                allowed=True,
                decision=PolicyVerdict.ALLOW,
                reason="; ".join(reasons),
                rules_triggered=rules_triggered,
                original_action=requested_action,
                final_action="stop",
            )

        # Unknown action
        rules_triggered.append("UNKNOWN_ACTION")
        reasons.append(f"Unknown action '{requested_action}'")
        return PolicyResult(
            allowed=False,
            decision=PolicyVerdict.BLOCK,
            reason="; ".join(reasons),
            rules_triggered=rules_triggered,
            original_action=requested_action,
            final_action="human_review",
        )

    def _evaluate_retry(
        self, amount, recovery_probability, confidence,
        failure_code, retry_count, rules_triggered, reasons
    ) -> PolicyResult:
        """Evaluate automated retry action."""
        passed = True

        # Check amount limit
        if amount > self.max_automated_amount:
            rules_triggered.append("AMOUNT_EXCEEDS_AUTO_LIMIT")
            reasons.append(
                f"Amount ₹{amount:,.0f} exceeds automated limit ₹{self.max_automated_amount:,.0f}"
            )
            passed = False

        # Check recovery probability
        if recovery_probability < self.min_auto_recovery_prob:
            rules_triggered.append("LOW_RECOVERY_PROBABILITY")
            reasons.append(
                f"Recovery probability {recovery_probability:.0%} below threshold {self.min_auto_recovery_prob:.0%}"
            )
            passed = False

        # Check failure type is retryable
        if failure_code and failure_code not in RETRYABLE and failure_code not in ("insufficient_funds", "authentication_failure", "unknown"):
            rules_triggered.append("FAILURE_NOT_RETRYABLE")
            reasons.append(f"Failure type '{failure_code}' is not in retryable category")
            passed = False

        if passed:
            rules_triggered.extend([
                "AMOUNT_CHECK_PASSED",
                "PROBABILITY_CHECK_PASSED",
                "RETRY_LIMIT_CHECK_PASSED",
                "FAILURE_TYPE_CHECK_PASSED",
            ])
            reasons.append("All automated retry checks passed")
            return PolicyResult(
                allowed=True,
                decision=PolicyVerdict.ALLOW,
                reason="; ".join(reasons),
                rules_triggered=rules_triggered,
                original_action="retry",
                final_action="retry",
            )
        else:
            # Downgrade to escalation
            return PolicyResult(
                allowed=False,
                decision=PolicyVerdict.ESCALATE,
                reason="; ".join(reasons),
                rules_triggered=rules_triggered,
                original_action="retry",
                final_action="human_review",
            )

    def _evaluate_nudge(
        self, requested_action, amount, recovery_probability,
        confidence, rules_triggered, reasons
    ) -> PolicyResult:
        """Evaluate customer nudge or payment link action."""
        if recovery_probability >= self.min_nudge_prob:
            rules_triggered.append("NUDGE_PROBABILITY_CHECK_PASSED")
            reasons.append(
                f"Recovery probability {recovery_probability:.0%} meets nudge threshold {self.min_nudge_prob:.0%}"
            )
            return PolicyResult(
                allowed=True,
                decision=PolicyVerdict.ALLOW,
                reason="; ".join(reasons),
                rules_triggered=rules_triggered,
                original_action=requested_action,
                final_action=requested_action,
            )
        else:
            rules_triggered.append("NUDGE_PROBABILITY_TOO_LOW")
            reasons.append(
                f"Recovery probability {recovery_probability:.0%} below nudge threshold {self.min_nudge_prob:.0%}"
            )
            return PolicyResult(
                allowed=False,
                decision=PolicyVerdict.STOP,
                reason="; ".join(reasons),
                rules_triggered=rules_triggered,
                original_action=requested_action,
                final_action="stop",
            )


# Singleton
policy_engine = PolicyEngine()
