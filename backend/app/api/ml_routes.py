"""ML metrics API route."""

from fastapi import APIRouter
from app.ml.predictor import predictor
from app.schemas import MLMetrics

router = APIRouter(prefix="/api/ml", tags=["ML"])


@router.get("/metrics", response_model=MLMetrics)
async def get_ml_metrics():
    """Get ML model performance metrics."""
    if predictor.is_loaded:
        metrics = predictor.get_metrics()
        return MLMetrics(**metrics)

    return MLMetrics(
        model_version="not_loaded",
        roc_auc=None,
        precision=None,
        recall=None,
        f1=None,
        accuracy=None,
    )
