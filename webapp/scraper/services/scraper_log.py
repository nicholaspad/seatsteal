from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import Integer, and_, cast, func, select, update
from datetime import datetime, timezone
from loguru import logger

from models.scraper_log import ScraperLog
from models.scraper import Scraper


class ScraperLogService:
    """Service for managing scraper execution logs"""

    def __init__(self, db: Session):
        """
        Initialize scraper log service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    async def get_scraper_id_from_college(self, college_id: int) -> Optional[int]:
        """
        Get scraper ID for a given college ID.

        Args:
            college_id: College ID

        Returns:
            Scraper ID or None if not found
        """
        result = self.db.execute(
            select(Scraper.id).where(Scraper.college_id == college_id)
        )
        scraper_id = result.scalar_one_or_none()
        return scraper_id

    async def start_log(self, scraper_id: int) -> int:
        """
        Create a new scraper log entry for a scraping run.

        Args:
            scraper_id: ID of the scraper being run

        Returns:
            ID of the created log entry
        """
        log = ScraperLog(
            scraper_id=scraper_id,
            outcome="running",
            courses_created=0,
            classes_created=0,
            started_at=datetime.now(),
        )

        self.db.add(log)
        self.db.flush()

        logger.debug(f"Started scraper log {log.id} for scraper {scraper_id}")
        return log.id

    async def complete_log(
        self,
        log_id: int,
        outcome: str,
        courses_created: int = 0,
        classes_created: int = 0,
        enrollments_saved: int = 0,
        error_message: Optional[str] = None,
    ):
        """
        Complete a scraper log entry.

        Args:
            log_id: ID of the log entry
            outcome: Final outcome ('success', 'error', 'partial', 'timeout')
            courses_created: Number of courses created
            classes_created: Number of classes created
            enrollments_saved: Number of enrollments saved
            error_message: Optional error message if failed
        """
        result = self.db.execute(select(ScraperLog).where(ScraperLog.id == log_id))
        log = result.scalar_one_or_none()

        if not log:
            logger.error(f"Scraper log {log_id} not found")
            return

        log.outcome = outcome
        log.courses_created = courses_created
        log.classes_created = classes_created
        log.enrollments_saved = enrollments_saved
        log.completed_at = datetime.now()

        if log.started_at:
            duration = (log.completed_at - log.started_at).total_seconds()
            log.duration_ms = int(duration * 1000)

        if error_message:
            log.error_message = error_message

        logger.debug(
            f"Completed scraper log {log_id}: outcome={outcome}, "
            f"courses={courses_created}, classes={classes_created}, enrollments={enrollments_saved}"
        )

    async def get_recent_logs(
        self, college_id: Optional[int] = None, limit: int = 10
    ) -> list[ScraperLog]:
        """
        Get recent scraper logs.

        Args:
            college_id: Optional college ID to filter by
            limit: Maximum number of logs to return

        Returns:
            List of ScraperLog objects
        """
        query = select(ScraperLog).order_by(ScraperLog.started_at.desc()).limit(limit)

        if college_id:
            # Join with scrapers to filter by college_id
            query = query.join(Scraper, ScraperLog.scraper_id == Scraper.id).where(
                Scraper.college_id == college_id
            )

        result = self.db.execute(query)
        return list(result.scalars().all())

    async def get_log(self, log_id: int) -> Optional[ScraperLog]:
        """
        Get a specific scraper log.

        Args:
            log_id: ID of the log entry

        Returns:
            ScraperLog object or None if not found
        """
        result = self.db.execute(select(ScraperLog).where(ScraperLog.id == log_id))
        return result.scalar_one_or_none()

    async def mark_orphaned_running_logs(self, process_started_at: datetime) -> int:
        """
        Mark leftover `running` scraper_logs rows from a previous process as error.

        Touches only scraper_logs. Rows whose started_at is at or after
        process_started_at (this process) are left alone.
        """
        completed_at = datetime.now(timezone.utc)
        duration_ms = func.greatest(
            0,
            cast(
                func.extract("epoch", completed_at - ScraperLog.started_at) * 1000,
                Integer,
            ),
        )
        result = self.db.execute(
            update(ScraperLog)
            .where(
                and_(
                    ScraperLog.outcome == "running",
                    ScraperLog.started_at < process_started_at,
                )
            )
            .values(
                outcome="error",
                error_message="orphaned by restart",
                completed_at=completed_at,
                duration_ms=duration_ms,
            )
        )
        orphan_count = result.rowcount or 0
        if orphan_count:
            logger.info(
                f"Marked {orphan_count} orphaned scraper_logs row(s) as error "
                f"(started_at before {process_started_at.isoformat()})"
            )
        return orphan_count

    async def get_last_successful_scrape(self, college_id: int) -> Optional[ScraperLog]:
        """
        Get the last successful scrape for a college.

        Args:
            college_id: College ID

        Returns:
            ScraperLog object or None if no successful scrapes found
        """
        result = self.db.execute(
            select(ScraperLog)
            .join(Scraper, ScraperLog.scraper_id == Scraper.id)
            .where(Scraper.college_id == college_id, ScraperLog.outcome == "success")
            .order_by(ScraperLog.completed_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
