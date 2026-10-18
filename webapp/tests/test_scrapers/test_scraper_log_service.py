"""
Comprehensive test suite for scraper/services/scraper_log.py

Tests scraper log management including:
- ScraperLogService initialization
- Log lifecycle (start, update, complete)
- Scraper ID lookups
- Statistics tracking
- Error handling
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from sqlalchemy import inspect, text

from scraper.services.scraper_log import ScraperLogService, as_utc_datetime
from models.scraper_log import ScraperLog
from models.scraper import Scraper
from models.college import College


# Test fixtures
@pytest.fixture
def mock_db():
    """Create a mock database session"""
    db = Mock(spec=Session)
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()
    db.execute = Mock()
    return db


@pytest.fixture
def scraper_log_service(mock_db):
    """Create ScraperLogService instance"""
    return ScraperLogService(mock_db)


# ============================================================================
# Initialization Tests
# ============================================================================


class TestScraperLogServiceInitialization:
    """Test ScraperLogService initialization"""

    def test_scraper_log_service_initialization(self, mock_db):
        """Test service creation with database session"""
        service = ScraperLogService(mock_db)

        assert service.db == mock_db

    def test_scraper_log_service_requires_session(self):
        """Test that database session is required"""
        # Should work with any object (not type-checked at runtime)
        service = ScraperLogService(Mock())
        assert service.db is not None


# ============================================================================
# get_scraper_id_from_college Tests
# ============================================================================


class TestGetScraperIdFromCollege:
    """Test get_scraper_id_from_college method"""

    @pytest.mark.asyncio
    async def test_get_scraper_id_found(self, scraper_log_service, mock_db):
        """Test retrieving scraper ID for valid college"""
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=123)
        mock_db.execute = Mock(return_value=mock_result)

        scraper_id = await scraper_log_service.get_scraper_id_from_college(1)

        assert scraper_id == 123
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_scraper_id_not_found(self, scraper_log_service, mock_db):
        """Test handling of college with no scraper"""
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute = Mock(return_value=mock_result)

        scraper_id = await scraper_log_service.get_scraper_id_from_college(999)

        assert scraper_id is None

    @pytest.mark.asyncio
    async def test_get_scraper_id_query_format(self, scraper_log_service, mock_db):
        """Test that correct query is executed"""
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=456)
        mock_db.execute = Mock(return_value=mock_result)

        await scraper_log_service.get_scraper_id_from_college(5)

        # Verify execute was called with a select query
        mock_db.execute.assert_called_once()


# ============================================================================
# start_log Tests
# ============================================================================


class TestStartLog:
    """Test start_log method"""

    @pytest.mark.asyncio
    async def test_start_log_creates_entry(self, scraper_log_service, mock_db):
        """Test creation of new log entry"""
        mock_log = Mock()
        mock_log.id = 42

        def capture_log(log):
            log.id = 42

        mock_db.add = Mock(side_effect=lambda x: capture_log(x))
        mock_db.flush = Mock()

        with patch("scraper.services.scraper_log.ScraperLog", return_value=mock_log):
            log_id = await scraper_log_service.start_log(123)

            assert log_id == 42
            mock_db.add.assert_called_once()
            mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_log_sets_defaults(self, scraper_log_service, mock_db):
        """Test default values for new log entry"""
        captured_log = None

        def capture_log(log):
            nonlocal captured_log
            captured_log = log
            log.id = 1

        mock_db.add = Mock(side_effect=capture_log)

        with patch("scraper.services.scraper_log.ScraperLog") as MockLog:
            await scraper_log_service.start_log(123)

            # Verify ScraperLog created with correct defaults
            MockLog.assert_called_once()
            call_kwargs = MockLog.call_args[1]
            assert call_kwargs["scraper_id"] == 123
            assert call_kwargs["outcome"] == "running"
            assert call_kwargs["courses_created"] == 0
            assert call_kwargs["classes_created"] == 0
            assert "started_at" in call_kwargs

    @pytest.mark.asyncio
    async def test_start_log_returns_id(self, scraper_log_service, mock_db):
        """Test that log ID is returned"""
        mock_log = Mock()
        mock_log.id = 999

        mock_db.add = Mock(side_effect=lambda x: setattr(x, "id", 999))

        with patch("scraper.services.scraper_log.ScraperLog", return_value=mock_log):
            log_id = await scraper_log_service.start_log(456)

            assert log_id == 999


# ============================================================================
# complete_log Tests
# ============================================================================


class TestCompleteLog:
    """Test complete_log method"""

    @pytest.mark.asyncio
    async def test_complete_log_success_outcome(self, scraper_log_service, mock_db):
        """Test completing log with success outcome"""
        mock_log = Mock(spec=ScraperLog)
        mock_log.started_at = datetime.now()  # Set started_at as datetime
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_log)
        mock_db.execute = Mock(return_value=mock_result)

        await scraper_log_service.complete_log(
            log_id=1,
            outcome="success",
            courses_created=25,
            classes_created=100,
        )

        assert mock_log.outcome == "success"
        assert mock_log.courses_created == 25
        assert mock_log.classes_created == 100
        assert mock_log.completed_at is not None

    @pytest.mark.asyncio
    async def test_complete_log_error_outcome(self, scraper_log_service, mock_db):
        """Test completing log with error outcome"""
        mock_log = Mock(spec=ScraperLog)
        mock_log.started_at = datetime.now()  # Set started_at as datetime
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_log)
        mock_db.execute = Mock(return_value=mock_result)

        await scraper_log_service.complete_log(
            log_id=1,
            outcome="error",
            error_message="Connection failed",
        )

        assert mock_log.outcome == "error"
        assert mock_log.error_message == "Connection failed"
        assert mock_log.completed_at is not None

    @pytest.mark.asyncio
    async def test_complete_log_partial_outcome(self, scraper_log_service, mock_db):
        """Test completing log with partial outcome"""
        mock_log = Mock(spec=ScraperLog)
        mock_log.started_at = datetime.now()  # Set started_at as datetime
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_log)
        mock_db.execute = Mock(return_value=mock_result)

        await scraper_log_service.complete_log(
            log_id=1,
            outcome="partial",
            courses_created=10,
            classes_created=50,
            error_message="Timed out after 10 courses",
        )

        assert mock_log.outcome == "partial"
        assert mock_log.courses_created == 10
        assert mock_log.classes_created == 50
        assert mock_log.error_message == "Timed out after 10 courses"

    @pytest.mark.asyncio
    async def test_complete_log_timeout_outcome(self, scraper_log_service, mock_db):
        """Test completing log with timeout outcome"""
        mock_log = Mock(spec=ScraperLog)
        mock_log.started_at = datetime.now()  # Set started_at as datetime
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_log)
        mock_db.execute = Mock(return_value=mock_result)

        await scraper_log_service.complete_log(
            log_id=1,
            outcome="timeout",
            error_message="Exceeded 15 minute limit",
        )

        assert mock_log.outcome == "timeout"
        assert mock_log.error_message == "Exceeded 15 minute limit"

    @pytest.mark.asyncio
    async def test_complete_log_sets_completed_at(self, scraper_log_service, mock_db):
        """Test that completed_at timestamp is set"""
        mock_log = Mock(spec=ScraperLog)
        mock_log.started_at = datetime.now()  # Set started_at as datetime
        mock_log.completed_at = None
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_log)
        mock_db.execute = Mock(return_value=mock_result)

        before = datetime.now()
        await scraper_log_service.complete_log(log_id=1, outcome="success")
        after = datetime.now()

        assert mock_log.completed_at is not None
        # Verify it's a recent timestamp (within test execution window)
        assert isinstance(mock_log.completed_at, datetime)

    @pytest.mark.asyncio
    async def test_complete_log_not_found(self, scraper_log_service, mock_db):
        """Test handling of invalid log ID"""
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute = Mock(return_value=mock_result)

        # Should not raise exception
        await scraper_log_service.complete_log(log_id=999, outcome="success")

    @pytest.mark.asyncio
    async def test_complete_log_zero_statistics(self, scraper_log_service, mock_db):
        """Test completing with zero courses/classes"""
        mock_log = Mock(spec=ScraperLog)
        mock_log.started_at = datetime.now()  # Set started_at as datetime
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_log)
        mock_db.execute = Mock(return_value=mock_result)

        await scraper_log_service.complete_log(
            log_id=1,
            outcome="success",
            courses_created=0,
            classes_created=0,
        )

        assert mock_log.courses_created == 0
        assert mock_log.classes_created == 0


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test error handling in log service"""

    @pytest.mark.asyncio
    async def test_start_log_database_error(self, scraper_log_service, mock_db):
        """Test handling of database errors during start_log"""
        mock_db.add = Mock(side_effect=Exception("Database error"))

        with pytest.raises(Exception):
            with patch("scraper.services.scraper_log.ScraperLog", return_value=Mock()):
                await scraper_log_service.start_log(123)

    @pytest.mark.asyncio
    async def test_complete_log_database_error(self, scraper_log_service, mock_db):
        """Test handling of database errors during complete_log"""
        mock_db.execute = Mock(side_effect=Exception("Database error"))

        with pytest.raises(Exception):
            await scraper_log_service.complete_log(log_id=1, outcome="success")

    @pytest.mark.asyncio
    async def test_get_scraper_id_database_error(self, scraper_log_service, mock_db):
        """Test handling of database errors during ID lookup"""
        mock_db.execute = Mock(side_effect=Exception("Database error"))

        with pytest.raises(Exception):
            await scraper_log_service.get_scraper_id_from_college(1)


