from fastapi import APIRouter, Depends, HTTPException
from app.schemas.transaction_flow import TransactionRequest, TransactionResponse
from app.models import Transaction, TransactionStatus, User
from app.services.risk_engine import score_transaction
from app.services.alert_service import trigger_alert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.main import AsyncSessionLocal, mongo_db
from datetime import datetime

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
    # Placeholder: Hook for fraud visualization (e.g., heatmap)
    # TODO: Add event to heatmap/visualization system
    return TransactionResponse(
        status=status,
        risk_score=risk_result["risk_score"],
        risk_level=risk_result["level"],
        reasons=risk_result["reasons"],
        message=message
    ) 