from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class BehaviorProfileCreate(BaseModel):
    user_id: int
    typing_pattern: Optional[Dict[str, Any]] = None
    mouse_dynamics: Optional[Dict[str, Any]] = None
    device_fingerprint: Optional[Dict[str, Any]] = None
    verification_status: str  # "passed" or "failed"
    risk_level: str  # "low", "medium", "high"

class BehaviorProfileOut(BaseModel):
    user_id: int
    typing_pattern: Optional[Dict[str, Any]] = None
    mouse_dynamics: Optional[Dict[str, Any]] = None
    device_fingerprint: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    verification_status: Optional[str] = None
    risk_level: Optional[str] = None