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
from datetime import datetime, timedelta, timezone
from typing import List, Optional, cast
from motor.motor_asyncio import AsyncIOMotorDatabase
import json
import pytz
from app.models.audit_log import AuditLog
from app.services.rate_limit import limiter
from app.services.drift_monitor import run_drift_scan
from app.middlewares.rbac import require_roles

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

# Use the get_db dependency from app.database instead of redefining it here
from app.database import get_db

def get_admin_claims(claims: dict = Depends(require_roles("admin"))):
    return claims

@router.get("/transactions", response_model=List[dict])
async def get_transactions(db: AsyncSession = Depends(get_db), _admin=Depends(get_admin_claims)):
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

@router.patch("/override", response_model=dict)
async def override_transaction(data: dict, db: AsyncSession = Depends(get_db), _admin=Depends(get_admin_claims)):
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
        setattr(txn, "status", TransactionStatus.allowed.value)
    elif action == "block":
        setattr(txn, "status", TransactionStatus.blocked.value)
    elif action == "flag":
        setattr(txn, "status", TransactionStatus.challenged.value)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action.")
    await db.commit()
    return {"message": f"Transaction {action}d."}

@router.get("/users", response_model=List[UserDetailResponse])
async def list_users(db: AsyncSession = Depends(get_db), _admin=Depends(get_admin_claims)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [
        UserDetailResponse(
            id=getattr(u, "id", 0),
            name=getattr(u, "name", ""),
            email=getattr(u, "email", ""),
            phone=getattr(u, "phone", None),
            created_at=to_ist(getattr(u, "created_at", None)) if getattr(u, "created_at", None) is not None else None,
            verified_at=to_ist(getattr(u, "verified_at", None)) if getattr(u, "verified_at", None) is not None else None,
            role=getattr(u, "role", "")
        ) for u in users
    ]

@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db), _admin=Depends(get_admin_claims)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        role_value = str(user.role) if user.role is not None else ""
    return UserDetailResponse(
        id=getattr(user, "id", 0),
        name=getattr(user, "name", ""),
        email=getattr(user, "email", ""),
        phone=getattr(user, "phone", None),
        created_at=to_ist(getattr(user, "created_at", None)) if getattr(user, "created_at", None) is not None else None,
        verified_at=to_ist(getattr(user, "verified_at", None)) if getattr(user, "verified_at", None) is not None else None,
    role=str(getattr(user, "role", ""))
    )

@router.patch("/users/{user_id}", response_model=UserDetailResponse)
async def update_user_patch(user_id: int, data: dict, db: AsyncSession = Depends(get_db), _admin=Depends(get_admin_claims)):
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
        id=getattr(user, "id", 0),
        name=getattr(user, "name", ""),
        email=getattr(user, "email", ""),
        phone=getattr(user, "phone", None),
        created_at=to_ist(getattr(user, "created_at", None)) if getattr(user, "created_at", None) is not None else None,
        verified_at=to_ist(getattr(user, "verified_at", None)) if getattr(user, "verified_at", None) is not None else None,
        role=str(getattr(user, "role", ""))
    )

@router.put("/users/{user_id}", response_model=UserDetailResponse)
async def put_update_user(user_id: int, data: dict, db: AsyncSession = Depends(get_db), _admin=Depends(get_admin_claims)):
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
        id=getattr(user, "id", 0),
        name=getattr(user, "name", ""),
        email=getattr(user, "email", ""),
        phone=getattr(user, "phone", None),
        created_at=to_ist(getattr(user, "created_at", None)) if getattr(user, "created_at", None) is not None else None,
        verified_at=to_ist(getattr(user, "verified_at", None)) if getattr(user, "verified_at", None) is not None else None,
        role=str(getattr(user, "role", ""))
    )

@router.delete("/users/{user_id}", response_model=dict)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db), _admin=Depends(get_admin_claims)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    await db.delete(user)
    await db.commit()
    return {"message": "User deleted."}

