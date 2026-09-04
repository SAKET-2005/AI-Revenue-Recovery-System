"""Evaluation API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.recovery import EvaluationRun

router = APIRouter(prefix="/api/evaluation", tags=["Evaluation"])


@router.get("")
async def get_evaluations(db: AsyncSession = Depends(get_db)):
    """Get all evaluation run results."""
    result = await db.execute(
        select(EvaluationRun).order_by(EvaluationRun.created_at.desc())
    )
    runs = result.scalars().all()

    return {
        "evaluations": [{
            "run_id": r.run_id,
            "total_transactions": r.total_transactions,
            "failed_transactions": r.failed_transactions,
            "revenue_at_risk": r.revenue_at_risk,
            "eligible_for_recovery": r.eligible_for_recovery,
            "recovery_attempts": r.recovery_attempts,
            "successful_recoveries": r.successful_recoveries,
            "revenue_recovered": r.revenue_recovered,
            "recovery_rate": r.recovery_rate,
            "avg_recovery_amount": r.avg_recovery_amount,
            "automated_action_rate": r.automated_action_rate,
            "human_escalation_rate": r.human_escalation_rate,
            "policy_block_rate": r.policy_block_rate,
            "baseline_recovered": r.baseline_recovered,
            "baseline_recovery_rate": r.baseline_recovery_rate,
            "improvement_pct": r.improvement_pct,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in runs]
    }
