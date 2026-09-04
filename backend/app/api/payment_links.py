"""Payment Links API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.database import get_db
from app.models.recovery import PaymentLink
from app.models.transaction import Transaction
from app.schemas import PaymentLinkCreate, PaymentLinkResponse
from app.integrations.payment_provider import get_payment_provider

router = APIRouter(prefix="/api/payment-links", tags=["Payment Links"])


@router.post("/create", response_model=PaymentLinkResponse)
async def create_payment_link(
    request: PaymentLinkCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a payment link for recovery."""
    provider = get_payment_provider()
    result = await provider.create_payment_link(
        amount=request.amount,
        currency=request.currency,
        description=request.description or f"Recovery payment for {request.transaction_id}",
        customer_name=request.customer_name,
        customer_email=request.customer_email,
        customer_phone=request.customer_phone,
    )

    # Store link
    link = PaymentLink(
        transaction_id=request.transaction_id,
        link_id=result.get("link_id", ""),
        link_url=result.get("link_url", ""),
        short_url=result.get("short_url"),
        amount=request.amount,
        currency=request.currency,
        provider=result.get("provider", "mock"),
    )
    db.add(link)
    await db.flush()

    return PaymentLinkResponse(**result)


@router.post("/complete/{link_id}")
async def complete_payment_link(
    link_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Simulate completing a payment link payment (demo mode)."""
    # Find the link
    result = await db.execute(
        select(PaymentLink).where(PaymentLink.link_id == link_id)
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Payment link not found")

    # Update link status
    link.status = "paid"

    # Update transaction status to recovered
    await db.execute(
        update(Transaction)
        .where(Transaction.transaction_id == link.transaction_id)
        .values(payment_status="recovered")
    )

    # Add audit log
    from app.models.audit import AuditLog
    db.add(AuditLog(
        transaction_id=link.transaction_id,
        event_type="PAYMENT_LINK_PAID",
        details=f"Payment link {link_id} completed — ₹{link.amount:,.0f} recovered",
        amount=link.amount,
        amount_recovered=link.amount,
        action="payment_link",
        action_result="success",
    ))

    await db.flush()

    return {
        "status": "paid",
        "link_id": link_id,
        "transaction_id": link.transaction_id,
        "amount_recovered": link.amount,
        "message": f"₹{link.amount:,.0f} recovered via payment link",
    }
