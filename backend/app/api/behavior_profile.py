from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.models.user import User
from app.schemas.behavior_profile import BehaviorProfileCreate, BehaviorProfileOut
from app.middlewares.rbac import require_roles
from app.database import mongo_db
from typing import Any

router = APIRouter()

@router.post("/behavior-profile", response_model=BehaviorProfileOut)
async def create_or_update_behavior_profile(
    profile: BehaviorProfileCreate,
    request: Request,
    user: User = Depends(require_roles("user", "admin"))
):
    # Only allow update if verification passed and risk is low/medium
    if profile.verification_status != "passed" or profile.risk_level == "high":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Profile update not allowed due to failed verification or high risk.")
    # Upsert profile in MongoDB
    mongo_db.behavior_profiles.update_one(
        {"user_id": user.id},
        {"$set": profile.dict()},
        upsert=True
    )
    return profile
