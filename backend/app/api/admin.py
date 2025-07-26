from fastapi import APIRouter, Depends, HTTPException, Request
from app.models import Transaction, TransactionStatus, User
from app.schemas.admin import (
    AdminTransactionActionRequest, AdminTransactionActionResponse,
    AdminUserUpdateRequest, AdminUserResponse,
    AdminRiskRule, AdminRiskRulesResponse, AdminRiskRuleUpdateRequest,
    HeatmapDataResponse
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.main import AsyncSessionLocal
from typing import List
import pytz
from datetime import datetime
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

@router.patch("/override", response_model=AdminTransactionActionResponse)
async def override_transaction(data: AdminTransactionActionRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transaction).where(Transaction.id == data.transaction_id))
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    if data.action == "approve":
        txn.status = TransactionStatus.allowed.value
    elif data.action == "block":
        txn.status = TransactionStatus.blocked.value
    elif data.action == "flag":
        txn.status = TransactionStatus.challenged.value
    else:
        raise HTTPException(status_code=400, detail="Invalid action.")
    await db.commit()
    return AdminTransactionActionResponse(message=f"Transaction {data.action}d.")

@router.get("/users", response_model=List[AdminUserResponse])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [
        AdminUserResponse(
            id=u.id,
            name=u.name,
            email=u.email,
            phone=u.phone,
            verified_at=to_ist(u.verified_at) if u.verified_at else None,
            role=u.role.value
        ) for u in users
    ]

@router.get("/users/{user_id}", response_model=AdminUserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return AdminUserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        verified_at=to_ist(user.verified_at) if user.verified_at else None,
        role=user.role.value
    )

@router.patch("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(user_id: int, data: AdminUserUpdateRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if data.name:
        user.name = data.name
    if data.phone:
        user.phone = data.phone
    if data.role:
        user.role = data.role
    await db.commit()
    return AdminUserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        verified_at=to_ist(user.verified_at) if user.verified_at else None,
        role=user.role.value
    )

@router.put("/users/{user_id}", response_model=AdminUserResponse)
async def put_update_user(user_id: int, data: AdminUserUpdateRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if data.name:
        user.name = data.name
    if data.phone:
        user.phone = data.phone
    if data.role:
        user.role = data.role
    await db.commit()
    return AdminUserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        verified_at=to_ist(user.verified_at) if user.verified_at else None,
        role=user.role.value
    )

@router.delete("/users/{user_id}", response_model=AdminTransactionActionResponse)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    await db.delete(user)
    await db.commit()
    return AdminTransactionActionResponse(message="User deleted.")

@router.put("/transactions/{transaction_id}", response_model=AdminTransactionActionResponse)
async def put_update_transaction(transaction_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    status = data.get("status")
    if status:
        txn.status = status
        await db.commit()
        return AdminTransactionActionResponse(message=f"Transaction status updated to {status}.")
    raise HTTPException(status_code=400, detail="Missing status field.")

@router.get("/risk-rules", response_model=AdminRiskRulesResponse)
async def get_risk_rules():
    return AdminRiskRulesResponse(rules=[AdminRiskRule(rule=k, value=v) for k, v in risk_rules.items()])

@router.patch("/adjust-risk", response_model=AdminRiskRulesResponse)
async def adjust_risk_rule(data: AdminRiskRuleUpdateRequest):
    if data.rule not in risk_rules:
        raise HTTPException(status_code=400, detail="Invalid rule.")
    risk_rules[data.rule] = data.value
    return AdminRiskRulesResponse(rules=[AdminRiskRule(rule=k, value=v) for k, v in risk_rules.items()])

@router.get("/heatmap-data", response_model=HeatmapDataResponse)
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
    return HeatmapDataResponse(data=data)

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

@router.get("/fraud-alerts")
async def get_fraud_alerts():
    # Dummy: Return recent alerts from in-memory alert service if available
    try:
        from app.services.alert_service import get_alerts
        return {"alerts": get_alerts()}
    except ImportError:
        # If alert_service is not available, return dummy data
        return {"alerts": [
            {"event_type": "high_risk_transaction", "details": "Transaction blocked for user 123", "timestamp": "2024-05-30T12:34:56Z"},
            {"event_type": "manual_override", "details": "Admin approved transaction 456", "timestamp": "2024-05-30T13:00:00Z"}
        ]}

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
        return Response(status_code=404)
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
        return Response(status_code=404)
    for k, v in data.items():
        if hasattr(txn, k):
            setattr(txn, k, v)
    await db.commit()
    return {"message": "Transaction updated"}

@router.get("/api/users")
async def api_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    # Fetch last login from audit_logs for each user
    user_objs = []
    for u in users:
        last_login = None
        audit_result = await db.execute(
            f"SELECT timestamp FROM audit_logs WHERE user_id = {u.id} AND action = 'login_success' ORDER BY timestamp DESC LIMIT 1"
        )
        row = audit_result.first()
        if row:
            last_login = row[0].isoformat() if row[0] else None
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
    return {"users": user_objs}

@router.get("/api/transactions")
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
    return {"transactions": txn_objs}

@router.get("/api/fraud-alerts")
async def api_fraud_alerts():
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
        return {"alerts": alert_objs}
    except ImportError:
        return {"alerts": []}

@router.get("/api/ping-db")
async def ping_db(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute("SELECT 1")
        return {"ok": True}
    except Exception:
        from fastapi import Response
        return Response(status_code=500)

@router.get("/api/ping-api")
async def ping_api():
    return {"ok": True} 