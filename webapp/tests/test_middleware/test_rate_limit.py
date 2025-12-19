"""Tests for rate limiting middleware."""

import pytest
from fastapi import Request, HTTPException
from unittest.mock import MagicMock, patch, AsyncMock
import time

from api.middleware.rate_limit import (
    RateLimiter,
    rate_limiter,
    rate_limit,
    rate_limit_middleware,
)


class TestRateLimiterInit:
    """Tests for RateLimiter initialization."""

    @pytest.mark.unit
    def test_initialization_with_cache_client(self):
        """Test RateLimiter uses shared CacheClient connection pool."""
        with patch("api.middleware.rate_limit.CacheClient") as mock_cache:
            mock_redis = MagicMock()
            mock_cache.get_client.return_value = mock_redis

            limiter = RateLimiter()

            assert limiter.redis_client == mock_redis
            assert limiter.key_prefix == "seatsteal:ratelimit:"
            mock_cache.get_client.assert_called_once()

    @pytest.mark.unit
    def test_initialization_fallback_to_direct_connection(self):
        """Test RateLimiter falls back to direct Redis connection."""
        with patch("api.middleware.rate_limit.CacheClient") as mock_cache:
            with patch("api.middleware.rate_limit.redis") as mock_redis_module:
                mock_cache.get_client.return_value = None
                mock_redis_connection = MagicMock()
                mock_redis_module.from_url.return_value = mock_redis_connection

                with patch("api.middleware.rate_limit.settings") as mock_settings:
                    mock_settings.REDIS_URL = "redis://localhost:6379"
                    limiter = RateLimiter()

                    assert limiter.redis_client == mock_redis_connection
                    mock_redis_module.from_url.assert_called_once_with(
                        "redis://localhost:6379", decode_responses=True
                    )

    @pytest.mark.unit
    def test_initialization_no_redis_available(self):
        """Test RateLimiter handles missing Redis gracefully."""
        with patch("api.middleware.rate_limit.CacheClient") as mock_cache:
            with patch("api.middleware.rate_limit.settings") as mock_settings:
                mock_cache.get_client.return_value = None
                mock_settings.REDIS_URL = None

                limiter = RateLimiter()

                assert limiter.redis_client is None

    @pytest.mark.unit
    def test_initialization_redis_connection_fails(self):
        """Test RateLimiter handles Redis connection failures."""
        with patch("api.middleware.rate_limit.CacheClient") as mock_cache:
            with patch("api.middleware.rate_limit.redis") as mock_redis_module:
                mock_cache.get_client.return_value = None
                mock_redis_module.from_url.side_effect = Exception("Connection refused")

                with patch("api.middleware.rate_limit.settings") as mock_settings:
                    mock_settings.REDIS_URL = "redis://localhost:6379"
                    limiter = RateLimiter()

                    assert limiter.redis_client is None


class TestGetClientKey:
    """Tests for _get_client_key method."""

    @pytest.mark.unit
    def test_client_key_with_custom_identifier(self):
        """Test client key generation with custom identifier."""
        limiter = RateLimiter()
        limiter.redis_client = None  # Don't need Redis for this test

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/test"

        key = limiter._get_client_key(mock_request, identifier="user:123")

        assert key == "seatsteal:ratelimit:user:123:/api/test"

    @pytest.mark.unit
    def test_client_key_with_forwarded_ip(self):
        """Test client key generation using X-Forwarded-For header."""
        limiter = RateLimiter()
        limiter.redis_client = None

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/test"
        mock_request.headers.get.return_value = "192.168.1.1, 10.0.0.1"

        key = limiter._get_client_key(mock_request)

        assert key == "seatsteal:ratelimit:ip:192.168.1.1:/api/test"

    @pytest.mark.unit
    def test_client_key_with_direct_ip(self):
        """Test client key generation using direct client IP."""
        limiter = RateLimiter()
        limiter.redis_client = None

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/courses"
        mock_request.headers.get.return_value = None
        mock_request.client.host = "203.0.113.42"

        key = limiter._get_client_key(mock_request)

        assert key == "seatsteal:ratelimit:ip:203.0.113.42:/api/courses"

    @pytest.mark.unit
    def test_client_key_no_client_info(self):
        """Test client key generation when no client info available."""
        limiter = RateLimiter()
        limiter.redis_client = None

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/test"
        mock_request.headers.get.return_value = None
        mock_request.client = None

        key = limiter._get_client_key(mock_request)

        assert key == "seatsteal:ratelimit:ip:unknown:/api/test"


