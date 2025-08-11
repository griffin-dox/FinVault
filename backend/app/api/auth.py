from fastapi import APIRouter, Depends, HTTPException, status, Request, Body, Query
from app.schemas.auth import (
    RegisterRequest, RegisterResponse, VerifyRequest, VerifyResponse, OnboardingRequest, OnboardingResponse, LoginRequest, LoginResponse,
    WebAuthnVerifyRequest, BehavioralVerifyRequest, TrustedConfirmRequest, MagicLinkRequest, MagicLinkVerifyRequest, StepupResponse,
    WebAuthnRegisterBeginRequest, WebAuthnRegisterBeginResponse, WebAuthnRegisterCompleteRequest, WebAuthnRegisterCompleteResponse,
    WebAuthnAuthBeginRequest, WebAuthnAuthBeginResponse, WebAuthnAuthCompleteRequest, WebAuthnAuthCompleteResponse
)
from app.services.email_service import send_magic_link_email
from app.services.sms_service import send_magic_link_sms
from app.services.token_service import create_magic_link_token, verify_magic_link_token
from app.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import AsyncSessionLocal, mongo_db, redis_client, get_db
import os
from app.services.alert_service import trigger_alert
from app.services.audit_log_service import log_login_attempt
from math import radians, cos, sin, asin, sqrt
from datetime import datetime
import uuid
from fido2.server import Fido2Server
from fido2.webauthn import PublicKeyCredentialRpEntity, PublicKeyCredentialUserEntity
from fido2.utils import websafe_encode, websafe_decode
from fido2 import cbor
from jose import jwt, JWTError
from typing import Optional

RP_ID = os.environ.get("WEBAUTHN_RP_ID", "localhost")
RP_NAME = os.environ.get("WEBAUTHN_RP_NAME", "FinVault")
server = Fido2Server(PublicKeyCredentialRpEntity(RP_ID, RP_NAME))

router = APIRouter(prefix="/auth", tags=["auth"])

# ...existing route definitions...

@router.post("/context-question")
async def context_question(data: dict, db: AsyncSession = Depends(get_db)):
    identifier = data.get("identifier")
    # Example: get last login location from audit logs
    result = await db.execute(select(User).where((User.email == identifier) | (User.name == identifier) | (User.phone == identifier)))
    user = result.scalar_one_or_none()
    if not user:
        return {"question": "What is your registered email?"}
    # Fetch last login location from audit logs (mock)
    question = f"What city did you last log in from? (mock: use 'New York')"
    return {"question": question}

@router.post("/context-answer")
async def context_answer(data: dict, db: AsyncSession = Depends(get_db)):
    identifier = data.get("identifier")
    answer = data.get("answer")
    # Validate answer (mock: correct answer is 'New York')
    if answer.strip().lower() == "new york":
        return {"success": True}
    # Alert admins on failed verification
    trigger_alert("failed_additional_verification", f"User {identifier} failed security question.")
    return {"success": False, "message": "Incorrect answer. Try again. Admins have been notified."}

