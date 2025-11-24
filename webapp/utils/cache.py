"""
Redis caching utilities for API response caching.

Provides a simple caching layer with TTL support for reducing database load
and improving API response times.
"""

import json
import hashlib
from typing import Any, Optional, Callable
from functools import wraps
from datetime import datetime
from pydantic import BaseModel
import redis
from loguru import logger

from config import settings


class CacheClient:
    """Redis cache client with connection pooling and error handling."""

    _instance: Optional[redis.Redis] = None

    @classmethod
    def get_client(cls) -> Optional[redis.Redis]:
        """
        Get or create Redis client instance.

        Returns None if Redis is not configured or connection fails.
        Uses connection pooling for efficiency.
        """
        if cls._instance is not None:
            return cls._instance

        if not settings.REDIS_URL:
            logger.warning("Redis URL not configured, caching disabled")
            return None

        try:
            cls._instance = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Test connection
            cls._instance.ping()
            logger.info("Redis connection established")
            return cls._instance
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return None

    @classmethod
    def close(cls):
        """Close Redis connection."""
        if cls._instance:
            cls._instance.close()
            cls._instance = None


def _serialize_for_cache(obj: Any) -> Any:
    """
    Recursively serialize objects for caching, handling Pydantic models and datetimes.

    Args:
        obj: Object to serialize

    Returns:
        JSON-serializable version of the object
    """
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json", by_alias=True)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: _serialize_for_cache(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_serialize_for_cache(item) for item in obj]
    else:
        return obj


def _make_cache_key(prefix: str, **kwargs) -> str:
    """
    Generate a cache key from a prefix and keyword arguments.

    Args:
        prefix: Cache key prefix (e.g., 'courses', 'colleges')
        **kwargs: Key-value pairs to include in cache key

    Returns:
        A deterministic cache key string
    """
    # Sort kwargs for consistent key generation
    sorted_params = sorted(kwargs.items())
    # Serialize for consistent string representation
    param_str = json.dumps(sorted_params, sort_keys=True, default=str)
    # Hash params to keep key length manageable
    param_hash = hashlib.md5(param_str.encode()).hexdigest()[:12]
    return f"{prefix}:{param_hash}"


def cache_response(
    prefix: str,
    ttl: int = 300,
    key_builder: Optional[Callable[..., dict]] = None,
):
    """
    Decorator to cache function responses in Redis.

    Args:
        prefix: Cache key prefix (e.g., 'courses', 'colleges')
        ttl: Time to live in seconds (default: 300 = 5 minutes)
        key_builder: Optional function to extract cache key parameters from function args

    Example:
        @cache_response(prefix='courses', ttl=600)
        async def get_courses(college_id: int, search: str):
            # Function implementation
            pass

        # With custom key builder
        def build_key(college_id, **kwargs):
            return {'college': college_id}

        @cache_response(prefix='courses', ttl=600, key_builder=build_key)
        async def get_courses(college_id: int, page: int = 1):
            # Only college_id is used in cache key, page is ignored
            pass
    """

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            client = CacheClient.get_client()

            # If Redis not available, bypass cache
            if client is None:
                return await func(*args, **kwargs)

            # Build cache key
            try:
                if key_builder:
                    key_params = key_builder(*args, **kwargs)
                else:
                    # Default: use all kwargs
                    key_params = kwargs

                cache_key = _make_cache_key(prefix, **key_params)

                # Try to get from cache
                cached = client.get(cache_key)
                if cached:
                    logger.debug(f"Cache hit: {cache_key}")
                    return json.loads(cached)

                # Cache miss - call function
                logger.debug(f"Cache miss: {cache_key}")
                result = await func(*args, **kwargs)

                # Serialize and store in cache
                serialized = _serialize_for_cache(result)
                client.setex(cache_key, ttl, json.dumps(serialized))
                return result

            except Exception as e:
                # If cache operations fail, log and continue without cache
                logger.error(f"Cache error: {e}")
                return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            client = CacheClient.get_client()

            # If Redis not available, bypass cache
            if client is None:
                return func(*args, **kwargs)

            # Build cache key
            try:
                if key_builder:
                    key_params = key_builder(*args, **kwargs)
                else:
                    # Default: use all kwargs
                    key_params = kwargs

                cache_key = _make_cache_key(prefix, **key_params)

                # Try to get from cache
                cached = client.get(cache_key)
                if cached:
                    logger.debug(f"Cache hit: {cache_key}")
                    return json.loads(cached)

                # Cache miss - call function
                logger.debug(f"Cache miss: {cache_key}")
                result = func(*args, **kwargs)

                # Serialize and store in cache
                serialized = _serialize_for_cache(result)
                client.setex(cache_key, ttl, json.dumps(serialized))
                return result

            except Exception as e:
                # If cache operations fail, log and continue without cache
                logger.error(f"Cache error: {e}")
                return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def invalidate_cache(prefix: str, **kwargs):
    """
    Invalidate a specific cache entry.

    Args:
        prefix: Cache key prefix
        **kwargs: Key-value pairs that were used to create the cache key
    """
    client = CacheClient.get_client()
    if client is None:
        return

    try:
        cache_key = _make_cache_key(prefix, **kwargs)
        client.delete(cache_key)
        logger.debug(f"Cache invalidated: {cache_key}")
    except Exception as e:
        logger.error(f"Cache invalidation error: {e}")