class TestGetBucketKey:
    """Tests for _get_bucket_key method."""

    @pytest.mark.unit
    def test_bucket_key_generation(self):
        """Test bucket key generation for token bucket algorithm."""
        limiter = RateLimiter()
        limiter.redis_client = None

        base_key = "seatsteal:ratelimit:user:123:/api/test"
        tokens_key, timestamp_key = limiter._get_bucket_key(base_key)

        assert tokens_key == "seatsteal:ratelimit:user:123:/api/test:tokens"
        assert timestamp_key == "seatsteal:ratelimit:user:123:/api/test:timestamp"


class TestCheckRateLimit:
    """Tests for check_rate_limit method."""

    @pytest.mark.unit
    async def test_check_rate_limit_no_redis(self):
        """Test rate limit check when Redis is unavailable (allows all requests)."""
        limiter = RateLimiter()
        limiter.redis_client = None

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/test"

        is_allowed, info = await limiter.check_rate_limit(
            mock_request, max_requests=10, window_seconds=60
        )

        assert is_allowed is True
        assert info["remaining"] == 10
        assert info["retry_after"] == 0
        assert "reset_time" in info

    @pytest.mark.unit
    async def test_check_rate_limit_first_request(self):
        """Test rate limit check for first request (initializes bucket)."""
        limiter = RateLimiter()
        mock_redis = MagicMock()
        limiter.redis_client = mock_redis

        # First request - no tokens in Redis
        mock_redis.get.return_value = None

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/test"
        mock_request.headers.get.return_value = None
        mock_request.client.host = "192.168.1.1"

        is_allowed, info = await limiter.check_rate_limit(
            mock_request, max_requests=100, window_seconds=60
        )

        assert is_allowed is True
        assert info["remaining"] == 99  # 100 - 1
        assert info["retry_after"] == 0
        assert mock_redis.setex.call_count == 2  # Set tokens and timestamp

    @pytest.mark.unit
    async def test_check_rate_limit_subsequent_request_allowed(self):
        """Test rate limit check for allowed subsequent request."""
        limiter = RateLimiter()
        mock_redis = MagicMock()
        limiter.redis_client = mock_redis

        current_time = time.time()

        # Mock Redis returning existing tokens
        def mock_get(key):
            if "tokens" in key:
                return "50"
            if "timestamp" in key:
                return str(current_time - 10)  # 10 seconds ago
            return None

        mock_redis.get.side_effect = mock_get
        mock_redis.ttl.return_value = 50  # 50 seconds remaining

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/test"
        mock_request.headers.get.return_value = None
        mock_request.client.host = "192.168.1.1"

        is_allowed, info = await limiter.check_rate_limit(
            mock_request, max_requests=100, window_seconds=60
        )

        assert is_allowed is True
        assert info["remaining"] >= 0  # Should have tokens remaining
        assert info["retry_after"] == 0

    @pytest.mark.unit
    async def test_check_rate_limit_exceeded(self):
        """Test rate limit check when limit is exceeded."""
        limiter = RateLimiter()
        mock_redis = MagicMock()
        limiter.redis_client = mock_redis

        current_time = time.time()

        # Mock Redis returning no tokens
        def mock_get(key):
            if "tokens" in key:
                return "0"
            if "timestamp" in key:
                return str(current_time - 1)  # 1 second ago
            return None

        mock_redis.get.side_effect = mock_get
        mock_redis.ttl.return_value = 30  # 30 seconds until reset

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/test"
        mock_request.headers.get.return_value = None
        mock_request.client.host = "192.168.1.1"

        is_allowed, info = await limiter.check_rate_limit(
            mock_request, max_requests=100, window_seconds=60
        )

        assert is_allowed is False
        assert info["remaining"] == 0
        assert info["retry_after"] > 0

    @pytest.mark.unit
    async def test_check_rate_limit_token_replenishment(self):
        """Test token bucket replenishment over time."""
        limiter = RateLimiter()
        mock_redis = MagicMock()
        limiter.redis_client = mock_redis

        current_time = time.time()

        # Mock Redis returning low tokens but enough time passed for replenishment
        def mock_get(key):
            if "tokens" in key:
                return "10"
            if "timestamp" in key:
                return str(current_time - 30)  # 30 seconds ago
            return None

        mock_redis.get.side_effect = mock_get
        mock_redis.ttl.return_value = 30

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/test"
        mock_request.headers.get.return_value = None
        mock_request.client.host = "192.168.1.1"

        # With 100 requests per 60 seconds and 30 seconds passed, should replenish ~50 tokens
        is_allowed, info = await limiter.check_rate_limit(
            mock_request, max_requests=100, window_seconds=60
        )

        assert is_allowed is True
        # Should have replenished tokens (10 + ~50 from 30 seconds)
        assert info["remaining"] > 10


