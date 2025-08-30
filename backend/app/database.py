import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING
import redis.asyncio as redis
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# PostgreSQL Database
POSTGRES_URI = os.getenv("POSTGRES_URI")
if POSTGRES_URI:
    engine = create_async_engine(POSTGRES_URI, echo=True)
    AsyncSessionLocal = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
else:
    engine = None
    AsyncSessionLocal = None

# MongoDB Database
MONGODB_URI = os.getenv("MONGODB_URI")
if MONGODB_URI:
    mongo_client = AsyncIOMotorClient(MONGODB_URI)
    mongo_db = mongo_client.finvault
else:
    mongo_client = None
    mongo_db = None

# Redis Database
REDIS_URI = os.getenv("REDIS_URI")
if REDIS_URI:
    redis_client = redis.from_url(REDIS_URI)
else:
    redis_client = None

# Database dependency
async def get_db():
    if AsyncSessionLocal is not None:
        async with AsyncSessionLocal() as session:
            yield session
    else:
        yield None 

# Mongo index setup (TTL + performance)
async def ensure_mongo_indexes():
    # Motor Database objects do not implement truthiness; compare with None explicitly
    if mongo_db is None:
        return
    try:
        # TTL for raw geo events: 30 days
        await mongo_db.geo_events.create_index(
            [("ts", ASCENDING)], expireAfterSeconds=30 * 24 * 3600
        )
        # Supporting indexes for user-based queries and grouping
        await mongo_db.geo_events.create_index([("user_id", ASCENDING)])
        await mongo_db.geo_events.create_index([("tile_lat", ASCENDING), ("tile_lon", ASCENDING)])

    # Aggregated tiles collection: keep 180 days
        await mongo_db.geo_tiles_agg.create_index(
            [("last_seen", ASCENDING)], expireAfterSeconds=180 * 24 * 3600
        )
        # Unique per user/tile key for merge/update semantics
        await mongo_db.geo_tiles_agg.create_index(
            [("user_id", ASCENDING), ("tile_lat", ASCENDING), ("tile_lon", ASCENDING)], unique=True
        )
        # Telemetry collections
        try:
            await mongo_db.ip_addresses.create_index([("ip", ASCENDING)], unique=True)
            await mongo_db.ip_addresses.create_index([("last_seen", ASCENDING)])
            await mongo_db.devices.create_index([("device_hash", ASCENDING)], unique=True)
            await mongo_db.devices.create_index([("last_seen", ASCENDING)])
            await mongo_db.device_ip_events.create_index([("device_id", ASCENDING), ("ip_id", ASCENDING)], unique=True)
            await mongo_db.device_ip_events.create_index([("last_seen", ASCENDING)])
            # Known network counters: unique per user/prefix/day for aggregation
            await mongo_db.known_network_counters.create_index([("user_id", ASCENDING), ("prefix", ASCENDING), ("day", ASCENDING)], unique=True)
            await mongo_db.known_network_counters.create_index([("last_seen", ASCENDING)])
        except Exception:
            pass
    except Exception as e:
        # Log silently to avoid crashing startup
        print(f"[MongoIndexes] Failed to ensure indexes: {e}")