from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from typing import List

class TransactionBase(BaseModel):
    user_id: int
    amount: float
    target_account: Optional[str] = None
    recipient: Optional[str] = None
    device_info: Optional[str] = None
    location: Optional[str] = None
    intent: Optional[str] = None
    description: Optional[str] = None

class TransactionCreate(TransactionBase):
    pass

class TransactionRead(TransactionBase):
    id: int
    risk_score: Optional[float]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True 

class TransactionRequest(TransactionCreate):
    pass

class TransactionResponse(TransactionRead):
    pass

class TransactionListResponse(BaseModel):
    transactions: List[TransactionRead] 