class TestRateLimitDecorator:
    """Tests for rate_limit decorator."""

    @pytest.mark.unit
    async def test_rate_limit_decorator_allows_request(self):
        """Test decorator allows request when under limit."""

        @rate_limit(max_requests=10, window_seconds=60)
        async def test_endpoint(request: Request):
            return {"message": "success"}

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/test"
        mock_request.headers.get.return_value = None
        mock_request.client.host = "192.168.1.1"

        with patch.object(
            rate_limiter,
            "check_rate_limit",
            return_value=(
                True,
                {"remaining": 9, "reset_time": int(time.time() + 60), "retry_after": 0},
            ),
        ):
            response = await test_endpoint(mock_request)
            assert response["message"] == "success"

    @pytest.mark.unit
    async def test_rate_limit_decorator_blocks_request(self):
        """Test decorator blocks request when limit exceeded."""

        @rate_limit(max_requests=10, window_seconds=60)
        async def test_endpoint(request: Request):
            return {"message": "success"}

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/test"

        with patch.object(
            rate_limiter,
            "check_rate_limit",
            return_value=(
                False,
                {
                    "remaining": 0,
                    "reset_time": int(time.time() + 30),
                    "retry_after": 30,
                },
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await test_endpoint(mock_request)

            assert exc_info.value.status_code == 429
            assert "Rate limit exceeded" in exc_info.value.detail["error"]
            assert exc_info.value.headers["Retry-After"] == "30"

    @pytest.mark.unit
    async def test_rate_limit_decorator_with_user_id(self):
        """Test decorator uses user ID when use_user_id=True."""

        @rate_limit(max_requests=10, window_seconds=60, use_user_id=True)
        async def test_endpoint(request: Request):
            return {"message": "success"}

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/test"
        mock_user = MagicMock()
        mock_user.id = 123
        mock_request.state.user = mock_user

        async def mock_check_rate_limit(
            request, max_requests, window_seconds, identifier
        ):
            # Verify identifier uses user ID
            assert identifier == "user:123"
            return True, {
                "remaining": 9,
                "reset_time": int(time.time() + 60),
                "retry_after": 0,
            }

        with patch.object(
            rate_limiter, "check_rate_limit", side_effect=mock_check_rate_limit
        ):
            response = await test_endpoint(mock_request)
            assert response["message"] == "success"

    @pytest.mark.unit
    async def test_rate_limit_decorator_no_request_object(self):
        """Test decorator skips rate limiting when no Request object found."""

        @rate_limit(max_requests=10, window_seconds=60)
        async def test_endpoint(data: dict):
            return {"message": "success"}

        # Call without Request object
        response = await test_endpoint({"test": "data"})
        assert response["message"] == "success"

    @pytest.mark.unit
    async def test_rate_limit_decorator_adds_headers_to_response(self):
        """Test decorator adds rate limit headers to response."""

        @rate_limit(max_requests=10, window_seconds=60)
        async def test_endpoint(request: Request):
            mock_response = MagicMock()
            mock_response.headers = {}
            return mock_response

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/test"

        reset_time = int(time.time() + 60)
        with patch.object(
            rate_limiter,
            "check_rate_limit",
            return_value=(
                True,
                {"remaining": 9, "reset_time": reset_time, "retry_after": 0},
            ),
        ):
            response = await test_endpoint(mock_request)
            assert response.headers["X-RateLimit-Limit"] == "10"
            assert response.headers["X-RateLimit-Remaining"] == "9"
            assert response.headers["X-RateLimit-Reset"] == str(reset_time)


class TestRateLimitMiddleware:
    """Tests for rate_limit_middleware function."""

    @pytest.mark.unit
    async def test_middleware_allows_request(self):
        """Test middleware allows request under global rate limit."""
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/test"

        mock_response = MagicMock()
        mock_response.headers = {}

        async def call_next(request):
            return mock_response

        with patch.object(
            rate_limiter,
            "check_rate_limit",
            return_value=(
                True,
                {
                    "remaining": 999,
                    "reset_time": int(time.time() + 60),
                    "retry_after": 0,
                },
            ),
        ):
            response = await rate_limit_middleware(mock_request, call_next)

            assert response == mock_response
            assert response.headers["X-RateLimit-Limit"] == "1000"
            assert response.headers["X-RateLimit-Remaining"] == "999"

    @pytest.mark.unit
    async def test_middleware_blocks_request(self):
        """Test middleware blocks request when global rate limit exceeded."""
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/test"

        async def call_next(request):
            return MagicMock()

        reset_time = int(time.time() + 30)
        with patch.object(
            rate_limiter,
            "check_rate_limit",
            return_value=(
                False,
                {"remaining": 0, "reset_time": reset_time, "retry_after": 30},
            ),
        ):
            response = await rate_limit_middleware(mock_request, call_next)

            assert response.status_code == 429
            assert response.headers["Retry-After"] == "30"
            assert response.headers["X-RateLimit-Limit"] == "1000"
            assert response.headers["X-RateLimit-Remaining"] == "0"
