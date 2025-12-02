"""Tests for user profile cache invalidation."""

import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4

from utils.cache import (
    get_user_profile_cache_key,
    cache_user_profile,
    get_cached_user_profile,
    invalidate_user_profile_cache,
)


class TestCacheKeyGeneration:
    """Tests for cache key generation."""

    @pytest.mark.unit
    def test_cache_key_format(self):
        """Test that cache key has correct format."""
        user_id = str(uuid4())
        key = get_user_profile_cache_key(user_id)

        assert key == f"user_profile:{user_id}"
        assert key.startswith("user_profile:")

    @pytest.mark.unit
    def test_cache_key_consistency(self):
        """Test that same user_id always generates same key."""
        user_id = str(uuid4())

        key1 = get_user_profile_cache_key(user_id)
        key2 = get_user_profile_cache_key(user_id)

        assert key1 == key2


class TestCacheUserProfile:
    """Tests for caching user profile data."""

    @pytest.mark.unit
    def test_cache_user_profile_stores_data(self):
        """Test that profile data is cached correctly."""
        with patch("utils.cache.CacheClient.get_client") as mock_get_client:
            mock_redis = MagicMock()
            mock_get_client.return_value = mock_redis

            user_id = str(uuid4())
            profile_data = {
                "id": user_id,
                "email": "test@example.com",
                "role": "user",
                "college_id": 1,
            }

            cache_user_profile(user_id, profile_data, ttl=300)

            # Verify Redis setex was called with correct parameters
            mock_redis.setex.assert_called_once()
            call_args = mock_redis.setex.call_args

            # Verify cache key
            assert call_args[0][0] == f"user_profile:{user_id}"
            # Verify TTL
            assert call_args[0][1] == 300
            # Verify data is JSON serialized (third argument)
            assert '"id"' in call_args[0][2]
            assert user_id in call_args[0][2]

    @pytest.mark.unit
    def test_cache_user_profile_handles_redis_unavailable(self):
        """Test that caching gracefully handles Redis unavailability."""
        with patch("utils.cache.CacheClient.get_client") as mock_get_client:
            mock_get_client.return_value = None

            user_id = str(uuid4())
            profile_data = {"id": user_id, "email": "test@example.com"}

            # Should not raise exception
            cache_user_profile(user_id, profile_data, ttl=300)

    @pytest.mark.unit
    def test_cache_user_profile_handles_redis_error(self):
        """Test that caching errors don't propagate."""
        with patch("utils.cache.CacheClient.get_client") as mock_get_client:
            mock_redis = MagicMock()
            mock_redis.setex.side_effect = Exception("Redis connection failed")
            mock_get_client.return_value = mock_redis

            user_id = str(uuid4())
            profile_data = {"id": user_id, "email": "test@example.com"}

            # Should not raise exception
            cache_user_profile(user_id, profile_data, ttl=300)


class TestGetCachedUserProfile:
    """Tests for retrieving cached user profile data."""

    @pytest.mark.unit
    def test_get_cached_profile_returns_data(self):
        """Test that cached profile data is retrieved correctly."""
        with patch("utils.cache.CacheClient.get_client") as mock_get_client:
            mock_redis = MagicMock()
            user_id = str(uuid4())
            cached_json = f'{{"id": "{user_id}", "email": "test@example.com"}}'
            mock_redis.get.return_value = cached_json
            mock_get_client.return_value = mock_redis

            result = get_cached_user_profile(user_id)

            assert result is not None
            assert result["id"] == user_id
            assert result["email"] == "test@example.com"

            # Verify correct cache key was used
            mock_redis.get.assert_called_once_with(f"user_profile:{user_id}")

    @pytest.mark.unit
    def test_get_cached_profile_cache_miss(self):
        """Test that cache miss returns None."""
        with patch("utils.cache.CacheClient.get_client") as mock_get_client:
            mock_redis = MagicMock()
            mock_redis.get.return_value = None
            mock_get_client.return_value = mock_redis

            user_id = str(uuid4())
            result = get_cached_user_profile(user_id)

            assert result is None

    @pytest.mark.unit
    def test_get_cached_profile_handles_redis_unavailable(self):
        """Test that retrieval handles Redis unavailability."""
        with patch("utils.cache.CacheClient.get_client") as mock_get_client:
            mock_get_client.return_value = None

            user_id = str(uuid4())
            result = get_cached_user_profile(user_id)

            assert result is None

    @pytest.mark.unit
    def test_get_cached_profile_handles_redis_error(self):
        """Test that retrieval errors don't propagate."""
        with patch("utils.cache.CacheClient.get_client") as mock_get_client:
            mock_redis = MagicMock()
            mock_redis.get.side_effect = Exception("Redis connection failed")
            mock_get_client.return_value = mock_redis

            user_id = str(uuid4())
            result = get_cached_user_profile(user_id)

            # Should return None instead of raising exception
            assert result is None