@router.post("/ambient-verify")
async def ambient_verify(data: dict, db: AsyncSession = Depends(get_db)):
    identifier = data.get("identifier")
    ambient = data.get("ambient", {})
    # Example: compare timezone and screen size (mock)
    expected_timezone = "America/New_York"
    expected_screen = "1920x1080"
    if ambient.get("timezone") == expected_timezone and ambient.get("screen") == expected_screen:
        return {"success": True}
    # Alert admins on failed ambient verification
    trigger_alert("failed_additional_verification", f"User {identifier} failed ambient authentication.")
    return {"success": False, "message": "Ambient data does not match profile. Admins have been notified."}
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body, Query
from app.schemas.auth import (
    RegisterRequest, RegisterResponse, VerifyRequest, VerifyResponse, OnboardingRequest, OnboardingResponse, LoginRequest, LoginResponse,
    WebAuthnVerifyRequest, BehavioralVerifyRequest, TrustedConfirmRequest, MagicLinkRequest, MagicLinkVerifyRequest, StepupResponse,
    WebAuthnRegisterBeginRequest, WebAuthnRegisterBeginResponse, WebAuthnRegisterCompleteRequest, WebAuthnRegisterCompleteResponse,
    WebAuthnAuthBeginRequest, WebAuthnAuthBeginResponse, WebAuthnAuthCompleteRequest, WebAuthnAuthCompleteResponse
)
from app.services.email_service import send_magic_link_email
from app.services.sms_service import send_magic_link_sms
from app.services.token_service import create_magic_link_token, verify_magic_link_token
from app.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import AsyncSessionLocal, mongo_db, redis_client, get_db
import os
from app.services.alert_service import trigger_alert
from app.services.audit_log_service import log_login_attempt
from math import radians, cos, sin, asin, sqrt
from datetime import datetime
import uuid
from fido2.server import Fido2Server
from fido2.webauthn import PublicKeyCredentialRpEntity, PublicKeyCredentialUserEntity
from fido2.utils import websafe_encode, websafe_decode
from fido2 import cbor
from fastapi import Depends
from jose import jwt, JWTError
from typing import Optional

RP_ID = os.environ.get("WEBAUTHN_RP_ID", "localhost")
RP_NAME = os.environ.get("WEBAUTHN_RP_NAME", "FinVault")
server = Fido2Server(PublicKeyCredentialRpEntity(RP_ID, RP_NAME))

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=RegisterResponse)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if user:
        # Check verification and onboarding status
        verified = bool(user.verified and user.verified_at)
        onboarding_complete = bool(mongo_db.behavior_profiles.find_one({"user_id": user.id}))
        raise HTTPException(
            status_code=409,
            detail={
                "message": "User already exists.",
                "verified": verified,
                "onboarding_complete": onboarding_complete
            }
        )
    # Create user
    new_user = User(name=data.name, email=data.email, phone=data.phone, role="user")
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    # Generate magic link token
    token = create_magic_link_token({"user_id": new_user.id, "email": new_user.email})
    magic_link = f"http://localhost:8000/auth/verify?token={token}"
    # Send magic link
    if data.email:
        send_magic_link_email(data.email, magic_link)
    if data.phone:
        send_magic_link_sms(data.phone, magic_link)
    return RegisterResponse(message="Registration successful. Please check your email or SMS for the magic link.")

@router.post("/verify", response_model=VerifyResponse)
async def verify(data: VerifyRequest, db: AsyncSession = Depends(get_db)):
    payload = verify_magic_link_token(data.token)
    if not payload:
        raise HTTPException(status_code=400, detail="Invalid or expired token.")
    user_id = payload.get("user_id")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    from datetime import datetime
    user.verified_at = datetime.utcnow()
    user.verified = True
    await db.commit()
    return VerifyResponse(message="Verification successful. You may now log in.")

@router.post("/onboarding", response_model=OnboardingResponse)
async def onboarding(data: OnboardingRequest):
    # Store behavioral profile in MongoDB
    profile = data.dict()
    mongo_db.behavior_profiles.insert_one(profile)
    return OnboardingResponse(message="Onboarding data recorded.")

def haversine(lat1, lon1, lat2, lon2):
    # Calculate the great circle distance between two points on the earth (specified in decimal degrees)
    if None in [lat1, lon1, lat2, lon2]:
        return float('inf')
    # convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r