@router.put("/transactions/{transaction_id}", response_model=dict)
async def put_update_transaction(transaction_id: int, data: dict, db: AsyncSession = Depends(get_db), _admin=Depends(get_admin_claims)):
    result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")
    new_status = data.get("status")
    if new_status:
        txn.status = new_status
        await db.commit()
        return {"message": f"Transaction status updated to {new_status}."}
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing status field.")

@router.get("/risk-rules", response_model=List[dict])
async def get_risk_rules(_admin=Depends(get_admin_claims)):
    return [{"rule": k, "value": v} for k, v in risk_rules.items()]

@router.patch("/adjust-risk", response_model=List[dict])
async def adjust_risk_rule(data: AdminRiskRuleUpdateRequest, _admin=Depends(get_admin_claims)):
    if data.rule not in risk_rules:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid rule.")
    risk_rules[data.rule] = data.value
    return [{"rule": k, "value": v} for k, v in risk_rules.items()]

@router.get("/telemetry/user/{user_id}", response_model=dict)
async def get_user_telemetry(user_id: int, db: AsyncSession = Depends(get_db), _admin=Depends(get_admin_claims)):
    # Resolve user to fetch identifier-based logs
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    identifier = user.email or user.phone or user.name

    # Initialize defaults
    profile = {}
    geo = []
    stepups = []
    feedback = []

    # Safely read from MongoDB if available
    mdb = mongo_db if mongo_db is not None and isinstance(mongo_db, AsyncIOMotorDatabase) else None
    if isinstance(mdb, AsyncIOMotorDatabase):
        # Only run async code if Motor is valid
        doc_profile = await mdb.get_collection("behavior_profiles").find_one({"user_id": user_id}, {"_id": 0}) # type: ignore # type: ignore
        profile = doc_profile or {}
        geo_cursor = mdb.get_collection("geo_events").find({"user_id": user_id}).sort("ts", -1).limit(10)
        async for doc in geo_cursor: # type: ignore
            doc.pop("_id", None)
            if doc.get("ts"):
                try:
                    doc["ts"] = doc["ts"].isoformat()
                except Exception:
                    pass
            geo.append(doc)
        stepup_cursor = mdb.get_collection("stepup_logs").find({"user": identifier}).sort("timestamp", -1).limit(10)
        async for doc in stepup_cursor: # type: ignore
            doc.pop("_id", None)
            if doc.get("timestamp"):
                try:
                    doc["timestamp"] = doc["timestamp"].isoformat()
                except Exception:
                    pass
            stepups.append(doc)
        fb_cursor = mdb.get_collection("risk_feedback").find({"identifier": identifier}).sort("timestamp", -1).limit(10)
        async for doc in fb_cursor: # type: ignore
            doc.pop("_id", None)
            if doc.get("timestamp"):
                try:
                    doc["timestamp"] = doc["timestamp"].isoformat()
                except Exception:
                    pass
            feedback.append(doc)

    return {"profile": profile, "geo": geo, "stepups": stepups, "feedback": feedback}
@router.get("/heatmap-data", response_model=dict)
async def get_heatmap_data(db: AsyncSession = Depends(get_db), _admin=Depends(get_admin_claims)):
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
async def get_login_heatmap(db: AsyncSession = Depends(get_db), _admin=Depends(get_admin_claims)):
    # Aggregate login attempts by location and status
    result = await db.execute(select(AuditLog))
    logs = result.scalars().all()
    heatmap = {}
    for log in logs:
        if str(log.action).startswith("login_"):
            loc = log.details or "unknown"
            status = str(log.action).replace("login_", "")
            key = (loc, status)
            if key not in heatmap:
                heatmap[key] = 0
            heatmap[key] += 1
    data = [
        {"location": loc, "status": status, "count": count}
        for (loc, status), count in heatmap.items()
    ]
    return data

