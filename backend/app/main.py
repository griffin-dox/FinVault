import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.database import AsyncSessionLocal, mongo_db, redis_client
from app.api import auth, transaction, dashboard, admin

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))

# CORS configuration
frontend_origins = os.environ.get("FRONTEND_ORIGINS")
if frontend_origins:
    origins = [origin.strip() for origin in frontend_origins.split(",") if origin.strip()]
else:
    # Default origins if FRONTEND_ORIGINS is not set
    origins = [
        "http://127.0.0.1:3000", 
        "http://localhost:3000", 
        "https://finvault-g6r7.onrender.com",  # Backend URL
        "https://securebank-lcz1.onrender.com"  # Frontend URL
    ]

# Debug: Log the origins being used
print(f"[CORS] Using origins: {origins}")

app = FastAPI(title="FinVault Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        "postgres": "connected" if AsyncSessionLocal else "not configured",
        "mongodb": "connected" if mongo_db else "not configured",
        "redis": "connected" if redis_client else "not configured"
    }

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(transaction.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(admin.router, prefix="/api") 