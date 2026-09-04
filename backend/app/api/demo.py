"""Demo mode controls API."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, init_db, drop_db

router = APIRouter(prefix="/api/demo", tags=["Demo"])


@router.post("/reset")
async def reset_demo(db: AsyncSession = Depends(get_db)):
    """Reset all data for a fresh demo."""
    await drop_db()
    await init_db()
    return {"status": "ok", "message": "Demo data reset. Generate new transactions to start."}
