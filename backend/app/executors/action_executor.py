"""
Action Executor for ReviveAI.

Executes approved recovery actions through the payment provider.
Only executes actions that have been APPROVED by the PolicyEngine.
"""

import uuid
from datetime import datetime
from typing import Dict, Optional
from app.integrations.payment_provider import PaymentProvider, get_payment_provider
from app.schemas import ActionResult, ActionStatus


class ActionExecutor:
    """Executes approved recovery actions."""

    def __init__(self, provider: Optional[PaymentProvider] = None):
        self.provider = provider or get_payment_provider()

    async def execute(
        self,
        transaction_id: str,
        action: str,
        amount: float,
        recovery_probability: float = 0.5,
        customer_message: Optional[str] = None,
        **kwargs
    ) -> ActionResult:
        """
        Execute a recovery action.

        This should ONLY be called after PolicyEngine approves.
        """
        action_id = f"ACT_{uuid.uuid4().hex[:12].upper()}"
        timestamp = datetime.now()

        try:
            if action == "retry":
                return await self._retry_payment(
                    action_id, transaction_id, amount,
                    recovery_probability, timestamp, **kwargs
                )
            elif action == "customer_nudge":
                return await self._send_nudge(
                    action_id, transaction_id, amount,
                    customer_message, timestamp, **kwargs
                )
            elif action == "payment_link":
                return await self._create_payment_link(
                    action_id, transaction_id, amount,
                    timestamp, **kwargs
                )
            elif action == "human_review":
                return self._escalate(action_id, transaction_id, amount, timestamp)
            elif action == "stop":
                return self._stop(action_id, transaction_id, amount, timestamp)
            else:
                return ActionResult(
                    action_id=action_id,
                    transaction_id=transaction_id,
                    action=action,
                    status=ActionStatus.FAILED,
                    timestamp=timestamp,
                    details={"error": f"Unknown action: {action}"},
                )
        except Exception as e:
            return ActionResult(
                action_id=action_id,
                transaction_id=transaction_id,
                action=action,
                status=ActionStatus.FAILED,
                timestamp=timestamp,
                details={"error": str(e)},
            )

    async def _retry_payment(
        self, action_id, transaction_id, amount,
        recovery_probability, timestamp, **kwargs
    ) -> ActionResult:
        """Execute payment retry through provider."""
        result = await self.provider.retry_payment(
            transaction_id, amount,
            recovery_probability=recovery_probability,
            **kwargs
        )

        success = result.get("status") == "success"
        return ActionResult(
            action_id=action_id,
            transaction_id=transaction_id,
            action="retry",
            status=ActionStatus.SUCCESS if success else ActionStatus.FAILED,
            timestamp=timestamp,
            amount_recovered=amount if success else 0.0,
            details=result,
        )

    async def _send_nudge(
        self, action_id, transaction_id, amount,
        customer_message, timestamp, **kwargs
    ) -> ActionResult:
        """Send customer nudge (simulated in demo)."""
        return ActionResult(
            action_id=action_id,
            transaction_id=transaction_id,
            action="customer_nudge",
            status=ActionStatus.SUCCESS,
            timestamp=timestamp,
            amount_recovered=0.0,  # Nudge doesn't directly recover
            details={
                "message_sent": True,
                "channel": "sms_email",
                "message": customer_message or "Payment reminder sent",
                "provider": self.provider.get_provider_name(),
            },
        )

    async def _create_payment_link(
        self, action_id, transaction_id, amount,
        timestamp, **kwargs
    ) -> ActionResult:
        """Create a payment link for recovery."""
        link_result = await self.provider.create_payment_link(
            amount=amount,
            description=f"Recovery payment for {transaction_id}",
            **kwargs
        )

        return ActionResult(
            action_id=action_id,
            transaction_id=transaction_id,
            action="payment_link",
            status=ActionStatus.PENDING,
            timestamp=timestamp,
            amount_recovered=0.0,  # Pending until customer pays
            details=link_result,
        )

    def _escalate(self, action_id, transaction_id, amount, timestamp) -> ActionResult:
        """Escalate to human review."""
        return ActionResult(
            action_id=action_id,
            transaction_id=transaction_id,
            action="human_review",
            status=ActionStatus.PENDING,
            timestamp=timestamp,
            amount_recovered=0.0,
            details={
                "escalated": True,
                "queue": "finance_review",
                "priority": "high" if amount > 50000 else "medium",
            },
        )

    def _stop(self, action_id, transaction_id, amount, timestamp) -> ActionResult:
        """Stop recovery — no further action."""
        return ActionResult(
            action_id=action_id,
            transaction_id=transaction_id,
            action="stop",
            status=ActionStatus.SKIPPED,
            timestamp=timestamp,
            amount_recovered=0.0,
            details={"reason": "Recovery stopped by policy or agent decision"},
        )


# Singleton
action_executor = ActionExecutor()