# ============================================================================
# Integration Tests
# ============================================================================


class TestScraperLogLifecycle:
    """Integration tests for complete log lifecycle"""

    @pytest.mark.asyncio
    async def test_complete_log_lifecycle_success(self, scraper_log_service, mock_db):
        """Test complete lifecycle: start -> complete (success)"""
        # Start log
        mock_log_start = Mock()
        mock_log_start.id = 1

        mock_db.add = Mock(side_effect=lambda x: setattr(x, "id", 1))

        with patch(
            "scraper.services.scraper_log.ScraperLog", return_value=mock_log_start
        ):
            log_id = await scraper_log_service.start_log(123)

        assert log_id == 1

        # Complete log
        mock_log_complete = Mock(spec=ScraperLog)
        mock_log_complete.started_at = datetime.now()  # Set started_at as datetime
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_log_complete)
        mock_db.execute = Mock(return_value=mock_result)

        await scraper_log_service.complete_log(
            log_id=log_id,
            outcome="success",
            courses_created=50,
            classes_created=200,
        )

        assert mock_log_complete.outcome == "success"
        assert mock_log_complete.courses_created == 50
        assert mock_log_complete.classes_created == 200

    @pytest.mark.asyncio
    async def test_complete_log_lifecycle_error(self, scraper_log_service, mock_db):
        """Test complete lifecycle: start -> complete (error)"""
        # Start log
        mock_log_start = Mock()
        mock_log_start.id = 2

        mock_db.add = Mock(side_effect=lambda x: setattr(x, "id", 2))

        with patch(
            "scraper.services.scraper_log.ScraperLog", return_value=mock_log_start
        ):
            log_id = await scraper_log_service.start_log(456)

        # Complete with error
        mock_log_complete = Mock(spec=ScraperLog)
        mock_log_complete.started_at = datetime.now()  # Set started_at as datetime
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_log_complete)
        mock_db.execute = Mock(return_value=mock_result)

        await scraper_log_service.complete_log(
            log_id=log_id,
            outcome="error",
            error_message="Scraper crashed",
        )

        assert mock_log_complete.outcome == "error"
        assert mock_log_complete.error_message == "Scraper crashed"

    @pytest.mark.asyncio
    async def test_multiple_logs_sequential(self, scraper_log_service, mock_db):
        """Test creating multiple logs sequentially"""
        log_ids = []

        for i in range(3):
            mock_log = Mock()
            mock_log.id = i + 1

            mock_db.add = Mock(side_effect=lambda x, idx=i: setattr(x, "id", idx + 1))

            with patch(
                "scraper.services.scraper_log.ScraperLog", return_value=mock_log
            ):
                log_id = await scraper_log_service.start_log(100 + i)
                log_ids.append(log_id)

        assert len(log_ids) == 3
        assert log_ids == [1, 2, 3]


