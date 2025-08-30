"""
Security Configuration Module

This module provides comprehensive security configurations for the FinVault backend.
"""

import os
from typing import List, Optional
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityConfig:
    """Security configuration class"""

    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.allowed_hosts = self._get_allowed_hosts()
        self.cors_origins = self._get_cors_origins()
        self.rate_limiter = self._create_rate_limiter()

    def _get_allowed_hosts(self) -> List[str]:
        """Get allowed hosts based on environment"""
        if self.environment == "production":
            return [
                "finvault-g6r7.onrender.com",
                "securebank-lcz1.onrender.com",
                "*.onrender.com",
            ]
        else:
            return ["*"]

    def _get_cors_origins(self) -> List[str]:
        """Get CORS origins based on environment"""
        if self.environment == "production":
            return [
                "https://securebank-lcz1.onrender.com",
                "https://finvault-g6r7.onrender.com",
            ]
        else:
            return [
                "http://127.0.0.1:3000",
                "http://localhost:3000",
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "https://finvault-g6r7.onrender.com",
                "https://securebank-lcz1.onrender.com",
            ]

    def _create_rate_limiter(self) -> Limiter:
        """Create rate limiter instance"""
        return Limiter(key_func=get_remote_address)

    def apply_security_middleware(self, app: FastAPI) -> None:
        """Apply all security middleware to the FastAPI app."""

        # Rate limiting
        app.state.limiter = self.rate_limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

        # Trusted hosts
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=self.allowed_hosts,
        )

        # GZip
        app.add_middleware(GZipMiddleware, minimum_size=1000)

        # CSRF (after CORS)
        app.add_middleware(CsrfMiddleware)

        # Security headers
        app.add_middleware(SecurityHeadersMiddleware)

        # Finally, add CORS outermost so even error responses include CORS headers
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
            allow_headers=[
                "Accept",
                "Accept-Language",
                "Content-Language",
                "Content-Type",
                "Authorization",
                "X-CSRF-Token",
                "X-Requested-With",
                "Origin",
                "Access-Control-Request-Method",
                "Access-Control-Request-Headers",
            ],
            expose_headers=["X-CSRF-Token"],
            max_age=86400,
        )

        logger.info(f"Security middleware applied for environment: {self.environment}")

