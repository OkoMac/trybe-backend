"""Rate limiting middleware using Redis"""

from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import time
from app.core.redis import get_redis
from app.core.config import settings


class RateLimiter:
    """
    Rate limiting using sliding window algorithm with Redis
    """

    def __init__(
        self,
        times: int = 10,
        seconds: int = 60,
        identifier: str = "ip"
    ):
        """
        Initialize rate limiter

        Args:
            times: Number of requests allowed
            seconds: Time window in seconds
            identifier: How to identify users ('ip' or 'user')
        """
        self.times = times
        self.seconds = seconds
        self.identifier = identifier

    async def __call__(self, request: Request):
        """
        Check if request should be rate limited

        Raises:
            HTTPException: If rate limit exceeded
        """
        # Get identifier
        if self.identifier == "ip":
            key_suffix = self._get_client_ip(request)
        elif self.identifier == "user":
            key_suffix = self._get_user_id(request)
        else:
            key_suffix = self._get_client_ip(request)

        # Create Redis key
        redis_key = f"rate_limit:{request.url.path}:{key_suffix}"

        # Get Redis client
        redis = await get_redis()

        # Get current count
        current = await redis.get(redis_key)

        if current is None:
            # First request in window
            await redis.setex(redis_key, self.seconds, 1)
            return

        current_count = int(current)

        if current_count >= self.times:
            # Rate limit exceeded
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Please try again in {self.seconds} seconds.",
                    "limit": self.times,
                    "window": f"{self.seconds}s",
                    "retry_after": self.seconds
                },
                headers={
                    "Retry-After": str(self.seconds),
                    "X-RateLimit-Limit": str(self.times),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + self.seconds)
                }
            )

        # Increment counter
        await redis.incr(redis_key)

        # Add rate limit headers to response
        request.state.rate_limit_remaining = self.times - current_count - 1
        request.state.rate_limit_limit = self.times
        request.state.rate_limit_reset = int(time.time()) + self.seconds

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request"""
        # Check X-Forwarded-For header (for proxies)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to direct client
        if request.client:
            return request.client.host

        return "unknown"

    def _get_user_id(self, request: Request) -> str:
        """Get user ID from request (if authenticated)"""
        # Try to get user from request state (set by auth middleware)
        if hasattr(request.state, "user"):
            return str(request.state.user.id)

        # Fallback to IP
        return self._get_client_ip(request)


# Pre-configured rate limiters
rate_limit_strict = RateLimiter(times=10, seconds=60)  # 10 requests per minute
rate_limit_moderate = RateLimiter(times=30, seconds=60)  # 30 requests per minute
rate_limit_relaxed = RateLimiter(times=100, seconds=60)  # 100 requests per minute

# Auth-specific rate limits
rate_limit_auth = RateLimiter(times=5, seconds=300)  # 5 auth attempts per 5 minutes
rate_limit_register = RateLimiter(times=3, seconds=3600)  # 3 registrations per hour per IP


async def add_rate_limit_headers(request: Request, call_next):
    """
    Middleware to add rate limit headers to all responses
    """
    response = await call_next(request)

    # Add rate limit headers if available
    if hasattr(request.state, "rate_limit_limit"):
        response.headers["X-RateLimit-Limit"] = str(request.state.rate_limit_limit)
        response.headers["X-RateLimit-Remaining"] = str(request.state.rate_limit_remaining)
        response.headers["X-RateLimit-Reset"] = str(request.state.rate_limit_reset)

    return response