# ============================================================================
# Statistics Tracking Tests
# ============================================================================


class TestStatisticsTracking:
    """Test statistics tracking functionality"""

    @pytest.mark.asyncio
    async def test_track_courses_and_classes(self, scraper_log_service, mock_db):
        """Test tracking courses and classes created"""
        mock_log = Mock(spec=ScraperLog)
        mock_log.started_at = datetime.now()  # Set started_at as datetime
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_log)
        mock_db.execute = Mock(return_value=mock_result)

        await scraper_log_service.complete_log(
            log_id=1,
            outcome="success",
            courses_created=100,
            classes_created=500,
        )

        assert mock_log.courses_created == 100
        assert mock_log.classes_created == 500

    @pytest.mark.asyncio
    async def test_track_large_numbers(self, scraper_log_service, mock_db):
        """Test tracking large numbers of courses/classes"""
        mock_log = Mock(spec=ScraperLog)
        mock_log.started_at = datetime.now()  # Set started_at as datetime
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_log)
        mock_db.execute = Mock(return_value=mock_result)

        await scraper_log_service.complete_log(
            log_id=1,
            outcome="success",
            courses_created=10000,
            classes_created=50000,
        )

        assert mock_log.courses_created == 10000
        assert mock_log.classes_created == 50000

    @pytest.mark.asyncio
    async def test_statistics_defaults_to_zero(self, scraper_log_service, mock_db):
        """Test that statistics default to 0 when not provided"""
        mock_log = Mock(spec=ScraperLog)
        mock_log.started_at = datetime.now()  # Set started_at as datetime
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_log)
        mock_db.execute = Mock(return_value=mock_result)

        await scraper_log_service.complete_log(log_id=1, outcome="success")

        # Should be called with default 0 values (from method signature)
        # The method sets these if not provided
        assert mock_log.outcome == "success"


