from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING
import os

# Celery task module
from app.services.celery_app import celery
from app.database import mongo_db

@celery.task(name="aggregate_geo_tiles_daily")
def aggregate_geo_tiles_daily():
    """Aggregate raw geo_events into geo_tiles_agg (per user/tile), keeping counts and avg accuracy.
    Runs across the last 24h window, upserting into geo_tiles_agg and updating last_seen.
    """
    # Use a sync client for Celery worker context if needed
    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        print("[AggTiles] MONGODB_URI not set; skipping")
        return
    client = AsyncIOMotorClient(mongo_uri)
    db = client.finvault
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=1)

    async def run():
        pipeline: List[Dict[str, Any]] = [
            {"$match": {"ts": {"$gte": since}}},
            {"$group": {
                "_id": {"user": "$user_id", "lat": "$tile_lat", "lon": "$tile_lon"},
                "count": {"$sum": 1},
                "avgAcc": {"$avg": "$accuracy"}
            }}
        ]
        async for doc in db.geo_events.aggregate(pipeline):
            key = doc["_id"]
            await db.geo_tiles_agg.update_one(
                {"user_id": key["user"], "tile_lat": key["lat"], "tile_lon": key["lon"]},
                {"$set": {"avgAcc": doc.get("avgAcc"), "last_seen": now}, "$inc": {"count": doc.get("count", 0)}},
                upsert=True,
            )
        print("[AggTiles] Aggregation complete")
    import asyncio
    asyncio.run(run())

@celery.task(name="dispatch_alert")
def dispatch_alert(event_type: str, details: str, channels: Optional[List[str]] = None):
    from app.services.email_service import send_magic_link_email as send_email  # placeholder
    # TODO: replace with proper email alert function
    try:
        # Route to console for now
        print(f"[AlertWorker] {event_type}: {details}")
        # Add email/SMS integration hooks here
    except Exception as e:
        print(f"[AlertWorker] Failed: {e}")
