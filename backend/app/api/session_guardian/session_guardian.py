from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, cast
from app.database import get_db, mongo_db, redis_client
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.risk_engine import score_session
from datetime import datetime, timezone
from app.services.drift_monitor import validate_behavior_signature
from jose import jwt, JWTError
import os

router = APIRouter(prefix="/session", tags=["session-guardian"])

@router.post("/telemetry")
async def ingest_telemetry(payload: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """
    Expected payload: {
      session_id: str,
      user_id: int,
      telemetry: { device, geo, ip, idle_jitter_ms, pointer_speed_std, nav_bf_usage }
    }
    """
    if mongo_db is None:
        raise HTTPException(status_code=503, detail="MongoDB not configured")
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not configured")

    session_id = payload.get("session_id")
    user_id = payload.get("user_id")
    telemetry = payload.get("telemetry") or {}
    if not session_id or not user_id:
        raise HTTPException(status_code=400, detail="Missing session_id or user_id")

    # Load behavior profile
    profile = mongo_db.behavior_profiles.find_one({"user_id": user_id}) or {}

    # Optional: validate behavior signature from bearer token for cloaking
    token = payload.get("token")
    if token:
        try:
            claims = jwt.decode(token, os.environ.get("JWT_SECRET", "secret"), algorithms=["HS256"])
        except JWTError:
            claims = {}
        await validate_behavior_signature(
            session_id,
            claims,
            (telemetry.get("device") or {}),
            telemetry.get("ip"),
        )

    # Score telemetry
    result = score_session(telemetry, profile)

    # Update Redis session state
    key = f"session:{session_id}"
    state = {
        "user_id": str(user_id),
        "risk_level": result.get("level"),
        "risk_score": str(result.get("risk_score")),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await cast(Any, redis_client).hset(key, mapping=state)
    await cast(Any, redis_client).expire(key, 3600)

    # Persist sample (thin log) for audits
    mongo_db.session_telemetry.insert_one({
        "session_id": session_id,
        "user_id": user_id,
        "telemetry": telemetry,
        "result": result,
        "ts": datetime.now(timezone.utc),
    })

    # If medium/high, signal client to step-up on next poll (client can poll a status endpoint)
    return {"status": "ok", "level": result.get("level"), "risk": result.get("risk_score")}

@router.get("/status/{session_id}")
async def session_status(session_id: str):
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not configured")
    key = f"session:{session_id}"
    data = await cast(Any, redis_client).hgetall(key)
    return {k.decode(): v.decode() for k, v in data.items()}