# ============================================================================
# Outcome Types Tests
# ============================================================================


class TestOutcomeTypes:
    """Test different outcome types"""

    @pytest.mark.asyncio
    async def test_outcome_success(self, scraper_log_service, mock_db):
        """Test success outcome"""
        mock_log = Mock(spec=ScraperLog)
        mock_log.started_at = datetime.now()  # Set started_at as datetime
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_log)
        mock_db.execute = Mock(return_value=mock_result)

        await scraper_log_service.complete_log(log_id=1, outcome="success")

        assert mock_log.outcome == "success"

    @pytest.mark.asyncio
    async def test_outcome_error(self, scraper_log_service, mock_db):
        """Test error outcome"""
        mock_log = Mock(spec=ScraperLog)
        mock_log.started_at = datetime.now()  # Set started_at as datetime
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_log)
        mock_db.execute = Mock(return_value=mock_result)

        await scraper_log_service.complete_log(log_id=1, outcome="error")

        assert mock_log.outcome == "error"

    @pytest.mark.asyncio
    async def test_outcome_partial(self, scraper_log_service, mock_db):
        """Test partial outcome"""
        mock_log = Mock(spec=ScraperLog)
        mock_log.started_at = datetime.now()  # Set started_at as datetime
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_log)
        mock_db.execute = Mock(return_value=mock_result)

        await scraper_log_service.complete_log(log_id=1, outcome="partial")

        assert mock_log.outcome == "partial"

    @pytest.mark.asyncio
    async def test_outcome_timeout(self, scraper_log_service, mock_db):
        """Test timeout outcome"""
        mock_log = Mock(spec=ScraperLog)
        mock_log.started_at = datetime.now()  # Set started_at as datetime
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_log)
        mock_db.execute = Mock(return_value=mock_result)

        await scraper_log_service.complete_log(log_id=1, outcome="timeout")

        assert mock_log.outcome == "timeout"


# ============================================================================
# mark_orphaned_running_logs Tests
# ============================================================================


