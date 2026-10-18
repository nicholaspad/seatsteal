"""
Scraper job orchestration - Manages scraping execution with locking and retry logic
"""

import time
import asyncio
from typing import Dict, Optional, Any
from loguru import logger
from sqlalchemy.orm import Session

from models.college import College
from scraper.scraper_lock import ScraperLock
from scraper.services.scraper_log import ScraperLogService
from scraper.services.scraper_service import ScraperService
from scraper.utils.errors import format_exception_message

# Wall-clock limit for one scraper_logs row (all retry attempts combined).
# cap = max(480m, 1.25 × longest successful run in the last 21 days).
DEFAULT_RUN_TIMEOUT_MINUTES = 480
DEFAULT_LOCK_TIMEOUT_MS = 900000  # 15 minutes

RUN_TIMEOUT_MINUTES_BY_SHORT_NAME = {
    "uiuc": 900,  # 21-day max 707m
    "purdue": 900,  # 21-day max 685m
    "ncsu": 785,  # 21-day max 628m
    "cornell": 709,  # 21-day max 567m
    "usc": 540,  # 21-day max 432m
    "asu": 539,  # 21-day max 431m
    "osu": 491,  # 21-day max 393m
}


def run_timeout_minutes_for_college(short_name: Optional[str]) -> int:
    """Return the per-college wall-clock limit in minutes."""
    if not short_name:
        return DEFAULT_RUN_TIMEOUT_MINUTES
    return RUN_TIMEOUT_MINUTES_BY_SHORT_NAME.get(
        short_name.lower(), DEFAULT_RUN_TIMEOUT_MINUTES
    )


