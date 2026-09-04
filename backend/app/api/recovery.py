"""Recovery API routes — analyze, execute, batch."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.recovery_service import recovery_service
from app.schemas import BatchRecoveryRequest

router = APIRouter(prefix="/api/recovery", tags=["Recovery"])


@router.post("/analyze/{transaction_id}")
async def analyze_transaction(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Run full recovery analysis pipeline on a transaction."""
    try:
        analysis = await recovery_service.analyze_transaction(transaction_id, db)
        return analysis.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/execute/{transaction_id}")
async def execute_recovery(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Execute approved recovery action for a transaction."""
    try:
        result = await recovery_service.execute_recovery(transaction_id, db)
        return result.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


@router.post("/run-batch")
async def run_batch_recovery(
    request: BatchRecoveryRequest = BatchRecoveryRequest(),
    db: AsyncSession = Depends(get_db),
):
    """Run recovery pipeline on all failed transactions."""
    try:
        result = await recovery_service.run_batch_recovery(db, limit=request.limit)
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch recovery failed: {str(e)}")
