from fastapi import Request, HTTPException
from typing import Optional
from app.database import redis_client


async def enforce_session_risk(request: Request):
    """FastAPI dependency that enforces session risk using Redis.
    Reads X-Session-ID header or session_id query param automatically.
    - high => 403 block
    - medium => 401 step-up required
    - low/unknown => allow
    """
    if not redis_client:
        return
    session_id: Optional[str] = request.headers.get("X-Session-ID") or request.query_params.get("session_id")
    if not session_id:
        return
    key = f"session:{session_id}"
    data = await redis_client.hgetall(key)
    if not data:
        return
    level = data.get(b"risk_level")
    if not level:
        return
    lvl = level.decode()
    if lvl == "high":
        raise HTTPException(status_code=403, detail={"message": "Session high risk. Blocked."})
    if lvl == "medium":
        raise HTTPException(status_code=401, detail={"message": "Session medium risk. Step-up required.", "action": "step_up"})
