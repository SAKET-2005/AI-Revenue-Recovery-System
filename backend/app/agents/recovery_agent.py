"""
Revenue Recovery AI Agent.

Produces structured recovery decisions using either:
1. LLM-based reasoning (when API key is available)
2. Deterministic fallback (always works)

The agent RECOMMENDS actions — it does NOT execute them.
Execution requires approval from the PolicyEngine.
"""

import json
from typing import Dict, Optional
from app.schemas import AgentDecision, RecoveryAction
from app.config import settings


# ─── Deterministic Recovery Rules ─────────────────────────

FAILURE_ACTION_MAP = {
    "temporary_bank_failure": RecoveryAction.RETRY,
    "network_timeout": RecoveryAction.RETRY,
    "authentication_failure": RecoveryAction.CUSTOMER_NUDGE,
    "insufficient_funds": RecoveryAction.PAYMENT_LINK,
    "expired_card": RecoveryAction.CUSTOMER_NUDGE,
    "risk_decline": RecoveryAction.HUMAN_REVIEW,
    "invalid_details": RecoveryAction.CUSTOMER_NUDGE,
    "unknown": RecoveryAction.HUMAN_REVIEW,
}

FAILURE_DIAGNOSIS = {
    "temporary_bank_failure": "Transient banking infrastructure failure — bank server temporarily unavailable",
    "network_timeout": "Network connectivity interruption during payment processing",
    "authentication_failure": "Customer authentication step failed — may need re-verification",
    "insufficient_funds": "Customer account balance insufficient for this transaction amount",
    "expired_card": "Payment card has expired and requires customer to update payment method",
    "risk_decline": "Transaction flagged by payment risk engine — needs manual review",
    "invalid_details": "Payment details entered incorrectly — customer needs to correct information",
    "unknown": "Unclassified failure — insufficient data for automated diagnosis",
}

CUSTOMER_MESSAGES = {
    "retry": None,  # No customer contact for automated retry
    "customer_nudge": "Hi! Your recent payment of ₹{amount:,.0f} didn't go through. This can happen due to temporary issues. Would you like to try again? Your order is saved and ready.",
    "payment_link": "Hi! We noticed your payment of ₹{amount:,.0f} couldn't be completed. We've created a secure payment link for you to complete your purchase easily. The link is valid for 24 hours.",
    "human_review": None,
    "stop": None,
}


