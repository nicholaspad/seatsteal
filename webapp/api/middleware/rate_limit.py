from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import redis
from typing import Optional, Callable
import time
from functools import wraps
import hashlib

from config import settings


class RateLimiter:
    """
    Redis-based rate limiting middleware for FastAPI.

    Implements token bucket algorithm for rate limiting API requests.
    """

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize rate limiter.

        Args:
            redis_url: Redis connection URL (uses settings.REDIS_URL if not provided)
        """
        self.redis_url = redis_url or settings.REDIS_URL
        if self.redis_url:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
        else:
            # Redis not configured - rate limiting will be disabled
            self.redis_client = None
        self.key_prefix = "seatsteal:ratelimit:"

    def _get_client_key(
        self, request: Request, identifier: Optional[str] = None
    ) -> str:
        """
        Generate a unique key for rate limiting based on client identifier.

        Args:
            request: FastAPI request object
            identifier: Optional custom identifier (e.g., user ID)

        Returns:
            Redis key string
        """
        if identifier:
            key_base = identifier
        else:
            # Use IP address as default identifier
            # Check for forwarded IPs (behind proxy)
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                client_ip = forwarded.split(",")[0].strip()
            else:
                client_ip = request.client.host if request.client else "unknown"

            key_base = f"ip:{client_ip}"

        # Include route path for per-endpoint rate limiting
        route = request.url.path
        key = f"{self.key_prefix}{key_base}:{route}"

        return key

    def _get_bucket_key(self, base_key: str) -> tuple[str, str]:
        """
        Get Redis keys for token bucket algorithm.

        Returns:
            Tuple of (tokens_key, timestamp_key)
        """
        return (f"{base_key}:tokens", f"{base_key}:timestamp")

    async def check_rate_limit(
        self,
        request: Request,
        max_requests: int = 100,
        window_seconds: int = 60,
        identifier: Optional[str] = None,
    ) -> tuple[bool, dict]:
        """
        Check if request should be rate limited.

        Args:
            request: FastAPI request object
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            identifier: Optional custom identifier

        Returns:
            Tuple of (is_allowed, info_dict)
            info_dict contains: remaining, reset_time, retry_after
        """
        # If Redis is not configured, skip rate limiting
        if self.redis_client is None:
            return True, {
                "remaining": max_requests,
                "reset_time": int(time.time() + window_seconds),
                "retry_after": 0,
            }

        key = self._get_client_key(request, identifier)
        tokens_key, timestamp_key = self._get_bucket_key(key)

        current_time = time.time()

        # Get current tokens and last update time
        tokens = self.redis_client.get(tokens_key)
        last_update = self.redis_client.get(timestamp_key)

        if tokens is None or last_update is None:
            # First request - initialize bucket
            tokens = max_requests - 1
            self.redis_client.setex(tokens_key, window_seconds, str(tokens))
            self.redis_client.setex(timestamp_key, window_seconds, str(current_time))

            return True, {
                "remaining": tokens,
                "reset_time": int(current_time + window_seconds),
                "retry_after": 0,
            }

        tokens = int(tokens)
        last_update = float(last_update)

        # Calculate token replenishment
        time_passed = current_time - last_update
        replenish_rate = max_requests / window_seconds
        tokens_to_add = int(time_passed * replenish_rate)

        # Update tokens
        tokens = min(max_requests, tokens + tokens_to_add)

        if tokens > 0:
            # Allow request and consume token
            tokens -= 1
            ttl = self.redis_client.ttl(tokens_key)
            if ttl < 0:
                ttl = window_seconds

            self.redis_client.setex(tokens_key, ttl, str(tokens))
            self.redis_client.setex(timestamp_key, ttl, str(current_time))

            reset_time = int(current_time + ttl)

            return True, {
                "remaining": tokens,
                "reset_time": reset_time,
                "retry_after": 0,
            }
        else:
            # Rate limit exceeded
            ttl = self.redis_client.ttl(tokens_key)
            reset_time = int(current_time + max(ttl, 1))

            return False, {
                "remaining": 0,
                "reset_time": reset_time,
                "retry_after": max(ttl, 1),
            }


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limit(
    max_requests: int = 100, window_seconds: int = 60, use_user_id: bool = False
):
    """
    Decorator for rate limiting FastAPI endpoints.

    Usage:
        @router.get("/api/courses")
        @rate_limit(max_requests=50, window_seconds=60)
        async def get_courses():
            return {"courses": [...]}

    Args:
        max_requests: Maximum requests allowed in time window
        window_seconds: Time window in seconds
        use_user_id: If True, rate limit by user ID instead of IP

    Returns:
        Decorated function
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from function arguments
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                # Check kwargs for FastAPI Request object by type
                for value in kwargs.values():
                    if isinstance(value, Request):
                        request = value
                        break

            if not request:
                # No request object found, skip rate limiting
                return await func(*args, **kwargs)

            # Determine identifier
            identifier = None
            if use_user_id:
                # Try to get user from request state (set by auth middleware)
                user = getattr(request.state, "user", None)
                if user:
                    identifier = f"user:{user.id}"

            # Check rate limit
            is_allowed, info = await rate_limiter.check_rate_limit(
                request,
                max_requests=max_requests,
                window_seconds=window_seconds,
                identifier=identifier,
            )

            if not is_allowed:
                # Rate limit exceeded
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "retry_after": info["retry_after"],
                        "reset_time": info["reset_time"],
                    },
                    headers={
                        "Retry-After": str(info["retry_after"]),
                        "X-RateLimit-Limit": str(max_requests),
                        "X-RateLimit-Remaining": str(info["remaining"]),
                        "X-RateLimit-Reset": str(info["reset_time"]),
                    },
                )

            # Add rate limit headers to response
            response = await func(*args, **kwargs)

            if hasattr(response, "headers"):
                response.headers["X-RateLimit-Limit"] = str(max_requests)
                response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
                response.headers["X-RateLimit-Reset"] = str(info["reset_time"])

            return response

        return wrapper

    return decorator


async def rate_limit_middleware(request: Request, call_next):
    """
    Global rate limiting middleware for all requests.

    Apply this middleware to the FastAPI app to rate limit all endpoints.
    Individual endpoints can override with the @rate_limit decorator.

    Usage:
        from webapp.api.middleware.rate_limit import rate_limit_middleware
        app.middleware("http")(rate_limit_middleware)
    """
    # Default global rate limit: 1000 requests per minute per IP
    is_allowed, info = await rate_limiter.check_rate_limit(
        request, max_requests=1000, window_seconds=60
    )

    if not is_allowed:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "retry_after": info["retry_after"],
                "reset_time": info["reset_time"],
            },
            headers={
                "Retry-After": str(info["retry_after"]),
                "X-RateLimit-Limit": "1000",
                "X-RateLimit-Remaining": str(info["remaining"]),
                "X-RateLimit-Reset": str(info["reset_time"]),
            },
        )

    response = await call_next(request)

    # Add rate limit headers
    response.headers["X-RateLimit-Limit"] = "1000"
    response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
    response.headers["X-RateLimit-Reset"] = str(info["reset_time"])

    return response
