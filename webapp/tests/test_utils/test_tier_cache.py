"""Tests for user subscription tier caching."""

import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4

from utils.cache import (
    get_user_tier_cache_key,
    cache_user_tier,
    get_cached_user_tier,
    invalidate_user_tier_cache,
    invalidate_user_caches,
)


class TestTierCacheKeyGeneration:
    """Tests for tier cache key generation."""

    @pytest.mark.unit
    def test_tier_cache_key_format(self):
        """Test that tier cache key has correct format."""
        user_id = str(uuid4())
        key = get_user_tier_cache_key(user_id)
        
        assert key == f"user_tier:{user_id}"
        assert key.startswith("user_tier:")

    @pytest.mark.unit
    def test_tier_cache_key_consistency(self):
        """Test that same user_id always generates same key."""
        user_id = str(uuid4())
        
        key1 = get_user_tier_cache_key(user_id)
        key2 = get_user_tier_cache_key(user_id)
        
        assert key1 == key2


class TestCacheUserTier:
    """Tests for caching user subscription tier."""

    @pytest.mark.unit
    def test_cache_user_tier_stores_data(self):
        """Test that tier is cached correctly."""
        with patch("utils.cache.CacheClient.get_client") as mock_get_client:
            mock_redis = MagicMock()
            mock_get_client.return_value = mock_redis
            
            user_id = str(uuid4())
            tier = "pro"
            
            cache_user_tier(user_id, tier, ttl=300)
            
            # Verify Redis setex was called with correct parameters
            mock_redis.setex.assert_called_once()
            call_args = mock_redis.setex.call_args
            
            # Verify cache key
            assert call_args[0][0] == f"user_tier:{user_id}"
            # Verify TTL
            assert call_args[0][1] == 300
            # Verify tier value
            assert call_args[0][2] == "pro"

    @pytest.mark.unit
    def test_cache_user_tier_all_tier_values(self):
        """Test caching all possible tier values."""
        with patch("utils.cache.CacheClient.get_client") as mock_get_client:
            mock_redis = MagicMock()
            mock_get_client.return_value = mock_redis
            
            user_id = str(uuid4())
            
            for tier in ["free", "plus", "pro"]:
                cache_user_tier(user_id, tier, ttl=300)
                
                # Get the last call
                call_args = mock_redis.setex.call_args
                assert call_args[0][2] == tier

    @pytest.mark.unit
    def test_cache_user_tier_handles_redis_unavailable(self):
        """Test that caching gracefully handles Redis unavailability."""
        with patch("utils.cache.CacheClient.get_client") as mock_get_client:
            mock_get_client.return_value = None
            
            user_id = str(uuid4())
            # Should not raise exception
            cache_user_tier(user_id, "pro", ttl=300)

    @pytest.mark.unit
    def test_cache_user_tier_handles_redis_error(self):
        """Test that caching errors don't propagate."""
        with patch("utils.cache.CacheClient.get_client") as mock_get_client:
            mock_redis = MagicMock()
            mock_redis.setex.side_effect = Exception("Redis connection failed")
            mock_get_client.return_value = mock_redis
            
            user_id = str(uuid4())
            # Should not raise exception
            cache_user_tier(user_id, "plus", ttl=300)


class TestGetCachedUserTier:
    """Tests for retrieving cached user tier."""

    @pytest.mark.unit
    def test_get_cached_tier_returns_data(self):
        """Test that cached tier is retrieved correctly."""
        with patch("utils.cache.CacheClient.get_client") as mock_get_client:
            mock_redis = MagicMock()
            user_id = str(uuid4())
            mock_redis.get.return_value = "pro"
            mock_get_client.return_value = mock_redis
            
            result = get_cached_user_tier(user_id)
            
            assert result == "pro"
            
            # Verify correct cache key was used
            mock_redis.get.assert_called_once_with(f"user_tier:{user_id}")

    @pytest.mark.unit
    def test_get_cached_tier_cache_miss(self):
        """Test that cache miss returns None."""
        with patch("utils.cache.CacheClient.get_client") as mock_get_client:
            mock_redis = MagicMock()
            mock_redis.get.return_value = None
            mock_get_client.return_value = mock_redis
            
            user_id = str(uuid4())
            result = get_cached_user_tier(user_id)
            
            assert result is None

    @pytest.mark.unit
    def test_get_cached_tier_handles_redis_unavailable(self):
        """Test that retrieval handles Redis unavailability."""
        with patch("utils.cache.CacheClient.get_client") as mock_get_client:
            mock_get_client.return_value = None
            
            user_id = str(uuid4())
            result = get_cached_user_tier(user_id)
            
            assert result is None

    @pytest.mark.unit
    def test_get_cached_tier_handles_redis_error(self):
        """Test that retrieval errors don't propagate."""
        with patch("utils.cache.CacheClient.get_client") as mock_get_client:
            mock_redis = MagicMock()
            mock_redis.get.side_effect = Exception("Redis connection failed")
            mock_get_client.return_value = mock_redis
            
            user_id = str(uuid4())
            result = get_cached_user_tier(user_id)
            
            # Should return None instead of raising exception
            assert result is None


