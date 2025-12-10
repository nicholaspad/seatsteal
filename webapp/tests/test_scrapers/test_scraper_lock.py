"""
Unit tests for ScraperLock functionality.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select

from scraper.scraper_lock import ScraperLock, LockResult
from models.scraper import Scraper
from models.college import College


class TestScraperLock:
    """Tests for ScraperLock class."""

    @pytest.fixture
    def test_scraper(self, test_db: Session, test_college: College) -> Scraper:
        """Create a test scraper."""
        scraper = Scraper(
            college_id=test_college.id,
            status="idle",
            last_run_at=None,
            next_run_at=None,
        )
        test_db.add(scraper)
        test_db.commit()
        test_db.refresh(scraper)
        return scraper

    @pytest.mark.unit
    def test_acquire_lock_success(
        self, test_db: Session, test_college: College, test_scraper: Scraper
    ):
        """Test successfully acquiring a lock on idle scraper."""
        lock = ScraperLock(test_college.id, test_db)
        result = lock.acquire()

        assert result.success is True
        assert result.scraper is not None
        assert lock.acquired is True

        # Verify the scraper is now running in database
        test_db.refresh(test_scraper)
        assert test_scraper.status == "running"

        # Clean up
        lock.release()

    @pytest.mark.unit
    def test_acquire_lock_already_running(
        self, test_db: Session, test_college: College, test_scraper: Scraper
    ):
        """Test that acquiring lock fails when scraper is already running."""
        # First lock acquires successfully
        lock1 = ScraperLock(test_college.id, test_db)
        result1 = lock1.acquire()
        assert result1.success is True

        # Second lock should fail
        lock2 = ScraperLock(test_college.id, test_db)
        result2 = lock2.acquire()
        assert result2.success is False
        assert result2.scraper.status == "running"
        assert lock2.acquired is False

        # Clean up
        lock1.release()

    @pytest.mark.unit
    def test_skip_lock_bypasses_status_check(
        self, test_db: Session, test_college: College, test_scraper: Scraper
    ):
        """Test that skip_lock=True bypasses status checks and always acquires lock."""
        # First, acquire lock normally
        lock1 = ScraperLock(test_college.id, test_db)
        result1 = lock1.acquire()
        assert result1.success is True

        # Verify scraper is running
        test_db.refresh(test_scraper)
        assert test_scraper.status == "running"

        # Now try to acquire with skip_lock=True (should succeed despite running status)
        lock2 = ScraperLock(test_college.id, test_db, skip_lock=True)
        result2 = lock2.acquire()
        assert result2.success is True
        assert result2.scraper is not None
        assert lock2.acquired is True

        # Verify still running
        test_db.refresh(test_scraper)
        assert test_scraper.status == "running"

        # Clean up
        lock2.release()

    @pytest.mark.unit
    def test_skip_lock_with_idle_scraper(
        self, test_db: Session, test_college: College, test_scraper: Scraper
    ):
        """Test that skip_lock works even with idle scraper."""
        lock = ScraperLock(test_college.id, test_db, skip_lock=True)
        result = lock.acquire()

        assert result.success is True
        assert result.scraper is not None
        assert lock.acquired is True

        # Verify scraper is running
        test_db.refresh(test_scraper)
        assert test_scraper.status == "running"

        # Clean up
        lock.release()

    @pytest.mark.unit
    def test_release_lock(
        self, test_db: Session, test_college: College, test_scraper: Scraper
    ):
        """Test releasing a lock."""
        lock = ScraperLock(test_college.id, test_db)
        lock.acquire()

        # Release the lock (defaults to 'completed' status)
        lock.release()

        # Verify scraper status is completed
        test_db.refresh(test_scraper)
        assert test_scraper.status == "completed"
        assert lock.acquired is False

    @pytest.mark.unit
    def test_release_lock_with_idle_status(
        self, test_db: Session, test_college: College, test_scraper: Scraper
    ):
        """Test releasing a lock with explicit idle status."""
        lock = ScraperLock(test_college.id, test_db)
        lock.acquire()

        # Release with idle status
        lock.release(status="idle")

        # Verify scraper status is idle
        test_db.refresh(test_scraper)
        assert test_scraper.status == "idle"
        assert lock.acquired is False

    @pytest.mark.unit
    def test_release_without_acquire(
        self, test_db: Session, test_college: College, test_scraper: Scraper
    ):
        """Test releasing a lock that was never acquired."""
        lock = ScraperLock(test_college.id, test_db)

        # Should not raise error and should return False
        result = lock.release()
        assert result is False

        # Scraper should still be idle
        test_db.refresh(test_scraper)
        assert test_scraper.status == "idle"

    @pytest.mark.unit
    def test_force_release_stuck_lock(
        self, test_db: Session, test_college: College, test_scraper: Scraper
    ):
        """Test that stuck locks are force released after timeout."""
        # Manually set scraper to running with old timestamp (timezone-naive to match implementation)
        old_time = datetime.now() - timedelta(hours=1)
        test_scraper.status = "running"
        test_scraper.last_run_at = old_time
        test_db.commit()

        # Try to acquire with short timeout (1 second = 1000ms)
        lock = ScraperLock(test_college.id, test_db, lock_timeout_ms=1000)
        result = lock.acquire()

        # Should successfully acquire by force-releasing the stuck lock
        assert result.success is True
        assert result.scraper is not None

        # Verify scraper is now running
        test_db.refresh(test_scraper)
        assert test_scraper.status == "running"

        # Clean up
        lock.release()

    @pytest.mark.unit
    def test_scraper_auto_created(self, test_db: Session, test_college: College):
        """Test that scraper record is auto-created if it doesn't exist."""
        # Don't create scraper in fixture, let the lock create it
        lock = ScraperLock(test_college.id, test_db)
        result = lock.acquire()

        assert result.success is True
        assert result.scraper is not None

        # Verify scraper was created in database
        scraper = test_db.execute(
            select(Scraper).where(Scraper.college_id == test_college.id)
        ).scalar_one()
        assert scraper is not None
        assert scraper.college_id == test_college.id
        assert scraper.status == "running"

        # Clean up
        lock.release()

    @pytest.mark.unit
    def test_get_scraper_id(
        self, test_db: Session, test_college: College, test_scraper: Scraper
    ):
        """Test getting scraper ID."""
        lock = ScraperLock(test_college.id, test_db)
        scraper_id = lock.get_scraper_id()

        assert scraper_id is not None
        assert scraper_id == test_scraper.id

    @pytest.mark.unit
    def test_is_acquired(
        self, test_db: Session, test_college: College, test_scraper: Scraper
    ):
        """Test checking if lock is acquired."""
        lock = ScraperLock(test_college.id, test_db)

        assert lock.is_acquired() is False

        lock.acquire()
        assert lock.is_acquired() is True

        lock.release()
        assert lock.is_acquired() is False