class TestInvalidateUserProfileCache:
    """Tests for cache invalidation."""

    @pytest.mark.unit
    def test_invalidate_deletes_cache_key(self):
        """Test that invalidation deletes the correct cache key."""
        with patch("utils.cache.CacheClient.get_client") as mock_get_client:
            mock_redis = MagicMock()
            mock_get_client.return_value = mock_redis

            user_id = str(uuid4())
            invalidate_user_profile_cache(user_id)

            # Verify Redis delete was called with correct key
            mock_redis.delete.assert_called_once_with(f"user_profile:{user_id}")

    @pytest.mark.unit
    def test_invalidate_handles_redis_unavailable(self):
        """Test that invalidation handles Redis unavailability."""
        with patch("utils.cache.CacheClient.get_client") as mock_get_client:
            mock_get_client.return_value = None

            user_id = str(uuid4())
            # Should not raise exception
            invalidate_user_profile_cache(user_id)

    @pytest.mark.unit
    def test_invalidate_handles_redis_error(self):
        """Test that invalidation errors don't propagate."""
        with patch("utils.cache.CacheClient.get_client") as mock_get_client:
            mock_redis = MagicMock()
            mock_redis.delete.side_effect = Exception("Redis connection failed")
            mock_get_client.return_value = mock_redis

            user_id = str(uuid4())
            # Should not raise exception
            invalidate_user_profile_cache(user_id)

    @pytest.mark.unit
    def test_invalidate_multiple_users_independent(self):
        """Test that invalidating one user doesn't affect others."""
        with patch("utils.cache.CacheClient.get_client") as mock_get_client:
            mock_redis = MagicMock()
            mock_get_client.return_value = mock_redis

            user_id1 = str(uuid4())
            user_id2 = str(uuid4())

            invalidate_user_profile_cache(user_id1)
            invalidate_user_profile_cache(user_id2)

            # Verify both users were invalidated with correct keys
            assert mock_redis.delete.call_count == 2
            calls = [call[0][0] for call in mock_redis.delete.call_args_list]
            assert f"user_profile:{user_id1}" in calls
            assert f"user_profile:{user_id2}" in calls


class TestCacheInvalidationIntegration:
    """Integration tests for cache invalidation scenarios."""

    @pytest.mark.unit
    def test_cache_write_read_invalidate_cycle(self):
        """Test complete cache lifecycle: write, read, invalidate."""
        with patch("utils.cache.CacheClient.get_client") as mock_get_client:
            mock_redis = MagicMock()
            mock_get_client.return_value = mock_redis

            user_id = str(uuid4())
            profile_data = {
                "id": user_id,
                "email": "test@example.com",
                "role": "user",
            }

            # Write to cache
            cache_user_profile(user_id, profile_data, ttl=300)
            assert mock_redis.setex.called

            # Simulate read (mock Redis returning cached data)
            import json

            mock_redis.get.return_value = json.dumps(profile_data)
            cached = get_cached_user_profile(user_id)
            assert cached is not None
            assert cached["id"] == user_id

            # Invalidate
            invalidate_user_profile_cache(user_id)
            assert mock_redis.delete.called

            # Simulate cache miss after invalidation
            mock_redis.get.return_value = None
            cached_after = get_cached_user_profile(user_id)
            assert cached_after is None
