from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from app.schemas.admin import (
    UserListResponse, UserDetailResponse, TransactionListResponse, 
    AdminRiskRuleUpdateRequest, AlertListResponse, SystemStatusResponse
)
from app.models import User, Transaction, TransactionStatus
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.database import AsyncSessionLocal, mongo_db, get_db
from app.services.alert_service import trigger_alert
from app.services.audit_log_service import log_admin_action
from datetime import datetime, timedelta
from typing import List, Optional
import json
import pytz
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/admin", tags=["admin"])

# In-memory risk rules (replace with DB in production)
risk_rules = {
    "device_mismatch": 50,
    "unusual_time": 30,
    "large_amount": 40,
    "high_threshold": 70,
    "medium_threshold": 40
}

def to_ist(dt):
    if not dt:
        return None
    ist = pytz.timezone('Asia/Kolkata')
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.utc)
    return dt.astimezone(ist).isoformat()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Dummy get_current_user for illustration; replace with your actual auth dependency
async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    # Extract user from JWT/session (replace with your real logic)
    # For now, just return user with id=1 for demo
    result = await db.execute(select(User).where(User.id == 1))
    user = result.scalar_one_or_none()
    return user

@router.get("/transactions", response_model=List[dict])
async def get_transactions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transaction))
    txns = result.scalars().all()
    return [
        {
            "id": t.id,
            "user_id": t.user_id,
            "amount": t.amount,
            "target_account": t.target_account,
            "device_info": t.device_info,
            "location": t.location,
            "intent": t.intent,
            "risk_score": t.risk_score,
            "status": t.status,
            "created_at": to_ist(t.created_at)
        } for t in txns
    ]

@router.patch("/override", response_model=dict) # Changed response_model to dict as per new schema
async def override_transaction(data: dict, db: AsyncSession = Depends(get_db)): # Changed data type to dict
    transaction_id = data.get("transaction_id")
    action = data.get("action")

    if not transaction_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transaction ID is required.")
    if not action:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Action is required.")

    result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")

    if action == "approve":
        txn.status = TransactionStatus.allowed
    elif action == "block":
        txn.status = TransactionStatus.blocked
    elif action == "flag":
        txn.status = TransactionStatus.challenged
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action.")
    await db.commit()
    return {"message": f"Transaction {action}d."}

@router.get("/users", response_model=List[UserDetailResponse])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [
        UserDetailResponse(
            id=u.id,
            name=u.name,
            email=u.email,
            phone=u.phone,
            verified_at=to_ist(u.verified_at) if u.verified_at else None,
            role=u.role.value
        ) for u in users
    ]

@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return UserDetailResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        verified_at=to_ist(user.verified_at) if user.verified_at else None,
        role=user.role.value
    )

@router.patch("/users/{user_id}", response_model=UserDetailResponse)
async def update_user(user_id: int, data: dict, db: AsyncSession = Depends(get_db)): # Changed data type to dict
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if data.get("name"): # Use .get() for safety
        user.name = data["name"]
    if data.get("phone"): # Use .get() for safety
        user.phone = data["phone"]
    if data.get("role"): # Use .get() for safety
        user.role = data["role"]
    await db.commit()
    return UserDetailResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        verified_at=to_ist(user.verified_at) if user.verified_at else None,
        role=user.role.value
    )

@router.put("/users/{user_id}", response_model=UserDetailResponse)
async def put_update_user(user_id: int, data: dict, db: AsyncSession = Depends(get_db)): # Changed data type to dict
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if data.get("name"): # Use .get() for safety
        user.name = data["name"]
    if data.get("phone"): # Use .get() for safety
        user.phone = data["phone"]
    if data.get("role"): # Use .get() for safety
        user.role = data["role"]
    await db.commit()
    return UserDetailResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        verified_at=to_ist(user.verified_at) if user.verified_at else None,
        role=user.role.value
    )

@router.delete("/users/{user_id}", response_model=dict) # Changed response_model to dict
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    await db.delete(user)
    await db.commit()
    return {"message": "User deleted."}

@router.put("/transactions/{transaction_id}", response_model=dict) # Changed response_model to dict
async def put_update_transaction(transaction_id: int, data: dict, db: AsyncSession = Depends(get_db)): # Changed data type to dict
    result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")
    status = data.get("status")
    if status:
        txn.status = status
        await db.commit()
        return {"message": f"Transaction status updated to {status}."}
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing status field.")

@router.get("/risk-rules", response_model=List[dict]) # Changed response_model to List[dict]
async def get_risk_rules():
    return [{"rule": k, "value": v} for k, v in risk_rules.items()]

