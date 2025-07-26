from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.schemas.transaction import TransactionRequest, TransactionResponse, TransactionListResponse
from app.models import User, Transaction, TransactionStatus
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import AsyncSessionLocal, mongo_db, get_db
from app.services.alert_service import trigger_alert
from app.services.audit_log_service import log_transaction
from app.services.risk_engine import score_transaction
from datetime import datetime
import uuid
from typing import List

router = APIRouter(prefix="/transaction", tags=["transaction"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.post("/", response_model=TransactionResponse)
async def create_transaction(data: TransactionRequest, db: AsyncSession = Depends(get_db)):
    # Fetch user
    result = await db.execute(select(User).where(User.id == data.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    # Fetch behavior profile from MongoDB
    profile = mongo_db.behavior_profiles.find_one({"user_id": data.user_id})
    if profile is None:
        profile = {}
    # Score risk
    risk_result = score_transaction(data.dict(), profile)
    # Determine status
    if risk_result["level"] == "high":
        status = TransactionStatus.blocked.value
        message = "Transaction blocked due to high risk."
        trigger_alert("high_risk_transaction", f"Blocked txn for user {user.id} (amount: {data.amount})")
    elif risk_result["level"] == "medium":
        status = TransactionStatus.challenged.value
        message = "Transaction requires additional verification."
        trigger_alert("medium_risk_transaction", f"Challenged txn for user {user.id} (amount: {data.amount})")
    else:
        status = TransactionStatus.allowed.value
        message = "Transaction allowed."
    # Store transaction
    txn = Transaction(
        user_id=data.user_id,
        amount=data.amount,
        target_account=data.target_account,
        device_info=data.device_info,
        location=data.location,
        intent=data.intent,
        risk_score=risk_result["risk_score"],
        status=status,
        created_at=datetime.utcnow()
    )
    db.add(txn)
    await db.commit()
    await db.refresh(txn)
    # Log the transaction event
    await log_transaction(db, user.id, txn.id, status, f"Amount: {data.amount}, Risk: {risk_result['risk_score']}")
    # Placeholder: Hook for fraud visualization (e.g., heatmap)
    # TODO: Add event to heatmap/visualization system
    return TransactionResponse(
        status=status,
        risk_score=risk_result["risk_score"],
        risk_level=risk_result["level"],
        reasons=risk_result["reasons"],
        message=message
    )

@router.get("/", response_model=TransactionListResponse)
async def list_transactions(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transaction).where(Transaction.user_id == user_id))
    transactions = result.scalars().all()
    return TransactionListResponse(transactions=transactions)

@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(transaction_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    return txn 