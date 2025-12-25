"""
Comprehensive test suite for utils/cache.py

Tests Redis caching utilities including:
- CacheClient connection management
- cache_response decorator for async/sync functions
- Serialization of Pydantic models and datetimes
- Cache invalidation
- User profile and tier caching
"""

import pytest
import json
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import Mock, patch, MagicMock
from pydantic import BaseModel

# Use fakeredis for testing
import fakeredis

from utils.cache import (
    CacheClient,
    _serialize_for_cache,
    _make_cache_key,
    cache_response,
    invalidate_cache,
    invalidate_cache_pattern,
    get_user_profile_cache_key,
    cache_user_profile,
    get_cached_user_profile,
    invalidate_user_profile_cache,
    get_user_tier_cache_key,
    cache_user_tier,
    get_cached_user_tier,
    invalidate_user_tier_cache,
    invalidate_user_caches,
)


# Test Pydantic models
class TestUserModel(BaseModel):
    id: str
    email: str
    name: str


class TestCourseModel(BaseModel):
    course_id: int
    title: str
    created_at: datetime

    class Config:
        populate_by_name = True
        alias_generator = lambda x: x  # Keep snake_case


@pytest.fixture(autouse=True)
def reset_cache_client():
    """Reset CacheClient singleton before each test"""
    CacheClient._instance = None
    yield
    CacheClient._instance = None


@pytest.fixture
def fake_redis():
    """Create a fake Redis instance for testing"""
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def mock_settings_with_redis():
    """Mock settings with Redis URL configured"""
    with patch("utils.cache.settings") as mock_settings:
        mock_settings.REDIS_URL = "redis://localhost:6379"
        yield mock_settings


@pytest.fixture
def mock_settings_without_redis():
    """Mock settings without Redis URL"""
    with patch("utils.cache.settings") as mock_settings:
        mock_settings.REDIS_URL = None
        yield mock_settings


# ============================================================================
# CacheClient Tests
# ============================================================================


class TestCacheClient:
    """Test CacheClient connection management and singleton pattern"""

    def test_cache_client_initialization(self, fake_redis, mock_settings_with_redis):
        """Test CacheClient singleton pattern"""
        with patch("redis.from_url", return_value=fake_redis):
            client1 = CacheClient.get_client()
            client2 = CacheClient.get_client()

            assert client1 is client2
            assert client1 is not None

    def test_cache_client_with_valid_redis_url(self, fake_redis, mock_settings_with_redis):
        """Test successful connection to Redis"""
        with patch("redis.from_url", return_value=fake_redis):
            client = CacheClient.get_client()

            assert client is not None
            # Verify ping works
            assert client.ping() is True

    def test_cache_client_with_invalid_redis_url(self, mock_settings_with_redis):
        """Test graceful handling of connection failures"""
        mock_redis = Mock()
        mock_redis.ping.side_effect = Exception("Connection failed")

        with patch("redis.from_url", return_value=mock_redis):
            client = CacheClient.get_client()

            assert client is None

    def test_cache_client_without_redis_url(self, mock_settings_without_redis):
        """Test behavior when Redis URL not configured"""
        client = CacheClient.get_client()

        assert client is None

    def test_cache_client_connection_timeout(self, fake_redis, mock_settings_with_redis):
        """Test socket timeout configuration"""
        with patch("redis.from_url", return_value=fake_redis) as mock_from_url:
            CacheClient.get_client()

            # Verify timeout settings
            mock_from_url.assert_called_once_with(
                "redis://localhost:6379",
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )

    def test_cache_client_close(self, fake_redis, mock_settings_with_redis):
        """Test closing connection properly"""
        with patch("redis.from_url", return_value=fake_redis):
            client = CacheClient.get_client()
            assert client is not None

            CacheClient.close()

            assert CacheClient._instance is None

    def test_cache_client_reuse_existing_connection(self, fake_redis, mock_settings_with_redis):
        """Test that get_client doesn't recreate connection"""
        with patch("redis.from_url", return_value=fake_redis) as mock_from_url:
            CacheClient.get_client()
            CacheClient.get_client()
            CacheClient.get_client()

            # Should only be called once
            assert mock_from_url.call_count == 1

    def test_cache_client_ping_failure(self, mock_settings_with_redis):
        """Test handling of ping failures"""
        mock_redis = Mock()
        mock_redis.ping.side_effect = Exception("Ping failed")

        with patch("redis.from_url", return_value=mock_redis):
            client = CacheClient.get_client()

            assert client is None


