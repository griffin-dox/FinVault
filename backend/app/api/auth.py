from fastapi import APIRouter, Depends, HTTPException, status, Request, Body, Query, Response
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
from sqlalchemy.exc import IntegrityError
from app.database import AsyncSessionLocal, mongo_db, redis_client, get_db
import os
from app.services.alert_service import trigger_alert
from app.services.audit_log_service import log_login_attempt
from math import radians, cos, sin, asin, sqrt
from datetime import datetime, timedelta
import uuid
from fido2.server import Fido2Server
from fido2.webauthn import PublicKeyCredentialRpEntity, PublicKeyCredentialUserEntity
from fido2.utils import websafe_encode, websafe_decode
from fido2 import cbor
from jose import jwt, JWTError
from app.services.token_service import JWT_SECRET as TS_JWT_SECRET, JWT_ALGORITHM as TS_JWT_ALG
from typing import Optional
import ipaddress
from app.services.risk_engine import typing_penalty, mouse_penalty
from app.services.rate_limit import limiter

RP_ID = os.environ.get("WEBAUTHN_RP_ID", "localhost")
RP_NAME = os.environ.get("WEBAUTHN_RP_NAME", "FinVault")
server = Fido2Server(PublicKeyCredentialRpEntity(RP_ID, RP_NAME))

router = APIRouter(prefix="/auth", tags=["auth"])

# Cookie policy: default to Lax in development (same-site localhost), None in production
ENV = os.environ.get("ENVIRONMENT", "development").lower()
COOKIE_SAMESITE_DEFAULT = "none" if ENV == "production" else "lax"

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
async def context_answer(request: Request, data: dict, db: AsyncSession = Depends(get_db), response: Response = None):
    identifier = data.get("identifier")
    answer = data.get("answer")
    # Validate answer (mock: correct answer is 'New York')
    if answer and answer.strip().lower() == "new york":
        # On success, issue auth cookies and treat as low risk (policy: grant access)
        # Resolve user by identifier
        user = None
        if db is not None and identifier:
            result = await db.execute(select(User).where(User.email == identifier))
            user = result.scalar_one_or_none()
            if not user:
                result = await db.execute(select(User).where(User.phone == identifier))
                user = result.scalar_one_or_none()
            if not user:
                result = await db.execute(select(User).where(User.name == identifier))
                user = result.scalar_one_or_none()
        if not user:
            # If user cannot be resolved, fail gracefully
            trigger_alert("failed_additional_verification", f"User {identifier} passed challenge but user not found.")
            raise HTTPException(status_code=404, detail="User not found.")
        # Create access token and set cookies (HttpOnly access_token + CSRF token)
        token = create_magic_link_token({
            "user_id": user.id,
            "email": user.email,
            "role": getattr(user, "role", "user")
        }, expires_in_seconds=3600, scope="access")
        try:
            if response is not None:
                import secrets
                csrf_token = secrets.token_urlsafe(24)
                response.set_cookie(
                    key="access_token",
                    value=token,
                    httponly=True,
                    secure=bool(int(os.environ.get("COOKIE_SECURE", "0"))),
                    samesite=os.environ.get("COOKIE_SAMESITE", COOKIE_SAMESITE_DEFAULT),
                    max_age=3600,
                    path="/"
                )
                response.set_cookie(
                    key="csrf_token",
                    value=csrf_token,
                    httponly=False,
                    secure=bool(int(os.environ.get("COOKIE_SECURE", "0"))),
                    samesite=os.environ.get("COOKIE_SAMESITE", COOKIE_SAMESITE_DEFAULT),
                    max_age=3600,
                    path="/"
                )
        except Exception as _ce:
            print(f"[STEPUP][context-answer] Cookie set error: {_ce}")
        # Audit success as login success after step-up
        try:
            await log_login_attempt(db, user_id=user.id, location="stepup_context", status="success", details="stepup_context_success")
        except Exception:
            pass
        # Learning: treat step-up success as successful login and enrich profile (only on success)
        try:
            metrics = data.get("metrics") or {}
            ambient = data.get("ambient") or {}
            # Derive client IP if not provided
            the_ip = metrics.get('ip') if isinstance(metrics, dict) else None
            if not the_ip:
                the_ip = request.headers.get('cf-connecting-ip') or request.headers.get('CF-Connecting-IP')
            if not the_ip:
                xff = request.headers.get('x-forwarded-for') or request.headers.get('X-Forwarded-For')
                if xff:
                    the_ip = xff.split(',')[0].strip()
            if not the_ip:
                the_ip = request.headers.get('x-real-ip') or request.headers.get('X-Real-IP')
            if not the_ip and request.client:
                the_ip = request.client.host
            ip_prefix = None
            if the_ip:
                try:
                    ip_obj = ipaddress.ip_address(the_ip)
                    if isinstance(ip_obj, ipaddress.IPv4Address):
                        ip_prefix = str(ipaddress.ip_network(f"{the_ip}/24", strict=False))
                    else:
                        ip_prefix = str(ipaddress.ip_network(f"{the_ip}/64", strict=False))
                except ValueError:
                    ip_prefix = None
            update_doc = {"last_seen": datetime.utcnow()}
            # Device fingerprint (best-effort from provided ambient/metrics)
            device_metrics = (metrics.get('device') or {}) if isinstance(metrics, dict) else {}
            core_device = {}
            for k in ["browser", "os", "screen", "timezone"]:
                if device_metrics.get(k) is not None:
                    core_device[k] = device_metrics.get(k)
            # Fill from ambient if present
            if ambient.get("screen") and not core_device.get("screen"):
                core_device["screen"] = ambient["screen"]
            if ambient.get("timezone") and not core_device.get("timezone"):
                core_device["timezone"] = ambient["timezone"]
            if core_device:
                update_doc["device_fingerprint"] = core_device
            # Behavior signature
            try:
                import hashlib, json
                sig_core = {k: v for k, v in core_device.items() if v is not None}
                if ip_prefix:
                    sig_core["ip_prefix"] = ip_prefix
                if sig_core:
                    update_doc["behavior_signature"] = hashlib.sha256(json.dumps(sig_core, sort_keys=True).encode()).hexdigest()
            except Exception:
                pass
            # Pull existing to update streak/version
            existing = await mongo_db.behavior_profiles.find_one({"user_id": user.id}) or {}
            low_streak = int(existing.get("low_risk_streak", 0)) + 1
            baseline_version = int(existing.get("baseline_version", 0)) + 1
            baseline_stable = existing.get("baseline_stable", False) or (low_streak >= 5)
            update_doc["low_risk_streak"] = low_streak
            update_doc["baseline_version"] = baseline_version
            update_doc["baseline_stable"] = baseline_stable
            # Keep short history of versions
            history_entry = {"version": baseline_version, "timestamp": datetime.utcnow(), "baselines": existing.get("baselines", {})}
            update_ops = {"$set": update_doc, "$push": {"baseline_history": {"$each": [history_entry], "$slice": -3}}}
            if ip_prefix:
                update_ops["$addToSet"] = {"known_networks": ip_prefix}
            await mongo_db.behavior_profiles.update_one({"user_id": user.id}, update_ops, upsert=True)
        except Exception as _learn_e:
            print(f"[STEPUP][context-answer] Learning error: {_learn_e}")
        return {
            "success": True,
            "message": "Verified",
            "risk": "low",
            "token": token,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": getattr(user, 'role', 'user'),
                "risk": "low",
                "riskLevel": "low",
                "isVerified": user.verified,
                "isAdmin": getattr(user, 'role', '') == 'admin' or getattr(user, 'is_admin', False),
                "lastLogin": datetime.utcnow().isoformat(),
                "location": "stepup_context"
            }
        }
    # Alert admins on failed verification
    trigger_alert("failed_additional_verification", f"User {identifier} failed security question.")
    return {"success": False, "message": "Incorrect answer. Try again. Admins have been notified."}

