from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
from fastapi import Request

# Global limiter instance for the app
limiter = Limiter(key_func=get_remote_address, default_limits=[])


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "detail": {
                "message": "Too many requests, please slow down.",
                "limit": str(exc.detail),
            }
        },
    )