class SecurityHeadersMiddleware:
    """Middleware to add security headers to all responses"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)

        async def send_with_headers(message):
            if message.get("type") == "http.response.start":
                existing_headers = list(message.get("headers", []))

                # Security headers
                security_headers = {
                    b"X-Content-Type-Options": b"nosniff",
                    b"X-Frame-Options": b"DENY",
                    b"X-XSS-Protection": b"1; mode=block",
                    b"Referrer-Policy": b"strict-origin-when-cross-origin",
                }

                # Add Content Security Policy
                # Widen connect-src in development to allow local SPA ports
                env = os.getenv("ENVIRONMENT", "development").lower()
                if env == "production":
                    csp_policy = (
                        "default-src 'self'; "
                        "script-src 'self' 'unsafe-inline'; "
                        "style-src 'self' 'unsafe-inline'; "
                        "img-src 'self' data: https:; "
                        "font-src 'self' data:; "
                        "connect-src 'self' https://finvault-g6r7.onrender.com; "
                        "frame-ancestors 'none';"
                    )
                else:
                    csp_policy = (
                        "default-src 'self' https://cdn.jsdelivr.net https://unpkg.com; "
                        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
                        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
                        "img-src 'self' data: https:; "
                        "font-src 'self' data: https:; "
                        "connect-src 'self' http://localhost:8000 http://127.0.0.1:8000 http://localhost:5173 http://127.0.0.1:5173; "
                        "frame-ancestors 'none';"
                    )
                security_headers[b"Content-Security-Policy"] = csp_policy.encode()

                for k, v in security_headers.items():
                    existing_headers.append((k, v))

                message["headers"] = existing_headers

            await send(message)

        return await self.app(scope, receive, send_with_headers)

class CsrfMiddleware:
    """Simple CSRF protection using double-submit token: requires cookie 'csrf_token' and matching header 'X-CSRF-Token' for unsafe methods."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)
        method = scope.get("method", "GET").upper()
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        cookie_header = headers.get("cookie", "")
        csrf_cookie = None
        for part in cookie_header.split(";"):
            if "=" in part:
                name, val = part.strip().split("=", 1)
                if name == "csrf_token":
                    csrf_cookie = val
                    break

        # Helper to set cookie on response start
        new_token: str | None = None

        def wrap_send_set_cookie(send_fn):
            async def _send(message):
                if message.get("type") == "http.response.start" and (new_token is not None):
                    headers_list = list(message.get("headers", []))
                    # For cross-site requests, cookies must be SameSite=None. Browsers require Secure in production.
                    cookie_parts = [f"csrf_token={new_token}", "Path=/", "SameSite=None"]
                    # Only mark Secure in production to avoid local http issues
                    if os.getenv("ENVIRONMENT", "development").lower() == "production":
                        cookie_parts.append("Secure")
                    # Not HttpOnly because client JS must read it to set X-CSRF-Token
                    headers_list.append((b"set-cookie", "; ".join(cookie_parts).encode()))
                    message["headers"] = headers_list
                await send_fn(message)
            return _send

        # For unsafe methods, require CSRF
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            csrf_header = headers.get("x-csrf-token")
            env = os.getenv("ENVIRONMENT", "development").lower()
            if env == "production":
                # Strict: header must match cookie
                if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
                    start = {"type": "http.response.start", "status": 403, "headers": [(b"content-type", b"application/json")]}
                    import json
                    body = json.dumps({"detail": "CSRF validation failed"}).encode()
                    await send(start)
                    return await send({"type": "http.response.body", "body": body})
                return await self.app(scope, receive, send)
            elif env == "test":
                # Test environment: skip CSRF validation
                return await self.app(scope, receive, send)
            else:
                # Development: allow header-only if Origin is allowed by CORS
                origin = headers.get("origin")
                # If no origin (same-origin XHR), fall back to header presence
                if not csrf_header or (origin and origin not in SecurityConfig()._get_cors_origins()):
                    start = {"type": "http.response.start", "status": 403, "headers": [(b"content-type", b"application/json")]}
                    import json
                    body = json.dumps({"detail": "CSRF validation failed (dev)"}).encode()
                    await send(start)
                    return await send({"type": "http.response.body", "body": body})
                return await self.app(scope, receive, send)

        # For safe methods, if cookie missing, set it (except on the dedicated /csrf-token endpoint
        # which explicitly sets and returns a token to avoid double-setting mismatches)
        if not csrf_cookie and method in ("GET", "HEAD"):
            path = scope.get("path", "")
            if path == "/csrf-token":
                return await self.app(scope, receive, send)
            import secrets
            new_token = secrets.token_urlsafe(32)
            return await self.app(scope, receive, wrap_send_set_cookie(send))

        return await self.app(scope, receive, send)

def validate_environment() -> None:
    """Validate environment configuration"""
    required_vars = [
        "JWT_SECRET",
        "POSTGRES_URI",
        "MONGODB_URI",
        "REDIS_URI"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.warning(f"Missing environment variables: {missing_vars}")
    
    # Validate JWT secret strength
    jwt_secret = os.getenv("JWT_SECRET", "")
    if len(jwt_secret) < 32:
        logger.warning("JWT_SECRET should be at least 32 characters long")
    
    # Validate environment
    env = os.getenv("ENVIRONMENT", "development")
    if env not in ["development", "staging", "production"]:
        logger.warning(f"Invalid ENVIRONMENT value: {env}")

def get_rate_limits() -> dict:
    """Get rate limiting configuration"""
    return {
        "default": "100/minute",
        "auth": "5/minute",
        "health": "60/minute",
        "api": "1000/hour",
    }

# Create global security config instance
security_config = SecurityConfig() 