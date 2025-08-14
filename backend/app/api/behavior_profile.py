from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.models.user import User
from app.schemas.behavior_profile import BehaviorProfileCreate, BehaviorProfileOut
from app.middlewares.rbac import require_roles
from app.database import mongo_db
from app.services.rate_limit import limiter
from typing import Any
from datetime import datetime

router = APIRouter()

@router.post("/behavior-profile", response_model=BehaviorProfileOut)
@limiter.limit("10/minute; 100/day")
async def create_or_update_behavior_profile(
    request: Request,
    profile: BehaviorProfileCreate,
    claims: dict = Depends(require_roles("user", "admin"))
):
    # Only allow update if verification passed and risk is low/medium
    if profile.verification_status != "passed" or profile.risk_level == "high":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Profile update not allowed due to failed verification or high risk.")
    user_id = profile.user_id or claims.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token (missing user_id).")
    # Optional: enforce token scope to be either 'access' or 'onboarding'
    scope = claims.get("scope", "access")
    if scope not in ("access", "onboarding"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient token scope.")
    # Upsert profile in MongoDB
    doc = profile.dict()
    doc["user_id"] = user_id
    if not doc.get("created_at"):
        doc["created_at"] = datetime.utcnow().isoformat()
    await mongo_db.behavior_profiles.update_one({"user_id": user_id}, {"$set": doc}, upsert=True)
    stored = await mongo_db.behavior_profiles.find_one({"user_id": user_id}, {"_id": 0})
    return stored or profile
