import redis
from typing import Optional
from contextlib import contextmanager
from loguru import logger
from config import settings


class RedisLock:
    """
    Redis-based distributed lock for preventing duplicate scraping jobs.

    This ensures that only one scraper can run for a specific college/department
    combination at a time across multiple workers.
    """

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize Redis lock manager.

        Args:
            redis_url: Redis connection URL (uses settings.REDIS_URL if not provided)
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
        self.lock_prefix = "seatsteal:scraper:lock:"
        self.default_timeout = 300  # 5 minutes default lock timeout

    def _get_lock_key(self, college: str, department: Optional[str] = None) -> str:
        """
        Generate Redis key for a lock.

        Args:
            college: College short name
            department: Optional department code

        Returns:
            Redis key string
        """
        if department:
            return f"{self.lock_prefix}{college}:{department}"
        return f"{self.lock_prefix}{college}"

    def acquire(
        self,
        college: str,
        department: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> bool:
        """
        Acquire a lock for scraping a college/department.

        Args:
            college: College short name
            department: Optional department code
            timeout: Lock timeout in seconds (default: 300)

        Returns:
            True if lock acquired, False if already locked
        """
        key = self._get_lock_key(college, department)
        timeout = timeout or self.default_timeout

        # Use SET with NX (only set if not exists) and EX (expiry time)
        acquired = self.redis_client.set(key, "locked", nx=True, ex=timeout)

        if acquired:
            logger.debug(f"Acquired lock: {key}")
        else:
            logger.debug(f"Lock already held: {key}")

        return bool(acquired)

    def release(self, college: str, department: Optional[str] = None) -> bool:
        """
        Release a lock for scraping a college/department.

        Args:
            college: College short name
            department: Optional department code

        Returns:
            True if lock was released, False if lock didn't exist
        """
        key = self._get_lock_key(college, department)
        deleted = self.redis_client.delete(key)

        if deleted:
            logger.debug(f"Released lock: {key}")
        else:
            logger.debug(f"Lock not found: {key}")

        return bool(deleted)

    def is_locked(self, college: str, department: Optional[str] = None) -> bool:
        """
        Check if a lock exists for a college/department.

        Args:
            college: College short name
            department: Optional department code

        Returns:
            True if locked, False otherwise
        """
        key = self._get_lock_key(college, department)
        return bool(self.redis_client.exists(key))

    def extend(
        self, college: str, department: Optional[str] = None, additional_time: int = 300
    ) -> bool:
        """
        Extend the expiry time of an existing lock.

        Args:
            college: College short name
            department: Optional department code
            additional_time: Additional time in seconds to extend

        Returns:
            True if extended, False if lock doesn't exist
        """
        key = self._get_lock_key(college, department)
        current_ttl = self.redis_client.ttl(key)

        if current_ttl > 0:
            new_ttl = current_ttl + additional_time
            self.redis_client.expire(key, new_ttl)
            logger.debug(f"Extended lock {key} to {new_ttl}s")
            return True
        else:
            logger.debug(f"Cannot extend lock {key}: lock doesn't exist or has no TTL")
            return False

    @contextmanager
    def lock(
        self,
        college: str,
        department: Optional[str] = None,
        timeout: Optional[int] = None,
        blocking: bool = False,
        blocking_timeout: int = 60,
    ):
        """
        Context manager for acquiring and automatically releasing a lock.

        Usage:
            lock_manager = RedisLock()
            with lock_manager.lock('princeton', 'CS'):
                # Perform scraping
                pass

        Args:
            college: College short name
            department: Optional department code
            timeout: Lock timeout in seconds
            blocking: If True, wait for lock to become available
            blocking_timeout: Maximum time to wait for lock (if blocking)

        Raises:
            RuntimeError: If lock cannot be acquired and blocking=False
        """
        import time

        acquired = False
        wait_time = 0

        # Try to acquire lock
        while not acquired:
            acquired = self.acquire(college, department, timeout)

            if acquired:
                break

            if not blocking:
                raise RuntimeError(
                    f"Could not acquire lock for {college}"
                    + (f" {department}" if department else "")
                )

            if wait_time >= blocking_timeout:
                raise RuntimeError(
                    f"Timeout waiting for lock: {college}"
                    + (f" {department}" if department else "")
                )

            # Wait a bit and retry
            time.sleep(1)
            wait_time += 1

        try:
            yield
        finally:
            # Always release lock
            if acquired:
                self.release(college, department)

    def clear_all_locks(self):
        """
        Clear all scraper locks (use with caution, mainly for testing/debugging).
        """
        pattern = f"{self.lock_prefix}*"
        keys = list(self.redis_client.scan_iter(match=pattern))

        if keys:
            deleted = self.redis_client.delete(*keys)
            logger.warning(f"Cleared {deleted} scraper locks")
            return deleted
        else:
            logger.debug("No scraper locks to clear")
            return 0
