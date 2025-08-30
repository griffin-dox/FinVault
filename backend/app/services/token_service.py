import os
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))

JWT_SECRET = os.getenv("JWT_SECRET", "fallback-secret-key-for-development-only")
JWT_ALGORITHM = "HS256"

# Warn if using fallback secret
if JWT_SECRET == "fallback-secret-key-for-development-only":
    print("[WARNING] Using fallback JWT secret. Set JWT_SECRET environment variable for production.")


def create_magic_link_token(data: dict, expires_in_seconds: int = 900, scope: str | None = None):
    """Generic token creator (JWT). Optionally include a scope claim and custom expiry."""
    to_encode = data.copy()
    if scope:
        to_encode["scope"] = scope
    expire = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_access_token(data: dict, expires_in_seconds: int = 900):
    """Create a short-lived access token (15 minutes default)."""
    return create_magic_link_token(data, expires_in_seconds=expires_in_seconds, scope="access")


def create_refresh_token(data: dict, expires_in_seconds: int = 604800):
    """Create a long-lived refresh token (7 days default)."""
    return create_magic_link_token(data, expires_in_seconds=expires_in_seconds, scope="refresh")


def create_jwt_token_pair(data: dict, access_expires_in: int = 900, refresh_expires_in: int = 604800):
    """Create both access and refresh tokens."""
    access_token = create_access_token(data, access_expires_in)
    refresh_token = create_refresh_token(data, refresh_expires_in)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": access_expires_in
    }


def verify_magic_link_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as e:
        print(f"[TokenService] Invalid or expired token: {e}")
        return None


def verify_refresh_token(token: str):
    """Verify a refresh token and return the payload."""
    payload = verify_magic_link_token(token)
    if payload and payload.get("scope") == "refresh":
        return payload
    return None


def refresh_access_token(refresh_token: str):
    """Create a new access token from a valid refresh token."""
    payload = verify_refresh_token(refresh_token)
    if not payload:
        return None
    
    # Remove token-specific claims and create new access token
    token_data = {k: v for k, v in payload.items() if k not in ["exp", "scope"]}
    return create_access_token(token_data) 