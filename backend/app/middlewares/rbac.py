from fastapi import Depends, HTTPException, status, Request
from jose import jwt, JWTError
from app.services.token_service import JWT_SECRET as TS_JWT_SECRET, JWT_ALGORITHM as TS_JWT_ALG

def _extract_bearer_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth.split(" ", 1)[1]
    # Optional: cookie fallback
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token
    return None

# Dependency to extract full JWT claims
def get_current_claims(request: Request) -> dict:
    token = _extract_bearer_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid token.")
    try:
        payload = jwt.decode(token, TS_JWT_SECRET, algorithms=[TS_JWT_ALG])
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")

# Dependency to require specific roles; returns claims for downstream usage
def require_roles(*roles: str):
    def dependency(claims: dict = Depends(get_current_claims)):
        role = claims.get("role", "user")
        if role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions.")
        return claims
    return dependency