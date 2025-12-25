"""
Comprehensive test suite for scraper/scraper_job.py

Tests scraper job orchestration including:
- JobConfig and JobResult classes
- ScraperJob initialization
- Lock acquisition and release
- Retry logic with exponential backoff
- Statistics tracking and logging
- Error handling across all scenarios
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from sqlalchemy.orm import Session

from scraper.scraper_job import ScraperJob, JobConfig, JobResult
from models.college import College
from scraper.scraper_lock import LockResult


# Test fixtures
@pytest.fixture
def test_college():
    """Create a test college"""
    college = College(
        id=1,
        name="Test University",
        short_name="test",
        is_active=True,
    )
    return college


@pytest.fixture
def mock_db():
    """Create a mock database session"""
    db = Mock(spec=Session)
    db.commit = Mock()
    db.rollback = Mock()
    db.flush = Mock()
    return db


@pytest.fixture
def mock_lock():
    """Create a mock ScraperLock"""
    lock = Mock()
    lock.get_scraper_id = Mock(return_value=1)
    lock.acquire = Mock(return_value=LockResult(success=True))
    lock.release = Mock()
    lock.cleanup = Mock()
    return lock


@pytest.fixture
def mock_log_service():
    """Create a mock ScraperLogService"""
    service = AsyncMock()
    service.start_log = AsyncMock(return_value=1)
    service.complete_log = AsyncMock()
    return service


@pytest.fixture
def mock_scraper_service():
    """Create a mock ScraperService"""
    service = AsyncMock()
    service.scrape_college = AsyncMock(
        return_value={"success": True, "courses_saved": 10, "classes_saved": 50}
    )
    return service


# ============================================================================
# JobConfig Tests
# ============================================================================


class TestJobConfig:
    """Test JobConfig configuration class"""

    def test_job_config_defaults(self):
        """Test default configuration values"""
        config = JobConfig()

        assert config.subject == "ALL"
        assert config.limit == 1000
        assert config.lock_timeout_ms == 900000  # 15 minutes
        assert config.retry_attempts == 3
        assert config.retry_delay_ms == 5000
        assert config.skip_lock is False

    def test_job_config_custom_values(self):
        """Test custom configuration values"""
        config = JobConfig(
            subject="CS",
            limit=500,
            lock_timeout_ms=600000,
            retry_attempts=5,
            retry_delay_ms=10000,
            skip_lock=True,
        )

        assert config.subject == "CS"
        assert config.limit == 500
        assert config.lock_timeout_ms == 600000
        assert config.retry_attempts == 5
        assert config.retry_delay_ms == 10000
        assert config.skip_lock is True

    def test_job_config_partial_custom(self):
        """Test partial custom configuration"""
        config = JobConfig(subject="MATH", retry_attempts=10)

        assert config.subject == "MATH"
        assert config.retry_attempts == 10
        # Others should be defaults
        assert config.limit == 1000
        assert config.lock_timeout_ms == 900000

    def test_job_config_zero_limit(self):
        """Test configuration with zero limit"""
        config = JobConfig(limit=0)

        assert config.limit == 0

    def test_job_config_none_limit(self):
        """Test configuration with None limit (no limit)"""
        config = JobConfig(limit=None)

        assert config.limit is None


# ============================================================================
# JobResult Tests
# ============================================================================


class TestJobResult:
    """Test JobResult result class"""

    def test_job_result_success(self):
        """Test successful job result"""
        result = JobResult(
            success=True,
            stats={"courses_saved": 10, "classes_saved": 50},
            duration_ms=5000,
        )

        assert result.success is True
        assert result.stats == {"courses_saved": 10, "classes_saved": 50}
        assert result.error is None
        assert result.duration_ms == 5000

    def test_job_result_failure(self):
        """Test failed job result"""
        result = JobResult(
            success=False, error="Network error", duration_ms=3000
        )

        assert result.success is False
        assert result.error == "Network error"
        assert result.stats == {}
        assert result.duration_ms == 3000

    def test_job_result_empty_stats(self):
        """Test result with empty stats defaults to dict"""
        result = JobResult(success=True)

        assert result.stats == {}

    def test_job_result_partial_success(self):
        """Test partial success with error message"""
        result = JobResult(
            success=False,
            stats={"courses_saved": 5},
            error="Partial failure",
        )

        assert result.success is False
        assert result.stats == {"courses_saved": 5}
        assert result.error == "Partial failure"


# ============================================================================
# ScraperJob Initialization Tests
# ============================================================================


class TestScraperJobInitialization:
    """Test ScraperJob initialization"""

    def test_scraper_job_initialization(self, test_college, mock_db):
        """Test basic job initialization"""
        with patch("scraper.scraper_job.ScraperLock") as MockLock:
            job = ScraperJob(test_college, mock_db)

            assert job.college == test_college
            assert job.db == mock_db
            assert isinstance(job.config, JobConfig)
            MockLock.assert_called_once()

    def test_scraper_job_with_custom_config(self, test_college, mock_db):
        """Test initialization with custom config"""
        config = JobConfig(subject="CS", limit=100)

        with patch("scraper.scraper_job.ScraperLock"):
            job = ScraperJob(test_college, mock_db, config)

            assert job.config.subject == "CS"
            assert job.config.limit == 100

    def test_scraper_job_lock_creation(self, test_college, mock_db):
        """Test that ScraperLock is created with correct parameters"""
        config = JobConfig(lock_timeout_ms=600000, skip_lock=True)

        with patch("scraper.scraper_job.ScraperLock") as MockLock:
            job = ScraperJob(test_college, mock_db, config)

            MockLock.assert_called_once_with(
                test_college.id, mock_db, 600000, True
            )

    def test_scraper_job_get_methods(self, test_college, mock_db):
        """Test getter methods"""
        config = JobConfig(subject="MATH")

        with patch("scraper.scraper_job.ScraperLock") as MockLock:
            mock_lock_instance = Mock()
            MockLock.return_value = mock_lock_instance

            job = ScraperJob(test_college, mock_db, config)

            assert job.get_college() == test_college
            assert job.get_config() == config
            assert job.get_lock() == mock_lock_instance


# ============================================================================
# execute() - Success Path Tests
# ============================================================================


class TestExecuteSuccess:
    """Test successful execution paths"""

    @pytest.mark.asyncio
    async def test_execute_success(
        self, test_college, mock_db, mock_lock, mock_log_service, mock_scraper_service
    ):
        """Test successful scraper execution"""
        with patch("scraper.scraper_job.ScraperLock", return_value=mock_lock):
            with patch("scraper.scraper_job.ScraperLogService", return_value=mock_log_service):
                with patch("scraper.scraper_job.ScraperService", return_value=mock_scraper_service):
                    job = ScraperJob(test_college, mock_db)

                    result = await job.execute()

                    assert result.success is True
                    assert result.stats["courses_saved"] == 10
                    assert result.stats["classes_saved"] == 50
                    assert result.duration_ms >= 0  # Can be 0 in fast tests
                    mock_lock.acquire.assert_called_once()
                    mock_lock.release.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_subject_filter(
        self, test_college, mock_db, mock_lock, mock_log_service, mock_scraper_service
    ):
        """Test execution with subject filter"""
        config = JobConfig(subject="CS")

        with patch("scraper.scraper_job.ScraperLock", return_value=mock_lock):
            with patch("scraper.scraper_job.ScraperLogService", return_value=mock_log_service):
                with patch("scraper.scraper_job.ScraperService", return_value=mock_scraper_service):
                    job = ScraperJob(test_college, mock_db, config)

                    await job.execute()

                    mock_scraper_service.scrape_college.assert_called_once_with(
                        "test", "CS", 1000
                    )

    @pytest.mark.asyncio
    async def test_execute_with_limit(
        self, test_college, mock_db, mock_lock, mock_log_service, mock_scraper_service
    ):
        """Test execution with course limit"""
        config = JobConfig(limit=100)

        with patch("scraper.scraper_job.ScraperLock", return_value=mock_lock):
            with patch("scraper.scraper_job.ScraperLogService", return_value=mock_log_service):
                with patch("scraper.scraper_job.ScraperService", return_value=mock_scraper_service):
                    job = ScraperJob(test_college, mock_db, config)

                    await job.execute()

                    mock_scraper_service.scrape_college.assert_called_once_with(
                        "test", "ALL", 100
                    )

    @pytest.mark.asyncio
    async def test_execute_statistics_tracking(
        self, test_college, mock_db, mock_lock, mock_log_service, mock_scraper_service
    ):
        """Test that statistics are tracked correctly"""
        mock_scraper_service.scrape_college = AsyncMock(
            return_value={
                "success": True,
                "courses_saved": 25,
                "classes_saved": 100,
            }
        )

        with patch("scraper.scraper_job.ScraperLock", return_value=mock_lock):
            with patch("scraper.scraper_job.ScraperLogService", return_value=mock_log_service):
                with patch("scraper.scraper_job.ScraperService", return_value=mock_scraper_service):
                    job = ScraperJob(test_college, mock_db)

                    result = await job.execute()

                    assert result.stats["courses_saved"] == 25
                    assert result.stats["classes_saved"] == 100

    @pytest.mark.asyncio
    async def test_execute_log_service_integration(
        self, test_college, mock_db, mock_lock, mock_log_service, mock_scraper_service
    ):
        """Test integration with log service"""
        with patch("scraper.scraper_job.ScraperLock", return_value=mock_lock):
            with patch("scraper.scraper_job.ScraperLogService", return_value=mock_log_service):
                with patch("scraper.scraper_job.ScraperService", return_value=mock_scraper_service):
                    job = ScraperJob(test_college, mock_db)

                    await job.execute()

                    # Should start and complete log
                    mock_log_service.start_log.assert_called_once_with(1)
                    mock_log_service.complete_log.assert_called_once()

                    # Verify completion with correct stats
                    call_args = mock_log_service.complete_log.call_args
                    assert call_args[1]["outcome"] == "success"
                    assert call_args[1]["courses_created"] == 10
                    assert call_args[1]["classes_created"] == 50


# ============================================================================
# execute() - Lock Management Tests
# ============================================================================


class TestExecuteLockManagement:
    """Test lock acquisition and release during execution"""

    @pytest.mark.asyncio
    async def test_execute_lock_acquisition_failure(
        self, test_college, mock_db, mock_log_service
    ):
        """Test handling of lock acquisition failure"""
        mock_lock = Mock()
        mock_lock.get_scraper_id = Mock(return_value=1)
        mock_lock.acquire = Mock(
            return_value=LockResult(success=False, reason="Already running")
        )

        with patch("scraper.scraper_job.ScraperLock", return_value=mock_lock):
            with patch("scraper.scraper_job.ScraperLogService", return_value=mock_log_service):
                job = ScraperJob(test_college, mock_db)

                result = await job.execute()

                assert result.success is False
                assert "Already running" in result.error
                mock_lock.release.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_lock_release_on_success(
        self, test_college, mock_db, mock_lock, mock_log_service, mock_scraper_service
    ):
        """Test lock is released after successful scrape"""
        with patch("scraper.scraper_job.ScraperLock", return_value=mock_lock):
            with patch("scraper.scraper_job.ScraperLogService", return_value=mock_log_service):
                with patch("scraper.scraper_job.ScraperService", return_value=mock_scraper_service):
                    job = ScraperJob(test_college, mock_db)

                    await job.execute()

                    mock_lock.release.assert_called_once()
                    call_args = mock_lock.release.call_args[0]
                    assert call_args[0] == "completed"

    @pytest.mark.asyncio
    async def test_execute_lock_release_on_failure(
        self, test_college, mock_db, mock_lock, mock_log_service
    ):
        """Test lock is released even on failure"""
        mock_scraper_service = AsyncMock()
        mock_scraper_service.scrape_college = AsyncMock(
            return_value={"success": False, "error": "Scraping failed"}
        )

        with patch("scraper.scraper_job.ScraperLock", return_value=mock_lock):
            with patch("scraper.scraper_job.ScraperLogService", return_value=mock_log_service):
                with patch("scraper.scraper_job.ScraperService", return_value=mock_scraper_service):
                    job = ScraperJob(test_college, mock_db)

                    await job.execute()

                    mock_lock.release.assert_called_once()
                    call_args = mock_lock.release.call_args[0]
                    assert call_args[0] == "error"

    @pytest.mark.asyncio
    async def test_execute_skip_lock_mode(self, test_college, mock_db, mock_log_service, mock_scraper_service):
        """Test execution with skip_lock enabled"""
        config = JobConfig(skip_lock=True)
        mock_lock = Mock()
        mock_lock.get_scraper_id = Mock(return_value=1)
        mock_lock.acquire = Mock(return_value=LockResult(success=True))
        mock_lock.release = Mock()

        with patch("scraper.scraper_job.ScraperLock", return_value=mock_lock):
            with patch("scraper.scraper_job.ScraperLogService", return_value=mock_log_service):
                with patch("scraper.scraper_job.ScraperService", return_value=mock_scraper_service):
                    job = ScraperJob(test_college, mock_db, config)

                    await job.execute()

                    # Lock still used but with skip_lock flag
                    mock_lock.acquire.assert_called()

    @pytest.mark.asyncio
    async def test_execute_no_scraper_found(self, test_college, mock_db):
        """Test handling when no scraper exists for college"""
        mock_lock = Mock()
        mock_lock.get_scraper_id = Mock(return_value=None)

        with patch("scraper.scraper_job.ScraperLock", return_value=mock_lock):
            job = ScraperJob(test_college, mock_db)

            result = await job.execute()

            assert result.success is False
            assert "No scraper found" in result.error
            mock_lock.acquire.assert_not_called()


# ============================================================================
# execute() - Retry Logic Tests
# ============================================================================


class TestExecuteRetryLogic:
    """Test retry logic with exponential backoff"""

    @pytest.mark.asyncio
    async def test_execute_retry_on_failure(
        self, test_college, mock_db, mock_lock, mock_log_service
    ):
        """Test retry on transient failure"""
        mock_scraper_service = AsyncMock()
        # Fail first 2 attempts, succeed on 3rd
        mock_scraper_service.scrape_college = AsyncMock(
            side_effect=[
                {"success": False, "error": "Network error"},
                {"success": False, "error": "Network error"},
                {"success": True, "courses_saved": 10, "classes_saved": 50},
            ]
        )

        with patch("scraper.scraper_job.ScraperLock", return_value=mock_lock):
            with patch("scraper.scraper_job.ScraperLogService", return_value=mock_log_service):
                with patch("scraper.scraper_job.ScraperService", return_value=mock_scraper_service):
                    job = ScraperJob(test_college, mock_db)

                    result = await job.execute()

                    assert result.success is True
                    assert mock_scraper_service.scrape_college.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_retry_exponential_backoff(
        self, test_college, mock_db, mock_lock, mock_log_service
    ):
        """Test exponential backoff between retries"""
        mock_scraper_service = AsyncMock()
        mock_scraper_service.scrape_college = AsyncMock(
            side_effect=[
                {"success": False, "error": "Error 1"},
                {"success": False, "error": "Error 2"},
                {"success": True, "courses_saved": 5, "classes_saved": 25},
            ]
        )

        config = JobConfig(retry_delay_ms=100)  # Short delay for testing

        with patch("scraper.scraper_job.ScraperLock", return_value=mock_lock):
            with patch("scraper.scraper_job.ScraperLogService", return_value=mock_log_service):
                with patch("scraper.scraper_job.ScraperService", return_value=mock_scraper_service):
                    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                        job = ScraperJob(test_college, mock_db, config)

                        await job.execute()

                        # Should sleep twice (after 1st and 2nd attempts)
                        assert mock_sleep.call_count == 2
                        # First delay: 100ms, second: 200ms (exponential)
                        mock_sleep.assert_any_call(0.1)
                        mock_sleep.assert_any_call(0.2)

    @pytest.mark.asyncio
    async def test_execute_max_retries_exceeded(
        self, test_college, mock_db, mock_lock, mock_log_service
    ):
        """Test failure after max retry attempts"""
        mock_scraper_service = AsyncMock()
        mock_scraper_service.scrape_college = AsyncMock(
            return_value={"success": False, "error": "Persistent error"}
        )

        config = JobConfig(retry_attempts=3)

        with patch("scraper.scraper_job.ScraperLock", return_value=mock_lock):
            with patch("scraper.scraper_job.ScraperLogService", return_value=mock_log_service):
                with patch("scraper.scraper_job.ScraperService", return_value=mock_scraper_service):
                    job = ScraperJob(test_college, mock_db, config)

                    result = await job.execute()

                    assert result.success is False
                    assert "Persistent error" in result.error
                    assert mock_scraper_service.scrape_college.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_retry_on_exception(
        self, test_college, mock_db, mock_lock, mock_log_service
    ):
        """Test retry on exceptions"""
        mock_scraper_service = AsyncMock()
        mock_scraper_service.scrape_college = AsyncMock(
            side_effect=[
                Exception("Connection timeout"),
                Exception("Connection timeout"),
                {"success": True, "courses_saved": 10, "classes_saved": 50},
            ]
        )

        with patch("scraper.scraper_job.ScraperLock", return_value=mock_lock):
            with patch("scraper.scraper_job.ScraperLogService", return_value=mock_log_service):
                with patch("scraper.scraper_job.ScraperService", return_value=mock_scraper_service):
                    job = ScraperJob(test_college, mock_db)

                    result = await job.execute()

                    assert result.success is True
                    assert mock_scraper_service.scrape_college.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_no_retry_after_last_attempt(
        self, test_college, mock_db, mock_lock, mock_log_service
    ):
        """Test no delay after final retry attempt"""
        mock_scraper_service = AsyncMock()
        mock_scraper_service.scrape_college = AsyncMock(
            return_value={"success": False, "error": "Error"}
        )

        config = JobConfig(retry_attempts=2, retry_delay_ms=100)

        with patch("scraper.scraper_job.ScraperLock", return_value=mock_lock):
            with patch("scraper.scraper_job.ScraperLogService", return_value=mock_log_service):
                with patch("scraper.scraper_job.ScraperService", return_value=mock_scraper_service):
                    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                        job = ScraperJob(test_college, mock_db, config)

                        await job.execute()

                        # Should only sleep once (after 1st attempt, not after 2nd)
                        assert mock_sleep.call_count == 1


# ============================================================================
# execute() - Error Handling Tests
# ============================================================================


class TestExecuteErrorHandling:
    """Test error handling in execute()"""

    @pytest.mark.asyncio
    async def test_execute_scraper_service_exception(
        self, test_college, mock_db, mock_lock, mock_log_service
    ):
        """Test handling of ScraperService exceptions"""
        mock_scraper_service = AsyncMock()
        mock_scraper_service.scrape_college = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        config = JobConfig(retry_attempts=1)  # Single attempt for faster test

        with patch("scraper.scraper_job.ScraperLock", return_value=mock_lock):
            with patch("scraper.scraper_job.ScraperLogService", return_value=mock_log_service):
                with patch("scraper.scraper_job.ScraperService", return_value=mock_scraper_service):
                    job = ScraperJob(test_college, mock_db)

                    result = await job.execute()

                    assert result.success is False
                    assert "Database connection failed" in result.error
                    mock_lock.release.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_log_service_error_continues(
        self, test_college, mock_db, mock_lock, mock_scraper_service
    ):
        """Test that log service errors don't fail the job"""
        mock_log_service = AsyncMock()
        mock_log_service.start_log = AsyncMock(side_effect=Exception("Log error"))

        with patch("scraper.scraper_job.ScraperLock", return_value=mock_lock):
            with patch("scraper.scraper_job.ScraperLogService", return_value=mock_log_service):
                with patch("scraper.scraper_job.ScraperService", return_value=mock_scraper_service):
                    job = ScraperJob(test_college, mock_db)

                    result = await job.execute()

                    # Job should still succeed despite log error
                    assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_unexpected_exception(
        self, test_college, mock_db, mock_log_service
    ):
        """Test handling of unexpected exceptions"""
        mock_lock = Mock()
        mock_lock.get_scraper_id = Mock(return_value=1)
        mock_lock.acquire = Mock(return_value=LockResult(success=True))
        mock_lock.release = Mock()

        # Make the service raise an exception
        mock_scraper_service = AsyncMock()
        mock_scraper_service.scrape_college = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with patch("scraper.scraper_job.ScraperLock", return_value=mock_lock):
            with patch("scraper.scraper_job.ScraperLogService", return_value=mock_log_service):
                with patch("scraper.scraper_job.ScraperService", return_value=mock_scraper_service):
                    job = ScraperJob(test_college, mock_db)

                    # Should not raise exception, should return failure
                    result = await job.execute()

                    assert result.success is False
                    assert "Unexpected error" in result.error


