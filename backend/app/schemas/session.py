from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SessionBase(BaseModel):
    user_id: int
    jwt_token: str
    device_info: Optional[str]
    login_time: datetime

class SessionCreate(SessionBase):
    session_id: str

class SessionRead(SessionBase):
    session_id: str

    class Config:
        from_attributes = True 