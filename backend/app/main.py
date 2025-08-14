import os
import os
import secrets
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import RequestValidationError
from fastapi.exceptions import HTTPException
from dotenv import load_dotenv
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded

from app.database import AsyncSessionLocal, mongo_db, redis_client, ensure_mongo_indexes
from app.api import auth, transaction, dashboard, admin, behavior_profile, geo, util, telemetry
from app.api.session_guardian import session_guardian
from app.security import security_config, validate_environment
from app.services.rate_limit import limiter, rate_limit_exceeded_handler

# Load environment variables and validate
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))
validate_environment()

app = FastAPI(title="FinVault Backend", version="0.1.0")

# JSON error responses
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail if exc.detail else str(exc)})

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

# Security and rate limiting
security_config.apply_security_middleware(app)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Basic routes
@app.get("/")
def root():
    return {"message": "FinVault API is running.", "status": "healthy"}

@app.head("/")
def root_head():
    return Response(status_code=200)

@app.get("/favicon.ico")
def favicon():
    return Response(content=b"", media_type="image/x-icon")

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "postgres": "connected" if AsyncSessionLocal else "not configured",
        "mongodb": "connected" if mongo_db is not None else "not configured"
    }

@app.get("/csrf-token")
def get_csrf_token():
    """Issue a CSRF token and return it with Set-Cookie and X-CSRF-Token on the SAME response."""
    token = secrets.token_urlsafe(32)
    cookie_kwargs = {"samesite": "none", "path": "/"}
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        cookie_kwargs["secure"] = True
    resp = JSONResponse({"csrf": token})
    resp.set_cookie("csrf_token", token, **cookie_kwargs)
    resp.headers["X-CSRF-Token"] = token
    return resp

ENV = os.getenv("ENVIRONMENT", "development").lower()
if ENV != "production":
    @app.get("/test-cors")
    def test_cors():
        return {"message": "CORS test successful", "timestamp": "2024-01-01T00:00:00Z"}

    @app.post("/test-cors")
    def test_cors_post():
        return {"message": "CORS POST test successful", "timestamp": "2024-01-01T00:00:00Z"}

@app.get("/redis-check")
async def redis_check():
    if not redis_client:
        return {"status": "not configured"}
    try:
        pong = await redis_client.ping()
        return {"status": "connected", "ping": pong}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# Routers
app.include_router(auth.router, prefix="/api")
app.include_router(transaction.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(behavior_profile.router, prefix="/api")
app.include_router(geo.router, prefix="/api")
app.include_router(session_guardian.router, prefix="/api")
app.include_router(util.router, prefix="/api")
app.include_router(telemetry.router, prefix="/api")

@app.on_event("startup")
async def on_startup():
    try:
        await ensure_mongo_indexes()
    except Exception as e:
        print(f"[Startup] Mongo index init failed: {e}")