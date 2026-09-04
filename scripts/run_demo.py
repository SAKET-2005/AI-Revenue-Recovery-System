"""
Command-line runner for interactive 5-minute hackathon demo walkthrough.

Usage: python scripts/run_demo.py
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.database import init_db, async_session
from app.services.recovery_service import recovery_service
from app.ml.predictor import predictor
from scripts.seed_database import seed


async def demo():
    print("=" * 70)
    print("  ReviveAI - Autonomous Revenue Recovery Command Center")
    print("  Razorpay AI Buildathon 2026 - Track 3")
    print("=" * 70)

    # 1. Init & ML check
    print("\n[Step 1] Initializing system & ML recovery model...")
    predictor.load()
    await init_db()
    print("  [OK] XGBoost recovery predictor loaded")

    # 2. Seed data
    print("\n[Step 2] Ingesting transaction stream (1,000 transactions)...")
    await seed(1000)

    # 3. Analyze single failure
    async with async_session() as db:
        metrics_before = await recovery_service.get_dashboard_metrics(db)
        print(f"\n[Step 3] Initial Dashboard State:")
        print(f"  - Revenue Processed: INR {metrics_before.revenue_processed:,.2f}")
        print(f"  - Revenue at Risk:   INR {metrics_before.revenue_at_risk:,.2f} ({metrics_before.failed_transactions} failures)")
        print(f"  - Recovered:         INR {metrics_before.revenue_recovered:,.2f}")

        # Pick a sample failure
        from sqlalchemy import select
        from app.models.transaction import Transaction
        result = await db.execute(select(Transaction).where(Transaction.payment_status == "failed").limit(1))
        sample_txn = result.scalar_one()

        print(f"\n[Step 4] Analyzing Sample Failed Payment: {sample_txn.transaction_id}")
        print(f"  - Amount:       INR {sample_txn.amount:,.2f}")
        print(f"  - Failure Code: {sample_txn.failure_code}")
        print(f"  - Failure Reason: {sample_txn.failure_reason}")

        analysis = await recovery_service.analyze_transaction(sample_txn.transaction_id, db)
        print(f"\n  AI Recovery Pipeline Output:")
        print(f"  - ML Probability: {analysis.prediction.recovery_probability:.1%}")
        print(f"  - AI Diagnosis:   {analysis.agent_decision.diagnosis}")
        print(f"  - Recommended:    {analysis.agent_decision.recommended_action.value}")
        print(f"  - Policy Verdict: {analysis.policy_result.decision.value} ({analysis.policy_result.reason})")

        print(f"\n[Step 5] Executing Autonomous Recovery Action...")
        act_res = await recovery_service.execute_recovery(sample_txn.transaction_id, db)
        print(f"  - Action: {act_res.action} -> Status: {act_res.status.value}")
        if act_res.amount_recovered > 0:
            print(f"  - Amount Recovered: +INR {act_res.amount_recovered:,.2f}")

        # 4. Batch evaluation
        print(f"\n[Step 6] Running Batch Revenue Recovery Agent on all remaining failures...")
        eval_run = await recovery_service.run_batch_recovery(db)
        print(f"\n  Batch Evaluation Results:")
        print(f"  - Total Evaluated:     {eval_run.failed_transactions} failed transactions")
        print(f"  - Revenue Recovered:   INR {eval_run.revenue_recovered:,.2f}")
        print(f"  - Recovery Rate:       {eval_run.recovery_rate:.1%}")
        print(f"  - Baseline (No AI):    INR {eval_run.baseline_recovered:,.2f} ({eval_run.baseline_recovery_rate:.1%})")
        print(f"  - Recovery Lift:       +{eval_run.improvement_pct:.1%}")

    print("\n" + "=" * 70)
    print("  Demo Complete! View interactive dashboard at http://localhost:5173")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
