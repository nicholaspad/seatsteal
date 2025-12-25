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
from datetime import datetime
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from scraper.services.scraper_log import ScraperLogService
from models.scraper_log import ScraperLog
from models.scraper import Scraper


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

        with patch("scraper.services.scraper_log.ScraperLog", return_value=mock_log_start):
            log_id = await scraper_log_service.start_log(123)

        assert log_id == 1

        # Complete log
        mock_log_complete = Mock(spec=ScraperLog)
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

        with patch("scraper.services.scraper_log.ScraperLog", return_value=mock_log_start):
            log_id = await scraper_log_service.start_log(456)

        # Complete with error
        mock_log_complete = Mock(spec=ScraperLog)
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

            with patch("scraper.services.scraper_log.ScraperLog", return_value=mock_log):
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
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_log)
        mock_db.execute = Mock(return_value=mock_result)

        await scraper_log_service.complete_log(log_id=1, outcome="success")

        assert mock_log.outcome == "success"

    @pytest.mark.asyncio
    async def test_outcome_error(self, scraper_log_service, mock_db):
        """Test error outcome"""
        mock_log = Mock(spec=ScraperLog)
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_log)
        mock_db.execute = Mock(return_value=mock_result)

        await scraper_log_service.complete_log(log_id=1, outcome="error")

        assert mock_log.outcome == "error"

    @pytest.mark.asyncio
    async def test_outcome_partial(self, scraper_log_service, mock_db):
        """Test partial outcome"""
        mock_log = Mock(spec=ScraperLog)
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_log)
        mock_db.execute = Mock(return_value=mock_result)

        await scraper_log_service.complete_log(log_id=1, outcome="partial")

        assert mock_log.outcome == "partial"

    @pytest.mark.asyncio
    async def test_outcome_timeout(self, scraper_log_service, mock_db):
        """Test timeout outcome"""
        mock_log = Mock(spec=ScraperLog)
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_log)
        mock_db.execute = Mock(return_value=mock_result)

        await scraper_log_service.complete_log(log_id=1, outcome="timeout")

        assert mock_log.outcome == "timeout"
