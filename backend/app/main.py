import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import RequestValidationError
from fastapi.exceptions import HTTPException
from dotenv import load_dotenv
from app.database import AsyncSessionLocal, mongo_db, redis_client, ensure_mongo_indexes
from app.api import auth, transaction, dashboard, admin, behavior_profile, geo, util
from app.api.session_guardian import session_guardian
from app.security import security_config, validate_environment
from fastapi import Response
import secrets
from app.services.rate_limit import limiter, rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded

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

# Apply rate limiter middleware and handler
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(transaction.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(behavior_profile.router, prefix="/api")
app.include_router(geo.router, prefix="/api")
app.include_router(session_guardian.router, prefix="/api")
app.include_router(util.router, prefix="/api")

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
from app.api import auth, transaction, dashboard, admin, behavior_profile, geo
from app.api.session_guardian import session_guardian
from app.security import security_config, validate_environment

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))

# Validate environment configuration
validate_environment()

app = FastAPI(title="FinVault Backend", version="0.1.0")

# Apply security middleware
security_config.apply_security_middleware(app)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

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

@app.get("/csrf-token")
def get_csrf_token(response: Response):
    """Issue a CSRF token and set it as a cookie; also echo it in a header for convenience."""
    token = secrets.token_urlsafe(32)
    # SameSite=None to support cross-site usage; Secure in prod
    cookie_kwargs = {"samesite": "none", "path": "/"}
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        cookie_kwargs["secure"] = True
    response.set_cookie("csrf_token", token, **cookie_kwargs)
    return JSONResponse({"csrf": token}, headers={"X-CSRF-Token": token})

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(transaction.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(behavior_profile.router, prefix="/api")
app.include_router(geo.router, prefix="/api")
app.include_router(session_guardian.router, prefix="/api")
app.include_router(util.router, prefix="/api")

@app.on_event("startup")
async def on_startup():
    # Ensure Mongo indexes exist (TTL etc.)
    try:
        await ensure_mongo_indexes()
    except Exception as e:
        print(f"[Startup] Mongo index init failed: {e}")