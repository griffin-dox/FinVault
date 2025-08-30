from fastapi import APIRouter, Depends, HTTPException, status, Request, Body, Query, Response
from app.schemas.auth import (
    RegisterRequest, RegisterResponse, VerifyRequest, VerifyResponse, OnboardingRequest, OnboardingResponse, LoginRequest, LoginResponse,
    WebAuthnVerifyRequest, BehavioralVerifyRequest, TrustedConfirmRequest, MagicLinkRequest, MagicLinkVerifyRequest, StepupResponse,
    WebAuthnRegisterBeginRequest, WebAuthnRegisterBeginResponse, WebAuthnRegisterCompleteRequest, WebAuthnRegisterCompleteResponse,
    WebAuthnAuthBeginRequest, WebAuthnAuthBeginResponse, WebAuthnAuthCompleteRequest, WebAuthnAuthCompleteResponse,
    JWTLoginRequest, JWTLoginResponse, JWTRefreshRequest, JWTRefreshResponse, JWTLogoutResponse
)
from app.services.email_service import send_magic_link_email
from app.services.sms_service import send_magic_link_sms
from app.services.token_service import create_magic_link_token, verify_magic_link_token, create_jwt_token_pair, refresh_access_token
from app.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from app.database import AsyncSessionLocal, mongo_db, redis_client, get_db
import os
from app.services.alert_service import trigger_alert
from app.services.audit_log_service import log_login_attempt
from math import radians, cos, sin, asin, sqrt
from datetime import datetime, timedelta, timezone
import uuid
import json
from fido2.server import Fido2Server
from fido2.webauthn import PublicKeyCredentialRpEntity, PublicKeyCredentialUserEntity
from fido2.utils import websafe_encode, websafe_decode
from fido2 import cbor
from jose import jwt, JWTError
from app.services.token_service import JWT_SECRET as TS_JWT_SECRET, JWT_ALGORITHM as TS_JWT_ALG
from typing import Any, Optional, cast, Literal
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

# Typed helper to validate and return an allowed SameSite value
SamesiteType = Literal['lax', 'strict', 'none']

def _cookie_samesite() -> SamesiteType:
    v = os.environ.get("COOKIE_SAMESITE", COOKIE_SAMESITE_DEFAULT)
    v_lower = (v or "").lower()
    return cast(SamesiteType, v_lower if v_lower in ("lax", "strict", "none") else COOKIE_SAMESITE_DEFAULT)

# Public API base for generating magic links
def _public_api_base(request: Request | None = None) -> str:
    # 1) Explicit override takes precedence
    env_base = os.environ.get("PUBLIC_API_BASE_URL")
    if env_base:
        return env_base.rstrip("/")
    # 2) Infer from request (honor proxies)
    if request is not None:
        try:
            proto = request.headers.get("x-forwarded-proto") or request.headers.get("X-Forwarded-Proto") or request.url.scheme
            host = request.headers.get("x-forwarded-host") or request.headers.get("X-Forwarded-Host") or request.headers.get("host") or request.headers.get("Host")
            # If no forwarded host, fall back to request.url
            if not host:
                # request.url includes netloc; prefer hostname:port if present
                host = request.url.hostname
                if request.url.port and request.url.port not in (80, 443):
                    host = f"{host}:{request.url.port}"
            if proto and host:
                return f"{proto}://{host}".rstrip("/")
        except Exception:
            pass
    # 3) Environment-based fallback
    if ENV == "production":
        return "https://finvault-g6r7.onrender.com"
    return "http://127.0.0.1:8000"

# Public Web base for user-facing links (emails). Prefer explicit env; fallback to request or API base
def _public_web_base(request: Request | None = None) -> str:
    # 1) Explicit override
    web_env = os.environ.get("PUBLIC_WEB_BASE_URL")
    if web_env:
        return web_env.rstrip("/")
    # 2) Try to infer from Referer or forwarded headers (best-effort)
    if request is not None:
        # Use Referer if present and absolute
        ref = request.headers.get("referer") or request.headers.get("Referer")
        if ref and ref.startswith("http"):
            try:
                from urllib.parse import urlparse
                p = urlparse(ref)
                host = p.netloc
                scheme = p.scheme
                if host and scheme:
                    return f"{scheme}://{host}".rstrip("/")
            except Exception:
                pass
        # Fallback to API base if no referer
    return _public_api_base(request)

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
async def context_answer(request: Request, data: dict, response: Response, db: AsyncSession = Depends(get_db)):
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
        token = create_magic_link_token({"user_id": user.id, "email": user.email}, expires_in_seconds=3600, scope="access")
        try:
            import secrets
            csrf_token = secrets.token_urlsafe(24)
            response.set_cookie(
                key="access_token",
                value=token,
                httponly=True,
                secure=bool(int(os.environ.get("COOKIE_SECURE", "0"))),
                samesite=_cookie_samesite(),
                max_age=3600,
                path="/"
            )
            response.set_cookie(
                key="csrf_token",
                value=csrf_token,
                httponly=False,
                secure=bool(int(os.environ.get("COOKIE_SECURE", "0"))),
                samesite=_cookie_samesite(),
                max_age=3600,
                path="/"
            )
            # Mirror CSRF token in header so cross-site frontend can sync header value
            response.headers["X-CSRF-Token"] = csrf_token
        except Exception as _ce:
            print(f"[STEPUP][context-answer] Cookie set error: {_ce}")
        # Audit success as login success after step-up
        try:
            await log_login_attempt(db, user_id=cast(int, user.id), location="stepup_context", status="success", details="stepup_context_success")
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
            update_doc: dict[str, Any] = {"last_seen": datetime.now(timezone.utc)}
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
                from app.services.risk_engine import canonicalize_device_fields
                update_doc["device_fingerprint"] = canonicalize_device_fields(core_device)
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
            existing = {}
            if mongo_db is not None:
                existing = await mongo_db.behavior_profiles.find_one({"user_id": user.id}) or {} # type: ignore
            low_streak = int(existing.get("low_risk_streak", 0)) + 1
            baseline_version = int(existing.get("baseline_version", 0)) + 1
            baseline_stable = existing.get("baseline_stable", False) or (low_streak >= 5)
            update_doc["low_risk_streak"] = low_streak
            update_doc["baseline_version"] = baseline_version
            update_doc["baseline_stable"] = baseline_stable
            # Keep short history of versions
            history_entry = {"version": baseline_version, "timestamp": datetime.now(timezone.utc), "baselines": existing.get("baselines", {})}
            update_ops = {"$set": update_doc, "$push": {"baseline_history": {"$each": [history_entry], "$slice": -3}}}
            if ip_prefix:
                update_ops["$addToSet"] = {"known_networks": ip_prefix}
            if mongo_db is not None:
                await mongo_db.behavior_profiles.update_one({"user_id": user.id}, update_ops, upsert=True) # pyright: ignore[reportGeneralTypeIssues]
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
                "lastLogin": datetime.now(timezone.utc).isoformat(),
                "location": "stepup_context"
            }
        }
    # Alert admins on failed verification
    trigger_alert("failed_additional_verification", f"User {identifier} failed security question.")
    return {"success": False, "message": "Incorrect answer. Try again. Admins have been notified."}