# ============================================================================
# Serialization Tests
# ============================================================================


class TestSerialization:
    """Test _serialize_for_cache function"""

    def test_serialize_pydantic_model(self):
        """Test serialization of Pydantic models"""
        user = TestUserModel(id="123", email="test@example.com", name="Test User")

        result = _serialize_for_cache(user)

        assert isinstance(result, dict)
        assert result["id"] == "123"
        assert result["email"] == "test@example.com"
        assert result["name"] == "Test User"

    def test_serialize_datetime(self):
        """Test serialization of datetime objects"""
        dt = datetime(2025, 12, 25, 12, 0, 0, tzinfo=timezone.utc)

        result = _serialize_for_cache(dt)

        assert isinstance(result, str)
        assert result == "2025-12-25T12:00:00+00:00"

    def test_serialize_dict(self):
        """Test serialization of dictionaries"""
        data = {
            "name": "Test",
            "created_at": datetime(2025, 12, 25, tzinfo=timezone.utc),
        }

        result = _serialize_for_cache(data)

        assert isinstance(result, dict)
        assert result["name"] == "Test"
        assert result["created_at"] == "2025-12-25T00:00:00+00:00"

    def test_serialize_list(self):
        """Test serialization of lists"""
        dt = datetime(2025, 12, 25, tzinfo=timezone.utc)
        data = ["test", 123, dt]

        result = _serialize_for_cache(data)

        assert isinstance(result, list)
        assert result[0] == "test"
        assert result[1] == 123
        assert result[2] == "2025-12-25T00:00:00+00:00"

    def test_serialize_nested_structure(self):
        """Test serialization of nested structures"""
        user = TestUserModel(id="123", email="test@example.com", name="Test")
        data = {
            "user": user,
            "courses": [
                {"id": 1, "title": "Course 1"},
                {"id": 2, "title": "Course 2"},
            ],
            "timestamp": datetime(2025, 12, 25, tzinfo=timezone.utc),
        }

        result = _serialize_for_cache(data)

        assert isinstance(result, dict)
        assert isinstance(result["user"], dict)
        assert result["user"]["id"] == "123"
        assert len(result["courses"]) == 2
        assert result["timestamp"] == "2025-12-25T00:00:00+00:00"

    def test_serialize_primitive_types(self):
        """Test that primitive types pass through unchanged"""
        assert _serialize_for_cache("string") == "string"
        assert _serialize_for_cache(123) == 123
        assert _serialize_for_cache(45.67) == 45.67
        assert _serialize_for_cache(True) is True
        assert _serialize_for_cache(None) is None


# ============================================================================
# Cache Key Generation Tests
# ============================================================================


class TestCacheKeyGeneration:
    """Test _make_cache_key function"""

    def test_make_cache_key_deterministic(self):
        """Test that same inputs produce same key"""
        key1 = _make_cache_key("courses", college_id=1, search="cs")
        key2 = _make_cache_key("courses", college_id=1, search="cs")

        assert key1 == key2

    def test_make_cache_key_different_inputs(self):
        """Test that different inputs produce different keys"""
        key1 = _make_cache_key("courses", college_id=1)
        key2 = _make_cache_key("courses", college_id=2)

        assert key1 != key2

    def test_make_cache_key_order_independent(self):
        """Test that kwargs order doesn't matter"""
        key1 = _make_cache_key("courses", college_id=1, search="cs", page=2)
        key2 = _make_cache_key("courses", page=2, search="cs", college_id=1)

        assert key1 == key2

    def test_make_cache_key_length(self):
        """Test that keys have manageable length"""
        key = _make_cache_key("courses", college_id=1, search="computer science")

        # Should be prefix + hash (12 chars)
        assert key.startswith("courses:")
        assert len(key) == len("courses:") + 12

    def test_make_cache_key_special_characters(self):
        """Test handling of special characters in values"""
        key = _make_cache_key("courses", search="C++ & algorithms")

        assert key.startswith("courses:")
        assert len(key) == len("courses:") + 12


# ============================================================================
# cache_response Decorator - Async Tests
# ============================================================================