@router.get("/user-activity-heatmap", response_model=List[dict])
async def get_user_activity_heatmap(
    db: AsyncSession = Depends(get_db),
    user_id: int = Query(..., description="User ID to get activity heatmap for"),
    days: int = Query(30, ge=1, le=365),
    claims: dict = Depends(get_admin_claims)
):
    """
    Get user activity heatmap showing transaction and login patterns.
    Similar to Snapchat's location sharing patterns.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Get user's transactions
    txn_result = await db.execute(
        select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.created_at >= since,
            Transaction.location.isnot(None),
            Transaction.location != "unknown"
        )
    )
    transactions = txn_result.scalars().all()

    # Get user's login events
    login_result = await db.execute(
        select(AuditLog).where(
            AuditLog.user_id == user_id,
            AuditLog.timestamp >= since,
            AuditLog.action.like("login_%"),
            AuditLog.details.isnot(None),
            AuditLog.details != "unknown"
        )
    )
    login_events = login_result.scalars().all()

    # Group by location
    location_activity = {}

    # Process transactions
    for txn in transactions:
        loc = txn.location.strip()
        if not loc or loc == "unknown":
            continue

        try:
            if "," in loc:
                lat, lon = map(float, loc.split(",", 1))
                grid_lat = round(lat, 2)
                grid_lon = round(lon, 2)
                grid_key = f"{grid_lat},{grid_lon}"
            else:
                grid_key = loc
        except (ValueError, TypeError):
            grid_key = loc

        if grid_key not in location_activity:
            location_activity[grid_key] = {
                "coordinates": None,
                "transactions": [],
                "logins": [],
                "total_amount": 0,
                "last_activity": None
            }

        location_activity[grid_key]["transactions"].append({
            "id": txn.id,
            "amount": txn.amount,
            "status": txn.status,
            "timestamp": txn.created_at.isoformat(),
            "description": txn.description
        })
        location_activity[grid_key]["total_amount"] += txn.amount or 0

        if location_activity[grid_key]["coordinates"] is None and "," in loc:
            try:
                lat, lon = map(float, loc.split(",", 1))
                location_activity[grid_key]["coordinates"] = [lat, lon]
            except (ValueError, TypeError):
                pass

        # Update last activity
        if location_activity[grid_key]["last_activity"] is None or txn.created_at > location_activity[grid_key]["last_activity"]:
            location_activity[grid_key]["last_activity"] = txn.created_at

    # Process login events
    for login in login_events:
        loc = login.details.strip()
        if not loc or loc == "unknown":
            continue

        try:
            if "," in loc:
                lat, lon = map(float, loc.split(",", 1))
                grid_lat = round(lat, 2)
                grid_lon = round(lon, 2)
                grid_key = f"{grid_lat},{grid_lon}"
            else:
                grid_key = loc
        except (ValueError, TypeError):
            grid_key = loc

        if grid_key not in location_activity:
            location_activity[grid_key] = {
                "coordinates": None,
                "transactions": [],
                "logins": [],
                "total_amount": 0,
                "last_activity": None
            }

        location_activity[grid_key]["logins"].append({
            "action": login.action,
            "timestamp": login.timestamp.isoformat(),
            "status": login.action.replace("login_", "")
        })

        if location_activity[grid_key]["coordinates"] is None and "," in loc:
            try:
                lat, lon = map(float, loc.split(",", 1))
                location_activity[grid_key]["coordinates"] = [lat, lon]
            except (ValueError, TypeError):
                pass

        # Update last activity
        if location_activity[grid_key]["last_activity"] is None or login.timestamp > location_activity[grid_key]["last_activity"]:
            location_activity[grid_key]["last_activity"] = login.timestamp

    # Convert to heatmap format
    heatmap_data = []
    for location, data in location_activity.items():
        total_activities = len(data["transactions"]) + len(data["logins"])

        if total_activities == 0:
            continue

        # Calculate activity intensity (more activities = higher intensity)
        intensity = min(1.0, total_activities / 10)  # Scale to 0-1

        # Determine activity type
        if len(data["transactions"]) > len(data["logins"]):
            activity_type = "transaction"
        elif len(data["logins"]) > len(data["transactions"]):
            activity_type = "login"
        else:
            activity_type = "mixed"

        heatmap_point = {
            "location": location,
            "coordinates": data["coordinates"] or location,
            "intensity": round(intensity, 3),
            "total_activities": total_activities,
            "transactions_count": len(data["transactions"]),
            "logins_count": len(data["logins"]),
            "total_amount": round(data["total_amount"], 2),
            "activity_type": activity_type,
            "last_activity": data["last_activity"].isoformat() if data["last_activity"] else None,
            "activity_details": {
                "recent_transactions": data["transactions"][-3:] if data["transactions"] else [],
                "recent_logins": data["logins"][-3:] if data["logins"] else []
            }
        }
        heatmap_data.append(heatmap_point)

    # Sort by intensity and recency
    heatmap_data.sort(key=lambda x: (x["intensity"], x["total_activities"]), reverse=True)

    return heatmap_data

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
        if t.created_at is not None:
            day = t.created_at.date().isoformat()
            if day not in buckets:
                buckets[day] = {"total": 0, "high": 0, "medium": 0, "low": 0}
            buckets[day]["total"] += 1
            status_str = str(t.status)
            if status_str == "blocked":
                buckets[day]["high"] += 1
            elif status_str == "challenged":
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

@router.get("/risk-heatmap", response_model=List[dict])
async def get_risk_heatmap(
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
    min_transactions: int = Query(1, ge=1)
):
    """
    Get risk-based heatmap data for admin analysis.
    Shows high-risk transaction areas based on location clustering.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Get transactions with location data
    result = await db.execute(
        select(Transaction).where(
            Transaction.created_at >= since,
            Transaction.location.isnot(None),
            Transaction.location != "unknown"
        )
    )
    txns = result.scalars().all()

    # Group by location and calculate risk metrics
    location_data = {}
    risk_level_map = {
        "allowed": 0.2,    # Low risk
        "challenged": 0.6, # Medium risk
        "blocked": 0.9,    # High risk
        "pending": 0.4     # Medium-low risk
    }

    for txn in txns:
        loc = txn.location.strip()
        if not loc or loc == "unknown":
            continue

        # Parse location coordinates if available
        try:
            if "," in loc:
                lat, lon = map(float, loc.split(",", 1))
                # Create a grid cell (round to ~1km precision)
                grid_lat = round(lat, 2)
                grid_lon = round(lon, 2)
                grid_key = f"{grid_lat},{grid_lon}"
            else:
                # Use location string as key if no coordinates
                grid_key = loc
        except (ValueError, TypeError):
            grid_key = loc

        if grid_key not in location_data:
            location_data[grid_key] = {
                "transactions": [],
                "total_amount": 0,
                "risk_scores": [],
                "statuses": [],
                "coordinates": None
            }

        location_data[grid_key]["transactions"].append(txn)
        location_data[grid_key]["total_amount"] += txn.amount or 0
        location_data[grid_key]["risk_scores"].append(txn.risk_score or 0)
        location_data[grid_key]["statuses"].append(txn.status or "pending")

        # Store coordinates if available
        if "," in loc and location_data[grid_key]["coordinates"] is None:
            try:
                lat, lon = map(float, loc.split(",", 1))
                location_data[grid_key]["coordinates"] = [lat, lon]
            except (ValueError, TypeError):
                pass

    # Calculate aggregated metrics
    heatmap_data = []
    for location, data in location_data.items():
        if len(data["transactions"]) < min_transactions:
            continue

        # Calculate average risk score
        avg_risk = sum(data["risk_scores"]) / len(data["risk_scores"]) if data["risk_scores"] else 0

        # Calculate risk level based on transaction statuses
        status_weights = [risk_level_map.get(status, 0.3) for status in data["statuses"]]
        status_risk = sum(status_weights) / len(status_weights) if status_weights else 0

        # Combine risk factors
        combined_risk = (avg_risk + status_risk) / 2

        # Calculate transaction velocity (transactions per day)
        days_active = max(1, (datetime.now(timezone.utc) - min(t.created_at for t in data["transactions"])).days)
        velocity = len(data["transactions"]) / days_active

        heatmap_point = {
            "location": location,
            "coordinates": data["coordinates"] or location,
            "count": len(data["transactions"]),
            "avg_risk": round(combined_risk, 3),
            "total_amount": round(data["total_amount"], 2),
            "velocity": round(velocity, 2),
            "risk_level": "high" if combined_risk > 0.7 else "medium" if combined_risk > 0.4 else "low",
            "status_breakdown": {
                "allowed": data["statuses"].count("allowed"),
                "challenged": data["statuses"].count("challenged"),
                "blocked": data["statuses"].count("blocked"),
                "pending": data["statuses"].count("pending")
            }
        }
        heatmap_data.append(heatmap_point)

    # Sort by risk level and count
    heatmap_data.sort(key=lambda x: (x["avg_risk"], x["count"]), reverse=True)

    # Inject dummy data if empty for demo purposes
    if not heatmap_data:
        heatmap_data = [
            {
                "location": "28.6139,77.2090",
                "coordinates": [28.6139, 77.2090],
                "count": 12,
                "avg_risk": 0.2,
                "total_amount": 15420.50,
                "velocity": 0.4,
                "risk_level": "low",
                "status_breakdown": {"allowed": 10, "challenged": 1, "blocked": 0, "pending": 1}
            },
            {
                "location": "19.0760,72.8777",
                "coordinates": [19.0760, 72.8777],
                "count": 8,
                "avg_risk": 0.65,
                "total_amount": 8750.25,
                "velocity": 0.27,
                "risk_level": "medium",
                "status_breakdown": {"allowed": 5, "challenged": 2, "blocked": 1, "pending": 0}
            },
            {
                "location": "12.9716,77.5946",
                "coordinates": [12.9716, 77.5946],
                "count": 5,
                "avg_risk": 0.8,
                "total_amount": 3210.75,
                "velocity": 0.17,
                "risk_level": "high",
                "status_breakdown": {"allowed": 2, "challenged": 1, "blocked": 2, "pending": 0}
            }
        ]

    return heatmap_data

