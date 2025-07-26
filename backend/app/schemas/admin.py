from pydantic import BaseModel
from typing import List, Optional, Dict, Any

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

class AdminRiskRule(BaseModel):
    rule: str
    value: Any

class AdminRiskRulesResponse(BaseModel):
    rules: List[AdminRiskRule]

class AdminRiskRuleUpdateRequest(BaseModel):
    rule: str
    value: Any

class HeatmapDataResponse(BaseModel):
    data: List[Dict[str, Any]] 