def invalidate_cache_pattern(pattern: str):
    """
    Invalidate all cache entries matching a pattern.

    Args:
        pattern: Redis key pattern (e.g., 'courses:*', 'colleges:*')

    Warning: Use sparingly as SCAN can be slow on large datasets
    """
    client = CacheClient.get_client()
    if client is None:
        return

    try:
        count = 0
        for key in client.scan_iter(match=pattern):
            client.delete(key)
            count += 1
        logger.info(f"Invalidated {count} cache entries matching '{pattern}'")
    except Exception as e:
        logger.error(f"Cache pattern invalidation error: {e}")


# User profile caching utilities


def get_user_profile_cache_key(user_id: str) -> str:
    """
    Generate cache key for user profile.

    Args:
        user_id: User UUID as string

    Returns:
        Cache key string
    """
    return f"user_profile:{user_id}"


def cache_user_profile(user_id: str, profile_data: dict, ttl: int = 300):
    """
    Cache user profile data with specified TTL.

    Args:
        user_id: User UUID as string
        profile_data: Dictionary containing profile data
        ttl: Time to live in seconds (default: 300 = 5 minutes)
    """
    client = CacheClient.get_client()
    if client is None:
        return

    try:
        cache_key = get_user_profile_cache_key(user_id)
        serialized = _serialize_for_cache(profile_data)
        client.setex(cache_key, ttl, json.dumps(serialized))
        logger.debug(f"Cached user profile: {cache_key}")
    except Exception as e:
        logger.error(f"Failed to cache user profile: {e}")


def get_cached_user_profile(user_id: str) -> Optional[dict]:
    """
    Get cached user profile data.

    Args:
        user_id: User UUID as string

    Returns:
        Cached profile data dictionary or None if not found
    """
    client = CacheClient.get_client()
    if client is None:
        return None

    try:
        cache_key = get_user_profile_cache_key(user_id)
        cached = client.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for user profile: {cache_key}")
            return json.loads(cached)
        logger.debug(f"Cache miss for user profile: {cache_key}")
        return None
    except Exception as e:
        logger.error(f"Failed to get cached user profile: {e}")
        return None


def invalidate_user_profile_cache(user_id: str):
    """
    Invalidate cached user profile data.

    This should be called whenever:
    - Profile data is updated (profiles table)
    - Stripe customer data is created/updated (stripe_customers table)
    - Stripe subscription data is created/updated (stripe_subscriptions table)

    Args:
        user_id: User UUID as string
    """
    client = CacheClient.get_client()
    if client is None:
        return

    try:
        cache_key = get_user_profile_cache_key(user_id)
        client.delete(cache_key)
        logger.info(f"Invalidated user profile cache: {cache_key}")
    except Exception as e:
        logger.error(f"Failed to invalidate user profile cache: {e}")


# User subscription tier caching utilities


def get_user_tier_cache_key(user_id: str) -> str:
    """
    Generate cache key for user subscription tier.

    Args:
        user_id: User UUID as string

    Returns:
        Cache key string
    """
    return f"user_tier:{user_id}"


def cache_user_tier(user_id: str, tier: str, ttl: int = 300):
    """
    Cache user subscription tier with specified TTL.

    Args:
        user_id: User UUID as string
        tier: Subscription tier ('free', 'plus', or 'pro')
        ttl: Time to live in seconds (default: 300 = 5 minutes)
    """
    client = CacheClient.get_client()
    if client is None:
        return

    try:
        cache_key = get_user_tier_cache_key(user_id)
        # Store tier as simple string (no need for JSON)
        client.setex(cache_key, ttl, tier)
        logger.debug(f"Cached user tier: {cache_key} = {tier}")
    except Exception as e:
        logger.error(f"Failed to cache user tier: {e}")


def get_cached_user_tier(user_id: str) -> Optional[str]:
    """
    Get cached user subscription tier.

    Args:
        user_id: User UUID as string

    Returns:
        Cached tier string ('free', 'plus', 'pro') or None if not found
    """
    client = CacheClient.get_client()
    if client is None:
        return None

    try:
        cache_key = get_user_tier_cache_key(user_id)
        cached = client.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for user tier: {cache_key} = {cached}")
            return cached
        logger.debug(f"Cache miss for user tier: {cache_key}")
        return None
    except Exception as e:
        logger.error(f"Failed to get cached user tier: {e}")
        return None


def invalidate_user_tier_cache(user_id: str):
    """
    Invalidate cached user subscription tier.

    This should be called whenever:
    - Stripe customer data is created/updated (stripe_customers table)
    - Stripe subscription data is created/updated (stripe_subscriptions table)

    Args:
        user_id: User UUID as string
    """
    client = CacheClient.get_client()
    if client is None:
        return

    try:
        cache_key = get_user_tier_cache_key(user_id)
        client.delete(cache_key)
        logger.info(f"Invalidated user tier cache: {cache_key}")
    except Exception as e:
        logger.error(f"Failed to invalidate user tier cache: {e}")


def invalidate_user_caches(user_id: str):
    """
    Invalidate all user-related caches (profile and tier).

    This is a convenience function to invalidate both caches at once.
    Call this whenever user profile or subscription data changes.

    Args:
        user_id: User UUID as string
    """
    try:
        invalidate_user_profile_cache(user_id)
    except Exception as e:
        logger.error(f"Failed to invalidate profile cache for {user_id}: {e}")

    try:
        invalidate_user_tier_cache(user_id)
    except Exception as e:
        logger.error(f"Failed to invalidate tier cache for {user_id}: {e}")