# ============================================================================
# Helper Methods Tests
# ============================================================================


class TestHelperMethods:
    """Test helper methods (can_run, cleanup, etc.)"""

    def test_can_run_lock_available(self, test_college, mock_db, mock_lock):
        """Test can_run when lock is available"""
        with patch("scraper.scraper_job.ScraperLock", return_value=mock_lock):
            job = ScraperJob(test_college, mock_db)

            can_run = job.can_run()

            assert can_run is True
            mock_lock.acquire.assert_called_once()
            mock_lock.release.assert_called_once_with("idle")

    def test_can_run_lock_unavailable(self, test_college, mock_db):
        """Test can_run when lock is not available"""
        mock_lock = Mock()
        mock_lock.acquire = Mock(return_value=LockResult(success=False))

        with patch("scraper.scraper_job.ScraperLock", return_value=mock_lock):
            job = ScraperJob(test_college, mock_db)

            can_run = job.can_run()

            assert can_run is False
            mock_lock.release.assert_not_called()

    def test_cleanup(self, test_college, mock_db, mock_lock):
        """Test cleanup releases resources"""
        with patch("scraper.scraper_job.ScraperLock", return_value=mock_lock):
            job = ScraperJob(test_college, mock_db)

            job.cleanup()

            mock_lock.cleanup.assert_called_once()

    def test_cleanup_idempotent(self, test_college, mock_db, mock_lock):
        """Test cleanup can be called multiple times safely"""
        with patch("scraper.scraper_job.ScraperLock", return_value=mock_lock):
            job = ScraperJob(test_college, mock_db)

            job.cleanup()
            job.cleanup()
            job.cleanup()

            assert mock_lock.cleanup.call_count == 3


