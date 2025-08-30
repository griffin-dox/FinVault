from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.database import redis_client
from app.middlewares.session_guardian import enforce_session_risk as session_risk_dep
from app.schemas.transaction import TransactionRequest, TransactionResponse, TransactionListResponse
from app.models import User, Transaction, TransactionStatus
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import AsyncSessionLocal, mongo_db, get_db
from app.services.alert_service import trigger_alert
from app.services.audit_log_service import log_transaction
from app.services.risk_engine import score_transaction
from app.services.rate_limit import limiter
from app.middlewares.rbac import require_roles
from datetime import datetime, timezone
import uuid
from typing import cast, Any

router = APIRouter(prefix="/transaction", tags=["transaction"])


@router.post("/", response_model=None)
@limiter.limit("10/minute; 200/hour")
async def create_transaction(request: Request, data: TransactionRequest, db: AsyncSession = Depends(get_db), _risk=Depends(session_risk_dep), claims: dict = Depends(require_roles("user", "admin"))):
    # Fetch user
    claims_user_id = claims.get("user_id")
    if not claims_user_id:
        raise HTTPException(status_code=401, detail="Invalid token (missing user_id)")
    # Enforce ownership for non-admins
    if claims.get("role") != "admin" and data.user_id != claims_user_id:
        raise HTTPException(status_code=403, detail="Cannot create transactions for another user")
    result = await db.execute(select(User).where(User.id == data.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    # Fetch behavior profile from MongoDB
    profile = {}
    if mongo_db is not None:
        profile = await cast(Any, mongo_db).behavior_profiles.find_one({"user_id": data.user_id}) or {}
    # Score risk
    risk_result = score_transaction(data.model_dump(), profile)
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
        target_account=data.target_account or "checking",  # Default to checking if not provided
        recipient=data.recipient,
        device_info=data.device_info,
        location=data.location,
        intent=data.intent or data.description,  # Use description as intent if intent not provided
        description=data.description,
        risk_score=risk_result["risk_score"],
        status=status,
        created_at=datetime.utcnow()
    )
    db.add(txn)
    await db.commit()
    await db.refresh(txn)
    # Log the transaction event
    await log_transaction(db, cast(int, user.id), cast(int, txn.id), status, f"Amount: {data.amount}, Risk: {risk_result['risk_score']}")
    # Placeholder: Hook for fraud visualization (e.g., heatmap)
    # TODO: Add event to heatmap/visualization system
    
    # Return response in format expected by frontend
    return {
        "riskScore": risk_result["risk_score"],
        "transaction": TransactionResponse(
            id=cast(int, txn.id),
            user_id=cast(int, txn.user_id),
            amount=cast(float, txn.amount),
            target_account=getattr(txn, 'target_account', None),
            recipient=getattr(txn, 'recipient', None),
            device_info=getattr(txn, 'device_info', None),
            location=getattr(txn, 'location', None),
            intent=getattr(txn, 'intent', None),
            description=getattr(txn, 'description', None),
            risk_score=risk_result["risk_score"],
            status=status,
            created_at=cast(datetime, txn.created_at)
        )
    }

@router.get("/", response_model=TransactionListResponse)
async def list_transactions(user_id: int, db: AsyncSession = Depends(get_db), _risk=Depends(session_risk_dep), claims: dict = Depends(require_roles("user", "admin"))):
    # Ownership check
    if claims.get("role") != "admin" and user_id != claims.get("user_id"):
        raise HTTPException(status_code=403, detail="Forbidden")
    result = await db.execute(select(Transaction).where(Transaction.user_id == user_id))
    transactions = result.scalars().all()
    return TransactionListResponse(transactions=list(transactions))

@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(transaction_id: int, db: AsyncSession = Depends(get_db), _risk=Depends(session_risk_dep), claims: dict = Depends(require_roles("user", "admin"))):
    result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    if claims.get("role") != "admin" and txn.user_id != claims.get("user_id"):
        raise HTTPException(status_code=403, detail="Forbidden")
    return txn 