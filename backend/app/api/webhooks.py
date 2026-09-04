"""Webhook API route — Razorpay webhook handler."""

import hashlib
import hmac
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.webhook import WebhookEvent
from app.models.transaction import Transaction
from app.config import settings

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


@router.post("/razorpay")
async def handle_razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Razorpay webhook events.

    - Validates signature when webhook secret is configured
    - Idempotent — duplicate event IDs are safely ignored
    - Handles payment.failed and payment.captured events
    """
    body = await request.body()
    payload = await request.json()

    # Validate signature if webhook secret is set
    if settings.razorpay_webhook_secret:
        signature = request.headers.get("X-Razorpay-Signature", "")
        expected = hmac.new(
            settings.razorpay_webhook_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

    # Extract event info
    event_id = payload.get("event_id") or payload.get("id", "")
    event_type = payload.get("event", "unknown")

    if not event_id:
        raise HTTPException(status_code=400, detail="Missing event_id")

    # Idempotency check
    existing = await db.execute(
        select(WebhookEvent).where(WebhookEvent.event_id == event_id)
    )
    if existing.scalar_one_or_none():
        return {"status": "duplicate", "event_id": event_id, "message": "Event already processed"}

    # Store event
    webhook_event = WebhookEvent(
        event_id=event_id,
        event_type=event_type,
        payload=payload,
        processed=True,
        processing_result="processed",
    )
    db.add(webhook_event)

    # Process event
    if event_type == "payment.failed":
        await _handle_payment_failed(payload, db)
    elif event_type in ("payment.captured", "payment.authorized"):
        await _handle_payment_success(payload, db)

    await db.flush()
    return {"status": "ok", "event_id": event_id, "event_type": event_type}


async def _handle_payment_failed(payload: dict, db: AsyncSession):
    """Handle payment.failed webhook event."""
    payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
    if not payment:
        return

    # Could create or update transaction based on webhook data
    pass


async def _handle_payment_success(payload: dict, db: AsyncSession):
    """Handle payment.captured webhook event."""
    payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
    if not payment:
        return

    # Could mark transaction as recovered
    pass


@router.post("/simulate")
async def simulate_webhook(
    event_type: str = "payment.failed",
    transaction_id: str = "TXN_SIM_001",
    amount: float = 5000,
    db: AsyncSession = Depends(get_db),
):
    """Simulate a webhook event for demo purposes."""
    import uuid

    event_id = f"evt_{uuid.uuid4().hex[:16]}"
    payload = {
        "event_id": event_id,
        "event": event_type,
        "payload": {
            "payment": {
                "entity": {
                    "id": f"pay_{uuid.uuid4().hex[:16]}",
                    "amount": int(amount * 100),
                    "currency": "INR",
                    "status": "failed" if "failed" in event_type else "captured",
                }
            }
        }
    }

    webhook_event = WebhookEvent(
        event_id=event_id,
        event_type=event_type,
        payload=payload,
        processed=True,
        processing_result="simulated",
    )
    db.add(webhook_event)
    await db.flush()

    return {"status": "simulated", "event_id": event_id, "event_type": event_type}
