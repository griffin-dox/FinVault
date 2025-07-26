from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from typing import List

class TransactionBase(BaseModel):
    user_id: int
    amount: float
    target_account: str
    device_info: Optional[str]
    location: Optional[str]
    intent: Optional[str]

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