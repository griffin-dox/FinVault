from pydantic import BaseModel
from typing import Optional, List

class TransactionRequest(BaseModel):
    user_id: int
    amount: float
    target_account: str
    device_info: Optional[str]
    location: Optional[str]
    intent: Optional[str]

class TransactionResponse(BaseModel):
    status: str  # allowed, challenged, blocked
    risk_score: float
    risk_level: str
    reasons: List[str]
    message: Optional[str] 