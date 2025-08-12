from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timedelta
from typing import List, Dict, Any
from app.database import mongo_db
from app.middlewares.rbac import require_roles

router = APIRouter(prefix="/geo", tags=["geo"])

@router.get("/users/{user_id}/heatmap")
async def user_heatmap(
    user_id: int,
    days: int = Query(90, ge=1, le=180),
    claims: dict = Depends(require_roles("user", "admin")),
):
    # Ownership enforcement for non-admins
    if claims.get("role") != "admin" and claims.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    since = datetime.utcnow() - timedelta(days=days)
    pipeline = [
        {"$match": {"user_id": user_id, "ts": {"$gte": since}}},
        {"$group": {
            "_id": {"lat": "$tile_lat", "lon": "$tile_lon"},
            "count": {"$sum": 1},
            "avgAcc": {"$avg": "$accuracy"}
        }},
        {"$project": {
            "tile_lat": "$_id.lat",
            "tile_lon": "$_id.lon",
            "count": 1,
            "avgAcc": 1,
            "_id": 0
        }},
        {"$sort": {"count": -1}}
    ]
    results: List[Dict[str, Any]] = []
    async for doc in mongo_db.geo_events.aggregate(pipeline):
        results.append(doc)
    return {"tiles": results, "since": since.isoformat()}