class TestCacheResponseAsync:
    """Test cache_response decorator with async functions"""

    @pytest.mark.asyncio
    async def test_cache_response_async_cache_miss(self, fake_redis, mock_settings_with_redis):
        """Test async function called on cache miss"""
        with patch("redis.from_url", return_value=fake_redis):
            call_count = 0

            @cache_response(prefix="test", ttl=300)
            async def test_func(value: int):
                nonlocal call_count
                call_count += 1
                return {"result": value * 2}

            result = await test_func(value=5)

            assert result == {"result": 10}
            assert call_count == 1
            # Verify stored in cache
            assert len(fake_redis.keys()) == 1

    @pytest.mark.asyncio
    async def test_cache_response_async_cache_hit(self, fake_redis, mock_settings_with_redis):
        """Test async function not called on cache hit"""
        with patch("redis.from_url", return_value=fake_redis):
            call_count = 0

            @cache_response(prefix="test", ttl=300)
            async def test_func(value: int):
                nonlocal call_count
                call_count += 1
                return {"result": value * 2}

            # First call - cache miss
            result1 = await test_func(value=5)
            assert call_count == 1

            # Second call - cache hit
            result2 = await test_func(value=5)
            assert call_count == 1  # Not called again
            assert result1 == result2

    @pytest.mark.asyncio
    async def test_cache_response_async_redis_unavailable(self, mock_settings_without_redis):
        """Test async function works when Redis unavailable"""
        call_count = 0

        @cache_response(prefix="test", ttl=300)
        async def test_func(value: int):
            nonlocal call_count
            call_count += 1
            return {"result": value * 2}

        result = await test_func(value=5)

        assert result == {"result": 10}
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_cache_response_async_redis_error(self, mock_settings_with_redis):
        """Test async function handles Redis errors gracefully"""
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_redis.get.side_effect = Exception("Redis error")

        with patch("redis.from_url", return_value=mock_redis):
            call_count = 0

            @cache_response(prefix="test", ttl=300)
            async def test_func(value: int):
                nonlocal call_count
                call_count += 1
                return {"result": value * 2}

            result = await test_func(value=5)

            # Should fall back to function call
            assert result == {"result": 10}
            assert call_count == 1

    @pytest.mark.asyncio
    async def test_cache_response_async_pydantic_serialization(self, fake_redis, mock_settings_with_redis):
        """Test async caching of Pydantic models"""
        with patch("redis.from_url", return_value=fake_redis):
            @cache_response(prefix="test", ttl=300)
            async def test_func():
                return TestUserModel(id="123", email="test@example.com", name="Test")

            result = await test_func()

            assert isinstance(result, TestUserModel)
            assert result.id == "123"

    @pytest.mark.asyncio
    async def test_cache_response_async_datetime_serialization(self, fake_redis, mock_settings_with_redis):
        """Test async caching of datetime objects"""
        with patch("redis.from_url", return_value=fake_redis):
            dt = datetime(2025, 12, 25, 12, 0, 0, tzinfo=timezone.utc)

            @cache_response(prefix="test", ttl=300)
            async def test_func():
                return {"timestamp": dt}

            result1 = await test_func()
            result2 = await test_func()

            # First call returns original object
            assert result1["timestamp"] == dt
            # Second call returns from cache (deserialized from JSON)
            assert result2["timestamp"] == "2025-12-25T12:00:00+00:00"

    @pytest.mark.asyncio
    async def test_cache_response_async_custom_key_builder(self, fake_redis, mock_settings_with_redis):
        """Test async caching with custom key builder"""
        with patch("redis.from_url", return_value=fake_redis):
            call_count = 0

            def build_key(college_id, **kwargs):
                # Only use college_id in cache key, ignore page
                return {"college": college_id}

            @cache_response(prefix="test", ttl=300, key_builder=build_key)
            async def test_func(college_id: int, page: int = 1):
                nonlocal call_count
                call_count += 1
                return {"college": college_id, "page": page}

            # Different pages, same college - should use cache
            result1 = await test_func(college_id=1, page=1)
            result2 = await test_func(college_id=1, page=2)

            assert call_count == 1  # Only called once
            assert result1 == result2  # Both return cached result

    @pytest.mark.asyncio
    async def test_cache_response_async_ttl_configuration(self, fake_redis, mock_settings_with_redis):
        """Test async caching respects TTL"""
        with patch("redis.from_url", return_value=fake_redis):
            @cache_response(prefix="test", ttl=600)
            async def test_func(value: int):
                return {"result": value}

            await test_func(value=5)

            # Check TTL was set
            keys = list(fake_redis.keys())
            assert len(keys) == 1
            ttl = fake_redis.ttl(keys[0])
            assert ttl > 0
            assert ttl <= 600


