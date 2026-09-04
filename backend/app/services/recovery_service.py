"""
Core recovery service — orchestrates the full recovery pipeline.

FAILED PAYMENT → RISK DETECTION → ML PREDICTION → AI DIAGNOSIS
→ POLICY CHECK → ACTION EXECUTION → OUTCOME TRACKING → AUDIT
"""

import uuid
from datetime import datetime
from typing import Dict, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, and_

from app.models.transaction import Transaction, Customer
from app.models.recovery import (
    ModelPrediction, RecoveryDecision, RecoveryAction as RecoveryActionModel,
    PaymentLink, EvaluationRun, PolicyDecision as PolicyDecisionModel,
)
from app.models.audit import AuditLog
from app.ml.predictor import predictor
from app.agents.recovery_agent import recovery_agent
from app.policies.policy_engine import policy_engine
from app.executors.action_executor import action_executor
from app.schemas import (
    TransactionDetail, CustomerDetail, MLPrediction, AgentDecision,
    PolicyResult, ActionResult, AuditEntry, DashboardMetrics,
    EvaluationResult, TransactionAnalysis,
)


class RecoveryService:
    """Orchestrates the full recovery pipeline."""

    async def analyze_transaction(
        self, transaction_id: str, db: AsyncSession
    ) -> TransactionAnalysis:
        """Run full analysis pipeline on a transaction."""
        # 1. Fetch transaction
        result = await db.execute(
            select(Transaction).where(Transaction.transaction_id == transaction_id)
        )
        txn = result.scalar_one_or_none()
        if not txn:
            raise ValueError(f"Transaction {transaction_id} not found")

        txn_detail = TransactionDetail.model_validate(txn)
        txn_dict = {
            "transaction_id": txn.transaction_id,
            "amount": txn.amount,
            "payment_method": txn.payment_method,
            "payment_status": txn.payment_status,
            "failure_code": txn.failure_code,
            "failure_reason": txn.failure_reason,
            "retry_count": txn.retry_count,
            "device_type": txn.device_type,
            "is_returning_customer": txn.is_returning_customer,
            "checkout_duration": txn.checkout_duration,
            "cart_value": txn.cart_value,
            "transaction_frequency": txn.transaction_frequency,
            "merchant_category": txn.merchant_category,
        }

        # 2. Fetch customer
        cust_result = await db.execute(
            select(Customer).where(Customer.customer_id == txn.customer_id)
        )
        cust = cust_result.scalar_one_or_none()
        cust_detail = CustomerDetail.model_validate(cust) if cust else None
        cust_dict = {
            "customer_id": txn.customer_id,
            "previous_transactions": cust.previous_transactions if cust else 0,
            "success_rate": cust.success_rate if cust else 0,
            "previous_failures": cust.previous_failures if cust else 0,
            "lifetime_value": cust.lifetime_value if cust else 0,
        }

        # 3. Log risk detection
        await self._log_audit(db, txn.transaction_id, "REVENUE_AT_RISK",
                              f"Failed payment detected: ₹{txn.amount:,.0f}", txn.amount)

        # 4. ML Prediction
        ml_features = {
            "amount": txn.amount,
            "payment_method": txn.payment_method,
            "failure_code": txn.failure_code or "unknown",
            "retry_count": txn.retry_count,
            "device_type": txn.device_type or "mobile",
            "checkout_duration": txn.checkout_duration or 120,
            "cart_value": txn.cart_value or txn.amount,
            "is_returning_customer": int(txn.is_returning_customer),
            "transaction_frequency": txn.transaction_frequency or 2.0,
            "merchant_category": txn.merchant_category or "ecommerce",
        }
        prediction_dict = predictor.predict(ml_features)
        ml_pred = MLPrediction(transaction_id=transaction_id, **prediction_dict)

        # Save prediction
        db.add(ModelPrediction(
            transaction_id=transaction_id,
            recovery_probability=ml_pred.recovery_probability,
            confidence=ml_pred.confidence,
            feature_importances=ml_pred.feature_importances,
            model_version=ml_pred.model_version,
        ))

        await self._log_audit(db, transaction_id, "ML_PREDICTION",
                              f"Recovery probability: {ml_pred.recovery_probability:.0%}",
                              ml_probability=ml_pred.recovery_probability)

        # 5. AI Agent Decision
        agent_decision = await recovery_agent.analyze(txn_dict, cust_dict, prediction_dict)

        await self._log_audit(db, transaction_id, "AI_DECISION",
                              f"Recommended: {agent_decision.recommended_action.value}",
                              ai_recommendation=agent_decision.recommended_action.value)

        # 6. Policy Check
        policy_result = policy_engine.evaluate(
            requested_action=agent_decision.recommended_action.value,
            amount=txn.amount,
            recovery_probability=ml_pred.recovery_probability,
            confidence=ml_pred.confidence,
            failure_code=txn.failure_code,
            retry_count=txn.retry_count,
        )

        # Save policy decision
        db.add(PolicyDecisionModel(
            transaction_id=transaction_id,
            requested_action=agent_decision.recommended_action.value,
            decision=policy_result.decision.value,
            reason=policy_result.reason,
            rules_triggered=policy_result.rules_triggered,
            amount=txn.amount,
            recovery_probability=ml_pred.recovery_probability,
            confidence=ml_pred.confidence,
        ))

        await self._log_audit(db, transaction_id, "POLICY_CHECK",
                              f"{policy_result.decision.value}: {policy_result.reason}",
                              policy_decision=policy_result.decision.value,
                              rules_triggered=policy_result.rules_triggered)

        # Save recovery decision
        db.add(RecoveryDecision(
            transaction_id=transaction_id,
            diagnosis=agent_decision.diagnosis,
            recommended_action=agent_decision.recommended_action.value,
            reasoning=agent_decision.reasoning,
            ai_confidence=agent_decision.confidence,
            retry_delay_minutes=agent_decision.retry_delay_minutes,
            customer_message=agent_decision.customer_message,
            policy_decision=policy_result.decision.value,
            policy_reason=policy_result.reason,
            rules_triggered=policy_result.rules_triggered,
            final_action=policy_result.final_action,
        ))

        await db.flush()

        # Fetch audit trail
        audit_trail = await self._get_audit_trail(db, transaction_id)

        return TransactionAnalysis(
            transaction=txn_detail,
            customer=cust_detail,
            prediction=ml_pred,
            agent_decision=agent_decision,
            policy_result=policy_result,
            audit_trail=audit_trail,
        )

    async def execute_recovery(
        self, transaction_id: str, db: AsyncSession
    ) -> ActionResult:
        """Execute recovery for an analyzed transaction."""
        # Get latest recovery decision
        result = await db.execute(
            select(RecoveryDecision)
            .where(RecoveryDecision.transaction_id == transaction_id)
            .order_by(RecoveryDecision.id.desc())
        )
        decision = result.scalar_one_or_none()
        if not decision:
            raise ValueError(f"No recovery decision found for {transaction_id}. Run analysis first.")

        # Get transaction
        txn_result = await db.execute(
            select(Transaction).where(Transaction.transaction_id == transaction_id)
        )
        txn = txn_result.scalar_one_or_none()
        if not txn:
            raise ValueError(f"Transaction {transaction_id} not found")

        final_action = decision.final_action or decision.recommended_action

        # Execute action
        action_result = await action_executor.execute(
            transaction_id=transaction_id,
            action=final_action,
            amount=txn.amount,
            recovery_probability=decision.ai_confidence or 0.5,
            customer_message=decision.customer_message,
            payment_method=txn.payment_method,
        )

        # Save action result
        db.add(RecoveryActionModel(
            action_id=action_result.action_id,
            transaction_id=transaction_id,
            action_type=action_result.action,
            status=action_result.status.value,
            amount_recovered=action_result.amount_recovered,
            execution_details=action_result.details,
        ))

        # Update transaction status if recovered
        if action_result.status.value == "success" and action_result.amount_recovered > 0:
            await db.execute(
                update(Transaction)
                .where(Transaction.transaction_id == transaction_id)
                .values(payment_status="recovered")
            )

        # Update retry count
        if final_action == "retry":
            await db.execute(
                update(Transaction)
                .where(Transaction.transaction_id == transaction_id)
                .values(retry_count=txn.retry_count + 1)
            )

        # Save payment link if created
        if final_action == "payment_link" and action_result.details:
            db.add(PaymentLink(
                transaction_id=transaction_id,
                link_id=action_result.details.get("link_id", ""),
                link_url=action_result.details.get("link_url", ""),
                short_url=action_result.details.get("short_url"),
                amount=txn.amount,
                provider=action_result.details.get("provider", "mock"),
            ))

        # Audit
        event_type = "RECOVERED" if action_result.amount_recovered > 0 else "ACTION_EXECUTED"
        await self._log_audit(
            db, transaction_id, event_type,
            f"{final_action}: {action_result.status.value}",
            amount=txn.amount,
            amount_recovered=action_result.amount_recovered,
            action=final_action,
            action_result=action_result.status.value,
        )

        await db.flush()
        return action_result

    async def run_batch_recovery(
        self, db: AsyncSession, limit: Optional[int] = None
    ) -> EvaluationResult:
        """Run recovery pipeline on all failed transactions."""
        # Get failed transactions
        query = select(Transaction).where(Transaction.payment_status == "failed")
        if limit:
            query = query.limit(limit)
        result = await db.execute(query)
        failed_txns = result.scalars().all()

        run_id = f"RUN_{uuid.uuid4().hex[:8].upper()}"
        total_count = await db.scalar(select(func.count()).select_from(Transaction))
        revenue_processed = await db.scalar(select(func.sum(Transaction.amount)).select_from(Transaction)) or 0

        stats = {
            "total": total_count,
            "failed": len(failed_txns),
            "risk_amount": 0,
            "eligible": 0,
            "attempted": 0,
            "recovered_count": 0,
            "recovered_amount": 0,
            "auto_actions": 0,
            "escalations": 0,
            "blocks": 0,
            "baseline_recovered": 0,
        }

        for txn in failed_txns:
            stats["risk_amount"] += txn.amount

            try:
                # Run full pipeline
                analysis = await self.analyze_transaction(txn.transaction_id, db)

                if analysis.policy_result:
                    stats["eligible"] += 1

                    if analysis.policy_result.decision.value == "ALLOW":
                        stats["auto_actions"] += 1
                        stats["attempted"] += 1

                        action_result = await self.execute_recovery(txn.transaction_id, db)
                        if action_result.amount_recovered > 0:
                            stats["recovered_count"] += 1
                            stats["recovered_amount"] += action_result.amount_recovered
                    elif analysis.policy_result.decision.value == "ESCALATE":
                        stats["escalations"] += 1
                        await self.execute_recovery(txn.transaction_id, db)
                    elif analysis.policy_result.decision.value in ("BLOCK", "STOP"):
                        stats["blocks"] += 1

                # Baseline: simple un-governed retry for everything
                import random
                if txn.failure_code in ("temporary_bank_failure", "network_timeout"):
                    if random.random() < 0.35:
                        stats["baseline_recovered"] += txn.amount
                elif random.random() < 0.10:
                    stats["baseline_recovered"] += txn.amount

            except Exception as e:
                print(f"[Batch] Error processing {txn.transaction_id}: {e}")
                continue

        # Calculate rates on consistent revenue basis
        recovery_rate = (stats["recovered_amount"] / stats["risk_amount"] * 100) if stats["risk_amount"] > 0 else 0
        avg_recovery = (stats["recovered_amount"] / stats["recovered_count"]) if stats["recovered_count"] > 0 else 0
        baseline_rate = (stats["baseline_recovered"] / stats["risk_amount"] * 100) if stats["risk_amount"] > 0 else 0
        # Standard relative recovery lift: (actual_rate - baseline_rate) / baseline_rate * 100
        recovery_lift = ((recovery_rate - baseline_rate) / baseline_rate * 100) if baseline_rate > 0 else 0

        eval_run = EvaluationRun(
            run_id=run_id,
            total_transactions=stats["total"],
            failed_transactions=stats["failed"],
            revenue_at_risk=stats["risk_amount"],
            eligible_for_recovery=stats["eligible"],
            recovery_attempts=stats["attempted"],
            successful_recoveries=stats["recovered_count"],
            revenue_recovered=stats["recovered_amount"],
            recovery_rate=round(recovery_rate, 2),
            avg_recovery_amount=round(avg_recovery, 2),
            automated_action_rate=round((stats["auto_actions"] / stats["eligible"] * 100) if stats["eligible"] > 0 else 0, 2),
            human_escalation_rate=round((stats["escalations"] / stats["eligible"] * 100) if stats["eligible"] > 0 else 0, 2),
            policy_block_rate=round((stats["blocks"] / stats["eligible"] * 100) if stats["eligible"] > 0 else 0, 2),
            baseline_recovered=round(stats["baseline_recovered"], 2),
            baseline_recovery_rate=round(baseline_rate, 2),
            improvement_pct=round(recovery_lift, 2),
        )
        db.add(eval_run)
        await db.flush()

        res = EvaluationResult.model_validate(eval_run)
        res.escalations = stats["escalations"]
        res.policy_blocks = stats["blocks"]
        return res

    async def get_dashboard_metrics(self, db: AsyncSession) -> DashboardMetrics:
        """Calculate dashboard metrics from actual data."""
        total = await db.scalar(select(func.count()).select_from(Transaction)) or 0
        if total == 0:
            return DashboardMetrics()

        revenue_processed = await db.scalar(
            select(func.sum(Transaction.amount)).select_from(Transaction)
        ) or 0

        failed = await db.scalar(
            select(func.count()).select_from(Transaction)
            .where(Transaction.payment_status == "failed")
        ) or 0

        revenue_at_risk = await db.scalar(
            select(func.sum(Transaction.amount))
            .where(Transaction.payment_status == "failed")
        ) or 0

        recovered_count = await db.scalar(
            select(func.count()).select_from(Transaction)
            .where(Transaction.payment_status == "recovered")
        ) or 0

        revenue_recovered = await db.scalar(
            select(func.sum(Transaction.amount))
            .where(Transaction.payment_status == "recovered")
        ) or 0

        # Action distribution
        action_results = await db.execute(
            select(
                RecoveryActionModel.action_type,
                func.count(RecoveryActionModel.id)
            ).group_by(RecoveryActionModel.action_type)
        )
        action_dist = {row[0]: row[1] for row in action_results.all()}

        # Escalations
        escalations = await db.scalar(
            select(func.count()).select_from(RecoveryActionModel)
            .where(RecoveryActionModel.action_type == "human_review")
        ) or 0

        # Policy blocks
        policy_blocks = await db.scalar(
            select(func.count()).select_from(PolicyDecisionModel)
            .where(PolicyDecisionModel.decision.in_(["BLOCK", "STOP"]))
        ) or 0

        # Recovery by failure type
        fail_recovery = await db.execute(
            select(
                Transaction.failure_code,
                func.count(Transaction.id),
                func.sum(Transaction.amount),
            )
            .where(Transaction.payment_status == "recovered")
            .group_by(Transaction.failure_code)
        )
        recovery_by_failure = {}
        for row in fail_recovery.all():
            if row[0]:
                recovery_by_failure[row[0]] = {"count": row[1], "amount": float(row[2] or 0)}

        # Recovery by payment method
        method_recovery = await db.execute(
            select(
                Transaction.payment_method,
                func.count(Transaction.id),
                func.sum(Transaction.amount),
            )
            .where(Transaction.payment_status == "recovered")
            .group_by(Transaction.payment_method)
        )
        recovery_by_method = {}
        for row in method_recovery.all():
            recovery_by_method[row[0]] = {"count": row[1], "amount": float(row[2] or 0)}

        # Recovery funnel
        diagnosed = await db.scalar(
            select(func.count(func.distinct(RecoveryDecision.transaction_id)))
            .select_from(RecoveryDecision)
        ) or 0

        attempted = await db.scalar(
            select(func.count(func.distinct(RecoveryActionModel.transaction_id)))
            .select_from(RecoveryActionModel)
        ) or 0

        at_risk_total = failed + recovered_count

        recovery_rate = (revenue_recovered / (revenue_at_risk + revenue_recovered) * 100) if (revenue_at_risk + revenue_recovered) > 0 else 0

        # Avg ML probability
        avg_prob = await db.scalar(
            select(func.avg(ModelPrediction.recovery_probability))
            .select_from(ModelPrediction)
        ) or 0

        return DashboardMetrics(
            total_transactions=total,
            revenue_processed=round(float(revenue_processed), 2),
            failed_transactions=failed,
            revenue_at_risk=round(float(revenue_at_risk), 2),
            revenue_recovered=round(float(revenue_recovered), 2),
            recovery_rate=round(float(recovery_rate), 2),
            automated_recoveries=recovered_count,
            human_escalations=escalations,
            policy_blocks=policy_blocks,
            avg_recovery_probability=round(float(avg_prob), 4),
            recovery_by_failure_type=recovery_by_failure,
            recovery_by_payment_method=recovery_by_method,
            recovery_action_distribution=action_dist,
            recovery_funnel={
                "at_risk": at_risk_total,
                "diagnosed": diagnosed,
                "intervention": attempted,
                "attempted": attempted,
                "recovered": recovered_count,
            },
        )

    async def _log_audit(
        self, db: AsyncSession, transaction_id: str, event_type: str,
        details: str = None, amount: float = None,
        amount_recovered: float = None, ai_recommendation: str = None,
        ml_probability: float = None, policy_decision: str = None,
        action: str = None, action_result: str = None,
        rules_triggered: list = None,
    ):
        """Write an audit log entry."""
        db.add(AuditLog(
            transaction_id=transaction_id,
            event_type=event_type,
            details=details,
            amount=amount,
            amount_recovered=amount_recovered,
            ai_recommendation=ai_recommendation,
            ml_probability=ml_probability,
            policy_decision=policy_decision,
            action=action,
            action_result=action_result,
            rules_triggered=rules_triggered,
        ))

    async def _get_audit_trail(
        self, db: AsyncSession, transaction_id: str
    ) -> List[AuditEntry]:
        """Fetch audit trail for a transaction."""
        result = await db.execute(
            select(AuditLog)
            .where(AuditLog.transaction_id == transaction_id)
            .order_by(AuditLog.created_at)
        )
        return [AuditEntry.model_validate(row) for row in result.scalars().all()]


# Singleton
recovery_service = RecoveryService()
