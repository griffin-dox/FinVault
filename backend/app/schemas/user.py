from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None

class UserCreate(UserBase):
    pass

class UserRead(UserBase):
    id: int
    verified_at: Optional[datetime]
    role: str

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    name: Optional[str]
    phone: Optional[str]
    role: Optional[str] 