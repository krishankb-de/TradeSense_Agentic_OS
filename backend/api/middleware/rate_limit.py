"""
Rate Limiting Middleware
Implements token bucket rate limiting for API endpoints

Validates: Requirements 18.2
"""

import logging
import time
from typing import Dict, Tuple
from collections import defaultdict
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using token bucket algorithm.
    
    Features:
    - Per-IP rate limiting
    - Configurable rate and burst size
    - Automatic token refill
    - Rate limit headers in response
    
    Validates: Requirement 18.2 (Rate limiting)
    """
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        burst_size: int = 10
    ):
        """
        Initialize rate limiter.
        
        Args:
            app: FastAPI application
            requests_per_minute: Maximum requests per minute
            burst_size: Maximum burst size
        """
        super().__init__(app)
        
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.refill_rate = requests_per_minute / 60.0  # tokens per second
        
        # Token buckets: ip -> (tokens, last_refill_time)
        self.buckets: Dict[str, Tuple[float, float]] = defaultdict(
            lambda: (float(burst_size), time.time())
        )
        
        logger.info(
            f"Rate limiter initialized: {requests_per_minute} req/min, "
            f"burst={burst_size}"
        )
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request.
        
        Args:
            request: FastAPI request
            
        Returns:
            Client IP address
        """
        # Check X-Forwarded-For header (for proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"
    
    def _refill_tokens(self, ip: str) -> float:
        """
        Refill tokens for IP address based on elapsed time.
        
        Args:
            ip: Client IP address
            
        Returns:
            Current token count
        """
        tokens, last_refill = self.buckets[ip]
        now = time.time()
        elapsed = now - last_refill
        
        # Calculate tokens to add
        tokens_to_add = elapsed * self.refill_rate
        tokens = min(self.burst_size, tokens + tokens_to_add)
        
        # Update bucket
        self.buckets[ip] = (tokens, now)
        
        return tokens
    
    def _consume_token(self, ip: str) -> bool:
        """
        Try to consume one token for request.
        
        Args:
            ip: Client IP address
            
        Returns:
            True if token consumed, False if rate limited
        """
        tokens = self._refill_tokens(ip)
        
        if tokens >= 1.0:
            # Consume token
            self.buckets[ip] = (tokens - 1.0, self.buckets[ip][1])
            return True
        else:
            # Rate limited
            return False
    
    def _get_rate_limit_headers(self, ip: str) -> dict:
        """
        Get rate limit headers for response.
        
        Args:
            ip: Client IP address
            
        Returns:
            Dictionary of rate limit headers
        """
        tokens, _ = self.buckets[ip]
        
        return {
            "X-RateLimit-Limit": str(self.requests_per_minute),
            "X-RateLimit-Remaining": str(int(tokens)),
            "X-RateLimit-Reset": str(int(time.time() + 60))
        }
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request with rate limiting.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response with rate limit headers
        """
        # Skip rate limiting for health check and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get client IP
        ip = self._get_client_ip(request)
        
        # Try to consume token
        if not self._consume_token(ip):
            # Rate limited
            logger.warning(f"Rate limit exceeded for IP: {ip}")
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers=self._get_rate_limit_headers(ip)
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        for key, value in self._get_rate_limit_headers(ip).items():
            response.headers[key] = value
        
        return response


def create_rate_limit_middleware(
    requests_per_minute: int = 60,
    burst_size: int = 10
) -> RateLimitMiddleware:
    """
    Factory function to create rate limit middleware.
    
    Args:
        requests_per_minute: Maximum requests per minute
        burst_size: Maximum burst size
        
    Returns:
        Configured RateLimitMiddleware instance
    """
    return lambda app: RateLimitMiddleware(
        app,
        requests_per_minute=requests_per_minute,
        burst_size=burst_size
    )