# ============================================================================
# cache_response Decorator - Sync Tests
# ============================================================================


class TestCacheResponseSync:
    """Test cache_response decorator with synchronous functions"""

    def test_cache_response_sync_cache_miss(self, fake_redis, mock_settings_with_redis):
        """Test sync function called on cache miss"""
        with patch("redis.from_url", return_value=fake_redis):
            call_count = 0

            @cache_response(prefix="test", ttl=300)
            def test_func(value: int):
                nonlocal call_count
                call_count += 1
                return {"result": value * 2}

            result = test_func(value=5)

            assert result == {"result": 10}
            assert call_count == 1

    def test_cache_response_sync_cache_hit(self, fake_redis, mock_settings_with_redis):
        """Test sync function not called on cache hit"""
        with patch("redis.from_url", return_value=fake_redis):
            call_count = 0

            @cache_response(prefix="test", ttl=300)
            def test_func(value: int):
                nonlocal call_count
                call_count += 1
                return {"result": value * 2}

            result1 = test_func(value=5)
            result2 = test_func(value=5)

            assert call_count == 1
            assert result1 == result2

    def test_cache_response_sync_redis_unavailable(self, mock_settings_without_redis):
        """Test sync function works when Redis unavailable"""
        @cache_response(prefix="test", ttl=300)
        def test_func(value: int):
            return {"result": value * 2}

        result = test_func(value=5)

        assert result == {"result": 10}

    def test_cache_response_sync_redis_error(self, mock_settings_with_redis):
        """Test sync function handles Redis errors"""
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_redis.get.side_effect = Exception("Redis error")

        with patch("redis.from_url", return_value=mock_redis):
            @cache_response(prefix="test", ttl=300)
            def test_func(value: int):
                return {"result": value * 2}

            result = test_func(value=5)

            assert result == {"result": 10}

    def test_cache_response_sync_pydantic_serialization(self, fake_redis, mock_settings_with_redis):
        """Test sync caching of Pydantic models"""
        with patch("redis.from_url", return_value=fake_redis):
            @cache_response(prefix="test", ttl=300)
            def test_func():
                return TestUserModel(id="456", email="sync@example.com", name="Sync")

            result1 = test_func()
            result2 = test_func()

            # First call returns original Pydantic model
            assert isinstance(result1, TestUserModel)
            assert result1.id == "456"
            # Second call returns deserialized dict from cache
            assert isinstance(result2, dict)
            assert result2["id"] == "456"


# ============================================================================
# Cache Invalidation Tests
# ============================================================================


class TestCacheInvalidation:
    """Test cache invalidation functions"""

    def test_invalidate_cache_single_key(self, fake_redis, mock_settings_with_redis):
        """Test deletion of specific cache key"""
        with patch("redis.from_url", return_value=fake_redis):
            # Set a cache value
            cache_key = _make_cache_key("courses", college_id=1)
            fake_redis.set(cache_key, json.dumps({"data": "test"}))

            assert fake_redis.exists(cache_key)

            invalidate_cache("courses", college_id=1)

            assert not fake_redis.exists(cache_key)

    def test_invalidate_cache_redis_unavailable(self, mock_settings_without_redis):
        """Test invalidation when Redis unavailable"""
        # Should not raise exception
        invalidate_cache("courses", college_id=1)

    def test_invalidate_cache_pattern_match(self, fake_redis, mock_settings_with_redis):
        """Test pattern-based invalidation"""
        with patch("redis.from_url", return_value=fake_redis):
            # Set multiple cache values
            fake_redis.set("courses:abc123", "data1")
            fake_redis.set("courses:def456", "data2")
            fake_redis.set("colleges:xyz789", "data3")

            invalidate_cache_pattern("courses:*")

            assert not fake_redis.exists("courses:abc123")
            assert not fake_redis.exists("courses:def456")
            assert fake_redis.exists("colleges:xyz789")  # Not deleted

    def test_invalidate_cache_pattern_no_matches(self, fake_redis, mock_settings_with_redis):
        """Test pattern invalidation with no matches"""
        with patch("redis.from_url", return_value=fake_redis):
            fake_redis.set("courses:abc123", "data1")

            # Should not raise exception
            invalidate_cache_pattern("nonexistent:*")

            assert fake_redis.exists("courses:abc123")

    def test_invalidate_cache_error_handling(self, mock_settings_with_redis):
        """Test error handling during invalidation"""
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_redis.delete.side_effect = Exception("Delete failed")

        with patch("redis.from_url", return_value=mock_redis):
            # Should not raise exception
            invalidate_cache("courses", college_id=1)


