from typing import Optional, Dict, Any, cast
from datetime import datetime, timezone

from app.database import mongo_db, redis_client


async def compute_behavior_signature(device: Dict[str, Any], ip_prefix: Optional[str]) -> Optional[str]:
    try:
        import hashlib, json
        core = {k: device.get(k) for k in ["browser", "os", "screen", "timezone"] if device.get(k)}
        if ip_prefix:
            core["ip_prefix"] = ip_prefix
        return hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()
    except Exception:
        return None


async def validate_behavior_signature(session_id: str, token_claims: Dict[str, Any], current_device: Dict[str, Any], current_ip: Optional[str]) -> bool:
    """Compare token's behavior_signature with current derive; if mismatch, mark session as medium risk in Redis."""
    if not redis_client:
        return True
    token_sig = token_claims.get("behavior_signature")
    if not token_sig:
        return True
    ip_prefix = None
    if current_ip:
        import ipaddress
        try:
            ip_obj = ipaddress.ip_address(current_ip)
            if isinstance(ip_obj, ipaddress.IPv4Address):
                ip_prefix = str(ipaddress.ip_network(f"{current_ip}/24", strict=False))
            else:
                ip_prefix = str(ipaddress.ip_network(f"{current_ip}/64", strict=False))
        except ValueError:
            ip_prefix = None
    cur_sig = await compute_behavior_signature(current_device or {}, ip_prefix)
    if cur_sig and token_sig != cur_sig:
        key = f"session:{session_id}"
        await cast(Any, redis_client).hset(key, mapping={
            "risk_level": "medium",
            "risk_score": "50",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "reason": "behavior_signature_mismatch",
        })
        await cast(Any, redis_client).expire(key, 3600)
        return False
    return True


async def run_drift_scan(limit: int = 200):
    """Simple drift scan over recent session telemetry to flag users with increasing risk trends.
    In production this would be a Celery scheduled task.
    """
    if mongo_db is None or not redis_client:
        return {"status": "skipped"}
    cursor = cast(Any, mongo_db).session_telemetry.find({}).sort("ts", -1).limit(limit)
    users_score = {}
    async for doc in cursor:
        uid = doc.get("user_id")
        score = (doc.get("result") or {}).get("risk_score", 0)
        users_score.setdefault(uid, []).append(score)
    flagged = []
    for uid, scores in users_score.items():
        if len(scores) >= 5:
            recent = scores[:5]
            if sum(recent[:2]) < sum(recent[2:]):  # naive worsening trend
                flagged.append(uid)
    return {"flagged_users": flagged, "scanned": len(users_score)}
