from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from loguru import logger

from models.scraper_log import ScraperLog


class ScraperLogService:
    """Service for managing scraper execution logs"""

    def __init__(self, db: AsyncSession):
        """
        Initialize scraper log service.

        Args:
            db: SQLAlchemy async database session
        """
        self.db = db

    async def start_log(self, college_id: int) -> int:
        """
        Create a new scraper log entry for a scraping run.

        Args:
            college_id: ID of the college being scraped

        Returns:
            ID of the created log entry
        """
        log = ScraperLog(
            college_id=college_id,
            status="running",
            courses_scraped=0,
            classes_scraped=0,
            started_at=datetime.now(),
        )

        self.db.add(log)
        await self.db.flush()

        logger.debug(f"Started scraper log {log.id} for college {college_id}")
        return log.id

    async def complete_log(
        self,
        log_id: int,
        status: str,
        courses_scraped: int = 0,
        classes_scraped: int = 0,
        error_message: Optional[str] = None,
    ):
        """
        Complete a scraper log entry.

        Args:
            log_id: ID of the log entry
            status: Final status ('success', 'failed', etc.)
            courses_scraped: Number of courses scraped
            classes_scraped: Number of classes scraped
            error_message: Optional error message if failed
        """
        result = await self.db.execute(
            select(ScraperLog).where(ScraperLog.id == log_id)
        )
        log = result.scalar_one_or_none()

        if not log:
            logger.error(f"Scraper log {log_id} not found")
            return

        log.status = status
        log.courses_scraped = courses_scraped
        log.classes_scraped = classes_scraped
        log.completed_at = datetime.now()

        if log.started_at:
            duration = (log.completed_at - log.started_at).total_seconds()
            log.duration_seconds = int(duration)

        if error_message:
            log.error_message = error_message

        await self.db.commit()

        logger.debug(
            f"Completed scraper log {log_id}: status={status}, "
            f"courses={courses_scraped}, classes={classes_scraped}"
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
            query = query.where(ScraperLog.college_id == college_id)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_log(self, log_id: int) -> Optional[ScraperLog]:
        """
        Get a specific scraper log.

        Args:
            log_id: ID of the log entry

        Returns:
            ScraperLog object or None if not found
        """
        result = await self.db.execute(
            select(ScraperLog).where(ScraperLog.id == log_id)
        )
        return result.scalar_one_or_none()

    async def get_last_successful_scrape(self, college_id: int) -> Optional[ScraperLog]:
        """
        Get the last successful scrape for a college.

        Args:
            college_id: College ID

        Returns:
            ScraperLog object or None if no successful scrapes found
        """
        result = await self.db.execute(
            select(ScraperLog)
            .where(ScraperLog.college_id == college_id, ScraperLog.status == "success")
            .order_by(ScraperLog.completed_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
