import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables from .env in backend directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))

# Get allowed origins from env, fallback to localhost dev
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

# --- Database Connections ---
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis

POSTGRES_URI = os.environ.get("POSTGRES_URI")
MONGODB_URI = os.environ.get("MONGODB_URI")
REDIS_URL = os.environ.get("REDIS_URL")

# PostgreSQL (SQLAlchemy async)
engine = create_async_engine(POSTGRES_URI, echo=True, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# MongoDB (Motor async)
mongo_client = AsyncIOMotorClient(MONGODB_URI)
mongo_db = mongo_client.get_default_database()

# Redis (async)
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

@app.get("/")
def root():
    return {"message": "FinVault API is running."}

@app.get("/favicon.ico")
def favicon():
    from fastapi.responses import Response
    return Response(content=b"", media_type="image/x-icon")

@app.get("/health")
def health_check():
    return {"status": "ok"}

# Routers will be included here (e.g., from .api import register_router, etc.)
from app.api import auth, transaction, dashboard, admin

app.include_router(auth.router, prefix="/api")
app.include_router(transaction.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(admin.router, prefix="/api") 