@router.patch("/adjust-risk", response_model=List[dict]) # Changed response_model to List[dict]
async def adjust_risk_rule(data: AdminRiskRuleUpdateRequest):
    if data.rule not in risk_rules:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid rule.")
    risk_rules[data.rule] = data.value
    return [{"rule": k, "value": v} for k, v in risk_rules.items()]

@router.get("/heatmap-data", response_model=dict) # Changed response_model to dict
async def get_heatmap_data(db: AsyncSession = Depends(get_db)):
    # Aggregate transactions by location and risk
    result = await db.execute(select(Transaction))
    txns = result.scalars().all()
    heatmap = {}
    for t in txns:
        key = (t.location, t.status)
        if key not in heatmap:
            heatmap[key] = 0
        heatmap[key] += 1
    data = [
        {"location": loc, "status": status, "count": count}
        for (loc, status), count in heatmap.items()
    ]
    return {"data": data}

@router.get("/login-heatmap", response_model=List[dict])
async def get_login_heatmap(db: AsyncSession = Depends(get_db)):
    # Aggregate login attempts by location and status
    result = await db.execute(select(AuditLog))
    logs = result.scalars().all()
    heatmap = {}
    for log in logs:
        if log.action.startswith("login_"):
            loc = log.details or "unknown"
            status = log.action.replace("login_", "")
            key = (loc, status)
            if key not in heatmap:
                heatmap[key] = 0
            heatmap[key] += 1
    data = [
        {"location": loc, "status": status, "count": count}
        for (loc, status), count in heatmap.items()
    ]
    return data

@router.get("/user/heatmap", response_model=List[dict])
async def get_user_heatmap(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id
    # Get login events
    login_logs = await db.execute(
        select(AuditLog).where(AuditLog.user_id == user_id, AuditLog.action.like("login_%"))
    )
    login_events = [
        {
            "location": log.details or "unknown",
            "type": log.action,
            "status": log.action.replace("login_", ""),
            "timestamp": log.timestamp,
        }
        for log in login_logs.scalars().all()
    ]
    # Get transaction events
    txns = await db.execute(
        select(Transaction).where(Transaction.user_id == user_id)
    )
    txn_events = [
        {
            "location": txn.location or "unknown",
            "type": f"transaction_{txn.status}",
            "status": txn.status,
            "timestamp": txn.created_at,
        }
        for txn in txns.scalars().all()
    ]
    return login_events + txn_events

@router.get("/behavioral-anomalies", response_model=List[dict])
async def get_behavioral_anomalies():
    # Dummy: Return recent anomalies from risk engine's in-memory history
    from app.services.risk_engine import user_tx_history
    anomalies = []
    for user_id, txns in user_tx_history.items():
        for t in txns:
            if t.get("anomalies"):
                anomalies.append({"user_id": user_id, **t})
    return anomalies[-20:]

@router.get("/transaction-trends", response_model=List[dict])
async def get_transaction_trends(db: AsyncSession = Depends(get_db)):
    # Return transaction volume, risk, and anomaly trends over time (dummy buckets)
    result = await db.execute(select(Transaction))
    txns = result.scalars().all()
    buckets = {}
    for t in txns:
        day = t.created_at.date().isoformat()
        if day not in buckets:
            buckets[day] = {"total": 0, "high": 0, "medium": 0, "low": 0}
        buckets[day]["total"] += 1
        if t.status == "blocked":
            buckets[day]["high"] += 1
        elif t.status == "challenged":
            buckets[day]["medium"] += 1
        else:
            buckets[day]["low"] += 1
    trends = [
        {"date": day, **stats}
        for day, stats in sorted(buckets.items())
    ]
    return trends

@router.get("/fraud-alerts", response_model=AlertListResponse)
async def get_fraud_alerts(db: AsyncSession = Depends(get_db)):
    # Dummy: Return recent alerts from in-memory alert service if available
    try:
        from app.services.alert_service import get_alerts
        alerts = get_alerts()
        # Map to expected structure
        alert_objs = [
            {
                "id": i,
                "alertType": a["event_type"],
                "description": a["details"],
                "severity": "high" if "high" in a["event_type"] else "medium" if "medium" in a["event_type"] else "low",
                "isResolved": False,
            }
            for i, a in enumerate(alerts)
        ]
        return AlertListResponse(alerts=alert_objs)
    except ImportError:
        # If alert_service is not available, return dummy data
        return AlertListResponse(alerts=[
            {"id": 0, "alertType": "high_risk_transaction", "description": "Transaction blocked for user 123", "severity": "high", "isResolved": False},
            {"id": 1, "alertType": "manual_override", "description": "Admin approved transaction 456", "severity": "medium", "isResolved": False}
        ])

@router.get("/admin/risk-heatmap", response_model=List[dict])
async def get_risk_heatmap(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transaction))
    txns = result.scalars().all()
    risk_map = {}
    risk_map_counts = {}
    risk_level_map = {"allowed": 0, "challenged": 1, "blocked": 2}
    for t in txns:
        loc = t.location or "unknown"
        risk = risk_level_map.get(t.status, 0)
        if loc not in risk_map:
            risk_map[loc] = 0
            risk_map_counts[loc] = 0
        risk_map[loc] += risk
        risk_map_counts[loc] += 1
    data = [
        {
            "location": loc,
            "avg_risk": risk_map[loc] / risk_map_counts[loc] if risk_map_counts[loc] else 0,
            "count": risk_map_counts[loc],
        }
        for loc in risk_map
    ]
    # Inject dummy data if empty
    if not data:
        data = [
            {"location": "28.6139,77.2090", "avg_risk": 0.2, "count": 12},  # Delhi
            {"location": "19.0760,72.8777", "avg_risk": 1.1, "count": 8},   # Mumbai
            {"location": "12.9716,77.5946", "avg_risk": 1.8, "count": 5},   # Bangalore
            {"location": "22.5726,88.3639", "avg_risk": 0.7, "count": 7},   # Kolkata
            {"location": "13.0827,80.2707", "avg_risk": 1.5, "count": 4},   # Chennai
        ]
    return data