# ============================================================================
# User Profile Caching Tests
# ============================================================================


class TestUserProfileCaching:
    """Test user profile caching utilities"""

    def test_get_user_profile_cache_key(self):
        """Test cache key generation for user profiles"""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        key = get_user_profile_cache_key(user_id)

        assert key == f"user_profile:{user_id}"

    def test_cache_user_profile(self, fake_redis, mock_settings_with_redis):
        """Test caching user profile data"""
        with patch("redis.from_url", return_value=fake_redis):
            user_id = "123e4567-e89b-12d3-a456-426614174000"
            profile_data = {
                "id": user_id,
                "email": "test@example.com",
                "name": "Test User",
            }

            cache_user_profile(user_id, profile_data, ttl=600)

            # Verify cached
            cache_key = get_user_profile_cache_key(user_id)
            cached = fake_redis.get(cache_key)
            assert cached is not None
            assert json.loads(cached) == profile_data

    def test_get_cached_user_profile_hit(self, fake_redis, mock_settings_with_redis):
        """Test retrieving cached user profile"""
        with patch("redis.from_url", return_value=fake_redis):
            user_id = "123e4567-e89b-12d3-a456-426614174000"
            profile_data = {"id": user_id, "email": "test@example.com"}

            cache_user_profile(user_id, profile_data)
            result = get_cached_user_profile(user_id)

            assert result == profile_data

    def test_get_cached_user_profile_miss(self, fake_redis, mock_settings_with_redis):
        """Test cache miss for user profile"""
        with patch("redis.from_url", return_value=fake_redis):
            user_id = "123e4567-e89b-12d3-a456-426614174000"
            result = get_cached_user_profile(user_id)

            assert result is None

    def test_get_cached_user_profile_redis_unavailable(self, mock_settings_without_redis):
        """Test getting profile when Redis unavailable"""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        result = get_cached_user_profile(user_id)

        assert result is None

    def test_invalidate_user_profile_cache(self, fake_redis, mock_settings_with_redis):
        """Test invalidating user profile cache"""
        with patch("redis.from_url", return_value=fake_redis):
            user_id = "123e4567-e89b-12d3-a456-426614174000"
            profile_data = {"id": user_id, "email": "test@example.com"}

            cache_user_profile(user_id, profile_data)
            assert get_cached_user_profile(user_id) is not None

            invalidate_user_profile_cache(user_id)
            assert get_cached_user_profile(user_id) is None


# ============================================================================
# User Tier Caching Tests
# ============================================================================


class TestUserTierCaching:
    """Test user subscription tier caching utilities"""

    def test_get_user_tier_cache_key(self):
        """Test cache key generation for user tier"""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        key = get_user_tier_cache_key(user_id)

        assert key == f"user_tier:{user_id}"

    def test_cache_user_tier(self, fake_redis, mock_settings_with_redis):
        """Test caching user tier"""
        with patch("redis.from_url", return_value=fake_redis):
            user_id = "123e4567-e89b-12d3-a456-426614174000"

            cache_user_tier(user_id, "pro", ttl=600)

            cache_key = get_user_tier_cache_key(user_id)
            cached = fake_redis.get(cache_key)
            assert cached == "pro"

    def test_get_cached_user_tier_hit(self, fake_redis, mock_settings_with_redis):
        """Test retrieving cached user tier"""
        with patch("redis.from_url", return_value=fake_redis):
            user_id = "123e4567-e89b-12d3-a456-426614174000"

            cache_user_tier(user_id, "plus")
            result = get_cached_user_tier(user_id)

            assert result == "plus"

    def test_get_cached_user_tier_miss(self, fake_redis, mock_settings_with_redis):
        """Test cache miss for user tier"""
        with patch("redis.from_url", return_value=fake_redis):
            user_id = "123e4567-e89b-12d3-a456-426614174000"
            result = get_cached_user_tier(user_id)

            assert result is None

    def test_invalidate_user_tier_cache(self, fake_redis, mock_settings_with_redis):
        """Test invalidating user tier cache"""
        with patch("redis.from_url", return_value=fake_redis):
            user_id = "123e4567-e89b-12d3-a456-426614174000"

            cache_user_tier(user_id, "pro")
            assert get_cached_user_tier(user_id) == "pro"

            invalidate_user_tier_cache(user_id)
            assert get_cached_user_tier(user_id) is None


