"""
Database-based locking for scraper jobs to prevent concurrent execution
"""

from typing import Dict, Optional
from datetime import datetime
from loguru import logger
from sqlalchemy import select, and_, update
from sqlalchemy.orm import Session

from models.scraper import Scraper
from models.college import College


class LockResult:
    """Result of a lock acquisition attempt"""

    def __init__(
        self,
        success: bool,
        scraper: Optional[Scraper] = None,
        reason: Optional[str] = None,
    ):
        self.success = success
        self.scraper = scraper
        self.reason = reason


class ScraperLock:
    """
    Database-based distributed lock for preventing duplicate scraping jobs.

    Uses the Scraper model's status field to implement locking via atomic updates.
    """

    def __init__(self, college_id: int, db: Session, lock_timeout_ms: int = 900000):
        """
        Initialize scraper lock.

        Args:
            college_id: College ID to lock for
            db: Database session
            lock_timeout_ms: Lock timeout in milliseconds (default: 15 minutes)
        """
        self.college_id = college_id
        self.db = db
        self.lock_timeout_ms = lock_timeout_ms
        self.acquired = False
        self.college_short_name: Optional[str] = None

    def _get_college_short_name(self) -> str:
        """Get college shortName for logging (cached after first lookup)"""
        if self.college_short_name is None:
            try:
                result = self.db.execute(
                    select(College.short_name).where(College.id == self.college_id)
                ).first()

                self.college_short_name = (
                    result[0] if result else f"college-{self.college_id}"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to lookup college shortName for ID {self.college_id}: {e}"
                )
                self.college_short_name = f"college-{self.college_id}"

        return self.college_short_name

    def acquire(self) -> LockResult:
        """
        Attempt to acquire a lock for the scraper.

        Returns:
            LockResult with success status and optional scraper/reason
        """
        college_short_name = self._get_college_short_name()

        try:
            # First, ensure scraper record exists
            self._ensure_scraper_exists()

            # Try to acquire lock by atomically updating status to 'running'
            # This will only succeed if the current status is NOT 'running'
            result = self.db.execute(
                update(Scraper)
                .where(
                    and_(
                        Scraper.college_id == self.college_id,
                        Scraper.status != "running",
                    )
                )
                .values(
                    status="running",
                    last_run_at=datetime.now(),
                    next_run_at=None,
                    updated_at=datetime.now(),
                )
                .returning(Scraper)
            ).first()

            if result:
                # Successfully transitioned to running
                self.acquired = True
                # Commit immediately to release the row lock
                self.db.commit()
                logger.info(f"🔒 Acquired scraper lock for {college_short_name}")
                return LockResult(success=True, scraper=result)

            # If we couldn't acquire the lock, check why
            current_scraper = self.db.execute(
                select(Scraper).where(Scraper.college_id == self.college_id)
            ).scalar_one_or_none()

            if current_scraper:
                # Check if the scraper is stuck (running for too long)
                if current_scraper.status == "running" and current_scraper.last_run_at:
                    time_since_last_run = (
                        datetime.now() - current_scraper.last_run_at
                    ).total_seconds() * 1000

                    if time_since_last_run > self.lock_timeout_ms:
                        logger.warning(
                            f"🔓 Scraper appears stuck for {college_short_name}, forcing release"
                        )
                        return self._force_release()

                logger.info(
                    f"⏳ Cannot acquire lock for {college_short_name}: scraper is currently {current_scraper.status}"
                    + (
                        f" (last run: {current_scraper.last_run_at.isoformat()})"
                        if current_scraper.last_run_at
                        else ""
                    )
                )

                return LockResult(
                    success=False,
                    scraper=current_scraper,
                    reason=f"Scraper is currently {current_scraper.status}",
                )

            logger.warning(
                f"Failed to acquire lock for {college_short_name}: no scraper record found"
            )
            return LockResult(success=False, reason="Failed to acquire lock")

        except Exception as e:
            logger.error(f"Error acquiring lock for {college_short_name}: {e}")
            # Rollback the transaction to prevent "transaction aborted" errors
            self.db.rollback()
            return LockResult(success=False, reason=f"Database error: {e}")

    def release(
        self,
        status: str = "completed",
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> bool:
        """
        Release the lock and update status.

        Args:
            status: Final status ('idle', 'completed', 'error')
            error_message: Optional error message if status is 'error'
            duration_ms: Duration of the scraper run in milliseconds

        Returns:
            True if lock was released successfully
        """
        college_short_name = self._get_college_short_name()

        if not self.acquired:
            logger.warning(
                f"Attempted to release lock but no lock was acquired for {college_short_name}"
            )
            return False

        try:
            update_data = {
                "status": status,
                "updated_at": datetime.now(),
            }

            if status == "completed":
                update_data["last_success_at"] = datetime.now()
                # Increment success_count
                scraper = self.db.execute(
                    select(Scraper).where(Scraper.college_id == self.college_id)
                ).scalar_one()
                update_data["success_count"] = scraper.success_count + 1

            elif status == "error":
                update_data["last_error_message"] = error_message
                # Increment error_count
                scraper = self.db.execute(
                    select(Scraper).where(Scraper.college_id == self.college_id)
                ).scalar_one()
                update_data["error_count"] = scraper.error_count + 1

            if duration_ms is not None:
                update_data["last_run_duration_ms"] = duration_ms

            # Always increment run_count
            scraper = self.db.execute(
                select(Scraper).where(Scraper.college_id == self.college_id)
            ).scalar_one()
            update_data["run_count"] = scraper.run_count + 1

            self.db.execute(
                update(Scraper)
                .where(Scraper.college_id == self.college_id)
                .values(**update_data)
            )
            self.db.commit()

            self.acquired = False
            logger.info(
                f"🔓 Released scraper lock for {college_short_name} with status: {status}"
            )
            return True

        except Exception as e:
            logger.error(f"Error releasing lock for {college_short_name}: {e}")
            self.db.rollback()
            return False

    def _force_release(self) -> LockResult:
        """Force release a stuck lock"""
        college_short_name = self._get_college_short_name()

        try:
            scraper = self.db.execute(
                select(Scraper).where(Scraper.college_id == self.college_id)
            ).scalar_one()

            self.db.execute(
                update(Scraper)
                .where(Scraper.college_id == self.college_id)
                .values(
                    status="idle",
                    last_error_message="Force released due to timeout",
                    error_count=scraper.error_count + 1,
                    updated_at=datetime.now(),
                )
            )
            self.db.commit()

            logger.info(f"🔓 Force released stuck scraper lock for {college_short_name}")

            # Now try to acquire the lock again
            return self.acquire()

        except Exception as e:
            logger.error(f"Error force releasing lock for {college_short_name}: {e}")
            self.db.rollback()
            return LockResult(success=False, reason=f"Database error: {e}")

    def _ensure_scraper_exists(self) -> None:
        """Ensure scraper record exists for this college"""
        college_short_name = self._get_college_short_name()

        try:
            existing = self.db.execute(
                select(Scraper.id).where(Scraper.college_id == self.college_id)
            ).first()

            if not existing:
                scraper = Scraper(college_id=self.college_id, status="idle")
                self.db.add(scraper)
                self.db.commit()
                logger.info(f"📝 Created scraper record for {college_short_name}")

        except Exception as e:
            logger.error(f"Error ensuring scraper exists for {college_short_name}: {e}")
            self.db.rollback()
            raise

    def is_acquired(self) -> bool:
        """Check if we have the lock"""
        return self.acquired

    def get_college_id(self) -> int:
        """Get college ID"""
        return self.college_id

    def get_scraper_id(self) -> Optional[int]:
        """
        Get scraper ID for this college.

        Returns:
            Scraper ID or None if not found
        """
        try:
            result = self.db.execute(
                select(Scraper.id).where(Scraper.college_id == self.college_id)
            ).first()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting scraper ID for college {self.college_id}: {e}")
            return None

    def cleanup(self) -> None:
        """Clean up on process exit"""
        if self.acquired:
            self.release(
                status="error", error_message="Process terminated unexpectedly"
            )
