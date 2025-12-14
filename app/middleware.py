import os
import time
from collections import defaultdict
from typing import Callable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .logging_config import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware to prevent API abuse.
    Tracks requests per IP address with time windows.
    """
    
    def __init__(self, app, per_minute: int = 60, per_hour: int = 1000):
        super().__init__(app)
        self.per_minute = per_minute
        self.per_hour = per_hour
        self.requests_minute = defaultdict(list)
        self.requests_hour = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting if disabled
        if not os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true":
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host
        current_time = time.time()
        
        # Clean old entries (older than 1 hour)
        self.requests_minute[client_ip] = [
            req_time for req_time in self.requests_minute[client_ip]
            if current_time - req_time < 60
        ]
        self.requests_hour[client_ip] = [
            req_time for req_time in self.requests_hour[client_ip]
            if current_time - req_time < 3600
        ]
        
        # Check rate limits
        minute_count = len(self.requests_minute[client_ip])
        hour_count = len(self.requests_hour[client_ip])
        
        if minute_count >= self.per_minute:
            logger.warning(f"Rate limit exceeded (per minute) for IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {self.per_minute} per minute."
                }
            )
        
        if hour_count >= self.per_hour:
            logger.warning(f"Rate limit exceeded (per hour) for IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {self.per_hour} per hour."
                }
            )
        
        # Record this request
        self.requests_minute[client_ip].append(current_time)
        self.requests_hour[client_ip].append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit-Minute"] = str(self.per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(self.per_minute - minute_count - 1)
        response.headers["X-RateLimit-Limit-Hour"] = str(self.per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(self.per_hour - hour_count - 1)
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    Protects against common web vulnerabilities.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Enable XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions policy
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        
        # HTTPS enforcement (only in production)
        if os.getenv("FORCE_HTTPS", "false").lower() == "true":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        return response


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Redirect HTTP requests to HTTPS in production.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only redirect if FORCE_HTTPS is enabled
        if os.getenv("FORCE_HTTPS", "false").lower() != "true":
            return await call_next(request)
        
        # Check if request is already HTTPS
        if request.url.scheme == "https" or request.headers.get("X-Forwarded-Proto") == "https":
            return await call_next(request)
        
        # Redirect to HTTPS
        https_url = request.url.replace(scheme="https")
        logger.info(f"Redirecting to HTTPS: {https_url}")
        return RedirectResponse(url=str(https_url), status_code=status.HTTP_301_MOVED_PERMANENTLY)