@router.post("/ambient-verify")
async def ambient_verify(request: Request, data: dict, db: AsyncSession = Depends(get_db), response: Response = None):
    identifier = data.get("identifier")
    ambient = data.get("ambient", {})
    # Example: compare timezone and screen size (mock)
    expected_timezone = "America/New_York"
    expected_screen = "1920x1080"
    if ambient.get("timezone") == expected_timezone and ambient.get("screen") == expected_screen:
        # On success, issue auth cookies and treat as low risk (policy: grant access)
        user = None
        if db is not None and identifier:
            result = await db.execute(select(User).where(User.email == identifier))
            user = result.scalar_one_or_none()
            if not user:
                result = await db.execute(select(User).where(User.phone == identifier))
                user = result.scalar_one_or_none()
            if not user:
                result = await db.execute(select(User).where(User.name == identifier))
                user = result.scalar_one_or_none()
        if not user:
            trigger_alert("failed_additional_verification", f"User {identifier} passed ambient but user not found.")
            raise HTTPException(status_code=404, detail="User not found.")
        token = create_magic_link_token({
            "user_id": user.id,
            "email": user.email,
            "role": getattr(user, "role", "user")
        }, expires_in_seconds=3600, scope="access")
        try:
            if response is not None:
                import secrets
                csrf_token = secrets.token_urlsafe(24)
                response.set_cookie(
                    key="access_token",
                    value=token,
                    httponly=True,
                    secure=bool(int(os.environ.get("COOKIE_SECURE", "0"))),
                    samesite=os.environ.get("COOKIE_SAMESITE", COOKIE_SAMESITE_DEFAULT),
                    max_age=3600,
                    path="/"
                )
                response.set_cookie(
                    key="csrf_token",
                    value=csrf_token,
                    httponly=False,
                    secure=bool(int(os.environ.get("COOKIE_SECURE", "0"))),
                    samesite=os.environ.get("COOKIE_SAMESITE", COOKIE_SAMESITE_DEFAULT),
                    max_age=3600,
                    path="/"
                )
        except Exception as _ce:
            print(f"[STEPUP][ambient-verify] Cookie set error: {_ce}")
        try:
            await log_login_attempt(db, user_id=user.id, location="stepup_ambient", status="success", details="stepup_ambient_success")
        except Exception:
            pass
        # Learning: treat ambient step-up success as successful login and enrich profile
        try:
            metrics = data.get("metrics") or {}
            ambient = data.get("ambient") or {}
            # Derive client IP
            the_ip = metrics.get('ip') if isinstance(metrics, dict) else None
            if not the_ip:
                the_ip = request.headers.get('cf-connecting-ip') or request.headers.get('CF-Connecting-IP')
            if not the_ip:
                xff = request.headers.get('x-forwarded-for') or request.headers.get('X-Forwarded-For')
                if xff:
                    the_ip = xff.split(',')[0].strip()
            if not the_ip:
                the_ip = request.headers.get('x-real-ip') or request.headers.get('X-Real-IP')
            if not the_ip and request.client:
                the_ip = request.client.host
            ip_prefix = None
            if the_ip:
                try:
                    ip_obj = ipaddress.ip_address(the_ip)
                    if isinstance(ip_obj, ipaddress.IPv4Address):
                        ip_prefix = str(ipaddress.ip_network(f"{the_ip}/24", strict=False))
                    else:
                        ip_prefix = str(ipaddress.ip_network(f"{the_ip}/64", strict=False))
                except ValueError:
                    ip_prefix = None
            update_doc = {"last_seen": datetime.utcnow()}
            # Device from ambient and metrics
            device_metrics = (metrics.get('device') or {}) if isinstance(metrics, dict) else {}
            core_device = {}
            for k in ["browser", "os", "screen", "timezone"]:
                if device_metrics.get(k) is not None:
                    core_device[k] = device_metrics.get(k)
            if ambient.get("screen") and not core_device.get("screen"):
                core_device["screen"] = ambient["screen"]
            if ambient.get("timezone") and not core_device.get("timezone"):
                core_device["timezone"] = ambient["timezone"]
            if core_device:
                update_doc["device_fingerprint"] = core_device
            # Behavior signature
            try:
                import hashlib, json
                sig_core = {k: v for k, v in core_device.items() if v is not None}
                if ip_prefix:
                    sig_core["ip_prefix"] = ip_prefix
                if sig_core:
                    update_doc["behavior_signature"] = hashlib.sha256(json.dumps(sig_core, sort_keys=True).encode()).hexdigest()
            except Exception:
                pass
            existing = await mongo_db.behavior_profiles.find_one({"user_id": user.id}) or {}
            low_streak = int(existing.get("low_risk_streak", 0)) + 1
            baseline_version = int(existing.get("baseline_version", 0)) + 1
            baseline_stable = existing.get("baseline_stable", False) or (low_streak >= 5)
            update_doc["low_risk_streak"] = low_streak
            update_doc["baseline_version"] = baseline_version
            update_doc["baseline_stable"] = baseline_stable
            history_entry = {"version": baseline_version, "timestamp": datetime.utcnow(), "baselines": existing.get("baselines", {})}
            update_ops = {"$set": update_doc, "$push": {"baseline_history": {"$each": [history_entry], "$slice": -3}}}
            if ip_prefix:
                update_ops["$addToSet"] = {"known_networks": ip_prefix}
            await mongo_db.behavior_profiles.update_one({"user_id": user.id}, update_ops, upsert=True)
        except Exception as _learn_e:
            print(f"[STEPUP][ambient-verify] Learning error: {_learn_e}")
        return {
            "success": True,
            "message": "Ambient verified",
            "risk": "low",
            "token": token,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": getattr(user, 'role', 'user'),
                "risk": "low",
                "riskLevel": "low",
                "isVerified": user.verified,
                "isAdmin": getattr(user, 'role', '') == 'admin' or getattr(user, 'is_admin', False),
                "lastLogin": datetime.utcnow().isoformat(),
                "location": "stepup_ambient"
            }
        }
    # Alert admins on failed ambient verification
    trigger_alert("failed_additional_verification", f"User {identifier} failed ambient authentication.")
    return {"success": False, "message": "Ambient data does not match profile. Admins have been notified."}

