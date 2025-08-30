from fastapi import APIRouter, Depends, Request, HTTPException, status
from typing import Optional, cast, Any
import os
from datetime import datetime, timedelta, timezone
from app.schemas.telemetry import TelemetryIn, TelemetryOut
from app.middlewares.rbac import get_current_claims
from app.services.telemetry_service import record_telemetry
from app.services.rate_limit import limiter
from app.database import mongo_db

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.post("/device", response_model=TelemetryOut)
@limiter.limit("20/minute; 300/day")
async def telemetry_device(
    payload: TelemetryIn,
    request: Request,
    claims: dict | None = Depends(get_current_claims),
):
    try:
        user_id = claims.get("user_id") if isinstance(claims, dict) else None
    except Exception:
        user_id = None
    try:
        result = await record_telemetry(request, (payload.device or {}).dict(), user_id)
        return TelemetryOut(ok=True, device_id=result.get("device_id"), ip_id=result.get("ip_id"), device_hash=result.get("device_hash"))
    except Exception as e:
        # Avoid leaking internal details
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"message": "Failed to record telemetry"}) from e


@router.get("/known-networks/summary")
@limiter.limit("60/minute; 1000/day")
async def known_networks_summary(
    request: Request,
    days: int = 30,
    user_id: Optional[int] = Depends(lambda claims=Depends(get_current_claims): (claims or {}).get("user_id") if isinstance(claims, dict) else None),
):
    if mongo_db is None:
        raise HTTPException(status_code=503, detail={"message": "Mongo unavailable"})
    # Admins can pass user_id; users get their own
    try:
        query = {}
        if user_id:
            query["user_id"] = user_id
        cutoff = (datetime.now(timezone.utc) - timedelta(days=max(1, days))).strftime('%Y-%m-%d')
        query["day"] = {"$gte": cutoff}
        coll = mongo_db.known_network_counters
        pipeline = [
            {"$match": query},
            {"$group": {"_id": {"user_id": "$user_id", "prefix": "$prefix"}, "distinct_days": {"$addToSet": "$day"}, "last_seen": {"$max": "$last_seen"}}},
            {"$project": {"user_id": "$_id.user_id", "prefix": "$_id.prefix", "days": {"$size": "$distinct_days"}, "last_seen": 1, "_id": 0}},
            {"$sort": {"user_id": 1, "prefix": 1}},
        ]
        cur = coll.aggregate(pipeline)
        rows = [doc async for doc in cur]  # type: ignore - async iteration over cursor
        # Also return current promoted list sizes
        promoted = {}
        async for bp in cast(Any, mongo_db).behavior_profiles.find({} if not user_id else {"user_id": user_id}, {"user_id": 1, "known_networks": 1}):
            promoted[bp.get("user_id")] = len(bp.get("known_networks") or [])
        return {"ok": True, "window_days": days, "prefixes": rows, "promoted_counts": promoted}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"message": "Failed to fetch summary"}) from e


@router.get("/known-networks/decay-report")
@limiter.limit("60/minute; 1000/day")
async def known_networks_decay_report(
    request: Request,
    user_id: Optional[int] = Depends(lambda claims=Depends(get_current_claims): (claims or {}).get("user_id") if isinstance(claims, dict) else None),
):
    if mongo_db is None:
        raise HTTPException(status_code=503, detail={"message": "Mongo unavailable"})
    try:
        decay_days = int(os.getenv("KNOWN_NETWORK_DECAY_DAYS", "90"))
        cutoff = datetime.now(timezone.utc) - timedelta(days=decay_days)
        query = {} if not user_id else {"user_id": user_id}
        # For each user/prefix currently promoted, produce last_seen and whether stale
        out = []
        async for bp in cast(Any, mongo_db).behavior_profiles.find(query, {"user_id": 1, "known_networks": 1}):
            uid = bp.get("user_id")
            for pref in (bp.get("known_networks") or []):
                doc = await cast(Any, mongo_db).known_network_counters.find_one({"user_id": uid, "prefix": pref}, sort=[("last_seen", -1)])
                last_seen = doc.get("last_seen") if doc else None
                out.append({
                    "user_id": uid,
                    "prefix": pref,
                    "last_seen": last_seen,
                    "stale": (last_seen is None or last_seen < cutoff),
                })
        return {"ok": True, "decay_days": decay_days, "networks": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"message": "Failed to fetch decay report"}) from e