def compare_typing(current, profile):
    reasons = []
    wpm_diff = abs(current.get('wpm', 0) - profile.get('wpm', 0))
    error_diff = abs(current.get('errorRate', 0) - profile.get('errorRate', 0))
    if wpm_diff > 10:
        reasons.append(f"Typing speed differs by {wpm_diff:.1f} WPM")
    if error_diff > 0.1:
        reasons.append(f"Error rate differs by {error_diff:.2f}")
    # Keystroke timings: compare mean/variance
    cur_timings = current.get('keystrokeTimings', [])
    prof_timings = profile.get('keystrokeTimings', [])
    if cur_timings and prof_timings:
        cur_mean = sum(cur_timings)/len(cur_timings)
        prof_mean = sum(prof_timings)/len(prof_timings)
        timing_diff = abs(cur_mean - prof_mean)
        if timing_diff > 100:
            reasons.append(f"Keystroke timing mean differs by {timing_diff:.0f}ms")
    return reasons

def compare_mouse(current, profile):
    reasons = []
    # Compare path length, jitter, clicks
    cur_path = current.get('path', [])
    prof_path = profile.get('path', [])
    if cur_path and prof_path:
        cur_len = len(cur_path)
        prof_len = len(prof_path)
        if abs(cur_len - prof_len) > 10:
            reasons.append(f"Mouse/touch path length differs by {abs(cur_len-prof_len)} points")
    cur_clicks = current.get('clicks', 0)
    prof_clicks = profile.get('clicks', 0)
    if abs(cur_clicks - prof_clicks) > 2:
        reasons.append(f"Click/tap count differs by {abs(cur_clicks-prof_clicks)}")
    return reasons

def compare_device(current, profile):
    reasons = []
    for k in ['browser', 'os', 'screen', 'timezone']:
        if current.get(k) and profile.get(k) and current.get(k) != profile.get(k):
            reasons.append(f"Device {k} mismatch: {current.get(k)} vs {profile.get(k)}")
    return reasons

def compare_geo(current, profile):
    reasons = []
    lat1, lon1 = current.get('latitude'), current.get('longitude')
    lat2, lon2 = profile.get('latitude'), profile.get('longitude')
    if lat1 and lon1 and lat2 and lon2:
        dist = haversine(lat1, lon1, lat2, lon2)
        if dist > 50:
            reasons.append(f"Geo location differs by {dist:.1f} km")
    return reasons

