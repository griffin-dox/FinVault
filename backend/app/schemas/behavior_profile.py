from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class BehaviorProfile(BaseModel):
    user_id: int
    typing_pattern: Optional[Dict[str, Any]] = None
    mouse_dynamics: Optional[Dict[str, Any]] = None
    device_fingerprint: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None 