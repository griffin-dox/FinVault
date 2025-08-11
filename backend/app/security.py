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
                "*.onrender.com"
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
        """Apply all security middleware to the FastAPI app"""
        
        # Add rate limiter
        app.state.limiter = self.rate_limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        
        # Add CORS middleware
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
                "X-Requested-With",
                "Origin",
                "Access-Control-Request-Method",
                "Access-Control-Request-Headers",
            ],
            expose_headers=["*"],
            max_age=86400,  # Cache preflight requests for 24 hours
        )
        
        # Add trusted host middleware
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=self.allowed_hosts
        )
        
        # Add Gzip compression
        app.add_middleware(GZipMiddleware, minimum_size=1000)
        
        # Add security headers middleware
        app.add_middleware(SecurityHeadersMiddleware)
        
        logger.info(f"Security middleware applied for environment: {self.environment}")

class SecurityHeadersMiddleware:
    """Middleware to add security headers to all responses"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Add security headers
            async def send_with_headers(message):
                if message["type"] == "http.response.start":
                    headers = dict(message.get("headers", []))
                    
                    # Security headers
                    security_headers = {
                        b"X-Content-Type-Options": b"nosniff",
                        b"X-Frame-Options": b"DENY",
                        b"X-XSS-Protection": b"1; mode=block",
                        b"Referrer-Policy": b"strict-origin-when-cross-origin",
                        b"Permissions-Policy": b"camera=(), microphone=(), geolocation=()",
                        b"Strict-Transport-Security": b"max-age=31536000; includeSubDomains",
                    }
                    
                    # Add Content Security Policy
                    csp_policy = (
                        "default-src 'self'; "
                        "script-src 'self' 'unsafe-inline'; "
                        "style-src 'self' 'unsafe-inline'; "
                        "img-src 'self' data: https:; "
                        "font-src 'self' data:; "
                        "connect-src 'self' https://finvault-g6r7.onrender.com; "
                        "frame-ancestors 'none';"
                    )
                    security_headers[b"Content-Security-Policy"] = csp_policy.encode()
                    
                    # Update headers
                    for key, value in security_headers.items():
                        headers[key] = value
                    
                    message["headers"] = list(headers.items())
                
                await send(message)
            
            await self.app(scope, receive, send_with_headers)
        else:
            await self.app(scope, receive, send)

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