#!/usr/bin/env python3
"""
Scraper daemon/CLI - Manages course scraping jobs

Usage:
    python run_scraper.py run --college princeton
    python run_scraper.py run-all
    python run_scraper.py --loop  # Run independent loops per college (configurable interval)
"""

import argparse
import asyncio
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
from loguru import logger
from sqlalchemy import select, update

# Add webapp directory to Python path
webapp_dir = Path(__file__).parent.parent
sys.path.insert(0, str(webapp_dir))

from db.session import SessionLocal
from db.connection import engine
from models.college import College
from models.scraper import Scraper
from scraper.scraper_job import ScraperJob, JobConfig


class ScraperCLI:
    """CLI for managing scraper jobs"""

    def __init__(self):
        self.loop_interval_seconds = 300  # 5 minutes (used by run_all_jobs)
        # Read scraper interval from environment variable (in minutes), default to 30 minutes
        interval_minutes = int(os.getenv("SCRAPER_INTERVAL_MINUTES", "30"))
        self.college_loop_interval_seconds = interval_minutes * 60

    async def _run_single_job(
        self,
        college: College,
        subject: str = "ALL",
        limit: Optional[int] = None,
    ) -> bool:
        """
        Run scraper job for a single college with its own database session.

        Args:
            college: College object to scrape
            subject: Subject filter (default: 'ALL')
            limit: Optional limit on courses

        Returns:
            True if successful, False otherwise
        """
        # Each job gets its own database session for thread safety
        with SessionLocal() as db:
            try:
                config = JobConfig(subject=subject, limit=limit)
                job = ScraperJob(college, db, config)

                result = await job.execute()
                job.cleanup()

                return result.success

            except Exception as e:
                logger.error(f"❌ Failed to scrape {college.short_name}: {e}")
                return False

    async def _run_college_loop(
        self,
        college: College,
        subject: str = "ALL",
        limit: Optional[int] = None,
    ) -> None:
        """
        Run a single college's scraper in an independent loop.

        After each scrape completes, waits for the configured interval
        (set via SCRAPER_INTERVAL_MINUTES env var) before starting the next run.

        Args:
            college: College object to scrape
            subject: Subject filter (default: 'ALL')
            limit: Optional limit on courses
        """
        while True:
            try:
                await self._run_single_job(college, subject=subject, limit=limit)
            except Exception as e:
                logger.error(f"❌ Error in {college.short_name} loop: {e}")

            # Wait before next run for THIS college
            interval_mins = self.college_loop_interval_seconds // 60
            logger.info(
                f"⏰ {college.short_name}: waiting {interval_mins} minutes until next run..."
            )
            await asyncio.sleep(self.college_loop_interval_seconds)

    async def run_job(
        self,
        college_short_name: str,
        subject: str = "ALL",
        limit: Optional[int] = None,
    ) -> bool:
        """
        Run scraper job for a single college.

        Args:
            college_short_name: College identifier (e.g., 'princeton')
            subject: Subject filter (default: 'ALL')
            limit: Optional limit on courses

        Returns:
            True if successful, False otherwise
        """
        with SessionLocal() as db:
            # Get college
            college = db.execute(
                select(College).where(College.short_name == college_short_name)
            ).scalar_one_or_none()

            if not college:
                logger.error(f"❌ College not found: {college_short_name}")
                return False

            if not college.is_active:
                logger.error(f"❌ College is not active: {college_short_name}")
                return False

            # Create job with skip_lock=True for CLI runs
            config = JobConfig(subject=subject, limit=limit, skip_lock=True)
            job = ScraperJob(college, db, config)

            # Execute job
            result = await job.execute()

            if result.success:
                logger.info(f"✅ Job completed successfully for {college_short_name}:")
                if result.stats:
                    logger.info(f"   Courses: {result.stats.get('courses_saved', 0)}")
                    logger.info(f"   Classes: {result.stats.get('classes_saved', 0)}")
                    logger.info(
                        f"   Enrollments: {result.stats.get('enrollments_saved', 0)}"
                    )
                logger.info(f"   Duration: {result.duration_ms}ms")

                job.cleanup()
                return True
            else:
                logger.error(f"❌ Job failed for {college_short_name}: {result.error}")
                job.cleanup()
                return False

    async def run_all_jobs(
        self, subject: str = "ALL", limit: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Run scraper jobs for all active colleges concurrently.

        Each scraper gets its own database session to prevent blocking.
        Connection pool is sized to handle concurrent scrapers (see db/connection.py).

        Args:
            subject: Subject filter (default: 'ALL')
            limit: Optional limit on courses

        Returns:
            Dict with success/failure counts
        """
        logger.info("🎯 Running all scraper jobs concurrently...")

        # Get all active colleges (using separate session)
        with SessionLocal() as db:
            colleges = (
                db.execute(select(College).where(College.is_active == True))
                .scalars()
                .all()
            )

        if not colleges:
            logger.warning("⚠️  No active colleges found")
            return {"total": 0, "successful": 0, "failed": 0}

        logger.info(f"Found {len(colleges)} active colleges to scrape concurrently")

        # Create tasks for all colleges
        tasks = [
            self._run_single_job(college, subject=subject, limit=limit)
            for college in colleges
        ]

        # Run all jobs concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes and failures
        successful = sum(1 for r in results if r is True)
        failed = len(results) - successful

        logger.info(f"✅ All jobs completed: {successful} successful, {failed} failed")

        return {"total": len(colleges), "successful": successful, "failed": failed}

    async def reset_all_scrapers_to_idle(self) -> None:
        """
        Reset all scraper statuses to idle.
        This is useful on startup to clear any stuck or stale states.

        Forces release of ALL database row locks by disposing of the connection pool
        and reinitializing it, ensuring a clean slate.
        """
        try:
            # Force release ALL database row locks by disposing of all connections
            # This closes all connections in the pool, which releases any held locks
            logger.info("🔓 Forcing release of all database row locks...")
            engine.dispose()
            logger.info("✅ All database connections disposed and locks released")

            # Now proceed with resetting scrapers using a fresh connection
            with SessionLocal() as db:
                # Use bulk update to avoid row-level locks
                result = db.execute(
                    update(Scraper)
                    .where(Scraper.status != "idle")
                    .values(status="idle", updated_at=datetime.now())
                )
                db.commit()

                reset_count = result.rowcount
                if reset_count > 0:
                    logger.info(f"🔄 Reset {reset_count} scraper(s) to idle status")
                else:
                    logger.info("✅ All scrapers already in idle status")

        except Exception as e:
            logger.error(f"❌ Error resetting scrapers: {e}")
            # Don't fail the startup, just log the error
            logger.warning("⚠️ Continuing with startup despite reset error")

    async def show_status(self) -> None:
        """Show status of all scrapers"""
        with SessionLocal() as db:
            scrapers = db.execute(
                select(Scraper, College)
                .join(College, Scraper.college_id == College.id)
                .order_by(College.name)
            ).all()

            if not scrapers:
                logger.info("📊 No scrapers found")
                return

            logger.info("📊 Scraper Status:")
            for scraper, college in scrapers:
                status_emoji = {
                    "idle": "⚪",
                    "running": "🟢",
                    "completed": "✅",
                    "error": "❌",
                }.get(scraper.status, "❓")

                logger.info(f"\n  {status_emoji} {college.name} ({college.short_name})")
                logger.info(f"     Status: {scraper.status}")
                logger.info(f"     Run count: {scraper.run_count}")
                logger.info(f"     Success count: {scraper.success_count}")
                logger.info(f"     Error count: {scraper.error_count}")

                if scraper.last_run_at:
                    logger.info(f"     Last run: {scraper.last_run_at.isoformat()}")

                if scraper.last_success_at:
                    logger.info(
                        f"     Last success: {scraper.last_success_at.isoformat()}"
                    )

                if scraper.last_run_duration_ms:
                    logger.info(f"     Last duration: {scraper.last_run_duration_ms}ms")

                if scraper.last_error_message:
                    logger.info(f"     Last error: {scraper.last_error_message}")

    async def loop(self, subject: str = "ALL", limit: Optional[int] = None) -> None:
        """
        Run scraper jobs in independent loops per college.

        Each college runs on its own schedule - after completing a scrape,
        it waits for the configured interval (SCRAPER_INTERVAL_MINUTES env var)
        before starting its next run. This ensures that fast-running colleges
        aren't blocked by slow-running ones.

        Args:
            subject: Subject filter (default: 'ALL')
            limit: Optional limit on courses
        """
        interval_mins = self.college_loop_interval_seconds // 60
        logger.info(
            f"🔁 Running scraper in loop mode (independent college loops, "
            f"{interval_mins} minute interval per college)"
        )

        # Reset all scrapers to idle on first bootup
        logger.info("🔄 Resetting all scraper statuses to idle on bootup...")
        await self.reset_all_scrapers_to_idle()

        # Get all active colleges
        with SessionLocal() as db:
            colleges = (
                db.execute(select(College).where(College.is_active == True))
                .scalars()
                .all()
            )

        if not colleges:
            logger.warning("⚠️  No active colleges found")
            return

        logger.info(f"🚀 Starting independent loops for {len(colleges)} colleges")

        # Create independent loop task for each college
        tasks = [
            self._run_college_loop(college, subject=subject, limit=limit)
            for college in colleges
        ]

        try:
            # Run all college loops concurrently (each runs independently forever)
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("🛑 Stopping all college loops...")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Course scraper daemon/CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_scraper.py run --college princeton
  python run_scraper.py run --college brown --subject CS --limit 50
  python run_scraper.py run-all
  python run_scraper.py status
  python run_scraper.py --loop
        """,
    )

    parser.add_argument(
        "command",
        nargs="?",
        default="run-all",
        choices=["run", "run-all", "status"],
        help="Command to execute (default: run-all)",
    )

    parser.add_argument(
        "--college", type=str, help="College short name (required for 'run' command)"
    )

    parser.add_argument(
        "--subject", type=str, default="ALL", help="Subject filter (default: ALL)"
    )

    parser.add_argument("--limit", type=int, help="Limit number of courses to scrape")

    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run independent loops per college (interval set by SCRAPER_INTERVAL_MINUTES env var, default: 30 min)",
    )

    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Configure logging
    logger.remove()
    log_level = "DEBUG" if args.debug else "INFO"
    logger.add(sys.stderr, level=log_level)

    cli = ScraperCLI()

    try:
        if args.loop:
            await cli.loop(subject=args.subject, limit=args.limit)
        elif args.command == "run":
            if not args.college:
                logger.error("❌ --college parameter required for 'run' command")
                sys.exit(1)

            success = await cli.run_job(
                args.college, subject=args.subject, limit=args.limit
            )
            sys.exit(0 if success else 1)

        elif args.command == "run-all":
            result = await cli.run_all_jobs(subject=args.subject, limit=args.limit)
            sys.exit(0 if result["failed"] == 0 else 1)

        elif args.command == "status":
            await cli.show_status()

    except KeyboardInterrupt:
        logger.info("\n🛑 Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