@router.put("/users/{user_id}")
async def update_user_put(user_id: int, data: dict, db: AsyncSession = Depends(get_db)):
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

@router.put("/transactions/{transaction_id}")
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

@router.get("/users", response_model=UserListResponse)
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
            last_login = row.timestamp.isoformat() if row.timestamp is not None else None
        user_objs.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "phone": u.phone,
            "verified_at": u.verified_at.isoformat() if u.verified_at is not None else None,
            "role": str(u.role),
            "riskLevel": "low",  # Placeholder, can be improved
            "lastLogin": last_login,
            "isVerified": bool(u.verified) and u.verified_at is not None,
        })
    return UserListResponse(users=user_objs)

@router.get("/transactions", response_model=TransactionListResponse)
async def api_transactions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transaction))
    txns = result.scalars().all()
    txn_objs = [
        {
            "id": t.id,
            "user_id": t.user_id,
            "amount": t.amount,
            "status": str(t.status),
            "created_at": t.created_at.isoformat() if t.created_at is not None else None,
        }
        for t in txns
    ]
    return TransactionListResponse(transactions=txn_objs)

@router.get("/fraud-alerts", response_model=AlertListResponse)
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

@router.get("/ping-db", response_model=SystemStatusResponse)
async def ping_db(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    from datetime import datetime
    try:
        await db.execute(text("SELECT 1"))
        return SystemStatusResponse(status="ok", message="Database connection successful", timestamp=datetime.now(timezone.utc))
    except Exception as e:
        return SystemStatusResponse(status="error", message=f"Database connection failed: {e}", timestamp=datetime.now(timezone.utc))

@router.get("/ping-api", response_model=SystemStatusResponse)
async def ping_api():
    from datetime import datetime
    return SystemStatusResponse(status="ok", message="API is running", timestamp=datetime.now(timezone.utc)) 

@router.post("/drift-scan", response_model=dict)
@limiter.limit("2/minute; 20/day")
async def api_drift_scan(request: Request):
    result = await run_drift_scan()
    return result