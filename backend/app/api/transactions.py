"""Transaction API routes."""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from app.database import get_db
from app.models.transaction import Transaction, Customer
from app.models.recovery import RecoveryDecision, RecoveryAction as RecoveryActionModel, ModelPrediction, PolicyDecision as PolicyDecisionModel, PaymentLink
from app.models.audit import AuditLog
from app.schemas import TransactionDetail, CustomerDetail, GenerateRequest, AuditEntry
from app.utils.data_generator import generate_transactions

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])


@router.get("")
async def list_transactions(
    status: Optional[str] = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List transactions with optional filtering."""
    query = select(Transaction).order_by(Transaction.id.desc())
    count_query = select(func.count()).select_from(Transaction)

    if status:
        query = query.where(Transaction.payment_status == status)
        count_query = count_query.where(Transaction.payment_status == status)

    total = await db.scalar(count_query) or 0
    result = await db.execute(query.offset(offset).limit(limit))
    transactions = result.scalars().all()

    # Enrich with recovery decision info
    enriched = []
    for txn in transactions:
        txn_dict = TransactionDetail.model_validate(txn).model_dump()

        # Get latest recovery decision
        dec_result = await db.execute(
            select(RecoveryDecision)
            .where(RecoveryDecision.transaction_id == txn.transaction_id)
            .order_by(RecoveryDecision.id.desc())
            .limit(1)
        )
        decision = dec_result.scalar_one_or_none()
        if decision:
            txn_dict["recommended_action"] = decision.recommended_action
            txn_dict["policy_decision"] = decision.policy_decision
            txn_dict["final_action"] = decision.final_action
            txn_dict["diagnosis"] = decision.diagnosis

        # Get latest ML prediction
        pred_result = await db.execute(
            select(ModelPrediction)
            .where(ModelPrediction.transaction_id == txn.transaction_id)
            .order_by(ModelPrediction.id.desc())
            .limit(1)
        )
        pred = pred_result.scalar_one_or_none()
        if pred:
            txn_dict["recovery_probability"] = pred.recovery_probability
            txn_dict["confidence"] = pred.confidence

        enriched.append(txn_dict)

    return {"transactions": enriched, "total": total, "limit": limit, "offset": offset}


@router.get("/{transaction_id}")
async def get_transaction(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get full transaction details with analysis."""
    result = await db.execute(
        select(Transaction).where(Transaction.transaction_id == transaction_id)
    )
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")

    txn_detail = TransactionDetail.model_validate(txn).model_dump()

    # Customer
    cust_result = await db.execute(
        select(Customer).where(Customer.customer_id == txn.customer_id)
    )
    cust = cust_result.scalar_one_or_none()
    txn_detail["customer"] = CustomerDetail.model_validate(cust).model_dump() if cust else None

    # ML Prediction
    pred_result = await db.execute(
        select(ModelPrediction)
        .where(ModelPrediction.transaction_id == transaction_id)
        .order_by(ModelPrediction.id.desc()).limit(1)
    )
    pred = pred_result.scalar_one_or_none()
    txn_detail["prediction"] = {
        "recovery_probability": pred.recovery_probability,
        "confidence": pred.confidence,
        "feature_importances": pred.feature_importances,
        "model_version": pred.model_version,
    } if pred else None

    # Recovery Decision
    dec_result = await db.execute(
        select(RecoveryDecision)
        .where(RecoveryDecision.transaction_id == transaction_id)
        .order_by(RecoveryDecision.id.desc()).limit(1)
    )
    decision = dec_result.scalar_one_or_none()
    txn_detail["decision"] = {
        "diagnosis": decision.diagnosis,
        "recommended_action": decision.recommended_action,
        "reasoning": decision.reasoning,
        "ai_confidence": decision.ai_confidence,
        "retry_delay_minutes": decision.retry_delay_minutes,
        "customer_message": decision.customer_message,
        "policy_decision": decision.policy_decision,
        "policy_reason": decision.policy_reason,
        "rules_triggered": decision.rules_triggered,
        "final_action": decision.final_action,
    } if decision else None

    # Recovery Actions
    action_result = await db.execute(
        select(RecoveryActionModel)
        .where(RecoveryActionModel.transaction_id == transaction_id)
        .order_by(RecoveryActionModel.id.desc())
    )
    actions = action_result.scalars().all()
    txn_detail["actions"] = [{
        "action_id": a.action_id,
        "action_type": a.action_type,
        "status": a.status,
        "amount_recovered": a.amount_recovered,
        "execution_details": a.execution_details,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    } for a in actions]

    # Payment Links
    link_result = await db.execute(
        select(PaymentLink).where(PaymentLink.transaction_id == transaction_id)
    )
    links = link_result.scalars().all()
    txn_detail["payment_links"] = [{
        "link_id": l.link_id,
        "link_url": l.link_url,
        "short_url": l.short_url,
        "amount": l.amount,
        "status": l.status,
        "provider": l.provider,
    } for l in links]

    # Audit Trail
    audit_result = await db.execute(
        select(AuditLog)
        .where(AuditLog.transaction_id == transaction_id)
        .order_by(AuditLog.created_at)
    )
    txn_detail["audit_trail"] = [
        AuditEntry.model_validate(a).model_dump() for a in audit_result.scalars().all()
    ]

    return txn_detail


@router.post("/generate")
async def generate_transaction_data(
    request: GenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate synthetic transaction data and seed the database."""
    transactions, customers = generate_transactions(n_transactions=request.count)

    # Insert customers
    for cust in customers:
        db.add(Customer(**cust))

    # Insert transactions
    for txn in transactions:
        # Remove ML target fields
        txn_data = {k: v for k, v in txn.items() if not k.startswith("_")}
        db.add(Transaction(**txn_data))

    await db.flush()

    failed_count = sum(1 for t in transactions if t["payment_status"] == "failed")
    total_amount = sum(t["amount"] for t in transactions)
    risk_amount = sum(t["amount"] for t in transactions if t["payment_status"] == "failed")

    return {
        "message": f"Generated {request.count} transactions",
        "total": request.count,
        "failed": failed_count,
        "success": request.count - failed_count,
        "total_amount": round(total_amount, 2),
        "risk_amount": round(risk_amount, 2),
        "customers": len(customers),
    }
