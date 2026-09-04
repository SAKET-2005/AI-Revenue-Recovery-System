"""Audit log API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from app.database import get_db
from app.models.audit import AuditLog
from app.schemas import AuditEntry

router = APIRouter(prefix="/api/audit-log", tags=["Audit"])


@router.get("")
async def get_audit_log(
    transaction_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Query audit log with optional filters."""
    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    count_query = select(func.count()).select_from(AuditLog)

    if transaction_id:
        query = query.where(AuditLog.transaction_id == transaction_id)
        count_query = count_query.where(AuditLog.transaction_id == transaction_id)
    if event_type:
        query = query.where(AuditLog.event_type == event_type)
        count_query = count_query.where(AuditLog.event_type == event_type)

    total = await db.scalar(count_query) or 0
    result = await db.execute(query.offset(offset).limit(limit))
    entries = [AuditEntry.model_validate(row) for row in result.scalars().all()]

    return {
        "entries": [e.model_dump() for e in entries],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