class RecoveryAgent:
    """AI Recovery Agent — recommends recovery actions."""

    def __init__(self):
        self._llm_available = False
        self._llm_client = None
        self._init_llm()

    def _init_llm(self):
        """Try to initialize LLM client."""
        if not settings.has_llm:
            print("[Agent] No LLM API key configured — using deterministic fallback")
            return

        try:
            from openai import OpenAI
            self._llm_client = OpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
            )
            self._llm_available = True
            print(f"[Agent] LLM initialized: {settings.llm_model}")
        except Exception as e:
            print(f"[Agent] LLM init failed: {e} — using deterministic fallback")

    async def analyze(
        self,
        transaction: Dict,
        customer: Dict,
        prediction: Dict,
    ) -> AgentDecision:
        """
        Analyze a failed transaction and recommend a recovery action.

        Always returns a valid AgentDecision — falls back to deterministic
        rules if LLM is unavailable or returns bad output.
        """
        if self._llm_available:
            try:
                decision = await self._llm_analyze(transaction, customer, prediction)
                if decision:
                    return decision
            except Exception as e:
                print(f"[Agent] LLM analysis failed: {e} — falling back")

        # Deterministic fallback
        return self._deterministic_analyze(transaction, customer, prediction)

    async def _llm_analyze(
        self, transaction: Dict, customer: Dict, prediction: Dict
    ) -> Optional[AgentDecision]:
        """Use LLM for reasoning. Returns None if invalid."""
        prompt = self._build_prompt(transaction, customer, prediction)

        try:
            import asyncio
            response = await asyncio.to_thread(
                self._llm_client.chat.completions.create,
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            data = json.loads(content)

            # Validate with Pydantic
            decision = AgentDecision(
                transaction_id=transaction["transaction_id"],
                diagnosis=data.get("diagnosis", ""),
                recovery_probability=prediction.get("recovery_probability", 0.5),
                recommended_action=data.get("recommended_action", "human_review"),
                retry_delay_minutes=data.get("retry_delay_minutes", 15),
                customer_message=data.get("customer_message"),
                reasoning=data.get("reasoning", []),
                confidence=prediction.get("confidence", 0.5),
            )
            return decision
        except Exception as e:
            print(f"[Agent] LLM parse error: {e}")
            # Retry once
            try:
                import asyncio
                response = await asyncio.to_thread(
                    self._llm_client.chat.completions.create,
                    model=settings.llm_model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt + "\n\nPrevious response was invalid JSON. Please return ONLY valid JSON."},
                    ],
                    temperature=0.0,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content
                data = json.loads(content)
                return AgentDecision(
                    transaction_id=transaction["transaction_id"],
                    diagnosis=data.get("diagnosis", ""),
                    recovery_probability=prediction.get("recovery_probability", 0.5),
                    recommended_action=data.get("recommended_action", "human_review"),
                    retry_delay_minutes=data.get("retry_delay_minutes", 15),
                    customer_message=data.get("customer_message"),
                    reasoning=data.get("reasoning", []),
                    confidence=prediction.get("confidence", 0.5),
                )
            except Exception:
                return None

    def _deterministic_analyze(
        self, transaction: Dict, customer: Dict, prediction: Dict
    ) -> AgentDecision:
        """Rule-based fallback — always produces a valid decision."""
        failure_code = transaction.get("failure_code", "unknown")
        amount = transaction.get("amount", 0)
        retry_count = transaction.get("retry_count", 0)
        recovery_prob = prediction.get("recovery_probability", 0.5)
        confidence = prediction.get("confidence", 0.5)

        # Determine action based on failure type
        base_action = FAILURE_ACTION_MAP.get(failure_code, RecoveryAction.HUMAN_REVIEW)

        # Override logic based on context
        if recovery_prob >= 0.80 and base_action == RecoveryAction.RETRY and retry_count < 2:
            action = RecoveryAction.RETRY
        elif recovery_prob >= 0.55 and base_action in (RecoveryAction.CUSTOMER_NUDGE, RecoveryAction.PAYMENT_LINK):
            action = base_action
        elif recovery_prob < 0.30:
            action = RecoveryAction.STOP
        elif amount > 50000:
            action = RecoveryAction.HUMAN_REVIEW
        elif confidence < 0.60:
            action = RecoveryAction.HUMAN_REVIEW
        elif retry_count >= 2:
            if recovery_prob >= 0.55:
                action = RecoveryAction.PAYMENT_LINK
            else:
                action = RecoveryAction.STOP
        else:
            action = base_action

        # Build reasoning
        reasoning = self._build_reasoning(
            transaction, customer, prediction, failure_code, action
        )

        # Customer message
        msg_template = CUSTOMER_MESSAGES.get(action.value)
        customer_message = None
        if msg_template:
            customer_message = msg_template.format(amount=amount)

        diagnosis = FAILURE_DIAGNOSIS.get(failure_code, "Unclassified failure")

        return AgentDecision(
            transaction_id=transaction.get("transaction_id", ""),
            diagnosis=diagnosis,
            recovery_probability=recovery_prob,
            recommended_action=action,
            retry_delay_minutes=15 if action == RecoveryAction.RETRY else None,
            customer_message=customer_message,
            reasoning=reasoning,
            confidence=confidence,
        )

    def _build_reasoning(
        self, transaction, customer, prediction, failure_code, action
    ) -> list:
        """Build human-readable reasoning list."""
        reasons = []
        recovery_prob = prediction.get("recovery_probability", 0.5)
        amount = transaction.get("amount", 0)
        retry_count = transaction.get("retry_count", 0)

        # Failure type analysis
        if failure_code in ("temporary_bank_failure", "network_timeout"):
            reasons.append("Failure type is historically transient and recoverable")
        elif failure_code == "insufficient_funds":
            reasons.append("Insufficient funds — retry unlikely to succeed immediately")
        elif failure_code == "expired_card":
            reasons.append("Expired card — customer must update payment method")
        elif failure_code == "authentication_failure":
            reasons.append("Authentication failed — customer re-verification needed")
        elif failure_code == "risk_decline":
            reasons.append("Risk engine declined — requires manual review")
        else:
            reasons.append(f"Failure classified as '{failure_code}'")

        # Customer history
        prev_txns = customer.get("previous_transactions", 0)
        success_rate = customer.get("success_rate", 0)
        if prev_txns > 5:
            reasons.append(f"Customer has {prev_txns} previous transactions")
        if success_rate > 0.80:
            reasons.append(f"Customer historical success rate is {success_rate:.0%}")

        if transaction.get("is_returning_customer"):
            reasons.append("Customer is a returning user")

        # Recovery probability
        reasons.append(f"ML recovery probability is {recovery_prob:.0%}")

        # Amount
        if amount <= 10000:
            reasons.append(f"Transaction amount ₹{amount:,.0f} is within automated threshold")
        elif amount > 50000:
            reasons.append(f"Transaction amount ₹{amount:,.0f} exceeds automated threshold — requires review")
        else:
            reasons.append(f"Transaction amount ₹{amount:,.0f} is moderate")

        # Retry count
        if retry_count == 0:
            reasons.append("No previous retry has been attempted")
        else:
            reasons.append(f"{retry_count} previous retry attempt(s) recorded")

        return reasons

    def _build_prompt(self, transaction, customer, prediction) -> str:
        """Build LLM prompt with structured context."""
        return f"""Analyze this failed payment transaction and recommend a recovery action.

TRANSACTION:
- ID: {transaction.get('transaction_id')}
- Amount: ₹{transaction.get('amount', 0):,.2f}
- Payment Method: {transaction.get('payment_method')}
- Failure Code: {transaction.get('failure_code')}
- Failure Reason: {transaction.get('failure_reason')}
- Retry Count: {transaction.get('retry_count', 0)}
- Device: {transaction.get('device_type')}
- Returning Customer: {transaction.get('is_returning_customer')}

CUSTOMER:
- Previous Transactions: {customer.get('previous_transactions', 0)}
- Success Rate: {customer.get('success_rate', 0):.1%}
- Previous Failures: {customer.get('previous_failures', 0)}
- Lifetime Value: ₹{customer.get('lifetime_value', 0):,.2f}

ML PREDICTION:
- Recovery Probability: {prediction.get('recovery_probability', 0):.1%}
- Confidence: {prediction.get('confidence', 0):.1%}

Return your analysis as JSON with these fields:
- diagnosis: brief diagnosis of the failure
- recommended_action: one of "retry", "customer_nudge", "payment_link", "human_review", "stop"
- retry_delay_minutes: if retry, suggested delay in minutes
- customer_message: message to send to customer if applicable
- reasoning: list of concise reason strings explaining your recommendation
"""


SYSTEM_PROMPT = """You are a payment recovery specialist AI. You analyze failed payment transactions and recommend recovery actions.

You must return ONLY valid JSON with these fields:
- diagnosis (string): Brief diagnosis of the failure
- recommended_action (string): One of "retry", "customer_nudge", "payment_link", "human_review", "stop"
- retry_delay_minutes (integer or null): Suggested delay if action is retry
- customer_message (string or null): Customer-facing message if applicable
- reasoning (array of strings): List of concise reasons for your recommendation

Rules:
- Temporary bank failures and network timeouts are often recoverable via retry
- Insufficient funds benefit from payment links or nudges
- Expired cards should NEVER be retried — suggest nudge to update payment method
- Risk declines need human review
- High-value transactions (>₹50,000) should be escalated
- Consider customer history and ML recovery probability
- Be conservative — when in doubt, escalate"""


# Singleton
recovery_agent = RecoveryAgent()