def job_config_for_college(
    college: College,
    subject: str = "ALL",
    limit: Optional[int] = None,
    skip_lock: bool = False,
) -> "JobConfig":
    """Build JobConfig with the college's run timeout and a matching lock timeout."""
    timeout_minutes = run_timeout_minutes_for_college(college.short_name)
    return JobConfig(
        subject=subject,
        limit=limit,
        skip_lock=skip_lock,
        run_timeout_minutes=timeout_minutes,
        lock_timeout_ms=max(DEFAULT_LOCK_TIMEOUT_MS, timeout_minutes * 60 * 1000),
    )


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
        lock_timeout_ms: int = DEFAULT_LOCK_TIMEOUT_MS,
        retry_attempts: int = 3,
        retry_delay_ms: int = 5000,
        skip_lock: bool = False,
        run_timeout_minutes: int = DEFAULT_RUN_TIMEOUT_MINUTES,
        run_timeout_seconds: Optional[float] = None,
    ):
        self.subject = subject
        self.limit = limit
        self.lock_timeout_ms = lock_timeout_ms
        self.retry_attempts = retry_attempts
        self.retry_delay_ms = retry_delay_ms
        self.skip_lock = skip_lock
        self.run_timeout_minutes = run_timeout_minutes
        # Seconds override is for tests; production uses minutes.
        self.run_timeout_seconds = (
            run_timeout_seconds
            if run_timeout_seconds is not None
            else float(run_timeout_minutes * 60)
        )


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
        self.config = config or job_config_for_college(college)
        self.lock = ScraperLock(
            college.id, db, self.config.lock_timeout_ms, self.config.skip_lock
        )

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
            # Scraper DB calls are synchronous SQLAlchemy inside this async
            # coroutine. A stuck query blocks the event loop, so wait_for
            # cannot cancel it until the driver returns. The scraper-only
            # 120s statement_timeout and TCP keepalives (scraper/db.py) are
            # what make a hung query raise; wait_for then records the error
            # and releases the lock. Wrapping every execute in to_thread
            # is not trivial (scrape_college mixes async HTTP with sync
            # batched upserts) so we keep those DB timeouts instead.
            result = await asyncio.wait_for(
                self._execute_with_retry(),
                timeout=self.config.run_timeout_seconds,
            )
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
                            enrollments_saved=result.stats.get("enrollments_saved", 0),
                        )
                        self.db.commit()
                    except Exception as e:
                        logger.warning(f"Failed to update log: {e}")
            else:
                # Determine outcome: partial (0 courses) vs error (exception/failure)
                outcome = result.stats.get("outcome", "error")

                # Only mark scraper as "error" for hard failures, not partials
                scraper_status = "error" if outcome == "error" else "completed"
                self.lock.release(
                    scraper_status, error_message=result.error, duration_ms=duration_ms
                )

                if outcome == "partial":
                    logger.warning(
                        f"⚠️  Scraper job for {self.college.name} completed with issues after {duration_ms}ms: {result.error}"
                    )
                else:
                    logger.error(
                        f"❌ Scraper job for {self.college.name} failed after {duration_ms}ms: {result.error}"
                    )

                # Update log with appropriate outcome (partial or error)
                if log_id:
                    try:
                        log_service = ScraperLogService(self.db)
                        await log_service.complete_log(
                            log_id,
                            outcome=outcome,
                            error_message=result.error,
                            courses_created=result.stats.get("courses_saved", 0),
                            classes_created=result.stats.get("classes_saved", 0),
                            enrollments_saved=result.stats.get("enrollments_saved", 0),
                        )
                        self.db.commit()
                    except Exception as e:
                        logger.warning(f"Failed to update log: {e}")

            result.duration_ms = duration_ms
            return result

        except TimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            error_message = f"timed out after {self.config.run_timeout_minutes}m"

            try:
                self.db.rollback()
            except Exception as rollback_error:
                logger.warning(
                    f"Failed to rollback after run timeout for {self.college.name}: "
                    f"{rollback_error}"
                )

            self.lock.release(
                "error", error_message=error_message, duration_ms=duration_ms
            )
            logger.error(
                f"❌ Scraper job for {self.college.name} {error_message} "
                f"(wall-clock limit reached after {duration_ms}ms)"
            )

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

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_message = format_exception_message(e)

            self.lock.release(
                "error", error_message=error_message, duration_ms=duration_ms
            )
            logger.error(
                f"❌ Scraper job for {self.college.name} threw exception after {duration_ms}ms: {error_message}"
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
        last_stats: Optional[Dict[str, Any]] = None

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
                    # Scrape failed - extract error with fallback to generic message.
                    # stats["error"] is formatted by ScraperService via
                    # format_exception_message so empty str(e) is not blank.
                    error_from_stats = (stats.get("error") or "").strip()
                    last_error = (
                        error_from_stats
                        if error_from_stats
                        else "Unknown error during scraping"
                    )
                    last_stats = stats

                    # Check outcome to determine if retry is appropriate
                    outcome = stats.get("outcome", "error")

                    # Non-retryable outcomes: partial (0 courses/enrollments) and budget_exceeded
                    if outcome in ["partial", "budget_exceeded"]:
                        outcome_label = (
                            "Partial failure"
                            if outcome == "partial"
                            else "Budget exceeded (non-retryable)"
                        )
                        logger.warning(
                            f"⚠️  {outcome_label} for {self.college.name} (attempt {attempt}): {last_error}"
                        )
                        return JobResult(success=False, error=last_error, stats=stats)

                    # Hard error - log and potentially retry
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
                last_error = format_exception_message(e)
                logger.error(
                    f"❌ Attempt {attempt}/{self.config.retry_attempts} failed for {self.college.name}: {last_error}"
                )

                # Don't wait after the last attempt
                if attempt < self.config.retry_attempts:
                    # Exponential backoff
                    delay_ms = self.config.retry_delay_ms * (2 ** (attempt - 1))
                    logger.info(f"⏱️  Waiting {delay_ms}ms before retry...")
                    await asyncio.sleep(delay_ms / 1000)

        # All retries exhausted - return failure with stats if available
        return JobResult(
            success=False,
            error=last_error or "Unknown error during scraping",
            stats=last_stats or {},
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
