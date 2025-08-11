import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import RequestValidationError
from fastapi.exceptions import HTTPException
from dotenv import load_dotenv
from app.database import AsyncSessionLocal, mongo_db, redis_client
from app.api import auth, transaction, dashboard, admin, behavior_profile
from app.security import security_config, validate_environment

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))

# Validate environment configuration
validate_environment()

app = FastAPI(title="FinVault Backend", version="0.1.0")

# Ensure all HTTP errors return JSON
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail if exc.detail else str(exc)}
    )

# Ensure validation errors return JSON
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )

# Apply security middleware
security_config.apply_security_middleware(app)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(transaction.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(behavior_profile.router, prefix="/api")

# Redis connection check endpoint
@app.get("/redis-check")
async def redis_check():
    if not redis_client:
        return {"status": "not configured"}
    try:
        pong = await redis_client.ping()
        return {"status": "connected", "ping": pong}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
import os
from fastapi import FastAPI
from dotenv import load_dotenv
from app.database import AsyncSessionLocal, mongo_db, redis_client
from app.api import auth, transaction, dashboard, admin, behavior_profile
from app.security import security_config, validate_environment

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))

# Validate environment configuration
validate_environment()

app = FastAPI(title="FinVault Backend", version="0.1.0")

# Apply security middleware
security_config.apply_security_middleware(app)

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
        "mongodb": "connected" if mongo_db is not None else "not configured"
    }

@app.get("/test-cors")
def test_cors():
    """Simple endpoint to test CORS configuration"""
    return {
        "message": "CORS test successful",
        "timestamp": "2024-01-01T00:00:00Z",
        "cors_origins": origins
    }

@app.post("/test-cors")
def test_cors_post():
    """Simple POST endpoint to test CORS configuration"""
    return {
        "message": "CORS POST test successful",
        "timestamp": "2024-01-01T00:00:00Z"
    }

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(transaction.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(behavior_profile.router, prefix="/api")