from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class AdminTransactionActionRequest(BaseModel):
    transaction_id: int
    action: str  # approve, block, flag
    reason: Optional[str]

class AdminTransactionActionResponse(BaseModel):
    message: str

class AdminUserUpdateRequest(BaseModel):
    name: Optional[str]
    phone: Optional[str]
    role: Optional[str]

class AdminUserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str]
    verified_at: Optional[str]
    role: str

class UserDetailResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str]
    verified_at: Optional[datetime]
    role: str
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    users: List[UserDetailResponse]

class TransactionListResponse(BaseModel):
    transactions: List[Dict[str, Any]]

class AdminRiskRule(BaseModel):
    rule: str
    value: Any

class AdminRiskRulesResponse(BaseModel):
    rules: List[AdminRiskRule]

class AdminRiskRuleUpdateRequest(BaseModel):
    rule: str
    value: Any

class AlertListResponse(BaseModel):
    alerts: List[Dict[str, Any]]

class SystemStatusResponse(BaseModel):
    status: str
    message: str
    timestamp: datetime

class HeatmapDataResponse(BaseModel):
    data: List[Dict[str, Any]] 