@router.put("/api/users/{user_id}")
async def update_user(user_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        from fastapi import Response
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    for k, v in data.items():
        if hasattr(user, k):
            setattr(user, k, v)
    await db.commit()
    return {"message": "User updated"}

@router.put("/api/transactions/{transaction_id}")
async def update_transaction(transaction_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    txn = result.scalar_one_or_none()
    if not txn:
        from fastapi import Response
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    for k, v in data.items():
        if hasattr(txn, k):
            setattr(txn, k, v)
    await db.commit()
    return {"message": "Transaction updated"}

@router.get("/api/users", response_model=UserListResponse)
async def api_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    # Fetch last login from audit_logs for each user
    user_objs = []
    for u in users:
        last_login = None
        audit_result = await db.execute(
            select(AuditLog).where(AuditLog.user_id == u.id, AuditLog.action == "login_success").order_by(AuditLog.timestamp.desc()).limit(1)
        )
        row = audit_result.scalar_one_or_none()
        if row:
            last_login = row.timestamp.isoformat() if row.timestamp else None
        user_objs.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "phone": u.phone,
            "verified_at": u.verified_at.isoformat() if u.verified_at else None,
            "role": u.role,
            "riskLevel": "low",  # Placeholder, can be improved
            "lastLogin": last_login,
            "isVerified": bool(u.verified and u.verified_at),
        })
    return UserListResponse(users=user_objs)

@router.get("/api/transactions", response_model=TransactionListResponse)
async def api_transactions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transaction))
    txns = result.scalars().all()
    txn_objs = [
        {
            "id": t.id,
            "user_id": t.user_id,
            "amount": t.amount,
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in txns
    ]
    return TransactionListResponse(transactions=txn_objs)

@router.get("/api/fraud-alerts", response_model=AlertListResponse)
async def api_fraud_alerts(db: AsyncSession = Depends(get_db)):
    try:
        from app.services.alert_service import get_alerts
        alerts = get_alerts()
        # Map to expected structure
        alert_objs = [
            {
                "id": i,
                "alertType": a["event_type"],
                "description": a["details"],
                "severity": "high" if "high" in a["event_type"] else "medium" if "medium" in a["event_type"] else "low",
                "isResolved": False,
            }
            for i, a in enumerate(alerts)
        ]
        return AlertListResponse(alerts=alert_objs)
    except ImportError:
        return AlertListResponse(alerts=[])

@router.get("/api/ping-db", response_model=SystemStatusResponse)
async def ping_db(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute("SELECT 1")
        return SystemStatusResponse(status="ok", message="Database connection successful")
    except Exception as e:
        from fastapi import Response
        return SystemStatusResponse(status="error", message=f"Database connection failed: {e}")

@router.get("/api/ping-api", response_model=SystemStatusResponse)
async def ping_api():
    return SystemStatusResponse(status="ok", message="API is running") 