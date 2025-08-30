from pydantic import BaseModel, EmailStr
from typing import Optional

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str]
    country: Optional[str] = None

class RegisterResponse(BaseModel):
    message: str
    user_id: int
    email: str

class VerifyRequest(BaseModel):
    token: str

class VerifyResponse(BaseModel):
    message: str
    onboarding_required: bool | None = None
    token: Optional[str] = None

class OnboardingRequest(BaseModel):
    user_id: Optional[int] = None
    typing_pattern: Optional[dict]
    mouse_dynamics: Optional[dict]
    touch_interaction: Optional[dict] = None
    scroll_behavior: Optional[dict] = None
    drag_drop: Optional[dict] = None
    geo: Optional[dict] = None
    device_fingerprint: Optional[dict]

class OnboardingResponse(BaseModel):
    message: str

class LoginRequest(BaseModel):
    identifier: str
    behavioral_challenge: dict  # or a more specific model if desired
    metrics: dict  # or a more specific model if desired

class LoginResponse(BaseModel):
    message: str
    token: Optional[str]
    risk: Optional[str] = None
    reasons: Optional[list] = []
    user: Optional[dict] = None

class WebAuthnVerifyRequest(BaseModel):
    identifier: str
    credential: dict

class BehavioralVerifyRequest(BaseModel):
    identifier: str
    behavioral_challenge: dict
    metrics: dict

class TrustedConfirmRequest(BaseModel):
    identifier: str
    device: dict
    ip: str

class MagicLinkRequest(BaseModel):
    identifier: str

class MagicLinkVerifyRequest(BaseModel):
    token: str

class StepupResponse(BaseModel):
    message: str
    token: Optional[str]
    risk: Optional[str] = None 

class WebAuthnRegisterBeginRequest(BaseModel):
    identifier: str

class WebAuthnRegisterBeginResponse(BaseModel):
    publicKey: dict
    challenge_id: str

class WebAuthnRegisterCompleteRequest(BaseModel):
    identifier: str
    credential: dict
    challenge_id: str

class WebAuthnRegisterCompleteResponse(BaseModel):
    success: bool
    message: str

class WebAuthnAuthBeginRequest(BaseModel):
    identifier: str

class WebAuthnAuthBeginResponse(BaseModel):
    publicKey: dict
    challenge_id: str

class WebAuthnAuthCompleteRequest(BaseModel):
    identifier: str
    credential: dict
    challenge_id: str

class WebAuthnAuthCompleteResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None


class JWTLoginRequest(BaseModel):
    identifier: str
    behavioral_challenge: dict
    metrics: dict


class JWTLoginResponse(BaseModel):
    message: str
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: dict


class JWTRefreshRequest(BaseModel):
    refresh_token: str


class JWTRefreshResponse(BaseModel):
    message: str
    access_token: str
    token_type: str
    expires_in: int


class JWTLogoutResponse(BaseModel):
    message: str 