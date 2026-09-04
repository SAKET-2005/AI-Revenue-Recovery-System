"""Dashboard metrics API."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.recovery_service import recovery_service
from app.schemas import DashboardMetrics

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(db: AsyncSession = Depends(get_db)):
    """Get aggregated dashboard metrics."""
    return await recovery_service.get_dashboard_metrics(db)