# ============================================================================
# Integration Tests
# ============================================================================


class TestScraperJobIntegration:
    """Integration tests for complete workflows"""

    @pytest.mark.asyncio
    async def test_full_successful_workflow(
        self, test_college, mock_db, mock_lock, mock_log_service, mock_scraper_service
    ):
        """Test complete successful workflow from start to finish"""
        with patch("scraper.scraper_job.ScraperLock", return_value=mock_lock):
            with patch("scraper.scraper_job.ScraperLogService", return_value=mock_log_service):
                with patch("scraper.scraper_job.ScraperService", return_value=mock_scraper_service):
                    job = ScraperJob(test_college, mock_db)

                    # Verify can run
                    assert job.can_run() is True

                    # Execute
                    result = await job.execute()

                    # Verify success
                    assert result.success is True
                    assert result.duration_ms >= 0  # Can be 0 in fast tests
                    assert result.stats["courses_saved"] == 10

                    # Cleanup
                    job.cleanup()

                    # Verify all interactions
                    mock_log_service.start_log.assert_called_once()
                    mock_log_service.complete_log.assert_called_once()
                    mock_scraper_service.scrape_college.assert_called_once()
                    mock_lock.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_retry_workflow(
        self, test_college, mock_db, mock_lock, mock_log_service
    ):
        """Test complete workflow with retries"""
        mock_scraper_service = AsyncMock()
        # Fail twice, then succeed
        mock_scraper_service.scrape_college = AsyncMock(
            side_effect=[
                {"success": False, "error": "Temp error 1"},
                {"success": False, "error": "Temp error 2"},
                {"success": True, "courses_saved": 15, "classes_saved": 75},
            ]
        )

        config = JobConfig(retry_attempts=3, retry_delay_ms=10)

        with patch("scraper.scraper_job.ScraperLock", return_value=mock_lock):
            with patch("scraper.scraper_job.ScraperLogService", return_value=mock_log_service):
                with patch("scraper.scraper_job.ScraperService", return_value=mock_scraper_service):
                    job = ScraperJob(test_college, mock_db, config)

                    result = await job.execute()

                    assert result.success is True
                    assert mock_scraper_service.scrape_college.call_count == 3
                    # Verify stats from successful (3rd) attempt
                    assert result.stats["courses_saved"] == 15
                    assert result.stats["classes_saved"] == 75