@router.post("/register", response_model=RegisterResponse)
@limiter.limit("5/minute; 50/day")
async def register(request: Request, data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    # Check by email first
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if user:
        verified = bool(user.verified and user.verified_at)
        onboarding_complete = bool(await mongo_db.behavior_profiles.find_one({"user_id": user.id}))
        raise HTTPException(status_code=409, detail={
            "message": "Email already registered.",
            "verified": verified,
            "onboarding_complete": onboarding_complete
        })
    # Check by phone if provided
    if data.phone:
        result = await db.execute(select(User).where(User.phone == data.phone))
        user_by_phone = result.scalar_one_or_none()
        if user_by_phone:
            verified = bool(user_by_phone.verified and user_by_phone.verified_at)
            onboarding_complete = bool(await mongo_db.behavior_profiles.find_one({"user_id": user_by_phone.id}))
            raise HTTPException(status_code=409, detail={
                "message": "Phone already registered.",
                "verified": verified,
                "onboarding_complete": onboarding_complete
            })
    # Create user
    new_user = User(name=data.name, email=data.email, phone=data.phone, role="user")
    db.add(new_user)
    try:
        await db.commit()
    except IntegrityError as ie:
        await db.rollback()
        # Handle unexpected unique constraint races gracefully
        raise HTTPException(status_code=409, detail={"message": "User already exists (email or phone)."})
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
@limiter.limit("10/minute; 100/day")
async def verify(request: Request, data: VerifyRequest, db: AsyncSession = Depends(get_db)):
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
@limiter.limit("10/minute; 200/day")
async def onboarding(request: Request, data: OnboardingRequest):
    # Store behavioral profile in MongoDB
    profile = data.dict()
    await mongo_db.behavior_profiles.insert_one(profile)
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

    

    

@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute; 20/hour")
async def login(request: Request, data: LoginRequest, db: AsyncSession = Depends(get_db), response: Response = None):
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

        # Keep device/geo handy for logging and enrich metrics with server-observed IP
        metrics = data.metrics or {}
        try:
            ip_candidate = (metrics.get('ip') if isinstance(metrics, dict) else None) or ''
            if not ip_candidate:
                ip_candidate = request.headers.get('cf-connecting-ip') or request.headers.get('CF-Connecting-IP') or ''
            if not ip_candidate:
                xff = request.headers.get('x-forwarded-for') or request.headers.get('X-Forwarded-For')
                if xff:
                    ip_candidate = xff.split(',')[0].strip()
            if not ip_candidate:
                ip_candidate = request.headers.get('x-real-ip') or request.headers.get('X-Real-IP') or ''
            if not ip_candidate and request.client:
                ip_candidate = request.client.host or ''
            if ip_candidate:
                if isinstance(metrics, dict):
                    metrics['ip'] = ip_candidate
                else:
                    metrics = {'ip': ip_candidate}
        except Exception:
            pass
        # Centralized risk evaluation (use enriched metrics)
        from app.services.risk_engine import score_login
        result = score_login(data.behavioral_challenge, metrics, profile)
        reasons = result.get("reasons", [])
        risk_score = result.get("risk_score", 0)
        level = result.get("level", "low")
        geo_metrics = (metrics.get('geo') or {}) if isinstance(metrics, dict) else {}
        device_metrics = (metrics.get('device') or {}) if isinstance(metrics, dict) else {}

        print(f"[LOGIN] Risk score: {risk_score}, Reasons: {reasons}")

        # Additional telemetry: Geo distance and IP prefix evaluations
        try:
            # Compute geo distance vs profile (if both available and not fallback)
            geo_dist_km = None
            cur_lat = geo_metrics.get('latitude') if isinstance(geo_metrics, dict) else None
            cur_lon = geo_metrics.get('longitude') if isinstance(geo_metrics, dict) else None
            cur_fallback = geo_metrics.get('fallback', True) if isinstance(geo_metrics, dict) else True
            prof_geo = profile.get('geo') or {}
            prof_lat = prof_geo.get('latitude') if isinstance(prof_geo, dict) else None
            prof_lon = prof_geo.get('longitude') if isinstance(prof_geo, dict) else None
            if cur_lat and cur_lon and prof_lat and prof_lon and not cur_fallback:
                geo_dist_km = round(haversine(cur_lat, cur_lon, prof_lat, prof_lon), 2)

            # IP prefix and network checks
            the_ip = metrics.get('ip') if isinstance(metrics, dict) else None
            ip_prefix = None
            if the_ip:
                try:
                    ip_obj = ipaddress.ip_address(the_ip)
                    if isinstance(ip_obj, ipaddress.IPv4Address):
                        ip_prefix = str(ipaddress.ip_network(f"{the_ip}/24", strict=False))
                    else:
                        ip_prefix = str(ipaddress.ip_network(f"{the_ip}/64", strict=False))
                except ValueError:
                    ip_prefix = None
            denylist = [p.strip() for p in os.environ.get('DENYLIST_IP_PREFIXES', '').split(',') if p.strip()]
            allowlist = [p.strip() for p in os.environ.get('ALLOWLIST_IP_PREFIXES', '').split(',') if p.strip()]
            def _in_prefixes(ip_str: Optional[str], prefixes: list[str]) -> bool:
                if not ip_str:
                    return False
                try:
                    ip_obj2 = ipaddress.ip_address(ip_str)
                except ValueError:
                    return False
                for pref in prefixes:
                    try:
                        net = ipaddress.ip_network(pref, strict=False)
                        if ip_obj2 in net:
                            return True
                    except ValueError:
                        continue
                return False
            deny_match = _in_prefixes(the_ip, denylist) if denylist else False
            allow_match = _in_prefixes(the_ip, allowlist) if allowlist else False
            known_networks = set(profile.get('known_networks', []) or [])
            known_match = False
            if the_ip and known_networks:
                for pref in known_networks:
                    try:
                        if ipaddress.ip_address(the_ip) in ipaddress.ip_network(pref, strict=False):
                            known_match = True
                            break
                    except ValueError:
                        continue

            print(f"[LOGIN][Geo] cur=({cur_lat},{cur_lon},fallback={cur_fallback}) prof=({prof_lat},{prof_lon}) dist_km={geo_dist_km}")
            print(f"[LOGIN][IP] ip={the_ip} prefix={ip_prefix} deny_match={deny_match} allow_match={allow_match} known_match={known_match} known_count={len(known_networks)}")
        except Exception as _e:
            print(f"[LOGIN] Telemetry log error: {_e}")

        # Compose extra details for audit logs
        extra_detail = []
        try:
            extra_detail.append(f"ip={metrics.get('ip')}")
            if 'ip_prefix' in locals() and ip_prefix:
                extra_detail.append(f"ip_prefix={ip_prefix}")
            if 'geo_dist_km' in locals() and geo_dist_km is not None:
                extra_detail.append(f"geo_dist_km={geo_dist_km}")
            if 'deny_match' in locals():
                extra_detail.append(f"deny={deny_match}")
            if 'allow_match' in locals():
                extra_detail.append(f"allow={allow_match}")
            if 'known_match' in locals():
                extra_detail.append(f"known_network={known_match}")
        except Exception:
            pass

        # Decision
        # New thresholds: low (<=40), medium (41-60), high (>60)
        if level == "high":
            trigger_alert("high_risk_login", f"Blocked login for user {user.id} (risk={risk_score})")
            audit_details = f"risk={risk_score}, reasons={reasons}"
            if extra_detail:
                audit_details += ", " + "; ".join(extra_detail)
            await log_login_attempt(db, user_id=user.id, location=location, status="blocked", details=audit_details)
            raise HTTPException(status_code=403, detail={"message": "High risk login detected. Blocked.", "risk": risk_score, "reasons": reasons})
        elif level == "medium":
            trigger_alert("medium_risk_login", f"Challenged login for user {user.id} (risk={risk_score})")
            audit_details = f"risk={risk_score}, reasons={reasons}"
            if extra_detail:
                audit_details += ", " + "; ".join(extra_detail)
            await log_login_attempt(db, user_id=user.id, location=location, status="challenged", details=audit_details)
            return LoginResponse(message="Medium risk: challenge required", token=None, risk="medium", reasons=reasons)
        else:
            # Determine risk label for response
            risk_label = level
            trigger_alert("successful_login", f"User {user.id} logged in from device {device_metrics.get('os', 'unknown')}")
            # Learning: persist last-seen metrics to behavior profile
            try:
                ip = (data.metrics or {}).get('ip') if data.metrics else None
                ip_prefix = None
                if ip:
                    try:
                        ip_obj = ipaddress.ip_address(ip)
                        # derive a /24 for IPv4, /64 for IPv6
                        if isinstance(ip_obj, ipaddress.IPv4Address):
                            ip_prefix = str(ipaddress.ip_network(f"{ip}/24", strict=False))
                        else:
                            ip_prefix = str(ipaddress.ip_network(f"{ip}/64", strict=False))
                    except ValueError:
                        ip_prefix = None
                update_doc = {"last_seen": datetime.utcnow()}
                if device_metrics:
                    update_doc["device_fingerprint"] = device_metrics
                if geo_metrics and not geo_metrics.get('fallback', True):
                    update_doc["geo"] = geo_metrics
                # Attach behavior signature for session cloaking
                behavior_signature = None
                try:
                    # simple signature: hash of core device fields + ip prefix (if any)
                    import hashlib, json
                    core = {
                        k: device_metrics.get(k)
                        for k in ["browser", "os", "screen", "timezone"]
                        if device_metrics.get(k)
                    }
                    if ip_prefix:
                        core["ip_prefix"] = ip_prefix
                    behavior_signature = hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()
                    update_doc["behavior_signature"] = behavior_signature
                except Exception:
                    pass

                # Baseline updates (EWMA) and warm-up policy
                # Pull existing profile to compute baselines
                existing = await mongo_db.behavior_profiles.find_one({"user_id": user.id}) or {}
                baselines = existing.get("baselines", {})

                def ewma_update(mean, var, x, alpha=0.3):
                    if mean is None or var is None:
                        return x, 1.0  # seed var to 1.0
                    new_mean = alpha * x + (1 - alpha) * mean
                    # Update variance as EWMA of squared deviation
                    new_var = alpha * (x - new_mean) ** 2 + (1 - alpha) * var
                    return new_mean, new_var

                # Update typing baselines if provided
                if data.behavioral_challenge and data.behavioral_challenge.get("type") == "typing":
                    t = data.behavioral_challenge.get("data") or {}
                    t_base = baselines.get("typing", {})
                    wpm_mean, wpm_var = ewma_update(t_base.get("wpm_mean"), t_base.get("wpm_var"), float(t.get("wpm", 0)))
                    err_mean, err_var = ewma_update(t_base.get("err_mean"), t_base.get("err_var"), float(t.get("errorRate", 0)))
                    timing_mean, timing_var = None, None
                    timings = t.get("keystrokeTimings") or []
                    if timings:
                        cur_mean = sum(timings) / len(timings)
                        timing_mean, timing_var = ewma_update(t_base.get("timing_mean"), t_base.get("timing_var"), float(cur_mean))
                    baselines["typing"] = {
                        "wpm_mean": wpm_mean,
                        "wpm_var": wpm_var,
                        "wpm_std": (wpm_var or 0) ** 0.5,
                        "err_mean": err_mean,
                        "err_var": err_var,
                        "err_std": (err_var or 0) ** 0.5,
                        "timing_mean": timing_mean,
                        "timing_var": timing_var,
                        "timing_std": (timing_var or 0) ** 0.5 if timing_var is not None else None,
                    }

                # Update pointer baselines if provided
                if data.behavioral_challenge and data.behavioral_challenge.get("type") in ["mouse", "touch"]:
                    m = data.behavioral_challenge.get("data") or {}
                    p_base = baselines.get("pointer", {})
                    path_len = len(m.get("path") or [])
                    clicks = int(m.get("clicks") or 0)
                    pl_mean, pl_var = ewma_update(p_base.get("path_len_mean"), p_base.get("path_len_var"), float(path_len))
                    ck_mean, ck_var = ewma_update(p_base.get("clicks_mean"), p_base.get("clicks_var"), float(clicks))
                    baselines["pointer"] = {
                        "path_len_mean": pl_mean,
                        "path_len_var": pl_var,
                        "path_len_std": (pl_var or 0) ** 0.5,
                        "clicks_mean": ck_mean,
                        "clicks_var": ck_var,
                        "clicks_std": (ck_var or 0) ** 0.5,
                    }

                update_doc["baselines"] = baselines

                # Warm-up policy and versioning
                low_streak = int(existing.get("low_risk_streak", 0)) + 1
                baseline_version = int(existing.get("baseline_version", 0)) + 1
                baseline_stable = existing.get("baseline_stable", False) or (low_streak >= 5)
                update_doc["low_risk_streak"] = low_streak
                update_doc["baseline_version"] = baseline_version
                update_doc["baseline_stable"] = baseline_stable

                # Keep last 3 baseline versions in history
                history_entry = {
                    "version": baseline_version,
                    "timestamp": datetime.utcnow(),
                    "baselines": baselines,
                }
                update_ops = {"$set": update_doc, "$push": {"baseline_history": {"$each": [history_entry], "$slice": -3}}}
                if ip_prefix:
                    update_ops["$addToSet"] = {"known_networks": ip_prefix}
                await mongo_db.behavior_profiles.update_one({"user_id": user.id}, update_ops, upsert=True)

                # Record geo event (tiled) and enforce retention
                try:
                    if geo_metrics and not geo_metrics.get('fallback', True) and geo_metrics.get('latitude') and geo_metrics.get('longitude'):
                        lat = float(geo_metrics['latitude'])
                        lon = float(geo_metrics['longitude'])
                        acc = float(geo_metrics.get('accuracy') or 0)
                        tile_lat = round(lat, 3)
                        tile_lon = round(lon, 3)
                        await mongo_db.geo_events.insert_one({
                            "user_id": user.id,
                            "lat": lat,
                            "lon": lon,
                            "tile_lat": tile_lat,
                            "tile_lon": tile_lon,
                            "accuracy": acc,
                            "ts": datetime.utcnow(),
                        })
                        # Raw retention: 30 days
                        cutoff = datetime.utcnow() - timedelta(days=30)
                        await mongo_db.geo_events.delete_many({"user_id": user.id, "ts": {"$lt": cutoff}})
                except Exception as _ge:
                    print(f"[LOGIN] Geo event store error: {_ge}")
            except Exception as e:
                print(f"[LOGIN] Warning: failed to persist profile updates: {e}")
            audit_details = f"risk={risk_score}, reasons={reasons}"
            if extra_detail:
                audit_details += ", " + "; ".join(extra_detail)
            await log_login_attempt(db, user_id=user.id, location=location, status="success", details=audit_details)
            # Embed behavior signature in token claims for session cloaking validation (best-effort)
            extra_claims = {"user_id": user.id, "email": user.email, "role": getattr(user, "role", "user")}
            if 'behavior_signature' in locals() and behavior_signature:
                extra_claims["behavior_signature"] = behavior_signature
            token = create_magic_link_token(extra_claims, expires_in_seconds=3600, scope="access")
            # Set HttpOnly cookie + CSRF token
            try:
                if response is not None:
                    # CSRF: double-submit token
                    import secrets
                    csrf_token = secrets.token_urlsafe(24)
                    response.set_cookie(
                        key="access_token",
                        value=token,
                        httponly=True,
                        secure=bool(int(os.environ.get("COOKIE_SECURE", "0"))),
                        samesite=os.environ.get("COOKIE_SAMESITE", COOKIE_SAMESITE_DEFAULT),
                        max_age=3600,
                        path="/"
                    )
                    response.set_cookie(
                        key="csrf_token",
                        value=csrf_token,
                        httponly=False,
                        secure=bool(int(os.environ.get("COOKIE_SECURE", "0"))),
                        samesite=os.environ.get("COOKIE_SAMESITE", COOKIE_SAMESITE_DEFAULT),
                        max_age=3600,
                        path="/"
                    )
            except Exception as _ce:
                print(f"[LOGIN] Cookie set error: {_ce}")
            print(f"[LOGIN] Login successful for user {user.id}")
            return LoginResponse(
                message="Login successful.",
                token=token,
                risk=risk_label,
                reasons=reasons,
                user={
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role,
                    "risk": risk_label,
                    "riskLevel": risk_label,
                    "isVerified": user.verified,
                    "isAdmin": getattr(user, 'role', '') == 'admin' or getattr(user, 'is_admin', False),
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
    await mongo_db.risk_feedback.insert_one({
        "identifier": data.get("identifier"),
        "risk": data.get("risk"),
        "correct": data.get("correct"),
        "reasons": data.get("reasons"),
        "metrics": data.get("metrics"),
        "timestamp": datetime.utcnow(),
    })
    return {"message": "Feedback received"}

# Removed legacy /webauthn-verify stub. Use /webauthn/auth/* and /webauthn/register/* flows.

@router.post("/behavioral-verify", response_model=StepupResponse)
@limiter.limit("5/minute; 30/hour")
async def behavioral_verify(request: Request, data: BehavioralVerifyRequest, db: AsyncSession = Depends(get_db)):
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
    profile = await mongo_db.behavior_profiles.find_one({"user_id": user.id}) or {}
    reasons = []
    risk_score = 0
    # Typing
    if data.behavioral_challenge['type'] == 'typing':
        t_pen, t_reasons = typing_penalty(data.behavioral_challenge['data'], profile.get('typing_pattern', {}))
        reasons += t_reasons
        risk_score += t_pen
    # Mouse/Touch
    if data.behavioral_challenge['type'] in ['mouse', 'touch']:
        m_pen, m_reasons = mouse_penalty(data.behavioral_challenge['data'], profile.get('mouse_dynamics', {}))
        reasons += m_reasons
        risk_score += m_pen
    # Device checks (inline)
    device = (data.metrics or {}).get('device', {}) if data.metrics else {}
    prof_device = profile.get('device_fingerprint', {}) or {}
    core_fields = ['browser', 'os', 'screen', 'timezone']
    device_mismatch_count = 0
    for k in core_fields:
        if device.get(k) and prof_device.get(k) and device.get(k) != prof_device.get(k):
            reasons.append(f"Device {k} mismatch: {device.get(k)} vs {prof_device.get(k)}")
            device_mismatch_count += 1
    if device_mismatch_count:
        risk_score += 20 * device_mismatch_count
    unknowns = [k for k in core_fields if not device.get(k)]
    if unknowns:
        reasons.append(f"Missing device fields: {', '.join(unknowns)}")
        risk_score += 10
    # Geo checks (inline)
    geo = (data.metrics or {}).get('geo', {}) if data.metrics else {}
    prof_geo = profile.get('geo', {}) or {}
    lat1, lon1 = geo.get('latitude'), geo.get('longitude')
    lat2, lon2 = prof_geo.get('latitude'), prof_geo.get('longitude')
    if lat1 and lon1 and lat2 and lon2:
        dist = haversine(lat1, lon1, lat2, lon2)
        if dist > 50:
            reasons.append(f"Geo location differs by {dist:.1f} km")
            risk_score += 20
    if not geo or geo.get('fallback', True):
        reasons.append("No reliable geolocation (fallback or missing)")
        risk_score += 10
    ip = (data.metrics or {}).get('ip') if data.metrics else None
    if ip in [None, '', 'unknown']:
        reasons.append("IP missing or unknown")
        risk_score += 5
    risk_score = min(risk_score, 100)
    await mongo_db.stepup_logs.insert_one({
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
    # Learning policy: Only learn when step-up passes with low residual risk
    update = {}
    if risk_score <= 10:
        if data.behavioral_challenge['type'] == 'typing':
            patterns = profile.get('typing_patterns', [])
            patterns.append(data.behavioral_challenge['data'])
            update['typing_patterns'] = patterns[-10:]
            update['typing_pattern'] = data.behavioral_challenge['data']
        if data.behavioral_challenge['type'] in ['mouse', 'touch']:
            patterns = profile.get('mouse_patterns', [])
            patterns.append(data.behavioral_challenge['data'])
            update['mouse_patterns'] = patterns[-10:]
            update['mouse_dynamics'] = data.behavioral_challenge['data']
        # Recompute behavior_signature with candidate update best-effort
        try:
            import hashlib, json
            device = (data.metrics or {}).get('device', {}) if data.metrics else {}
            core = {k: device.get(k) for k in ["browser", "os", "screen", "timezone"] if device.get(k)}
            ip = (data.metrics or {}).get('ip') if data.metrics else None
            ip_prefix = None
            if ip:
                import ipaddress
                try:
                    ip_obj = ipaddress.ip_address(ip)
                    if isinstance(ip_obj, ipaddress.IPv4Address):
                        ip_prefix = str(ipaddress.ip_network(f"{ip}/24", strict=False))
                    else:
                        ip_prefix = str(ipaddress.ip_network(f"{ip}/64", strict=False))
                except ValueError:
                    ip_prefix = None
            if ip_prefix:
                core["ip_prefix"] = ip_prefix
            update['behavior_signature'] = hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()
        except Exception:
            pass
        if update:
            await mongo_db.behavior_profiles.update_one({"user_id": user.id}, {"$set": update}, upsert=True)
    # Short-lived token for onboarding-only actions
    token = create_magic_link_token({"user_id": user.id, "email": user.email}, expires_in_seconds=600, scope="onboarding")
    return StepupResponse(message="Behavioral verified", token=token, risk="low")

@router.post("/trusted-confirm", response_model=StepupResponse)
@limiter.limit("5/minute; 50/day")
async def trusted_confirm(request: Request, data: TrustedConfirmRequest, db: AsyncSession = Depends(get_db)):
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
        await mongo_db.stepup_logs.insert_one({"user": data.identifier, "method": "trusted_device", "timestamp": datetime.utcnow(), "success": False, "reason": "User not found"})
        raise HTTPException(status_code=404, detail="User not found.")
    # Check trusted devices
    trusted = await mongo_db.trusted_devices.find_one({"user": data.identifier, "device": data.device, "ip": data.ip})
    if not trusted:
        await mongo_db.stepup_logs.insert_one({"user": data.identifier, "method": "trusted_device", "timestamp": datetime.utcnow(), "success": False, "reason": "Device not trusted"})
        raise HTTPException(status_code=403, detail={"message": "Device not trusted. Use magic link.", "risk": "medium"})
    await mongo_db.stepup_logs.insert_one({"user": data.identifier, "method": "trusted_device", "timestamp": datetime.utcnow(), "success": True})
    # Short-lived token for onboarding-only actions
    token = create_magic_link_token({"user_id": user.id, "email": user.email}, expires_in_seconds=600, scope="onboarding")
    return StepupResponse(message="Trusted device confirmed", token=token, risk="low")

@router.post("/send-magic-link", response_model=StepupResponse)
@limiter.limit("3/minute; 10/hour")
async def send_magic_link(request: Request, data: MagicLinkRequest, db: AsyncSession = Depends(get_db)):
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
        await mongo_db.stepup_logs.insert_one({"user": data.identifier, "method": "magic_link", "timestamp": datetime.utcnow(), "success": False, "reason": "User not found"})
        raise HTTPException(status_code=404, detail="User not found.")
    # Generate secure token
    token = str(uuid.uuid4())
    expires_at = datetime.utcnow().timestamp() + 600  # 10 minutes
    await mongo_db.magic_links.insert_one({
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
    await mongo_db.stepup_logs.insert_one({"user": data.identifier, "method": "magic_link", "timestamp": datetime.utcnow(), "success": True})
    return StepupResponse(message="Magic link sent to your email.", token=None, risk="medium")

@router.get("/magic-link/verify", response_model=StepupResponse)
@limiter.limit("10/minute; 100/day")
async def magic_link_verify(request: Request, token: str):
    # Lookup token
    entry = await mongo_db.magic_links.find_one({"token": token})
    if not entry:
        await mongo_db.stepup_logs.insert_one({"method": "magic_link_verify", "token": token, "timestamp": datetime.utcnow(), "success": False, "reason": "Token not found"})
        raise HTTPException(status_code=404, detail="Invalid or expired magic link.")
    if entry.get("used"):
        await mongo_db.stepup_logs.insert_one({"method": "magic_link_verify", "token": token, "timestamp": datetime.utcnow(), "success": False, "reason": "Token already used"})
        raise HTTPException(status_code=400, detail="Magic link already used. Please request a new one.")
    if datetime.utcnow().timestamp() > entry["expires_at"]:
        await mongo_db.stepup_logs.insert_one({"method": "magic_link_verify", "token": token, "timestamp": datetime.utcnow(), "success": False, "reason": "Token expired"})
        raise HTTPException(status_code=400, detail="Magic link expired. Please request a new one.")
    # Mark as used
    await mongo_db.magic_links.update_one({"token": token}, {"$set": {"used": True, "used_at": datetime.utcnow()}})
    # Issue JWT
    user_id = entry["user_id"]
    email = entry["email"]
    token_jwt = create_magic_link_token({"user_id": user_id, "email": email}, expires_in_seconds=3600)
    await mongo_db.stepup_logs.insert_one({"method": "magic_link_verify", "token": token, "timestamp": datetime.utcnow(), "success": True, "user_id": user_id})
    return StepupResponse(message="Magic link verified. You are now logged in.", token=token_jwt, risk="low")

@router.post("/webauthn/register/begin", response_model=WebAuthnRegisterBeginResponse)
@limiter.limit("5/minute; 50/day")
async def webauthn_register_begin(request: Request, data: WebAuthnRegisterBeginRequest):
    user = await mongo_db.users.find_one({"$or": [
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
    await redis_client.setex(f"webauthn:register:{challenge_id}", 600, cbor.dumps(state))
    return WebAuthnRegisterBeginResponse(publicKey=registration_data, challenge_id=challenge_id)

@router.post("/webauthn/register/complete", response_model=WebAuthnRegisterCompleteResponse)
@limiter.limit("5/minute; 50/day")
async def webauthn_register_complete(request: Request, data: WebAuthnRegisterCompleteRequest):
    state = await redis_client.get(f"webauthn:register:{data.challenge_id}")
    if not state:
        raise HTTPException(status_code=400, detail="Registration challenge expired or invalid.")
    state = cbor.loads(state)
    attestation_object = websafe_decode(data.credential["response"]["attestationObject"])
    client_data_json = websafe_decode(data.credential["response"]["clientDataJSON"])
    # Complete registration (python-fido2 expects state, client_data_json, attestation_object)
    auth_data = server.register_complete(state, client_data_json, attestation_object)
    # Store credential (keep credential_id/public_key as bytes)
    await mongo_db.webauthn_credentials.insert_one({
        "user_identifier": data.identifier,
        "credential_id": websafe_decode(data.credential.get("rawId") or data.credential.get("id")),
        "public_key": auth_data.credential_public_key,
        "sign_count": auth_data.sign_count,
        "aaguid": getattr(auth_data, "aaguid", None),
        "device": data.credential.get("authenticatorAttachment"),
        "transports": data.credential.get("transports"),
        "created_at": datetime.utcnow()
    })
    return WebAuthnRegisterCompleteResponse(success=True, message="WebAuthn credential registered.")

@router.post("/webauthn/auth/begin", response_model=WebAuthnAuthBeginResponse)
@limiter.limit("5/minute; 50/day")
async def webauthn_auth_begin(request: Request, data: WebAuthnAuthBeginRequest):
    creds = await mongo_db.webauthn_credentials.find({"user_identifier": data.identifier}).to_list(length=None)
    if not creds:
        raise HTTPException(status_code=404, detail="No WebAuthn credentials found for user.")
    def _to_bytes(v):
        if isinstance(v, (bytes, bytearray)):
            return v
        try:
            return websafe_decode(v)
        except Exception:
            return v
    allow_credentials = [{"type": "public-key", "id": _to_bytes(c.get("credential_id"))} for c in creds]
    auth_data, state = server.authenticate_begin(allow_credentials=allow_credentials, user_verification="preferred")
    challenge_id = str(uuid.uuid4())
    await redis_client.setex(f"webauthn:auth:{challenge_id}", 600, cbor.dumps(state))
    return WebAuthnAuthBeginResponse(publicKey=auth_data, challenge_id=challenge_id)

@router.post("/webauthn/auth/complete", response_model=WebAuthnAuthCompleteResponse)
@limiter.limit("5/minute; 50/day")
async def webauthn_auth_complete(request: Request, data: WebAuthnAuthCompleteRequest):
    state = await redis_client.get(f"webauthn:auth:{data.challenge_id}")
    if not state:
        raise HTTPException(status_code=400, detail="Authentication challenge expired or invalid.")
    state = cbor.loads(state)
    creds = await mongo_db.webauthn_credentials.find({"user_identifier": data.identifier}).to_list(length=None)
    if not creds:
        raise HTTPException(status_code=404, detail="No WebAuthn credentials found for user.")
    # Decode fields from client
    credential_id = websafe_decode(data.credential.get("rawId") or data.credential.get("id"))
    client_data_json = websafe_decode(data.credential["response"]["clientDataJSON"])
    authenticator_data = websafe_decode(data.credential["response"]["authenticatorData"])
    signature = websafe_decode(data.credential["response"]["signature"])
    # Build credentials set
    def _to_bytes(v):
        if isinstance(v, (bytes, bytearray)):
            return v
        try:
            return websafe_decode(v)
        except Exception:
            return v
    credentials = [
        {
            "id": _to_bytes(c.get("credential_id")),
            "public_key": c.get("public_key"),
            "sign_count": c.get("sign_count", 0),
        }
        for c in creds
    ]
    # Complete authentication
    auth_data = server.authenticate_complete(state, credentials, credential_id, client_data_json, authenticator_data, signature)
    # Update sign_count
    await mongo_db.webauthn_credentials.update_one({"credential_id": credential_id}, {"$set": {"sign_count": getattr(auth_data, 'new_sign_count', 0)}})
    # Log success
    await mongo_db.stepup_logs.insert_one({
        "user": data.identifier,
        "method": "webauthn",
        "credential_id": credential_id,
        "timestamp": datetime.utcnow(),
        "success": True
    })
    # Issue JWT
    user = await mongo_db.users.find_one({"$or": [
        {"email": data.identifier},
        {"phone": data.identifier},
        {"name": data.identifier}
    ]})
    token = create_magic_link_token({"user_id": str(user["_id"]), "email": user["email"]}, expires_in_seconds=3600)
    return WebAuthnAuthCompleteResponse(success=True, message="WebAuthn authentication successful.", token=token)

# Helper to get current user email from JWT (for demo, fallback to query param)
def get_current_user_email(request: Request, email: Optional[str] = Query(None)):
    # Accept either Authorization: Bearer <token> or access_token cookie containing the raw JWT
    auth_header = request.headers.get("authorization")
    cookie_token = request.cookies.get("access_token")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
    elif cookie_token:
        token = cookie_token
    if token:
        try:
            payload = jwt.decode(token, TS_JWT_SECRET, algorithms=[TS_JWT_ALG])
            return payload.get("email")
        except JWTError:
            pass
    return email

@router.get("/webauthn/devices")
async def get_webauthn_devices(request: Request, email: Optional[str] = Query(None)):
    user_email = get_current_user_email(request, email)
    if not user_email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    devices = await mongo_db.webauthn_credentials.find({"user_identifier": user_email}).to_list(length=None)
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
    result = await mongo_db.webauthn_credentials.delete_one({"user_identifier": user_email, "credential_id": credential_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Device not found or not owned by user")
    await mongo_db.stepup_logs.insert_one({
        "user": user_email,
        "method": "webauthn_remove",
        "credential_id": credential_id,
        "timestamp": datetime.utcnow(),
        "success": True
    })
    return {"success": True, "message": "Device removed"} 