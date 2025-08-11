import os
from datetime import datetime, timedelta
from jose import jwt, JWTError
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))

JWT_SECRET = os.getenv("JWT_SECRET", "fallback-secret-key-for-development-only")
JWT_ALGORITHM = "HS256"

# Warn if using fallback secret
if JWT_SECRET == "fallback-secret-key-for-development-only":
    print("[WARNING] Using fallback JWT secret. Set JWT_SECRET environment variable for production.")


def create_magic_link_token(data: dict, expires_in_seconds: int = 900):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(seconds=expires_in_seconds)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_magic_link_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as e:
        print(f"[TokenService] Invalid or expired token: {e}")
        return None 