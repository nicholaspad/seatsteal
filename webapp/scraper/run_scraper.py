#!/usr/bin/env python3
"""
Scraper daemon/CLI - Manages course scraping jobs

Usage:
    python run_scraper.py run --college princeton
    python run_scraper.py run-all
    python run_scraper.py --loop  # Run every 10 minutes
"""

import argparse
import asyncio
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
        self.loop_interval_seconds = 180  # 3 minutes

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

    async def _college_loop(self, college: College) -> None:
        """
        Run scraper for a single college on independent 3-minute schedule.

        This task runs indefinitely, executing the scraper and waiting 3 minutes
        between runs. Errors are caught and logged but don't terminate the loop.

        Args:
            college: College to scrape on a loop
        """
        logger.info(f"🔄 Starting independent scraper loop for {college.name}")

        while True:
            try:
                logger.info(f"🎯 Running scraper for {college.name}")
                success = await self._run_single_job(college)

                if success:
                    logger.info(
                        f"✅ Completed scraper for {college.name}, waiting 3 minutes"
                    )
                else:
                    logger.warning(
                        f"⚠️  Scraper failed for {college.name}, waiting 3 minutes before retry"
                    )

                # Wait 3 minutes before next run
                await asyncio.sleep(180)

            except asyncio.CancelledError:
                # Handle graceful shutdown
                logger.info(f"🛑 Scraper loop cancelled for {college.name}")
                raise
            except Exception as e:
                # Catch all other exceptions to keep task alive
                logger.error(
                    f"❌ Unexpected error in scraper loop for {college.name}: {e}"
                )
                logger.info(f"⏰ Waiting 3 minutes before retry")
                await asyncio.sleep(180)

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
        Run scraper jobs in a loop every 10 minutes.

        Args:
            subject: Subject filter (default: 'ALL')
            limit: Optional limit on courses
        """
        logger.info(
            f"🔁 Running scraper in loop mode (every {self.loop_interval_seconds}s)"
        )

        # Reset all scrapers to idle on first bootup
        logger.info("🔄 Resetting all scraper statuses to idle on bootup...")
        await self.reset_all_scrapers_to_idle()

        while True:
            try:
                await self.run_all_jobs(subject=subject, limit=limit)

                # Wait until next interval
                logger.info(
                    f"⏰ Waiting {self.loop_interval_seconds}s until next run..."
                )
                await asyncio.sleep(self.loop_interval_seconds)

            except KeyboardInterrupt:
                logger.info("🛑 Stopping loop...")
                break
            except Exception as e:
                logger.error(f"❌ Loop iteration failed: {e}")
                # Still wait before next iteration
                await asyncio.sleep(self.loop_interval_seconds)

    async def loop_independent(
        self, subject: str = "ALL", limit: Optional[int] = None
    ) -> None:
        """
        Run scraper jobs in independent loops with 3-minute intervals per college.

        Each active college runs on its own schedule:
        - After completing a run, waits 3 minutes
        - Then runs again, independently of other colleges
        - Errors in one college don't affect others

        Args:
            subject: Subject filter (default: 'ALL')
            limit: Optional limit on courses
        """
        logger.info("🚀 Starting independent scraper loops (3 minutes per college)")

        # Reset all scrapers to idle on first bootup
        logger.info("🔄 Resetting all scraper statuses to idle on bootup...")
        await self.reset_all_scrapers_to_idle()

        # Get all active colleges (using separate session)
        with SessionLocal() as db:
            colleges = (
                db.execute(select(College).where(College.is_active == True))
                .scalars()
                .all()
            )

        if not colleges:
            logger.warning("⚠️  No active colleges found")
            return

        logger.info(
            f"📚 Found {len(colleges)} active colleges to scrape independently:"
        )
        for college in colleges:
            logger.info(f"   - {college.name} ({college.short_name})")

        try:
            # Create independent task for each college
            tasks = [
                asyncio.create_task(
                    self._college_loop(college), name=f"scraper-{college.short_name}"
                )
                for college in colleges
            ]

            # Wait for all tasks (will run indefinitely)
            # return_exceptions=True prevents one task failure from killing others
            await asyncio.gather(*tasks, return_exceptions=True)

        except KeyboardInterrupt:
            logger.info("🛑 Received shutdown signal, stopping all scraper loops...")

            # Cancel all tasks
            for task in tasks:
                task.cancel()

            # Wait for tasks to finish cancelling
            await asyncio.gather(*tasks, return_exceptions=True)

            logger.info("✅ All scraper loops stopped")


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
        "--loop", action="store_true", help="Run continuously every 10 minutes"
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
            await cli.loop_independent(subject=args.subject, limit=args.limit)
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
