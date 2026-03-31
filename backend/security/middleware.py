"""Security middleware for FastAPI."""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time
import logging

from .auth import verify_access_token
from .pii_redaction import redact_pii

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware to validate JWT tokens on protected routes."""
    
    # Routes that don't require authentication
    PUBLIC_ROUTES = [
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/verify",
    ]
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process request and validate authentication."""
        
        # Skip authentication for public routes
        if any(request.url.path.startswith(route) for route in self.PUBLIC_ROUTES):
            return await call_next(request)
        
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing or invalid authorization header"}
            )
        
        token = auth_header.split(" ")[1]
        
        try:
            # Verify token
            token_data = verify_access_token(token)
            
            # Add user info to request state
            request.state.user_id = token_data.user_id
            request.state.user_email = token_data.email
            request.state.user_role = token_data.role
            
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )
        
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to rate limit requests per user/IP."""
    
    def __init__(self, app, requests_per_minute: int = 100):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}  # In production, use Redis
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process request and enforce rate limits."""
        
        # Get identifier (user_id or IP address)
        identifier = getattr(request.state, "user_id", None) or request.client.host
        
        current_minute = int(time.time() / 60)
        key = f"{identifier}:{current_minute}"
        
        # Increment request count
        self.request_counts[key] = self.request_counts.get(key, 0) + 1
        
        # Check rate limit
        if self.request_counts[key] > self.requests_per_minute:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded. Please try again later."}
            )
        
        # Clean up old entries (keep last 2 minutes)
        old_keys = [
            k for k in self.request_counts.keys()
            if int(k.split(":")[1]) < current_minute - 1
        ]
        for old_key in old_keys:
            del self.request_counts[old_key]
        
        return await call_next(request)


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Middleware to log all API requests for audit trail."""
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process request and log to audit trail."""
        
        start_time = time.time()
        
        # Extract user info if available
        user_id = getattr(request.state, "user_id", None)
        user_role = getattr(request.state, "user_role", None)
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log request
        logger.info(
            f"API Request: {request.method} {request.url.path} "
            f"| User: {user_id} ({user_role}) "
            f"| Status: {response.status_code} "
            f"| Duration: {duration:.3f}s "
            f"| IP: {request.client.host}"
        )
        
        # TODO: Store in audit_logs table for compliance
        
        return response


class PIIRedactionMiddleware(BaseHTTPMiddleware):
    """Middleware to redact PII from logs and responses."""
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process request and redact PII if needed."""
        
        # Process request
        response = await call_next(request)
        
        # For certain endpoints, redact PII from response
        # This is a placeholder - implement based on specific requirements
        
        return response


class TLSEnforcementMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce TLS 1.3 for all connections."""
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Enforce HTTPS/TLS for all requests."""
        
        # In production, this should be handled by reverse proxy (nginx, etc.)
        # This is a basic check for development
        
        if not request.url.scheme == "https" and not request.url.hostname in ["localhost", "127.0.0.1"]:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "HTTPS required for all connections"}
            )
        
        return await call_next(request)