class TestInvalidateUserTierCache:
    """Tests for tier cache invalidation."""

    @pytest.mark.unit
    def test_invalidate_tier_deletes_cache_key(self):
        """Test that invalidation deletes the correct cache key."""
        with patch("utils.cache.CacheClient.get_client") as mock_get_client:
            mock_redis = MagicMock()
            mock_get_client.return_value = mock_redis
            
            user_id = str(uuid4())
            invalidate_user_tier_cache(user_id)
            
            # Verify Redis delete was called with correct key
            mock_redis.delete.assert_called_once_with(f"user_tier:{user_id}")

    @pytest.mark.unit
    def test_invalidate_tier_handles_redis_unavailable(self):
        """Test that invalidation handles Redis unavailability."""
        with patch("utils.cache.CacheClient.get_client") as mock_get_client:
            mock_get_client.return_value = None
            
            user_id = str(uuid4())
            # Should not raise exception
            invalidate_user_tier_cache(user_id)

    @pytest.mark.unit
    def test_invalidate_tier_handles_redis_error(self):
        """Test that invalidation errors don't propagate."""
        with patch("utils.cache.CacheClient.get_client") as mock_get_client:
            mock_redis = MagicMock()
            mock_redis.delete.side_effect = Exception("Redis connection failed")
            mock_get_client.return_value = mock_redis
            
            user_id = str(uuid4())
            # Should not raise exception
            invalidate_user_tier_cache(user_id)


class TestInvalidateUserCaches:
    """Tests for invalidating all user caches at once."""

    @pytest.mark.unit
    def test_invalidate_user_caches_invalidates_both(self):
        """Test that invalidate_user_caches invalidates both profile and tier."""
        with patch("utils.cache.invalidate_user_profile_cache") as mock_invalidate_profile, \
             patch("utils.cache.invalidate_user_tier_cache") as mock_invalidate_tier:
            
            user_id = str(uuid4())
            invalidate_user_caches(user_id)
            
            # Verify both invalidation functions were called
            mock_invalidate_profile.assert_called_once_with(user_id)
            mock_invalidate_tier.assert_called_once_with(user_id)

    @pytest.mark.unit
    def test_invalidate_user_caches_continues_on_error(self):
        """Test that invalidate_user_caches continues even if one fails."""
        with patch("utils.cache.invalidate_user_profile_cache") as mock_invalidate_profile, \
             patch("utils.cache.invalidate_user_tier_cache") as mock_invalidate_tier:
            
            # Make profile invalidation raise an error
            mock_invalidate_profile.side_effect = Exception("Profile cache error")
            
            user_id = str(uuid4())
            
            # Should not raise exception, and should still call tier invalidation
            invalidate_user_caches(user_id)
            
            # Both should have been called
            mock_invalidate_profile.assert_called_once_with(user_id)
            mock_invalidate_tier.assert_called_once_with(user_id)


class TestTierCacheIntegration:
    """Integration tests for tier cache lifecycle."""

    @pytest.mark.unit
    def test_tier_cache_write_read_invalidate_cycle(self):
        """Test complete tier cache lifecycle: write, read, invalidate."""
        with patch("utils.cache.CacheClient.get_client") as mock_get_client:
            mock_redis = MagicMock()
            mock_get_client.return_value = mock_redis
            
            user_id = str(uuid4())
            tier = "plus"
            
            # Write to cache
            cache_user_tier(user_id, tier, ttl=300)
            assert mock_redis.setex.called
            
            # Simulate read (mock Redis returning cached tier)
            mock_redis.get.return_value = tier
            cached = get_cached_user_tier(user_id)
            assert cached == tier
            
            # Invalidate
            invalidate_user_tier_cache(user_id)
            assert mock_redis.delete.called
            
            # Simulate cache miss after invalidation
            mock_redis.get.return_value = None
            cached_after = get_cached_user_tier(user_id)
            assert cached_after is None

