import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# PostgreSQL Database
POSTGRES_URI = os.getenv("POSTGRES_URI")
if POSTGRES_URI:
    engine = create_async_engine(POSTGRES_URI, echo=True)
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
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
    if AsyncSessionLocal:
        async with AsyncSessionLocal() as session:
            yield session
    else:
        yield None 