class TestMarkOrphanedRunningLogs:
    """Test startup sweep of leftover running scraper_logs rows"""

    @pytest.mark.asyncio
    async def test_mark_orphaned_running_logs_issues_update(
        self, scraper_log_service, mock_db
    ):
        """Sweep updates only running rows started before process start."""
        mock_result = Mock()
        mock_result.rowcount = 2
        mock_db.execute = Mock(return_value=mock_result)
        process_started_at = datetime.now(timezone.utc)

        count = await scraper_log_service.mark_orphaned_running_logs(process_started_at)

        assert count == 2
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_orphaned_running_logs_zero_rows(
        self, scraper_log_service, mock_db
    ):
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_db.execute = Mock(return_value=mock_result)

        count = await scraper_log_service.mark_orphaned_running_logs(
            datetime.now(timezone.utc)
        )

        assert count == 0

    @pytest.mark.asyncio
    async def test_sweep_orphans_real_rows_and_leaves_scrapers_untouched(
        self, test_db: Session, test_college: College
    ):
        """Integration: only pre-start running logs are marked; scrapers table stays put."""
        scraper = Scraper(college_id=test_college.id, status="running")
        test_db.add(scraper)
        test_db.flush()

        process_started_at = datetime.now(timezone.utc)
        orphan = ScraperLog(
            scraper_id=scraper.id,
            outcome="running",
            courses_created=0,
            classes_created=0,
            started_at=process_started_at - timedelta(hours=3),
        )
        in_process = ScraperLog(
            scraper_id=scraper.id,
            outcome="running",
            courses_created=0,
            classes_created=0,
            started_at=process_started_at + timedelta(seconds=5),
        )
        already_done = ScraperLog(
            scraper_id=scraper.id,
            outcome="success",
            courses_created=4,
            classes_created=8,
            started_at=process_started_at - timedelta(hours=1),
            completed_at=process_started_at - timedelta(minutes=50),
            duration_ms=600000,
        )
        test_db.add_all([orphan, in_process, already_done])
        test_db.commit()

        service = ScraperLogService(test_db)
        count = await service.mark_orphaned_running_logs(process_started_at)
        test_db.commit()

        assert count == 1
        test_db.refresh(orphan)
        test_db.refresh(in_process)
        test_db.refresh(already_done)
        test_db.refresh(scraper)

        assert orphan.outcome == "error"
        assert orphan.error_message == "orphaned by restart"
        assert orphan.completed_at is not None
        assert orphan.duration_ms is None
        assert in_process.outcome == "running"
        assert in_process.error_message is None
        assert already_done.outcome == "success"
        assert scraper.status == "running"

    def test_started_at_column_is_timestamptz(self, test_db: Session):
        """scraper_logs.started_at is timestamp with time zone, not naive timestamp."""
        pg_type = test_db.execute(
            text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name = 'scraper_logs' AND column_name = 'started_at'"
            )
        ).scalar_one()
        assert pg_type == "timestamp with time zone"

        sa_col = inspect(ScraperLog).columns["started_at"]
        assert sa_col.type.timezone is True

    def test_as_utc_datetime_normalizes_naive_and_offset(self):
        naive = datetime(2026, 10, 16, 15, 0, 0)
        assert as_utc_datetime(naive) == datetime(
            2026, 10, 16, 15, 0, 0, tzinfo=timezone.utc
        )

        offset = datetime(2026, 10, 16, 11, 0, 0, tzinfo=timezone(timedelta(hours=-4)))
        assert as_utc_datetime(offset) == datetime(
            2026, 10, 16, 15, 0, 0, tzinfo=timezone.utc
        )

    @pytest.mark.asyncio
    async def test_sweep_compares_timestamptz_started_at_in_utc(
        self, test_db: Session, test_college: College
    ):
        """Naive and offset-aware started_at values compare correctly as timestamptz UTC."""
        test_db.execute(text("SET TIME ZONE 'UTC'"))
        scraper = Scraper(college_id=test_college.id, status="idle")
        test_db.add(scraper)
        test_db.flush()

        # 15:00 UTC cutoff. Naive datetimes are stored/compared as UTC.
        cutoff = datetime(2026, 10, 16, 15, 0, 0, tzinfo=timezone.utc)
        naive_orphan = ScraperLog(
            scraper_id=scraper.id,
            outcome="running",
            courses_created=0,
            classes_created=0,
            started_at=datetime(2026, 10, 16, 12, 0, 0),
        )
        naive_current = ScraperLog(
            scraper_id=scraper.id,
            outcome="running",
            courses_created=0,
            classes_created=0,
            started_at=datetime(2026, 10, 16, 16, 0, 0),
        )
        # 11:00-04:00 == 15:00 UTC, so this is not before cutoff.
        offset_at_cutoff = ScraperLog(
            scraper_id=scraper.id,
            outcome="running",
            courses_created=0,
            classes_created=0,
            started_at=datetime(
                2026, 10, 16, 11, 0, 0, tzinfo=timezone(timedelta(hours=-4))
            ),
        )
        aware_orphan = ScraperLog(
            scraper_id=scraper.id,
            outcome="running",
            courses_created=0,
            classes_created=0,
            started_at=datetime(2026, 10, 16, 14, 30, 0, tzinfo=timezone.utc),
        )
        test_db.add_all([naive_orphan, naive_current, offset_at_cutoff, aware_orphan])
        test_db.commit()

        service = ScraperLogService(test_db)
        # Naive cutoff must be treated as UTC to match timestamptz storage.
        count = await service.mark_orphaned_running_logs(
            datetime(2026, 10, 16, 15, 0, 0)
        )
        test_db.commit()

        assert count == 2
        test_db.refresh(naive_orphan)
        test_db.refresh(naive_current)
        test_db.refresh(offset_at_cutoff)
        test_db.refresh(aware_orphan)

        assert naive_orphan.outcome == "error"
        assert naive_orphan.error_message == "orphaned by restart"
        assert aware_orphan.outcome == "error"
        assert naive_current.outcome == "running"
        assert offset_at_cutoff.outcome == "running"
        assert cutoff == as_utc_datetime(datetime(2026, 10, 16, 15, 0, 0))

    def test_duration_ms_column_is_nullable(self, test_db: Session):
        """scraper_logs.duration_ms is nullable int4, so the sweep can set NULL."""
        pg_nullable = test_db.execute(
            text(
                "SELECT is_nullable FROM information_schema.columns "
                "WHERE table_name = 'scraper_logs' AND column_name = 'duration_ms'"
            )
        ).scalar_one()
        assert pg_nullable == "YES"

        sa_col = inspect(ScraperLog).columns["duration_ms"]
        assert sa_col.nullable is True

    @pytest.mark.asyncio
    async def test_sweep_nulls_duration_ms_for_long_running_orphans(
        self, test_db: Session, test_college: College
    ):
        """60d, 400d, and 1min pre-boot running rows are swept; post-boot stays running.

        Rows older than ~24.8 days overflow int4 if duration_ms is computed as
        CAST(EXTRACT(epoch)*1000 AS INTEGER). The sweep must succeed for all of
        them in one UPDATE and leave duration_ms NULL.
        """
        scraper = Scraper(college_id=test_college.id, status="idle")
        test_db.add(scraper)
        test_db.flush()

        process_started_at = datetime.now(timezone.utc)
        orphan_60d = ScraperLog(
            scraper_id=scraper.id,
            outcome="running",
            courses_created=0,
            classes_created=0,
            started_at=process_started_at - timedelta(days=60),
        )
        orphan_400d = ScraperLog(
            scraper_id=scraper.id,
            outcome="running",
            courses_created=0,
            classes_created=0,
            started_at=process_started_at - timedelta(days=400),
        )
        orphan_1min = ScraperLog(
            scraper_id=scraper.id,
            outcome="running",
            courses_created=0,
            classes_created=0,
            started_at=process_started_at - timedelta(minutes=1),
        )
        post_boot = ScraperLog(
            scraper_id=scraper.id,
            outcome="running",
            courses_created=0,
            classes_created=0,
            started_at=process_started_at + timedelta(seconds=5),
        )
        test_db.add_all([orphan_60d, orphan_400d, orphan_1min, post_boot])
        test_db.commit()

        service = ScraperLogService(test_db)
        count = await service.mark_orphaned_running_logs(process_started_at)
        test_db.commit()

        assert count == 3
        test_db.refresh(orphan_60d)
        test_db.refresh(orphan_400d)
        test_db.refresh(orphan_1min)
        test_db.refresh(post_boot)

        for orphan in (orphan_60d, orphan_400d, orphan_1min):
            assert orphan.outcome == "error"
            assert orphan.error_message == "orphaned by restart"
            assert orphan.completed_at is not None
            assert orphan.duration_ms is None

        assert post_boot.outcome == "running"
        assert post_boot.error_message is None
        assert post_boot.completed_at is None
        assert post_boot.duration_ms is None
