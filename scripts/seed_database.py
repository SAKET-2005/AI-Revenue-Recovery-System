"""
Seed database with synthetic transactions, customer profiles, recovery actions, and audit logs.

Usage: python scripts/seed_database.py [count]
"""

import asyncio
import sys
import os
import uuid
import random
from datetime import datetime, timedelta

# Put backend on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.database import init_db, drop_db, async_session
from app.models.transaction import Transaction, Customer
from app.models.recovery import (
    ModelPrediction,
    RecoveryDecision,
    RecoveryAction,
    PolicyDecision,
    EvaluationRun,
)
from app.models.audit import AuditLog
from app.utils.data_generator import generate_transactions


async def seed(count: int = 1000):
    print(f"[*] Resetting and initializing database schema...")
    await drop_db()
    await init_db()

    print(f"[*] Generating {count} synthetic transactions...")
    transactions, customers = generate_transactions(n_transactions=count, seed=42)

    async with async_session() as session:
        # 1. Seed customers
        for c in customers:
            session.add(Customer(**c))

        failed_txns = [t for t in transactions if t["payment_status"] == "failed"]
        # Recoverable candidates: high probability & transient failures
        # We simulate that ReviveAI has already actively recovered ~70% of historical eligible failures
        # leaving recent failures active in the queue for live demo runs
        failed_idx = 0
        target_recovered_count = 210

        recovered_count = 0
        recovered_amount = 0.0
        escalation_count = 0
        block_count = 0

        # 2. Seed transactions & correlated recovery intelligence
        for t in transactions:
            txn_clean = {k: v for k, v in t.items() if not k.startswith("_")}
            prob = t.get("_recovery_probability") or random.uniform(0.65, 0.92)
            final_outcome = t.get("_final_outcome", "unrecovered")

            if t["payment_status"] == "failed":
                failed_idx += 1
                # Determine if this was an already-recovered historic event
                if recovered_count < target_recovered_count and (final_outcome == "recovered" or prob >= 0.65) and t["amount"] <= 10000:
                    txn_clean["payment_status"] = "recovered"
                    recovered_count += 1
                    recovered_amount += t["amount"]

                    # Model prediction
                    pred = ModelPrediction(
                        transaction_id=t["transaction_id"],
                        recovery_probability=round(prob, 4),
                        confidence=round(min(0.98, prob + 0.05), 4),
                        feature_importances={
                            "failure_code": 0.35,
                            "payment_method": 0.25,
                            "amount": 0.20,
                            "is_returning_customer": 0.20,
                        },
                        model_version="xgb_v1",
                    )
                    session.add(pred)

                    # Policy decision (Approved)
                    policy = PolicyDecision(
                        transaction_id=t["transaction_id"],
                        requested_action="retry" if t["amount"] <= 10000 else "payment_link",
                        decision="ALLOW",
                        reason=f"Recovery probability {int(prob*100)}% exceeds 80% threshold and amount within limits",
                    )
                    session.add(policy)

                    # Recovery decision
                    dec = RecoveryDecision(
                        transaction_id=t["transaction_id"],
                        diagnosis=f"Transient {t.get('failure_code', 'bank failure')} identified; high retry probability",
                        recommended_action="retry" if t["amount"] <= 10000 else "payment_link",
                        reasoning=[
                            f"Payment method {t['payment_method'].upper()} pattern verified",
                            f"Recovery score {int(prob*100)}% within approval zone",
                            "Retry velocity guardrails preserved (< 2 attempts)",
                        ],
                        ai_confidence=round(prob, 2),
                        policy_decision="ALLOW",
                        policy_reason="Passed all financial guardrails",
                        final_action="retry" if t["amount"] <= 10000 else "payment_link",
                    )
                    session.add(dec)

                    # Recovery action
                    act = RecoveryAction(
                        action_id=f"ACT_{uuid.uuid4().hex[:8].upper()}",
                        transaction_id=t["transaction_id"],
                        action_type="retry" if t["amount"] <= 10000 else "payment_link",
                        status="success",
                        amount_recovered=t["amount"],
                        execution_details={"simulated": True, "latency_ms": 340},
                    )
                    session.add(act)

                    # Audit log entries
                    session.add(AuditLog(
                        transaction_id=t["transaction_id"],
                        event_type="RECOVERY_SUCCESS",
                        details=f"Payment recovered autonomously via {act.action_type}",
                        amount=t["amount"],
                        amount_recovered=t["amount"],
                        ai_recommendation=dec.recommended_action,
                        ml_probability=round(prob, 4),
                        policy_decision="ALLOW",
                        action=act.action_type,
                        action_result="success",
                    ))

                elif t["amount"] > 10000 and prob >= 0.70:
                    # Policy Escalation
                    escalation_count += 1
                    session.add(PolicyDecision(
                        transaction_id=t["transaction_id"],
                        requested_action="retry",
                        decision="ESCALATE",
                        reason=f"Transaction amount ₹{t['amount']:,.2f} exceeds automated recovery threshold (₹10,000)",
                    ))
                    session.add(RecoveryAction(
                        action_id=f"ACT_{uuid.uuid4().hex[:8].upper()}",
                        transaction_id=t["transaction_id"],
                        action_type="human_review",
                        status="pending",
                        amount_recovered=0.0,
                    ))
                    session.add(AuditLog(
                        transaction_id=t["transaction_id"],
                        event_type="POLICY_ESCALATION",
                        details="Amount threshold exceeded; routed to merchant review",
                        amount=t["amount"],
                        policy_decision="ESCALATE",
                        action="human_review",
                    ))

                elif prob < 0.40 or "limit" in str(t.get("failure_reason", "")).lower():
                    # Policy Block
                    block_count += 1
                    session.add(PolicyDecision(
                        transaction_id=t["transaction_id"],
                        requested_action="retry",
                        decision="BLOCK",
                        reason="Non-retryable condition or confidence floor violated (< 40%)",
                    ))
                    session.add(AuditLog(
                        transaction_id=t["transaction_id"],
                        event_type="POLICY_BLOCKED",
                        details="Automated retry prevented by risk guardrails",
                        amount=t["amount"],
                        policy_decision="BLOCK",
                    ))

            session.add(Transaction(**txn_clean))

        # 3. Seed historical evaluation run
        total_val = sum(t["amount"] for t in transactions)
        risk_val = sum(t["amount"] for t in transactions if t["payment_status"] == "failed")
        rec_rate = (recovered_amount / (recovered_amount + risk_val) * 100) if (recovered_amount + risk_val) > 0 else 67.4
        baseline_rec = recovered_amount * 0.58

        eval_run = EvaluationRun(
            run_id=f"RUN_{uuid.uuid4().hex[:8].upper()}",
            total_transactions=count,
            failed_transactions=len(failed_txns),
            revenue_at_risk=round(recovered_amount + risk_val, 2),
            eligible_for_recovery=recovered_count + escalation_count,
            recovery_attempts=recovered_count + escalation_count,
            successful_recoveries=recovered_count,
            revenue_recovered=round(recovered_amount, 2),
            recovery_rate=round(rec_rate, 2),
            avg_recovery_amount=round(recovered_amount / max(1, recovered_count), 2),
            automated_action_rate=round((recovered_count / max(1, len(failed_txns))) * 100, 2),
            human_escalation_rate=round((escalation_count / max(1, len(failed_txns))) * 100, 2),
            policy_block_rate=round((block_count / max(1, len(failed_txns))) * 100, 2),
            baseline_recovered=round(baseline_rec, 2),
            baseline_recovery_rate=round((baseline_rec / max(1, (recovered_amount + risk_val))) * 100, 2),
            improvement_pct=round(rec_rate - ((baseline_rec / max(1, (recovered_amount + risk_val))) * 100), 2),
        )
        session.add(eval_run)

        await session.commit()

    active_failed = len(failed_txns) - recovered_count
    print(f"[+] Successfully seeded {count} transactions across {len(customers)} customers:")
    print(f"    - Processed Revenue:  INR {total_val:,.2f}")
    print(f"    - Recovered Revenue:  INR {recovered_amount:,.2f} ({recovered_count} automated recoveries)")
    print(f"    - Revenue at Risk:    INR {risk_val:,.2f} ({active_failed} active queue items)")
    print(f"    - Human Escalations:  {escalation_count} high-value cases")
    print(f"    - Policy Blocked:     {block_count} unretryable cases")
    print(f"    - Recovery Rate:      {rec_rate:.1f}%")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    asyncio.run(seed(n))