# ============================================================================
# Combined User Cache Tests
# ============================================================================


class TestCombinedUserCaches:
    """Test invalidating all user caches together"""

    def test_invalidate_user_caches(self, fake_redis, mock_settings_with_redis):
        """Test invalidating both profile and tier caches"""
        with patch("redis.from_url", return_value=fake_redis):
            user_id = "123e4567-e89b-12d3-a456-426614174000"

            # Cache both profile and tier
            cache_user_profile(user_id, {"id": user_id, "email": "test@example.com"})
            cache_user_tier(user_id, "pro")

            assert get_cached_user_profile(user_id) is not None
            assert get_cached_user_tier(user_id) == "pro"

            # Invalidate both
            invalidate_user_caches(user_id)

            assert get_cached_user_profile(user_id) is None
            assert get_cached_user_tier(user_id) is None

    def test_invalidate_user_caches_partial_failure(self, fake_redis, mock_settings_with_redis):
        """Test that partial failures don't stop invalidation"""
        with patch("redis.from_url", return_value=fake_redis):
            user_id = "123e4567-e89b-12d3-a456-426614174000"

            cache_user_tier(user_id, "pro")

            # Mock profile invalidation to fail
            with patch("utils.cache.invalidate_user_profile_cache", side_effect=Exception("Failed")):
                # Should not raise exception
                invalidate_user_caches(user_id)

            # Tier should still be invalidated
            assert get_cached_user_tier(user_id) is None


# ============================================================================
# Integration Tests
# ============================================================================


class TestCacheIntegration:
    """Integration tests for caching across multiple calls"""

    @pytest.mark.asyncio
    async def test_cache_across_multiple_calls(self, fake_redis, mock_settings_with_redis):
        """Test caching behavior across multiple function calls"""
        with patch("redis.from_url", return_value=fake_redis):
            call_count = 0

            @cache_response(prefix="test", ttl=300)
            async def expensive_operation(value: int):
                nonlocal call_count
                call_count += 1
                return {"result": value * 2}

            # First call - cache miss
            result1 = await expensive_operation(value=10)
            assert call_count == 1

            # Multiple calls with same args - cache hits
            result2 = await expensive_operation(value=10)
            result3 = await expensive_operation(value=10)
            assert call_count == 1  # Still only 1 call

            # Different args - new cache miss
            result4 = await expensive_operation(value=20)
            assert call_count == 2

            assert result1 == result2 == result3
            assert result4 != result1

    def test_cache_with_different_prefixes(self, fake_redis, mock_settings_with_redis):
        """Test that different prefixes don't collide"""
        with patch("redis.from_url", return_value=fake_redis):
            @cache_response(prefix="courses", ttl=300)
            def get_courses(college_id: int):
                return {"courses": [f"course_{college_id}"]}

            @cache_response(prefix="classes", ttl=300)
            def get_classes(college_id: int):
                return {"classes": [f"class_{college_id}"]}

            courses = get_courses(college_id=1)
            classes = get_classes(college_id=1)

            assert courses != classes
            assert "courses" in courses
            assert "classes" in classes

    def test_cache_serialization_round_trip(self, fake_redis, mock_settings_with_redis):
        """Test serialization and deserialization maintains data integrity"""
        with patch("redis.from_url", return_value=fake_redis):
            dt = datetime(2025, 12, 25, 15, 30, 0, tzinfo=timezone.utc)
            original_data = {
                "id": 123,
                "name": "Test Course",
                "created_at": dt,
                "tags": ["python", "testing"],
                "metadata": {
                    "difficulty": "intermediate",
                    "duration": 60,
                },
            }

            @cache_response(prefix="test", ttl=300)
            def get_data():
                return original_data

            # First call - stores in cache
            result1 = get_data()

            # Second call - retrieves from cache
            result2 = get_data()

            # Data should be identical
            assert result2["id"] == 123
            assert result2["name"] == "Test Course"
            assert result2["created_at"] == dt.isoformat()
            assert result2["tags"] == ["python", "testing"]
            assert result2["metadata"]["difficulty"] == "intermediate"
