import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis
from app.api import auth, transaction, dashboard, admin

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))

# CORS configuration
frontend_origins = os.environ.get("FRONTEND_ORIGINS")
if frontend_origins:
    origins = [origin.strip() for origin in frontend_origins.split(",") if origin.strip()]
else:
    origins = ["http://127.0.0.1:3000", "http://localhost:3000"]

app = FastAPI(title="FinVault Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
POSTGRES_URI = os.environ.get("POSTGRES_URI")
MONGODB_URI = os.environ.get("MONGODB_URI")
REDIS_URL = os.environ.get("REDIS_URL")

# Initialize database connections
if POSTGRES_URI:
    engine = create_async_engine(POSTGRES_URI, echo=False, future=True)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
else:
    engine = None
    AsyncSessionLocal = None

if MONGODB_URI:
    mongo_client = AsyncIOMotorClient(MONGODB_URI)
    mongo_db = mongo_client.get_default_database()
else:
    mongo_client = None
    mongo_db = None

if REDIS_URL:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
else:
    redis_client = None

# Dependency injection
async def get_db():
    if AsyncSessionLocal:
        async with AsyncSessionLocal() as session:
            yield session
    else:
        yield None

@app.get("/")
def root():
    return {"message": "FinVault API is running.", "status": "healthy"}

@app.get("/favicon.ico")
def favicon():
    from fastapi.responses import Response
    return Response(content=b"", media_type="image/x-icon")

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "postgres": "connected" if engine else "not configured",
        "mongodb": "connected" if mongo_client else "not configured",
        "redis": "connected" if redis_client else "not configured"
    }

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(transaction.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(admin.router, prefix="/api") 