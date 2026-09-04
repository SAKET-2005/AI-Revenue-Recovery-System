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

        # Explicitly seed the 4 deterministic demo scenario transactions
        demo_txns = [
            # Example A: Successful Autonomous Recovery Candidate
            {
                "txn": Transaction(
                    transaction_id="TXN_9281",
                    customer_id=customers[0]["customer_id"],
                    merchant_id="MERCH_001",
                    amount=4500.0,
                    currency="INR",
                    payment_method="upi",
                    payment_status="failed",
                    failure_code="temporary_bank_failure",
                    failure_reason="Bank server timeout during UPI handshake",
                    retry_count=0,
                    device_type="mobile",
                    location="Bengaluru, IN",
                    merchant_category="ecommerce",
                    checkout_duration=74.0,
                    cart_value=4500.0,
                    is_returning_customer=True,
                    transaction_frequency=5.2,
                ),
                "pred": ModelPrediction(
                    transaction_id="TXN_9281",
                    recovery_probability=0.91,
                    confidence=0.94,
                    feature_importances={"failure_code": 0.35, "payment_method": 0.25, "amount": 0.20, "is_returning_customer": 0.20},
                    model_version="xgb_v1",
                ),
                "policy": PolicyDecision(
                    transaction_id="TXN_9281",
                    requested_action="retry",
                    decision="ALLOW",
                    reason="Recovery probability 91% exceeds 80% threshold; amount within limits",
                    rules_triggered=["AMOUNT_CHECK_PASSED", "PROBABILITY_CHECK_PASSED", "RETRY_LIMIT_CHECK_PASSED", "FAILURE_TYPE_CHECK_PASSED"],
                    amount=4500.0,
                    recovery_probability=0.91,
                    confidence=0.94,
                ),
                "decision": RecoveryDecision(
                    transaction_id="TXN_9281",
                    diagnosis="Transient bank failure — server temporarily unavailable during UPI settlement",
                    recommended_action="retry",
                    reasoning=[
                        "UPI payment method pattern verified with historical transient recovery",
                        "Recovery score 91% exceeds automated retry threshold",
                        "Transaction amount ₹4,500 within automated ceiling",
                        "Retry velocity guardrails preserved (< 2 attempts)",
                    ],
                    ai_confidence=0.94,
                    policy_decision="ALLOW",
                    policy_reason="Passed all financial and operational guardrails",
                    rules_triggered=["AMOUNT_CHECK_PASSED", "PROBABILITY_CHECK_PASSED", "RETRY_LIMIT_CHECK_PASSED", "FAILURE_TYPE_CHECK_PASSED"],
                    final_action="retry",
                ),
                "audits": [
                    AuditLog(transaction_id="TXN_9281", event_type="REVENUE_AT_RISK", details="Failed payment detected: ₹4,500", amount=4500.0),
                    AuditLog(transaction_id="TXN_9281", event_type="ML_PREDICTION", details="Recovery probability: 91%", ml_probability=0.91),
                    AuditLog(transaction_id="TXN_9281", event_type="AI_DECISION", details="Recommended: retry", ai_recommendation="retry"),
                    AuditLog(transaction_id="TXN_9281", event_type="POLICY_CHECK", details="ALLOW: Passed all guardrails", policy_decision="ALLOW"),
                ]
            },
            # Example B1: High Value Guardrail Escalation
            {
                "txn": Transaction(
                    transaction_id="TXN_9282",
                    customer_id=customers[1]["customer_id"],
                    merchant_id="MERCH_001",
                    amount=65000.0,
                    currency="INR",
                    payment_method="credit_card",
                    payment_status="failed",
                    failure_code="temporary_bank_failure",
                    failure_reason="Acquiring gateway timeout",
                    retry_count=0,
                    device_type="desktop",
                    location="Mumbai, IN",
                    merchant_category="electronics",
                    checkout_duration=190.0,
                    cart_value=65000.0,
                    is_returning_customer=True,
                    transaction_frequency=1.2,
                ),
                "pred": ModelPrediction(
                    transaction_id="TXN_9282",
                    recovery_probability=0.88,
                    confidence=0.91,
                    feature_importances={"amount": 0.40, "failure_code": 0.30},
                    model_version="xgb_v1",
                ),
                "policy": PolicyDecision(
                    transaction_id="TXN_9282",
                    requested_action="retry",
                    decision="ESCALATE",
                    reason="Amount ₹65,000 exceeds escalation threshold ₹50,000",
                    rules_triggered=["HIGH_VALUE_ESCALATION"],
                    amount=65000.0,
                    recovery_probability=0.88,
                    confidence=0.91,
                ),
                "decision": RecoveryDecision(
                    transaction_id="TXN_9282",
                    diagnosis="Transient bank gateway timeout on high-value transaction",
                    recommended_action="retry",
                    reasoning=["High value transaction requires human review"],
                    ai_confidence=0.91,
                    policy_decision="ESCALATE",
                    policy_reason="Amount ₹65,000 exceeds escalation threshold ₹50,000",
                    rules_triggered=["HIGH_VALUE_ESCALATION"],
                    final_action="human_review",
                ),
                "audits": [
                    AuditLog(transaction_id="TXN_9282", event_type="REVENUE_AT_RISK", details="High value failed payment detected: ₹65,000", amount=65000.0),
                    AuditLog(transaction_id="TXN_9282", event_type="POLICY_ESCALATION", details="Amount exceeds threshold; routed to human review", amount=65000.0, policy_decision="ESCALATE", action="human_review"),
                ]
            },
            # Example B2: Non-Retryable Failure Block
            {
                "txn": Transaction(
                    transaction_id="TXN_9283",
                    customer_id=customers[2]["customer_id"],
                    merchant_id="MERCH_001",
                    amount=3500.0,
                    currency="INR",
                    payment_method="credit_card",
                    payment_status="failed",
                    failure_code="expired_card",
                    failure_reason="Payment card has expired",
                    retry_count=0,
                    device_type="mobile",
                    location="Delhi, IN",
                    merchant_category="fashion",
                    checkout_duration=110.0,
                    cart_value=3500.0,
                    is_returning_customer=False,
                    transaction_frequency=0.8,
                ),
                "pred": ModelPrediction(
                    transaction_id="TXN_9283",
                    recovery_probability=0.68,
                    confidence=0.85,
                    feature_importances={"failure_code": 0.45},
                    model_version="xgb_v1",
                ),
                "policy": PolicyDecision(
                    transaction_id="TXN_9283",
                    requested_action="retry",
                    decision="BLOCK",
                    reason="Failure type 'expired_card' cannot be automatically retried",
                    rules_triggered=["NON_RETRYABLE_FAILURE"],
                    amount=3500.0,
                    recovery_probability=0.68,
                    confidence=0.85,
                ),
                "decision": RecoveryDecision(
                    transaction_id="TXN_9283",
                    diagnosis="Expired card — customer must update payment method",
                    recommended_action="customer_nudge",
                    reasoning=["Card expired; automated retry impossible; nudge recommended"],
                    ai_confidence=0.85,
                    policy_decision="BLOCK",
                    policy_reason="Failure type 'expired_card' cannot be automatically retried",
                    rules_triggered=["NON_RETRYABLE_FAILURE"],
                    final_action="customer_nudge",
                ),
                "audits": [
                    AuditLog(transaction_id="TXN_9283", event_type="REVENUE_AT_RISK", details="Failed payment detected: ₹3,500 (expired card)", amount=3500.0),
                    AuditLog(transaction_id="TXN_9283", event_type="POLICY_BLOCKED", details="Retry blocked for expired card; routed to customer nudge", amount=3500.0, policy_decision="BLOCK"),
                ]
            },
            # Example C: Stop Condition
            {
                "txn": Transaction(
                    transaction_id="TXN_9284",
                    customer_id=customers[3]["customer_id"],
                    merchant_id="MERCH_001",
                    amount=1800.0,
                    currency="INR",
                    payment_method="upi",
                    payment_status="failed",
                    failure_code="temporary_bank_failure",
                    failure_reason="Bank timeout",
                    retry_count=2,
                    device_type="mobile",
                    location="Pune, IN",
                    merchant_category="ecommerce",
                    checkout_duration=45.0,
                    cart_value=1800.0,
                    is_returning_customer=False,
                    transaction_frequency=0.5,
                ),
                "pred": ModelPrediction(
                    transaction_id="TXN_9284",
                    recovery_probability=0.38,
                    confidence=0.82,
                    feature_importances={"retry_count": 0.50},
                    model_version="xgb_v1",
                ),
                "policy": PolicyDecision(
                    transaction_id="TXN_9284",
                    requested_action="retry",
                    decision="STOP",
                    reason="Retry count 2 has reached limit of 2",
                    rules_triggered=["RETRY_LIMIT_REACHED"],
                    amount=1800.0,
                    recovery_probability=0.38,
                    confidence=0.82,
                ),
                "decision": RecoveryDecision(
                    transaction_id="TXN_9284",
                    diagnosis="Exhausted retry velocity limits",
                    recommended_action="stop",
                    reasoning=["Maximum retry count reached; stopping automated attempts"],
                    ai_confidence=0.82,
                    policy_decision="STOP",
                    policy_reason="Retry count 2 has reached limit of 2",
                    rules_triggered=["RETRY_LIMIT_REACHED"],
                    final_action="stop",
                ),
                "audits": [
                    AuditLog(transaction_id="TXN_9284", event_type="REVENUE_AT_RISK", details="Failed payment: ₹1,800 (retries exhausted)", amount=1800.0),
                    AuditLog(transaction_id="TXN_9284", event_type="ACTION_STOPPED", details="Recovery stopped: retry count limit reached", amount=1800.0, policy_decision="STOP", action="stop"),
                ]
            }
        ]

        for d in demo_txns:
            session.add(d["txn"])
            session.add(d["pred"])
            session.add(d["policy"])
            session.add(d["decision"])
            for a in d["audits"]:
                session.add(a)

        # 3. Seed historical evaluation run with mathematically sound relative lift
        total_val = sum(t["amount"] for t in transactions) + sum(d["txn"].amount for d in demo_txns)
        risk_val = sum(t["amount"] for t in transactions if t["payment_status"] == "failed") + sum(d["txn"].amount for d in demo_txns)
        total_at_risk = recovered_amount + risk_val
        rec_rate = (recovered_amount / total_at_risk * 100) if total_at_risk > 0 else 0.0
        baseline_rate = 28.5  # Benchmark naive retry baseline recovery rate (%)
        baseline_rec = round(total_at_risk * (baseline_rate / 100), 2)
        relative_lift = round(((rec_rate - baseline_rate) / baseline_rate) * 100, 2) if baseline_rate > 0 else 0.0

        eval_run = EvaluationRun(
            run_id=f"RUN_{uuid.uuid4().hex[:8].upper()}",
            total_transactions=count + len(demo_txns),
            failed_transactions=len(failed_txns) + len(demo_txns),
            revenue_at_risk=round(total_at_risk, 2),
            eligible_for_recovery=recovered_count + escalation_count + len(demo_txns),
            recovery_attempts=recovered_count,
            successful_recoveries=recovered_count,
            revenue_recovered=round(recovered_amount, 2),
            recovery_rate=round(rec_rate, 2),
            avg_recovery_amount=round(recovered_amount / max(1, recovered_count), 2),
            automated_action_rate=round((recovered_count / max(1, len(failed_txns) + len(demo_txns))) * 100, 2),
            human_escalation_rate=round(((escalation_count + 1) / max(1, len(failed_txns) + len(demo_txns))) * 100, 2),
            policy_block_rate=round(((block_count + 2) / max(1, len(failed_txns) + len(demo_txns))) * 100, 2),
            baseline_recovered=round(baseline_rec, 2),
            baseline_recovery_rate=round(baseline_rate, 2),
            improvement_pct=relative_lift,
        )
        session.add(eval_run)

        await session.commit()

    active_failed = len(failed_txns) + len(demo_txns) - recovered_count
    print(f"[+] Successfully seeded {count + len(demo_txns)} transactions across {len(customers)} customers:")
    print(f"    - Processed Revenue:  INR {total_val:,.2f}")
    print(f"    - Recovered Revenue:  INR {recovered_amount:,.2f} ({recovered_count} automated recoveries)")
    print(f"    - Revenue at Risk:    INR {risk_val:,.2f} ({active_failed} active queue items)")
    print(f"    - Human Escalations:  {escalation_count + 1} cases (including demo TXN_9282)")
    print(f"    - Policy Blocked:     {block_count + 2} cases (including demo TXN_9283, TXN_9284)")
    print(f"    - Recovery Rate:      {rec_rate:.2f}% (Baseline: {baseline_rate:.2f}%, Relative Lift: +{relative_lift:.2f}%)")
    print(f"    - Live Demo TXN:      TXN_9281 (4.5k ready for 1-click live recovery)")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    asyncio.run(seed(n))