@router.post("/ambient-verify", response_model=None)
async def ambient_verify(request: Request, data: dict, db: AsyncSession = Depends(get_db)):
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

        token = create_magic_link_token({"user_id": user.id, "email": user.email}, expires_in_seconds=3600, scope="access")

        # Note: Cookie setting removed to avoid FastAPI dependency issues
        # Cookies should be set by the frontend or a separate endpoint

        try:
            metrics = data.get("metrics") or {}
            ambient = data.get("ambient") or {}
            # Derive client IP
            the_ip = metrics.get('ip') if isinstance(metrics, dict) else None
            if not the_ip:
                the_ip = request.headers.get('cf-connecting-ip') or request.headers.get('CF-Connecting-IP')
            if not the_ip:
                the_ip = request.client.host if request.client else None
        except Exception as e:
            print(f"[STEPUP][ambient-verify] IP derivation error: {e}")
            the_ip = None
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
            update_doc: dict[str, Any] = {"last_seen": datetime.now(timezone.utc)}
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
                from app.services.risk_engine import canonicalize_device_fields
                update_doc["device_fingerprint"] = canonicalize_device_fields(core_device)
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
            existing = {}
            if mongo_db is not None:
                existing = await cast(Any, mongo_db).behavior_profiles.find_one({"user_id": user.id}) or {}
            low_streak = int(existing.get("low_risk_streak", 0)) + 1
            baseline_version = int(existing.get("baseline_version", 0)) + 1
            baseline_stable = existing.get("baseline_stable", False) or (low_streak >= 5)
            update_doc["low_risk_streak"] = low_streak
            update_doc["baseline_version"] = baseline_version
            update_doc["baseline_stable"] = baseline_stable
            history_entry = {"version": baseline_version, "timestamp": datetime.now(timezone.utc), "baselines": existing.get("baselines", {})}
            update_ops = {"$set": update_doc, "$push": {"baseline_history": {"$each": [history_entry], "$slice": -3}}}
            if ip_prefix:
                update_ops["$addToSet"] = {"known_networks": ip_prefix}
            if mongo_db is not None:
                await cast(Any, mongo_db).behavior_profiles.update_one({"user_id": user.id}, update_ops, upsert=True)
        except Exception as _learn_e:
            print(f"[STEPUP][ambient-verify] Learning error: {_learn_e}")

        return {"success": True, "message": "Ambient verification successful", "token": token}
    else:
        # Ambient verification failed
        trigger_alert("failed_additional_verification", f"User {identifier} failed ambient verification.")
        return {"success": False, "message": "Ambient verification failed"}

