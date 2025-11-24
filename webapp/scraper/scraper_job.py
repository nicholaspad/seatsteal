"""
Scraper job orchestration - Manages scraping execution with locking and retry logic
"""

import time
import asyncio
from typing import Dict, Optional
from datetime import datetime
from loguru import logger
from sqlalchemy.orm import Session

from models.college import College
from scraper.scraper_lock import ScraperLock
from scraper.services.scraper_log import ScraperLogService
from scraper.services.scraper_service import ScraperService


class JobResult:
    """Result of a scraper job execution"""

    def __init__(
        self,
        success: bool,
        stats: Optional[Dict] = None,
        error: Optional[str] = None,
        duration_ms: int = 0,
    ):
        self.success = success
        self.stats = stats or {}
        self.error = error
        self.duration_ms = duration_ms


class JobConfig:
    """Configuration for a scraper job"""

    def __init__(
        self,
        subject: str = "ALL",
        limit: Optional[int] = 1000,
        lock_timeout_ms: int = 900000,  # 15 minutes
        retry_attempts: int = 3,
        retry_delay_ms: int = 5000,
    ):
        self.subject = subject
        self.limit = limit
        self.lock_timeout_ms = lock_timeout_ms
        self.retry_attempts = retry_attempts
        self.retry_delay_ms = retry_delay_ms


class ScraperJob:
    """Handles execution of a scraping job for a single college"""

    def __init__(
        self, college: College, db: Session, config: Optional[JobConfig] = None
    ):
        """
        Initialize scraper job.

        Args:
            college: College to scrape
            db: Synchronous database session
            config: Optional job configuration
        """
        self.college = college
        self.db = db
        self.config = config or JobConfig()
        self.lock = ScraperLock(college.id, db, self.config.lock_timeout_ms)

    async def execute(self) -> JobResult:
        """
        Execute the scraping job.

        Returns:
            JobResult with success status, stats, and duration
        """
        start_time = time.time()
        log_id: Optional[int] = None

        logger.info(f"🎯 Starting scraper job for {self.college.name}")

        # Get scraper_id and create log entry for this run
        scraper_id = self.lock.get_scraper_id()
        if not scraper_id:
            logger.error(f"❌ No scraper found for {self.college.name}")
            return JobResult(success=False, error="No scraper found for college")

        try:
            log_service = ScraperLogService(self.db)
            log_id = await log_service.start_log(scraper_id)
        except Exception as e:
            logger.warning(
                f"⚠️  Failed to create log entry for {self.college.name}: {e}"
            )

        # Try to acquire lock
        lock_result = self.lock.acquire()
        if not lock_result.success:
            logger.info(
                f"⏳ Cannot start scraper for {self.college.name}: {lock_result.reason}"
            )

            # Update log with timeout outcome
            if log_id:
                try:
                    log_service = ScraperLogService(self.db)
                    await log_service.complete_log(
                        log_id,
                        outcome="timeout",
                        error_message=lock_result.reason or "Failed to acquire lock",
                    )
                    self.db.commit()
                except Exception as e:
                    logger.warning(f"Failed to update log: {e}")

            duration_ms = int((time.time() - start_time) * 1000)
            return JobResult(
                success=False,
                error=lock_result.reason or "Failed to acquire lock",
                duration_ms=duration_ms,
            )

        logger.info(f"🔒 Acquired lock for {self.college.name}")

        try:
            result = await self._execute_with_retry()
            duration_ms = int((time.time() - start_time) * 1000)

            if result.success:
                self.lock.release("completed", duration_ms=duration_ms)
                logger.info(
                    f"✅ Scraper job for {self.college.name} completed successfully in {duration_ms}ms"
                )

                # Update log with success outcome
                if log_id:
                    try:
                        log_service = ScraperLogService(self.db)
                        await log_service.complete_log(
                            log_id,
                            outcome="success",
                            courses_created=result.stats.get("courses_saved", 0),
                            classes_created=result.stats.get("classes_saved", 0),
                        )
                        self.db.commit()
                    except Exception as e:
                        logger.warning(f"Failed to update log: {e}")
            else:
                self.lock.release(
                    "error", error_message=result.error, duration_ms=duration_ms
                )
                logger.error(
                    f"❌ Scraper job for {self.college.name} failed after {duration_ms}ms: {result.error}"
                )

                # Update log with error outcome
                if log_id:
                    try:
                        log_service = ScraperLogService(self.db)
                        await log_service.complete_log(
                            log_id, outcome="error", error_message=result.error
                        )
                        self.db.commit()
                    except Exception as e:
                        logger.warning(f"Failed to update log: {e}")

            result.duration_ms = duration_ms
            return result

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_message = str(e)

            self.lock.release(
                "error", error_message=error_message, duration_ms=duration_ms
            )
            logger.error(
                f"❌ Scraper job for {self.college.name} threw exception after {duration_ms}ms: {e}"
            )

            # Update log with error outcome
            if log_id:
                try:
                    log_service = ScraperLogService(self.db)
                    await log_service.complete_log(
                        log_id, outcome="error", error_message=error_message
                    )
                    self.db.commit()
                except Exception as ex:
                    logger.warning(f"Failed to update log: {ex}")

            return JobResult(
                success=False, error=error_message, duration_ms=duration_ms
            )

    async def _execute_with_retry(self) -> JobResult:
        """Execute with retry logic"""
        last_error: Optional[str] = None

        for attempt in range(1, self.config.retry_attempts + 1):
            try:
                logger.info(
                    f"🔄 Attempt {attempt}/{self.config.retry_attempts} for {self.college.name}"
                )

                service = ScraperService(self.db)
                stats = await service.scrape_college(
                    self.college.short_name, self.config.subject, self.config.limit
                )

                # Check if the scrape was actually successful
                if stats.get("success", False):
                    return JobResult(success=True, stats=stats)
                else:
                    # Scrape failed, treat as error and retry
                    last_error = stats.get("error", "Unknown error during scraping")
                    logger.error(
                        f"❌ Attempt {attempt}/{self.config.retry_attempts} failed for {self.college.name}: {last_error}"
                    )
                    
                    # Don't wait after the last attempt
                    if attempt < self.config.retry_attempts:
                        # Exponential backoff
                        delay_ms = self.config.retry_delay_ms * (2 ** (attempt - 1))
                        logger.info(f"⏱️  Waiting {delay_ms}ms before retry...")
                        await asyncio.sleep(delay_ms / 1000)

            except Exception as e:
                last_error = str(e)
                logger.error(
                    f"❌ Attempt {attempt}/{self.config.retry_attempts} failed for {self.college.name}: {last_error}"
                )

                # Don't wait after the last attempt
                if attempt < self.config.retry_attempts:
                    # Exponential backoff
                    delay_ms = self.config.retry_delay_ms * (2 ** (attempt - 1))
                    logger.info(f"⏱️  Waiting {delay_ms}ms before retry...")
                    await asyncio.sleep(delay_ms / 1000)

        return JobResult(
            success=False, error=last_error or "Unknown error during scraping"
        )

    def can_run(self) -> bool:
        """Check if the job can run (lock is available)"""
        lock_result = self.lock.acquire()
        if lock_result.success:
            self.lock.release("idle")
            return True
        return False

    def get_college(self) -> College:
        """Get college information"""
        return self.college

    def get_config(self) -> JobConfig:
        """Get job configuration"""
        return self.config

    def cleanup(self) -> None:
        """Clean up resources"""
        self.lock.cleanup()

    def get_lock(self) -> ScraperLock:
        """Get the lock instance (for testing/debugging)"""
        return self.lock