@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        # Debug logging
        print(f"[LOGIN] Attempting login for identifier: {data.identifier}")
        print(f"[LOGIN] Database session: {db is not None}")
        
        # Find user by identifier (email, phone, or username)
        user = None
        if db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
            
        result = await db.execute(select(User).where(User.email == data.identifier))
        user = result.scalar_one_or_none()
        if not user:
            result = await db.execute(select(User).where(User.phone == data.identifier))
            user = result.scalar_one_or_none()
        if not user:
            result = await db.execute(select(User).where(User.name == data.identifier))
            user = result.scalar_one_or_none()
            
        print(f"[LOGIN] User found: {user is not None}")
        
        # Prefer real device location for login event
        location = None
        geo = data.metrics.get('geo') if data.metrics else None
        if geo and not geo.get('fallback') and geo.get('latitude') and geo.get('longitude'):
            location = f"{geo['latitude']},{geo['longitude']}"
        elif data.metrics and data.metrics.get('ip'):
            location = data.metrics['ip']
        else:
            location = "unknown"
            
        if not user or not (user.verified and user.verified_at):
            print(f"[LOGIN] Login failed - user not found or not verified")
            trigger_alert("failed_login", f"Failed login for identifier {data.identifier}")
            await log_login_attempt(db, user_id=None, location=location, status="failure", details=f"identifier={data.identifier}")
            raise HTTPException(status_code=401, detail="User not found or not verified.")
            
        # --- Behavioral comparison ---
        profile = {}
        if mongo_db is not None:
            profile = await mongo_db.behavior_profiles.find_one({"user_id": user.id}) or {}
        else:
            print("[LOGIN] Warning: MongoDB not available, skipping behavioral analysis")
            
        reasons = []
        risk_score = 0
        
        # Typing
        if data.behavioral_challenge and data.behavioral_challenge.get('type') == 'typing':
            reasons += compare_typing(data.behavioral_challenge['data'], profile.get('typing_pattern', {}))
            if any("speed" in r or "error" in r or "timing" in r for r in reasons):
                risk_score += 10 * len([r for r in reasons if "speed" in r or "error" in r or "timing" in r])
                
        # Mouse/Touch
        if data.behavioral_challenge and data.behavioral_challenge.get('type') in ['mouse', 'touch']:
            reasons += compare_mouse(data.behavioral_challenge['data'], profile.get('mouse_dynamics', {}))
            if any("path" in r or "click" in r for r in reasons):
                risk_score += 10 * len([r for r in reasons if "path" in r or "click" in r])
                
        # Device
        if data.metrics:
            reasons += compare_device(data.metrics.get('device', {}), profile.get('device_fingerprint', {}))
            if any("Device" in r for r in reasons):
                risk_score += 20 * len([r for r in reasons if "Device" in r])
                
        # Geo
        if data.metrics:
            reasons += compare_geo(data.metrics.get('geo', {}), profile.get('geo', {}))
            if any("Geo" in r for r in reasons):
                risk_score += 20 * len([r for r in reasons if "Geo" in r])
                
        # Clamp risk score
        risk_score = min(risk_score, 100)
        
        print(f"[LOGIN] Risk score: {risk_score}, Reasons: {reasons}")
        
        # Decision
        # New thresholds: low (<=40), medium (41-60), high (>60)
        if risk_score > 60:
            trigger_alert("high_risk_login", f"Blocked login for user {user.id} (risk={risk_score})")
            await log_login_attempt(db, user_id=user.id, location=location, status="blocked", details=f"risk={risk_score}, reasons={reasons}")
            raise HTTPException(status_code=403, detail={"message": "High risk login detected. Blocked.", "risk": risk_score, "reasons": reasons})
        elif risk_score > 40:
            trigger_alert("medium_risk_login", f"Challenged login for user {user.id} (risk={risk_score})")
            await log_login_attempt(db, user_id=user.id, location=location, status="challenged", details=f"risk={risk_score}, reasons={reasons}")
            return LoginResponse(message="Medium risk: challenge required", token=None, risk="medium", reasons=reasons)
        else:
            trigger_alert("successful_login", f"User {user.id} logged in from device {getattr(data.metrics.get('device', {}), 'os', 'unknown')}")
            await log_login_attempt(db, user_id=user.id, location=location, status="success", details=f"risk={risk_score}, reasons={reasons}")
            token = create_magic_link_token({"user_id": user.id, "email": user.email}, expires_in_seconds=3600)
            print(f"[LOGIN] Login successful for user {user.id}")
            return LoginResponse(
                message="Login successful.",
                token=token,
                risk="low",
                reasons=reasons,
                user={
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role,
                    "risk": "low",
                    "verified": user.verified,
                    "lastLogin": datetime.utcnow().isoformat(),
                    "location": location
                }
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log unexpected errors
        print(f"[LOGIN] Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/verify-email")
async def verify_email(data: dict, db: AsyncSession = Depends(get_db)):
    email = data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required.")
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.verified and user.verified_at:
        return {"message": "Email already verified."}
    # In a real app, resend magic link here
    return {"message": "Verification email sent (mock)."}

@router.post("/complete-onboarding")
async def complete_onboarding(data: dict, db: AsyncSession = Depends(get_db)):
    email = data.get("email")
    behavior_profile = data.get("behaviorProfile")
    device_fingerprint = data.get("deviceFingerprint")
    if not email or not behavior_profile:
        raise HTTPException(status_code=400, detail="Email and behavior profile required.")
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    # Store profile in MongoDB
    mongo_db.behavior_profiles.insert_one({"user_id": user.id, **behavior_profile, "device_fingerprint": device_fingerprint})
    user.onboarding_complete = True
    await db.commit()
    return {"user": {"id": user.id, "email": user.email}}

@router.post("/feedback")
async def feedback(data: dict):
    # Store feedback in MongoDB for future learning
    mongo_db.risk_feedback.insert_one({
        "identifier": data.get("identifier"),
        "risk": data.get("risk"),
        "correct": data.get("correct"),
        "reasons": data.get("reasons"),
        "metrics": data.get("metrics"),
        "timestamp": datetime.utcnow(),
    })
    return {"message": "Feedback received"}

@router.post("/webauthn-verify", response_model=StepupResponse)
async def webauthn_verify(data: WebAuthnVerifyRequest, db: AsyncSession = Depends(get_db)):
    # TODO: Implement real WebAuthn verification
    mongo_db.stepup_logs.insert_one({
        "user": data.identifier,
        "method": "webauthn",
        "credential": data.credential,
        "timestamp": datetime.utcnow(),
        "success": True
    })
    # Issue dummy JWT for now
    token = create_magic_link_token({"user_id": 1, "email": data.identifier}, expires_in_seconds=3600)
    return StepupResponse(message="WebAuthn verified (stub)", token=token, risk="low")

@router.post("/behavioral-verify", response_model=StepupResponse)
async def behavioral_verify(data: BehavioralVerifyRequest, db: AsyncSession = Depends(get_db)):
    # Fetch user
    result = await db.execute(select(User).where(User.email == data.identifier))
    user = result.scalar_one_or_none()
    if not user:
        result = await db.execute(select(User).where(User.phone == data.identifier))
        user = result.scalar_one_or_none()
    if not user:
        result = await db.execute(select(User).where(User.name == data.identifier))
        user = result.scalar_one_or_none()
    if not user:
        mongo_db.stepup_logs.insert_one({"user": data.identifier, "method": "behavioral", "timestamp": datetime.utcnow(), "success": False, "reason": "User not found"})
        raise HTTPException(status_code=404, detail="User not found.")
    # Fetch behavioral profile
    profile = mongo_db.behavior_profiles.find_one({"user_id": user.id}) or {}
    reasons = []
    risk_score = 0
    # Typing
    if data.behavioral_challenge['type'] == 'typing':
        reasons += compare_typing(data.behavioral_challenge['data'], profile.get('typing_pattern', {}))
        if any("speed" in r or "error" in r or "timing" in r for r in reasons):
            risk_score += 10 * len([r for r in reasons if "speed" in r or "error" in r or "timing" in r])
    # Mouse/Touch
    if data.behavioral_challenge['type'] in ['mouse', 'touch']:
        reasons += compare_mouse(data.behavioral_challenge['data'], profile.get('mouse_dynamics', {}))
        if any("path" in r or "click" in r for r in reasons):
            risk_score += 10 * len([r for r in reasons if "path" in r or "click" in r])
    # Device
    reasons += compare_device(data.metrics.get('device', {}), profile.get('device_fingerprint', {}))
    if any("Device" in r for r in reasons):
        risk_score += 20 * len([r for r in reasons if "Device" in r])
    # Geo
    reasons += compare_geo(data.metrics.get('geo', {}), profile.get('geo', {}))
    if any("Geo" in r for r in reasons):
        risk_score += 20 * len([r for r in reasons if "Geo" in r])
    risk_score = min(risk_score, 100)
    mongo_db.stepup_logs.insert_one({
        "user": data.identifier,
        "method": "behavioral",
        "metrics": data.metrics,
        "challenge": data.behavioral_challenge,
        "timestamp": datetime.utcnow(),
        "success": risk_score <= 20,
        "risk_score": risk_score,
        "reasons": reasons
    })
    if risk_score > 20:
        raise HTTPException(status_code=403, detail={"message": "Behavioral step-up failed", "risk": risk_score, "reasons": reasons})
    # Continuous learning: append new pattern
    update = {}
    if data.behavioral_challenge['type'] == 'typing':
        patterns = profile.get('typing_patterns', [])
        patterns.append(data.behavioral_challenge['data'])
        update['typing_patterns'] = patterns[-10:]  # keep last 10
        update['typing_pattern'] = data.behavioral_challenge['data']  # update latest summary
    if data.behavioral_challenge['type'] in ['mouse', 'touch']:
        patterns = profile.get('mouse_patterns', [])
        patterns.append(data.behavioral_challenge['data'])
        update['mouse_patterns'] = patterns[-10:]
        update['mouse_dynamics'] = data.behavioral_challenge['data']
    mongo_db.behavior_profiles.update_one({"user_id": user.id}, {"$set": update}, upsert=True)
    token = create_magic_link_token({"user_id": user.id, "email": user.email}, expires_in_seconds=3600)
    return StepupResponse(message="Behavioral verified", token=token, risk="low")

@router.post("/trusted-confirm", response_model=StepupResponse)
async def trusted_confirm(data: TrustedConfirmRequest, db: AsyncSession = Depends(get_db)):
    # Fetch user
    result = await db.execute(select(User).where(User.email == data.identifier))
    user = result.scalar_one_or_none()
    if not user:
        result = await db.execute(select(User).where(User.phone == data.identifier))
        user = result.scalar_one_or_none()
    if not user:
        result = await db.execute(select(User).where(User.name == data.identifier))
        user = result.scalar_one_or_none()
    if not user:
        mongo_db.stepup_logs.insert_one({"user": data.identifier, "method": "trusted_device", "timestamp": datetime.utcnow(), "success": False, "reason": "User not found"})
        raise HTTPException(status_code=404, detail="User not found.")
    # Check trusted devices
    trusted = mongo_db.trusted_devices.find_one({"user": data.identifier, "device": data.device, "ip": data.ip})
    if not trusted:
        mongo_db.stepup_logs.insert_one({"user": data.identifier, "method": "trusted_device", "timestamp": datetime.utcnow(), "success": False, "reason": "Device not trusted"})
        raise HTTPException(status_code=403, detail={"message": "Device not trusted. Use magic link.", "risk": "medium"})
    mongo_db.stepup_logs.insert_one({"user": data.identifier, "method": "trusted_device", "timestamp": datetime.utcnow(), "success": True})
    token = create_magic_link_token({"user_id": user.id, "email": user.email}, expires_in_seconds=3600)
    return StepupResponse(message="Trusted device confirmed", token=token, risk="low")

@router.post("/send-magic-link", response_model=StepupResponse)
async def send_magic_link(data: MagicLinkRequest, db: AsyncSession = Depends(get_db)):
    # Fetch user
    result = await db.execute(select(User).where(User.email == data.identifier))
    user = result.scalar_one_or_none()
    if not user:
        result = await db.execute(select(User).where(User.phone == data.identifier))
        user = result.scalar_one_or_none()
    if not user:
        result = await db.execute(select(User).where(User.name == data.identifier))
        user = result.scalar_one_or_none()
    if not user:
        mongo_db.stepup_logs.insert_one({"user": data.identifier, "method": "magic_link", "timestamp": datetime.utcnow(), "success": False, "reason": "User not found"})
        raise HTTPException(status_code=404, detail="User not found.")
    # Generate secure token
    token = str(uuid.uuid4())
    expires_at = datetime.utcnow().timestamp() + 600  # 10 minutes
    mongo_db.magic_links.insert_one({
        "user_id": user.id,
        "email": user.email,
        "token": token,
        "expires_at": expires_at,
        "used": False,
        "created_at": datetime.utcnow()
    })
    # Send email with link
    link = f"http://localhost:8000/api/auth/magic-link/verify?token={token}"
    send_magic_link_email(user.email, link)
    mongo_db.stepup_logs.insert_one({"user": data.identifier, "method": "magic_link", "timestamp": datetime.utcnow(), "success": True})
    return StepupResponse(message="Magic link sent to your email.", token=None, risk="medium")

@router.get("/magic-link/verify", response_model=StepupResponse)
async def magic_link_verify(token: str):
    # Lookup token
    entry = mongo_db.magic_links.find_one({"token": token})
    if not entry:
        mongo_db.stepup_logs.insert_one({"method": "magic_link_verify", "token": token, "timestamp": datetime.utcnow(), "success": False, "reason": "Token not found"})
        raise HTTPException(status_code=404, detail="Invalid or expired magic link.")
    if entry.get("used"):
        mongo_db.stepup_logs.insert_one({"method": "magic_link_verify", "token": token, "timestamp": datetime.utcnow(), "success": False, "reason": "Token already used"})
        raise HTTPException(status_code=400, detail="Magic link already used. Please request a new one.")
    if datetime.utcnow().timestamp() > entry["expires_at"]:
        mongo_db.stepup_logs.insert_one({"method": "magic_link_verify", "token": token, "timestamp": datetime.utcnow(), "success": False, "reason": "Token expired"})
        raise HTTPException(status_code=400, detail="Magic link expired. Please request a new one.")
    # Mark as used
    mongo_db.magic_links.update_one({"token": token}, {"$set": {"used": True, "used_at": datetime.utcnow()}})
    # Issue JWT
    user_id = entry["user_id"]
    email = entry["email"]
    token_jwt = create_magic_link_token({"user_id": user_id, "email": email}, expires_in_seconds=3600)
    mongo_db.stepup_logs.insert_one({"method": "magic_link_verify", "token": token, "timestamp": datetime.utcnow(), "success": True, "user_id": user_id})
    return StepupResponse(message="Magic link verified. You are now logged in.", token=token_jwt, risk="low")

@router.post("/webauthn/register/begin", response_model=WebAuthnRegisterBeginResponse)
async def webauthn_register_begin(data: WebAuthnRegisterBeginRequest):
    user = mongo_db.users.find_one({"$or": [
        {"email": data.identifier},
        {"phone": data.identifier},
        {"name": data.identifier}
    ]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user_entity = PublicKeyCredentialUserEntity(
        id=str(user["_id"]).encode(),
        name=user["email"],
        display_name=user.get("name", user["email"])
    )
    registration_data, state = server.register_begin(user_entity, user_verification="preferred")
    challenge_id = str(uuid.uuid4())
    redis_client.setex(f"webauthn:register:{challenge_id}", 600, cbor.dumps(state))
    return WebAuthnRegisterBeginResponse(publicKey=registration_data, challenge_id=challenge_id)

@router.post("/webauthn/register/complete", response_model=WebAuthnRegisterCompleteResponse)
async def webauthn_register_complete(data: WebAuthnRegisterCompleteRequest):
    state = redis_client.get(f"webauthn:register:{data.challenge_id}")
    if not state:
        raise HTTPException(status_code=400, detail="Registration challenge expired or invalid.")
    state = cbor.loads(state)
    attestation_object = websafe_decode(data.credential["response"]["attestationObject"])
    client_data_json = websafe_decode(data.credential["response"]["clientDataJSON"])
    auth_data = server.register_complete(state, data.credential, attestation_object, client_data_json)
    # Store credential
    mongo_db.webauthn_credentials.insert_one({
        "user_identifier": data.identifier,
        "credential_id": data.credential["id"],
        "public_key": auth_data.credential_public_key,
        "sign_count": auth_data.sign_count,
        "aaguid": getattr(auth_data, "aaguid", None),
        "device": data.credential.get("authenticatorAttachment"),
        "transports": data.credential.get("transports"),
        "created_at": datetime.utcnow()
    })
    return WebAuthnRegisterCompleteResponse(success=True, message="WebAuthn credential registered.")

@router.post("/webauthn/auth/begin", response_model=WebAuthnAuthBeginResponse)
async def webauthn_auth_begin(data: WebAuthnAuthBeginRequest):
    creds = list(mongo_db.webauthn_credentials.find({"user_identifier": data.identifier}))
    if not creds:
        raise HTTPException(status_code=404, detail="No WebAuthn credentials found for user.")
    allow_credentials = [{
        "type": "public-key",
        "id": c["credential_id"]
    } for c in creds]
    auth_data, state = server.authenticate_begin(allow_credentials=allow_credentials, user_verification="preferred")
    challenge_id = str(uuid.uuid4())
    redis_client.setex(f"webauthn:auth:{challenge_id}", 600, cbor.dumps(state))
    return WebAuthnAuthBeginResponse(publicKey=auth_data, challenge_id=challenge_id)

@router.post("/webauthn/auth/complete", response_model=WebAuthnAuthCompleteResponse)
async def webauthn_auth_complete(data: WebAuthnAuthCompleteRequest):
    state = redis_client.get(f"webauthn:auth:{data.challenge_id}")
    if not state:
        raise HTTPException(status_code=400, detail="Authentication challenge expired or invalid.")
    state = cbor.loads(state)
    creds = list(mongo_db.webauthn_credentials.find({"user_identifier": data.identifier}))
    if not creds:
        raise HTTPException(status_code=404, detail="No WebAuthn credentials found for user.")
    credential_id = data.credential["id"]
    cred = next((c for c in creds if c["credential_id"] == credential_id), None)
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found.")
    auth_data = server.authenticate_complete(state, cred, data.credential)
    # Update sign_count
    mongo_db.webauthn_credentials.update_one({"credential_id": credential_id}, {"$set": {"sign_count": auth_data.new_sign_count}})
    # Log success
    mongo_db.stepup_logs.insert_one({
        "user": data.identifier,
        "method": "webauthn",
        "credential_id": credential_id,
        "timestamp": datetime.utcnow(),
        "success": True
    })
    # Issue JWT
    user = mongo_db.users.find_one({"$or": [
        {"email": data.identifier},
        {"phone": data.identifier},
        {"name": data.identifier}
    ]})
    token = create_magic_link_token({"user_id": str(user["_id"]), "email": user["email"]}, expires_in_seconds=3600)
    return WebAuthnAuthCompleteResponse(success=True, message="WebAuthn authentication successful.", token=token)

# Helper to get current user email from JWT (for demo, fallback to query param)
def get_current_user_email(request: Request, email: Optional[str] = Query(None)):
    auth = request.headers.get("authorization") or request.cookies.get("access_token")
    if auth and auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, os.environ.get("JWT_SECRET", "secret"), algorithms=["HS256"])
            return payload.get("email")
        except JWTError:
            pass
    return email

@router.get("/webauthn/devices")
async def get_webauthn_devices(request: Request, email: Optional[str] = Query(None)):
    user_email = get_current_user_email(request, email)
    if not user_email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    devices = list(mongo_db.webauthn_credentials.find({"user_identifier": user_email}))
    for d in devices:
        d["_id"] = str(d["_id"])
        d["created_at"] = d.get("created_at") and d["created_at"].isoformat()
    return {"devices": devices}

@router.post("/webauthn/device/remove")
async def remove_webauthn_device(request: Request, data: dict):
    credential_id = data.get("credential_id")
    if not credential_id:
        raise HTTPException(status_code=400, detail="Missing credential_id")
    user_email = get_current_user_email(request, data.get("email"))
    if not user_email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = mongo_db.webauthn_credentials.delete_one({"user_identifier": user_email, "credential_id": credential_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Device not found or not owned by user")
    mongo_db.stepup_logs.insert_one({
        "user": user_email,
        "method": "webauthn_remove",
        "credential_id": credential_id,
        "timestamp": datetime.utcnow(),
        "success": True
    })
    return {"success": True, "message": "Device removed"} 