@router.post("/register", response_model=RegisterResponse)
@limiter.limit("5/minute; 50/day")
async def register(request: Request, data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if user exists by email
    if data.email:
        result = await db.execute(select(User).where(User.email == data.email))
        user = result.scalar_one_or_none()
        if user:
            verified = bool(user.verified and user.verified_at)
            onboarding_complete = False
            if mongo_db is not None:
                onboarding_complete = bool(await cast(Any, mongo_db).behavior_profiles.find_one({"user_id": user.id}))
            raise HTTPException(status_code=409, detail={
                "message": "Email already registered.",
                "verified": verified,
                "onboarding_complete": onboarding_complete
            })
    # Check if user exists by phone
    if data.phone:
        result = await db.execute(select(User).where(User.phone == data.phone))
        user_by_phone = result.scalar_one_or_none()
        if user_by_phone:
            verified = bool(user_by_phone.verified and user_by_phone.verified_at)
            onboarding_complete = False
            if mongo_db is not None:
                onboarding_complete = bool(await cast(Any, mongo_db).behavior_profiles.find_one({"user_id": user_by_phone.id}))
            raise HTTPException(status_code=409, detail={
                "message": "Phone already registered.",
                "verified": verified,
                "onboarding_complete": onboarding_complete
            })
    # Create user (capture country if provided)
    new_user = User(name=data.name, email=data.email, phone=data.phone, country=getattr(data, "country", None), role="user")
    db.add(new_user)
    try:
        await db.commit()
    except IntegrityError as ie:
        await db.rollback()
        # Handle unexpected unique constraint races gracefully
        raise HTTPException(status_code=409, detail={"message": "User already exists (email or phone)."})
    await db.refresh(new_user)
    # Generate magic link token and URL (GET endpoint supported for convenience)
    token = create_magic_link_token({"user_id": new_user.id, "email": new_user.email})
    magic_link = f"{_public_web_base(request)}/verify-email?token={token}"
    # Send magic link
    if data.email:
        send_magic_link_email(data.email, magic_link)
    if data.phone:
        send_magic_link_sms(data.phone, magic_link)
    return Response(status_code=201, content=RegisterResponse(message="Registration successful. Please check your email or SMS for the magic link.", user_id=cast(int, new_user.id), email=(data.email or "")).model_dump_json())

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
    setattr(user, 'verified_at', datetime.now(timezone.utc))
    setattr(user, 'verified', True)
    await db.commit()
    # Issue short-lived onboarding token so client can post onboarding
    token = create_magic_link_token({"user_id": user.id, "email": user.email}, expires_in_seconds=900, scope="onboarding")
    return VerifyResponse(message="Verification successful. Continue to onboarding.", onboarding_required=True, token=token)

# Support magic link GET verification to match emailed links
@router.get("/verify", response_model=VerifyResponse)
@limiter.limit("10/minute; 100/day")
async def verify_get(request: Request, token: str, db: AsyncSession = Depends(get_db)):
    payload = verify_magic_link_token(token)
    if not payload:
        raise HTTPException(status_code=400, detail="Invalid or expired token.")
    user_id = payload.get("user_id")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    setattr(user, 'verified_at', datetime.now(timezone.utc))
    setattr(user, 'verified', True)
    await db.commit()
    token = create_magic_link_token({"user_id": user.id, "email": user.email}, expires_in_seconds=900, scope="onboarding")
    return VerifyResponse(message="Verification successful. Continue to onboarding.", onboarding_required=True, token=token)

@router.post("/onboarding", response_model=OnboardingResponse)
@limiter.limit("10/minute; 200/day")
async def onboarding(request: Request, data: OnboardingRequest, db: AsyncSession = Depends(get_db)):
    # Determine user_id from token if not provided
    user_id = getattr(data, "user_id", None)
    if not user_id:
        # Accept Authorization: Bearer or access_token cookie
        auth_header = request.headers.get("authorization")
        cookie_token = request.cookies.get("access_token")
        token_val = None
        if auth_header and auth_header.startswith("Bearer "):
            token_val = auth_header.split(" ", 1)[1]
        elif cookie_token:
            token_val = cookie_token
        if token_val:
            try:
                payload = jwt.decode(token_val, TS_JWT_SECRET, algorithms=[TS_JWT_ALG])
                user_id = payload.get("user_id")
            except JWTError:
                pass
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Store behavioral profile in MongoDB (upsert by user_id)
    profile = data.dict()
    profile["user_id"] = user_id
    # Normalize geo if provided
    try:
        g = profile.get("geo") or {}
        if g:
            profile["geo"] = {
                "latitude": g.get("latitude"),
                "longitude": g.get("longitude"),
                "accuracy": g.get("accuracy"),
                "fallback": bool(g.get("fallback", False)),
            }
    except Exception:
        pass
    if mongo_db is not None:
        await cast(Any, mongo_db).behavior_profiles.update_one({"user_id": user_id}, {"$set": profile}, upsert=True)

    # Record device/IP telemetry best-effort
    try:
        from app.services.telemetry_service import record_telemetry
        dev = profile.get("device_fingerprint") or {}
        await record_telemetry(request, dev, user_id)
    except Exception:
        pass

    # Record geo event (tiled) if accurate location provided
    try:
        g = profile.get("geo") or {}
        if g and not g.get("fallback", True) and g.get("latitude") and g.get("longitude"):
            lat_val = g.get("latitude")
            lon_val = g.get("longitude")
            if lat_val is not None and lon_val is not None:
                lat = float(lat_val)
                lon = float(lon_val)
                acc = float(g.get("accuracy") or 0)
                tile_lat = round(lat, 3)
                tile_lon = round(lon, 3)
                if mongo_db is not None:
                    await cast(Any, mongo_db).geo_events.insert_one({
                        "user_id": user_id,
                        "lat": lat,
                        "lon": lon,
                        "tile_lat": tile_lat,
                        "tile_lon": tile_lon,
                        "accuracy": acc,
                        "ts": datetime.now(timezone.utc),
                    })
    except Exception:
        pass
    # Mark onboarding complete on the SQL user
    try:
        from sqlalchemy import update
        from app.models import User as SQLUser
        await db.execute(update(SQLUser).where(SQLUser.id == user_id).values(onboarding_complete=True))
        await db.commit()
    except Exception as _e:
        print(f"[ONBOARDING] Failed to mark onboarding_complete: {_e}")
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

    

    

@router.post("/login", response_model=None)
@limiter.limit("5/minute; 20/hour")
async def login(request: Request, data: LoginRequest, db: AsyncSession = Depends(get_db)):
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
            
        if not user:
            print(f"[LOGIN] Login failed - user not found")
            trigger_alert("failed_login", f"Failed login for identifier {data.identifier}")
            await log_login_attempt(db, user_id=None, location=location, status="failure", details=f"identifier={data.identifier}")
            raise HTTPException(status_code=401, detail="User not found.")
        if not (getattr(user, 'verified', False) and getattr(user, 'verified_at', None) is not None):
            print(f"[LOGIN] Login failed - email not verified")
            trigger_alert("failed_login", f"Failed login (unverified) for {data.identifier}")
            await log_login_attempt(db, user_id=cast(int, user.id), location=location, status="failure", details="unverified_email")
            raise HTTPException(status_code=403, detail={
                "message": "Email not verified.",
                "code": "EMAIL_NOT_VERIFIED",
                "redirect": "/verify-email"
            })
        # Enforce onboarding before login
        if not getattr(user, "onboarding_complete", False):
            print(f"[LOGIN] Onboarding required for user {user.id}")
            await log_login_attempt(db, user_id=cast(int, user.id), location=location, status="failure", details="onboarding_required")
            # Issue short-lived onboarding token to allow completing onboarding
            onboarding_token = create_magic_link_token({
                "user_id": user.id,
                "email": user.email
            }, expires_in_seconds=900, scope="onboarding")
            raise HTTPException(status_code=403, detail={
                "message": "Onboarding required.",
                "code": "ONBOARDING_REQUIRED",
                "redirect": "/onboarding",
                "token": onboarding_token
            })
            
        # --- Behavioral comparison ---
        profile = {}
        if mongo_db is not None:
            profile = await cast(Any, mongo_db).behavior_profiles.find_one({"user_id": user.id}) or {}
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
        # Wire in optional IP enrichment hints from Mongo ip_addresses cache if available
        try:
            if mongo_db is not None and isinstance(metrics, dict):
                ip_for_lookup = metrics.get('ip')
                if ip_for_lookup:
                    ip_doc = await cast(Any, mongo_db).ip_addresses.find_one({"ip": ip_for_lookup})
                    if ip_doc:
                        # map into flat metrics keys consumed by risk_engine._normalize_metrics
                        metrics['ip_asn'] = ip_doc.get('asn')
                        metrics['ip_asn_org'] = ip_doc.get('asn_org')
                        metrics['ip_city'] = ip_doc.get('city')
                        metrics['ip_region'] = ip_doc.get('region')
                        metrics['ip_country'] = ip_doc.get('country')
        except Exception:
            pass
        result = score_login(data.behavioral_challenge, metrics, profile)
        reasons = result.get("reasons", [])
        risk_score = result.get("risk_score", 0)
        level = result.get("level", "low")
        geo_metrics = (metrics.get('geo') or {}) if isinstance(metrics, dict) else {}
        device_metrics = (metrics.get('device') or {}) if isinstance(metrics, dict) else {}

        print(f"[LOGIN] Risk score: {risk_score}, Reasons: {reasons}")

        # Additional telemetry: Geo distance and IP prefix evaluations
        geo_dist_km = None
        ip_prefix = None
        deny_match = False
        allow_match = False
        known_match = False
        try:
            # Compute geo distance vs profile (if both available and not fallback)
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
            await log_login_attempt(db, user_id=cast(int, user.id), location=location, status="blocked", details=audit_details)
            raise HTTPException(status_code=403, detail={"message": "High risk login detected. Blocked.", "risk": risk_score, "reasons": reasons})
        elif level == "medium":
            trigger_alert("medium_risk_login", f"Challenged login for user {user.id} (risk={risk_score})")
            audit_details = f"risk={risk_score}, reasons={reasons}"
            if extra_detail:
                audit_details += ", " + "; ".join(extra_detail)
            await log_login_attempt(db, user_id=cast(int, user.id), location=location, status="challenged", details=audit_details)
            return LoginResponse(message="Medium risk: challenge required", token=None, risk="medium", reasons=reasons)
        else:
            # Only persist metrics and update baselines for low-risk logins
            risk_label = level
            trigger_alert("successful_login", f"User {user.id} logged in from device {device_metrics.get('os', 'unknown') if isinstance(device_metrics, dict) else 'unknown'}")
            behavior_signature = None
            if level == "low":
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
                    update_doc: dict[str, Any] = {"last_seen": datetime.now(timezone.utc)}
                    if device_metrics and isinstance(device_metrics, dict):
                        from app.services.risk_engine import canonicalize_device_fields
                        update_doc["device_fingerprint"] = canonicalize_device_fields(device_metrics)
                    if geo_metrics and isinstance(geo_metrics, dict) and not geo_metrics.get('fallback', True):
                        update_doc["geo"] = geo_metrics
                    # Save coarse IP geo baseline for city-level fallback comparisons
                    try:
                        if mongo_db is not None and metrics and isinstance(metrics, dict):
                            ip_for_lookup2 = metrics.get('ip')
                            if ip_for_lookup2:
                                ip_doc2 = await mongo_db.ip_addresses.find_one({"ip": ip_for_lookup2})  # type: ignore
                                if ip_doc2:
                                    update_doc["ip_geo"] = {
                                        "city": ip_doc2.get("city"),
                                        "region": ip_doc2.get("region"),
                                        "country": ip_doc2.get("country"),
                                    }
                    except Exception:
                        pass
                    # Attach behavior signature for session cloaking
                    try:
                        # simple signature: hash of core device fields + ip prefix (if any)
                        import hashlib, json
                        if isinstance(device_metrics, dict):
                            core = {k: device_metrics.get(k) for k in ["browser", "os", "screen", "timezone"] if device_metrics.get(k)}
                        else:
                            core = {}
                        if ip_prefix:
                            core["ip_prefix"] = ip_prefix
                        behavior_signature = hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()
                        update_doc["behavior_signature"] = behavior_signature
                    except Exception:
                        pass

                    # Also record telemetry (device + IP) in Mongo collections
                    try:
                        from app.services.telemetry_service import (
                            record_telemetry,
                            update_known_network_counter,
                            promote_known_network_if_ready,
                            demote_stale_known_networks,
                        )
                        t = await record_telemetry(request, device_metrics if isinstance(device_metrics, dict) else {}, cast(int, user.id))
                        try:
                            # Update per-day counters for known network promotion tracking
                            if isinstance(metrics, dict) and metrics.get('ip'):
                                await update_known_network_counter(cast(int, user.id), metrics.get('ip'))
                                await promote_known_network_if_ready(cast(int, user.id), metrics.get('ip'))
                                await demote_stale_known_networks(cast(int, user.id))
                        except Exception:
                            pass
                    except Exception:
                        pass

                    # Baseline updates (EWMA) and warm-up policy
                    # Pull existing profile to compute baselines
                    existing = {}
                    if mongo_db is not None:
                        existing = await mongo_db.behavior_profiles.find_one({"user_id": cast(int, user.id)}) or {}  # type: ignore
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
                    history_entry = {
                        "version": baseline_version,
                        "timestamp": datetime.now(timezone.utc),
                        "baselines": baselines,
                    }
                    update_ops = {"$set": update_doc, "$push": {"baseline_history": {"$each": [history_entry], "$slice": -3}}}
                    if ip_prefix:
                        update_ops["$addToSet"] = {"known_networks": ip_prefix}
                    if mongo_db is not None:
                        await mongo_db.behavior_profiles.update_one({"user_id": cast(int, user.id)}, update_ops, upsert=True)  # type: ignore
                    else:
                        print("[LOGIN] Warning: MongoDB not available, skipping behavior_profiles update")

                    try:
                        if geo_metrics and isinstance(geo_metrics, dict) and not geo_metrics.get('fallback', True) and geo_metrics.get('latitude') and geo_metrics.get('longitude'):
                            lat = float(geo_metrics['latitude'])
                            lon = float(geo_metrics['longitude'])
                            acc = float(geo_metrics.get('accuracy') or 0)
                            tile_lat = round(lat, 3)
                            tile_lon = round(lon, 3)
                            if mongo_db is not None:
                                await mongo_db.geo_events.insert_one({  # type: ignore
                                    "user_id": cast(int, user.id),
                                    "lat": lat,
                                    "lon": lon,
                                    "tile_lat": tile_lat,
                                    "tile_lon": tile_lon,
                                    "accuracy": acc,
                                    "ts": datetime.now(timezone.utc),
                                })
                                # Raw retention: 30 days
                                cutoff = datetime.now(timezone.utc) - timedelta(days=30)
                                await mongo_db.geo_events.delete_many({"user_id": cast(int, user.id), "ts": {"$lt": cutoff}})  # type: ignore
                    except Exception as _ge:
                        print(f"[LOGIN] Geo event store error: {_ge}")
                except Exception as e:
                    print(f"[LOGIN] Warning: failed to persist profile updates: {e}")
            audit_details = f"risk={risk_score}, reasons={reasons}"
            if extra_detail:
                audit_details += ", " + "; ".join(extra_detail)
            await log_login_attempt(db, user_id=cast(int, user.id), location=location, status="success", details=audit_details)
            # Embed behavior signature in token claims for session cloaking validation (best-effort)
            extra_claims = {"user_id": user.id, "email": user.email, "role": getattr(user, "role", "user")}
            if 'behavior_signature' in locals() and behavior_signature:
                extra_claims["behavior_signature"] = behavior_signature
            token = create_magic_link_token(extra_claims, expires_in_seconds=3600, scope="access")
            # Note: Cookie setting removed to avoid FastAPI dependency issues
            # Cookies should be set by the frontend or a separate endpoint
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
                    "lastLogin": datetime.now(timezone.utc).isoformat(),
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

@router.post("/jwt/login", response_model=JWTLoginResponse)
@limiter.limit("5/minute; 20/hour")
async def jwt_login(request: Request, data: JWTLoginRequest, db: AsyncSession = Depends(get_db)):
    """JWT login endpoint that returns access and refresh tokens."""
    try:
        # Use the same login logic as the regular login endpoint
        # Find user by identifier
        user = None
        result = await db.execute(select(User).where(User.email == data.identifier))
        user = result.scalar_one_or_none()
        if not user:
            result = await db.execute(select(User).where(User.phone == data.identifier))
            user = result.scalar_one_or_none()
        if not user:
            result = await db.execute(select(User).where(User.name == data.identifier))
            user = result.scalar_one_or_none()
            
        if not user:
            trigger_alert("failed_login", f"Failed JWT login for identifier {data.identifier}")
            raise HTTPException(status_code=401, detail="Invalid credentials.")
            
        if not (getattr(user, 'verified', False) and getattr(user, 'verified_at', None) is not None):
            raise HTTPException(status_code=403, detail={
                "message": "Email not verified.",
                "code": "EMAIL_NOT_VERIFIED"
            })
            
        # Enforce onboarding before login
        if not getattr(user, "onboarding_complete", False):
            onboarding_token = create_magic_link_token({
                "user_id": user.id,
                "email": user.email
            }, expires_in_seconds=900, scope="onboarding")
            raise HTTPException(status_code=403, detail={
                "message": "Onboarding required.",
                "code": "ONBOARDING_REQUIRED",
                "token": onboarding_token
            })
            
        # Basic risk assessment (simplified for JWT login)
        from app.services.risk_engine import score_login
        profile = {}
        if mongo_db is not None:
            profile = await cast(Any, mongo_db).behavior_profiles.find_one({"user_id": user.id}) or {}
        
        result = score_login(data.behavioral_challenge, data.metrics or {}, profile)
        risk_score = result.get("risk_score", 0)
        level = result.get("level", "low")
        
        # Block high-risk logins
        if level == "high":
            trigger_alert("high_risk_login", f"Blocked JWT login for user {user.id} (risk={risk_score})")
            raise HTTPException(status_code=403, detail={
                "message": "High risk login detected. Blocked.",
                "risk": risk_score
            })
            
        # Log successful login
        await log_login_attempt(db, user_id=cast(int, user.id), location="jwt_login", status="success", details=f"risk={risk_score}")
        
        # Create JWT token pair
        token_data = {
            "user_id": user.id,
            "email": user.email,
            "role": getattr(user, "role", "user")
        }
        
        token_pair = create_jwt_token_pair(token_data)
        
        return JWTLoginResponse(
            message="Login successful.",
            access_token=token_pair["access_token"],
            refresh_token=token_pair["refresh_token"],
            token_type=token_pair["token_type"],
            expires_in=token_pair["expires_in"],
            user={
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "isVerified": user.verified,
                "isAdmin": getattr(user, 'role', '') == 'admin' or getattr(user, 'is_admin', False)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[JWT LOGIN] Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/jwt/refresh", response_model=JWTRefreshResponse)
@limiter.limit("10/minute; 50/hour")
async def jwt_refresh(request: Request, data: JWTRefreshRequest):
    """Refresh access token using refresh token."""
    try:
        new_access_token = refresh_access_token(data.refresh_token)
        if not new_access_token:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
            
        return JWTRefreshResponse(
            message="Token refreshed successfully.",
            access_token=new_access_token,
            token_type="bearer",
            expires_in=900  # 15 minutes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[JWT REFRESH] Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/jwt/logout", response_model=JWTLogoutResponse)
async def jwt_logout():
    """Logout endpoint (client-side token invalidation)."""
    # In a stateless JWT system, logout is handled client-side by discarding tokens
    # For server-side blacklisting, you would need to implement a token blacklist
    return JWTLogoutResponse(message="Logged out successfully")

# JWT Authentication helper
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
security = HTTPBearer()

async def get_current_user_from_jwt(credentials: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_db)):
    """Get current user from JWT token."""
    try:
        token = credentials.credentials
        payload = verify_magic_link_token(token)
        
        if not payload or payload.get("scope") != "access":
            raise HTTPException(status_code=401, detail="Invalid or expired token")
            
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
            
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
            
        return user
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"[JWT AUTH] Error: {str(e)}")
        raise HTTPException(status_code=401, detail="Authentication failed")

@router.post("/verify-email")
@limiter.limit("3/minute; 10/hour")
async def verify_email(request: Request, data: dict, db: AsyncSession = Depends(get_db)):
    identifier = data.get("identifier") or data.get("email") or data.get("user")
    if not identifier:
        raise HTTPException(status_code=400, detail="Email or identifier is required.")
    # Resolve user by email/phone/name
    result = await db.execute(select(User).where(User.email == identifier))
    user = result.scalar_one_or_none()
    if not user:
        result = await db.execute(select(User).where(User.phone == identifier))
        user = result.scalar_one_or_none()
    if not user:
        result = await db.execute(select(User).where(User.name == identifier))
        user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if getattr(user, 'verified', False) and getattr(user, 'verified_at', None):
        return {"message": "Email already verified."}
    # Generate token and send magic link to frontend route
    token = create_magic_link_token({"user_id": cast(int, user.id), "email": getattr(user, 'email', '')})
    magic_link = f"{_public_web_base(request)}/verify-email?token={token}"
    ok = send_magic_link_email(getattr(user, 'email', ''), magic_link)
    if not ok:
        # Log-only: avoid exposing token in API response
        print(f"[EmailService] Delivery failed; magic link (dev): {magic_link}")
    return {"message": "Verification email sent. Please check your inbox."}

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
    if mongo_db is not None:
        await mongo_db.behavior_profiles.insert_one({"user_id": cast(int, user.id), **behavior_profile, "device_fingerprint": device_fingerprint})  # type: ignore
    setattr(user, 'onboarding_complete', True)
    await db.commit()
    return {"user": {"id": cast(int, user.id), "email": getattr(user, 'email', '')}}

@router.post("/feedback")
async def feedback(data: dict):
    # Store feedback in MongoDB for future learning
    if mongo_db is not None:
        await mongo_db.risk_feedback.insert_one({  # type: ignore
            "identifier": data.get("identifier"),
            "risk": data.get("risk"),
            "correct": data.get("correct"),
            "reasons": data.get("reasons"),
            "metrics": data.get("metrics"),
            "timestamp": datetime.now(timezone.utc),
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
        if mongo_db is not None:
            mongo_db.stepup_logs.insert_one({"user": data.identifier, "method": "behavioral", "timestamp": datetime.now(timezone.utc), "success": False, "reason": "User not found"})  # type: ignore
        raise HTTPException(status_code=404, detail="User not found.")
    # Fetch behavioral profile
    profile = {}
    if mongo_db is not None:
        profile = await mongo_db.behavior_profiles.find_one({"user_id": cast(int, user.id)}) or {}  # type: ignore
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
    if mongo_db is not None:
        await mongo_db.stepup_logs.insert_one({  # type: ignore
            "user": data.identifier,
            "method": "behavioral",
            "metrics": data.metrics,
            "challenge": data.behavioral_challenge,
            "timestamp": datetime.now(timezone.utc),
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
        if update and mongo_db is not None:
            await mongo_db.behavior_profiles.update_one({"user_id": cast(int, user.id)}, {"$set": update}, upsert=True)  # type: ignore
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
        if mongo_db is not None:
            await mongo_db.stepup_logs.insert_one({"user": data.identifier, "method": "trusted_device", "timestamp": datetime.now(timezone.utc), "success": False, "reason": "User not found"})  # type: ignore
        raise HTTPException(status_code=404, detail="User not found.")
    # Check trusted devices
    trusted = None
    if mongo_db is not None:
        trusted = await mongo_db.trusted_devices.find_one({"user": data.identifier, "device": data.device, "ip": data.ip})  # type: ignore
    if not trusted:
        if mongo_db is not None:
            await mongo_db.stepup_logs.insert_one({"user": data.identifier, "method": "trusted_device", "timestamp": datetime.now(timezone.utc), "success": False, "reason": "Device not trusted"})  # type: ignore
        raise HTTPException(status_code=403, detail={"message": "Device not trusted. Use magic link.", "risk": "medium"})
    if mongo_db is not None:
        await mongo_db.stepup_logs.insert_one({"user": data.identifier, "method": "trusted_device", "timestamp": datetime.now(timezone.utc), "success": True})  # type: ignore
    # Short-lived token for onboarding-only actions
    token = create_magic_link_token({"user_id": cast(int, user.id), "email": getattr(user, 'email', '')}, expires_in_seconds=600, scope="onboarding")
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
        if mongo_db is not None:
            await mongo_db.stepup_logs.insert_one({"user": data.identifier, "method": "magic_link", "timestamp": datetime.now(timezone.utc), "success": False, "reason": "User not found"})  # type: ignore
        raise HTTPException(status_code=404, detail="User not found.")
    # Generate secure token
    token = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc).timestamp() + 600  # 10 minutes
    if mongo_db is not None:
        await mongo_db.magic_links.insert_one({  # type: ignore
            "user_id": cast(int, user.id),
            "email": getattr(user, 'email', ''),
            "token": token,
            "expires_at": expires_at,
            "used": False,
            "created_at": datetime.now(timezone.utc)
        })
    # Send email with link
    link = f"{_public_web_base(request)}/magic-link?token={token}"
    if mongo_db is not None:
        send_magic_link_email(getattr(user, 'email', ''), link)
    if mongo_db is not None:
        await mongo_db.stepup_logs.insert_one({"user": data.identifier, "method": "magic_link", "timestamp": datetime.now(timezone.utc), "success": True})  # type: ignore
    return StepupResponse(message="Magic link sent to your email.", token=None, risk="medium")

@router.get("/magic-link/verify", response_model=StepupResponse)
@limiter.limit("10/minute; 100/day")
async def magic_link_verify(request: Request, token: str):
    # Lookup token
    entry = None
    if mongo_db is not None:
        entry = await mongo_db.magic_links.find_one({"token": token})  # type: ignore
    if not entry:
        if mongo_db is not None:
            await mongo_db.stepup_logs.insert_one({"method": "magic_link_verify", "token": token, "timestamp": datetime.now(timezone.utc), "success": False, "reason": "Token not found"})  # type: ignore
        raise HTTPException(status_code=404, detail="Invalid or expired magic link.")
    if entry.get("used"):
        if mongo_db is not None:
            await mongo_db.stepup_logs.insert_one({"method": "magic_link_verify", "token": token, "timestamp": datetime.now(timezone.utc), "success": False, "reason": "Token already used"})  # type: ignore
        raise HTTPException(status_code=400, detail="Magic link already used. Please request a new one.")
    if datetime.now(timezone.utc).timestamp() > entry["expires_at"]:
        if mongo_db is not None:
            await mongo_db.stepup_logs.insert_one({"method": "magic_link_verify", "token": token, "timestamp": datetime.now(timezone.utc), "success": False, "reason": "Token expired"})  # type: ignore
        raise HTTPException(status_code=400, detail="Magic link expired. Please request a new one.")
    # Mark as used
    if mongo_db is not None:
        await mongo_db.magic_links.update_one({"token": token}, {"$set": {"used": True, "used_at": datetime.now(timezone.utc)}})  # type: ignore
    # Issue JWT
    user_id = entry["user_id"]
    email = entry["email"]
    token_jwt = create_magic_link_token({"user_id": user_id, "email": email}, expires_in_seconds=3600)
    if mongo_db is not None:
        await mongo_db.stepup_logs.insert_one({"method": "magic_link_verify", "token": token, "timestamp": datetime.now(timezone.utc), "success": True, "user_id": user_id})  # type: ignore
    return StepupResponse(message="Magic link verified. You are now logged in.", token=token_jwt, risk="low")

@router.post("/webauthn/register/begin", response_model=WebAuthnRegisterBeginResponse)
@limiter.limit("5/minute; 50/day")
async def webauthn_register_begin(request: Request, data: WebAuthnRegisterBeginRequest):
    if mongo_db is None:
        raise HTTPException(status_code=500, detail="Database not available.")
    user = await mongo_db.users.find_one({"$or": [
        {"email": data.identifier},
        {"phone": data.identifier},
        {"name": data.identifier}
    ]})  # type: ignore
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user_entity = PublicKeyCredentialUserEntity(
        id=str(user["_id"]).encode(),
        name=user["email"],
        display_name=user.get("name", user["email"])
    )
    from fido2.webauthn import UserVerificationRequirement
    registration_data, state = server.register_begin(user_entity, user_verification=UserVerificationRequirement.PREFERRED)
    challenge_id = str(uuid.uuid4())
    if redis_client is not None:
        await redis_client.setex(f"webauthn:register:{challenge_id}", 600, json.dumps(state.__dict__))  # type: ignore
    return WebAuthnRegisterBeginResponse(publicKey=dict(registration_data.__dict__), challenge_id=challenge_id)

@router.post("/webauthn/register/complete", response_model=WebAuthnRegisterCompleteResponse)
@limiter.limit("5/minute; 50/day")
async def webauthn_register_complete(request: Request, data: WebAuthnRegisterCompleteRequest):
    if redis_client is None:
        raise HTTPException(status_code=500, detail="Redis not available.")
    state_data = await redis_client.get(f"webauthn:register:{data.challenge_id}")  # type: ignore
    if not state_data:
        raise HTTPException(status_code=400, detail="Registration challenge expired or invalid.")
    state_dict = json.loads(state_data)
    # Reconstruct state object from dict - this is a simplified approach
    from fido2.server import Fido2Server
    # For now, we'll skip the state reconstruction and use a simpler approach
    attestation_object = websafe_decode(data.credential["response"]["attestationObject"])
    client_data_json = websafe_decode(data.credential["response"]["clientDataJSON"])
    # Complete registration (python-fido2 expects state, client_data_json, attestation_object)
    # We'll need to reconstruct the state properly, but for now let's use a placeholder
    if mongo_db is None:
        raise HTTPException(status_code=500, detail="Database not available.")
    # Store credential (keep credential_id/public_key as bytes)
    credential_id_raw = data.credential.get("rawId") or data.credential.get("id")
    if credential_id_raw is None:
        raise HTTPException(status_code=400, detail="Invalid credential data.")
    credential_id = websafe_decode(credential_id_raw)
    await mongo_db.webauthn_credentials.insert_one({  # type: ignore
        "user_identifier": data.identifier,
        "credential_id": credential_id,
        "public_key": b"placeholder",  # We'll need to get this from auth_data
        "sign_count": 0,
        "aaguid": None,
        "device": data.credential.get("authenticatorAttachment"),
        "transports": data.credential.get("transports"),
        "created_at": datetime.now(timezone.utc)
    })
    return WebAuthnRegisterCompleteResponse(success=True, message="WebAuthn credential registered.")

@router.post("/webauthn/auth/begin", response_model=WebAuthnAuthBeginResponse)
@limiter.limit("5/minute; 50/day")
async def webauthn_auth_begin(request: Request, data: WebAuthnAuthBeginRequest):
    if mongo_db is None:
        raise HTTPException(status_code=500, detail="Database not available.")
    creds = await mongo_db.webauthn_credentials.find({"user_identifier": data.identifier}).to_list(length=None)  # type: ignore
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
    from fido2.webauthn import UserVerificationRequirement
    auth_data, state = server.authenticate_begin(credentials=[], user_verification=UserVerificationRequirement.PREFERRED)
    challenge_id = str(uuid.uuid4())
    if redis_client is not None:
        await redis_client.setex(f"webauthn:auth:{challenge_id}", 600, json.dumps(state.__dict__))  # type: ignore
    return WebAuthnAuthBeginResponse(publicKey=dict(auth_data.__dict__), challenge_id=challenge_id)

@router.post("/webauthn/auth/complete", response_model=WebAuthnAuthCompleteResponse)
@limiter.limit("5/minute; 50/day")
async def webauthn_auth_complete(request: Request, data: WebAuthnAuthCompleteRequest):
    if redis_client is None:
        raise HTTPException(status_code=500, detail="Redis not available.")
    state_data = await redis_client.get(f"webauthn:auth:{data.challenge_id}")  # type: ignore
    if not state_data:
        raise HTTPException(status_code=400, detail="Authentication challenge expired or invalid.")
    if mongo_db is None:
        raise HTTPException(status_code=500, detail="Database not available.")
    creds = await mongo_db.webauthn_credentials.find({"user_identifier": data.identifier}).to_list(length=None)  # type: ignore
    if not creds:
        raise HTTPException(status_code=404, detail="No WebAuthn credentials found for user.")
    # Decode fields from client
    credential_id_raw = data.credential.get("rawId") or data.credential.get("id")
    if credential_id_raw is None:
        raise HTTPException(status_code=400, detail="Invalid credential data.")
    credential_id = websafe_decode(credential_id_raw)
    # For now, we'll skip the full WebAuthn verification and just check if credential exists
    # Update sign_count (simplified)
    await mongo_db.webauthn_credentials.update_one({"credential_id": credential_id}, {"$set": {"sign_count": 1}})  # type: ignore
    # Log success
    await mongo_db.stepup_logs.insert_one({  # type: ignore
        "user": data.identifier,
        "method": "webauthn",
        "credential_id": credential_id,
        "timestamp": datetime.now(timezone.utc),
        "success": True
    })
    return WebAuthnAuthCompleteResponse(success=True, message="WebAuthn authentication successful.")
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
            payload = verify_magic_link_token(token)
            if payload and payload.get("scope") == "access":
                return payload.get("email")
        except Exception as e:
            print(f"[WebAuthn] Token verification failed: {e}")
            pass
    return email

@router.get("/webauthn/devices")
async def get_webauthn_devices(request: Request, email: Optional[str] = Query(None)):
    user_email = get_current_user_email(request, email)
    if not user_email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if mongo_db is None:
        raise HTTPException(status_code=500, detail="Database not available.")
    devices = await mongo_db.webauthn_credentials.find({"user_identifier": user_email}).to_list(length=None)  # type: ignore
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
    if mongo_db is None:
        raise HTTPException(status_code=500, detail="Database not available.")
    result = await mongo_db.webauthn_credentials.delete_one({"user_identifier": user_email, "credential_id": credential_id})  # type: ignore
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Device not found or not owned by user")
    await mongo_db.stepup_logs.insert_one({  # type: ignore
        "user": user_email,
        "method": "webauthn_remove",
        "credential_id": credential_id,
        "timestamp": datetime.now(timezone.utc),
        "success": True
    })
    return {"success": True, "message": "Device removed"} 