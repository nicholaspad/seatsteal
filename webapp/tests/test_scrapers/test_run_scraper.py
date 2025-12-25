"""
Comprehensive test suite for scraper/run_scraper.py

Tests scraper CLI and job management including:
- ScraperCLI initialization
- Single job execution with filters
- Parallel job execution
- College lookup and validation
- Database session management
- Error handling and recovery
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from sqlalchemy.orm import Session

from scraper.run_scraper import ScraperCLI
from scraper.scraper_job import JobResult, JobConfig
from models.college import College


# Test fixtures
@pytest.fixture
def test_college():
    """Create a test college"""
    return College(id=1, name="Test University", short_name="test", is_active=True)


@pytest.fixture
def inactive_college():
    """Create an inactive college"""
    return College(id=2, name="Inactive University", short_name="inactive", is_active=False)


@pytest.fixture
def mock_db():
    """Create a mock database session"""
    db = Mock(spec=Session)
    db.execute = Mock()
    db.commit = Mock()
    db.close = Mock()
    return db


@pytest.fixture
def mock_session_local(mock_db):
    """Mock SessionLocal context manager"""
    mock = MagicMock()
    mock.__enter__ = Mock(return_value=mock_db)
    mock.__exit__ = Mock(return_value=False)
    return mock


@pytest.fixture
def mock_scraper_job():
    """Mock ScraperJob with successful result"""
    job = Mock()
    job.execute = AsyncMock(
        return_value=JobResult(
            success=True,
            stats={"courses_saved": 10, "classes_saved": 50, "enrollments_saved": 200},
            duration_ms=5000,
        )
    )
    job.cleanup = Mock()
    return job


# ============================================================================
# ScraperCLI Initialization Tests
# ============================================================================


class TestScraperCLIInitialization:
    """Test ScraperCLI initialization"""

    def test_scraper_cli_initialization(self):
        """Test basic CLI initialization"""
        cli = ScraperCLI()

        assert cli.loop_interval_seconds == 300

    def test_scraper_cli_default_interval(self):
        """Test default loop interval is 5 minutes"""
        cli = ScraperCLI()

        assert cli.loop_interval_seconds == 300  # 5 minutes


# ============================================================================
# run_job Tests
# ============================================================================


class TestRunJob:
    """Test run_job method"""

    @pytest.mark.asyncio
    async def test_run_job_success(self, test_college, mock_db):
        """Test successful job execution"""
        # Mock database query
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=test_college)
        mock_db.execute = Mock(return_value=mock_result)

        # Mock ScraperJob
        mock_job = Mock()
        mock_job.execute = AsyncMock(
            return_value=JobResult(
                success=True,
                stats={"courses_saved": 15, "classes_saved": 75},
                duration_ms=3000,
            )
        )
        mock_job.cleanup = Mock()

        with patch("scraper.run_scraper.SessionLocal", return_value=MagicMock(__enter__=Mock(return_value=mock_db), __exit__=Mock())):
            with patch("scraper.run_scraper.ScraperJob", return_value=mock_job):
                cli = ScraperCLI()
                result = await cli.run_job("test")

                assert result is True
                mock_job.execute.assert_called_once()
                mock_job.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_job_college_not_found(self, mock_db):
        """Test handling of non-existent college"""
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute = Mock(return_value=mock_result)

        with patch("scraper.run_scraper.SessionLocal", return_value=MagicMock(__enter__=Mock(return_value=mock_db), __exit__=Mock())):
            cli = ScraperCLI()
            result = await cli.run_job("nonexistent")

            assert result is False

    @pytest.mark.asyncio
    async def test_run_job_inactive_college(self, inactive_college, mock_db):
        """Test handling of inactive college"""
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=inactive_college)
        mock_db.execute = Mock(return_value=mock_result)

        with patch("scraper.run_scraper.SessionLocal", return_value=MagicMock(__enter__=Mock(return_value=mock_db), __exit__=Mock())):
            cli = ScraperCLI()
            result = await cli.run_job("inactive")

            assert result is False

    @pytest.mark.asyncio
    async def test_run_job_with_subject_filter(self, test_college, mock_db):
        """Test job execution with subject filter"""
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=test_college)
        mock_db.execute = Mock(return_value=mock_result)

        mock_job = Mock()
        mock_job.execute = AsyncMock(return_value=JobResult(success=True))
        mock_job.cleanup = Mock()

        with patch("scraper.run_scraper.SessionLocal", return_value=MagicMock(__enter__=Mock(return_value=mock_db), __exit__=Mock())):
            with patch("scraper.run_scraper.ScraperJob", return_value=mock_job) as MockJob:
                cli = ScraperCLI()
                await cli.run_job("test", subject="CS")

                # Verify JobConfig passed with subject
                call_args = MockJob.call_args
                config = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("config")
                assert config.subject == "CS"

    @pytest.mark.asyncio
    async def test_run_job_with_limit(self, test_college, mock_db):
        """Test job execution with limit"""
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=test_college)
        mock_db.execute = Mock(return_value=mock_result)

        mock_job = Mock()
        mock_job.execute = AsyncMock(return_value=JobResult(success=True))
        mock_job.cleanup = Mock()

        with patch("scraper.run_scraper.SessionLocal", return_value=MagicMock(__enter__=Mock(return_value=mock_db), __exit__=Mock())):
            with patch("scraper.run_scraper.ScraperJob", return_value=mock_job) as MockJob:
                cli = ScraperCLI()
                await cli.run_job("test", limit=100)

                call_args = MockJob.call_args
                config = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("config")
                assert config.limit == 100

    @pytest.mark.asyncio
    async def test_run_job_failure(self, test_college, mock_db):
        """Test handling of job failure"""
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=test_college)
        mock_db.execute = Mock(return_value=mock_result)

        mock_job = Mock()
        mock_job.execute = AsyncMock(
            return_value=JobResult(success=False, error="Scraping failed")
        )
        mock_job.cleanup = Mock()

        with patch("scraper.run_scraper.SessionLocal", return_value=MagicMock(__enter__=Mock(return_value=mock_db), __exit__=Mock())):
            with patch("scraper.run_scraper.ScraperJob", return_value=mock_job):
                cli = ScraperCLI()
                result = await cli.run_job("test")

                assert result is False
                mock_job.cleanup.assert_called_once()


# ============================================================================
# _run_single_job Tests
# ============================================================================


class TestRunSingleJob:
    """Test _run_single_job internal method"""

    @pytest.mark.asyncio
    async def test_run_single_job_success(self, test_college, mock_db):
        """Test successful single job execution"""
        mock_job = Mock()
        mock_job.execute = AsyncMock(return_value=JobResult(success=True))
        mock_job.cleanup = Mock()

        with patch("scraper.run_scraper.SessionLocal", return_value=MagicMock(__enter__=Mock(return_value=mock_db), __exit__=Mock())):
            with patch("scraper.run_scraper.ScraperJob", return_value=mock_job):
                cli = ScraperCLI()
                result = await cli._run_single_job(test_college)

                assert result is True
                mock_job.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_single_job_exception(self, test_college, mock_db):
        """Test handling of exceptions in single job"""
        mock_job = Mock()
        mock_job.execute = AsyncMock(side_effect=Exception("Unexpected error"))

        with patch("scraper.run_scraper.SessionLocal", return_value=MagicMock(__enter__=Mock(return_value=mock_db), __exit__=Mock())):
            with patch("scraper.run_scraper.ScraperJob", return_value=mock_job):
                cli = ScraperCLI()
                result = await cli._run_single_job(test_college)

                assert result is False


# ============================================================================
# run_all_jobs Tests
# ============================================================================


class TestRunAllJobs:
    """Test run_all_jobs parallel execution"""

    @pytest.mark.asyncio
    async def test_run_all_jobs_success(self, mock_db):
        """Test parallel execution of all jobs"""
        colleges = [
            College(id=1, name="College 1", short_name="c1", is_active=True),
            College(id=2, name="College 2", short_name="c2", is_active=True),
            College(id=3, name="College 3", short_name="c3", is_active=True),
        ]

        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=colleges)))
        mock_db.execute = Mock(return_value=mock_result)

        with patch("scraper.run_scraper.SessionLocal", return_value=MagicMock(__enter__=Mock(return_value=mock_db), __exit__=Mock())):
            with patch.object(ScraperCLI, "_run_single_job", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = True

                cli = ScraperCLI()
                result = await cli.run_all_jobs()

                assert result["total"] == 3
                assert result["successful"] == 3
                assert result["failed"] == 0
                assert mock_run.call_count == 3

    @pytest.mark.asyncio
    async def test_run_all_jobs_with_failures(self, mock_db):
        """Test parallel execution with some failures"""
        colleges = [
            College(id=1, name="College 1", short_name="c1", is_active=True),
            College(id=2, name="College 2", short_name="c2", is_active=True),
            College(id=3, name="College 3", short_name="c3", is_active=True),
        ]

        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=colleges)))
        mock_db.execute = Mock(return_value=mock_result)

        with patch("scraper.run_scraper.SessionLocal", return_value=MagicMock(__enter__=Mock(return_value=mock_db), __exit__=Mock())):
            with patch.object(ScraperCLI, "_run_single_job", new_callable=AsyncMock) as mock_run:
                # 2 success, 1 failure
                mock_run.side_effect = [True, False, True]

                cli = ScraperCLI()
                result = await cli.run_all_jobs()

                assert result["total"] == 3
                assert result["successful"] == 2
                assert result["failed"] == 1

    @pytest.mark.asyncio
    async def test_run_all_jobs_no_colleges(self, mock_db):
        """Test handling of no active colleges"""
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))
        mock_db.execute = Mock(return_value=mock_result)

        with patch("scraper.run_scraper.SessionLocal", return_value=MagicMock(__enter__=Mock(return_value=mock_db), __exit__=Mock())):
            cli = ScraperCLI()
            result = await cli.run_all_jobs()

            assert result["total"] == 0
            assert result["successful"] == 0
            assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_run_all_jobs_with_subject_filter(self, mock_db):
        """Test parallel execution with subject filter"""
        colleges = [College(id=1, name="College 1", short_name="c1", is_active=True)]

        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=colleges)))
        mock_db.execute = Mock(return_value=mock_result)

        with patch("scraper.run_scraper.SessionLocal", return_value=MagicMock(__enter__=Mock(return_value=mock_db), __exit__=Mock())):
            with patch.object(ScraperCLI, "_run_single_job", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = True

                cli = ScraperCLI()
                await cli.run_all_jobs(subject="MATH")

                # Verify subject passed to _run_single_job
                mock_run.assert_called_once()
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs.get("subject") == "MATH"

    @pytest.mark.asyncio
    async def test_run_all_jobs_exception_handling(self, mock_db):
        """Test that exceptions in one job don't affect others"""
        colleges = [
            College(id=1, name="College 1", short_name="c1", is_active=True),
            College(id=2, name="College 2", short_name="c2", is_active=True),
        ]

        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=colleges)))
        mock_db.execute = Mock(return_value=mock_result)

        with patch("scraper.run_scraper.SessionLocal", return_value=MagicMock(__enter__=Mock(return_value=mock_db), __exit__=Mock())):
            with patch.object(ScraperCLI, "_run_single_job", new_callable=AsyncMock) as mock_run:
                # First raises exception (caught by gather), second succeeds
                mock_run.side_effect = [Exception("Error in job 1"), True]

                cli = ScraperCLI()
                result = await cli.run_all_jobs()

                # Should handle exception gracefully
                assert result["total"] == 2
                assert result["successful"] == 1  # Only the second succeeded


# ============================================================================
# Session Management Tests
# ============================================================================


class TestSessionManagement:
    """Test database session management"""

    @pytest.mark.asyncio
    async def test_run_job_session_cleanup(self, test_college, mock_db):
        """Test that database sessions are properly cleaned up"""
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=test_college)
        mock_db.execute = Mock(return_value=mock_result)

        mock_context = MagicMock()
        mock_context.__enter__ = Mock(return_value=mock_db)
        mock_context.__exit__ = Mock(return_value=False)

        mock_job = Mock()
        mock_job.execute = AsyncMock(return_value=JobResult(success=True))
        mock_job.cleanup = Mock()

        with patch("scraper.run_scraper.SessionLocal", return_value=mock_context):
            with patch("scraper.run_scraper.ScraperJob", return_value=mock_job):
                cli = ScraperCLI()
                await cli.run_job("test")

                # Verify context manager was used (session cleaned up)
                mock_context.__exit__.assert_called()

    @pytest.mark.asyncio
    async def test_run_single_job_separate_session(self, test_college, mock_db):
        """Test that each job gets its own database session"""
        mock_context = MagicMock()
        mock_context.__enter__ = Mock(return_value=mock_db)
        mock_context.__exit__ = Mock(return_value=False)

        mock_job = Mock()
        mock_job.execute = AsyncMock(return_value=JobResult(success=True))
        mock_job.cleanup = Mock()

        with patch("scraper.run_scraper.SessionLocal", return_value=mock_context) as MockSession:
            with patch("scraper.run_scraper.ScraperJob", return_value=mock_job):
                cli = ScraperCLI()
                await cli._run_single_job(test_college)

                # Should create new session
                MockSession.assert_called()
                mock_context.__exit__.assert_called()


# ============================================================================
# Configuration Tests
# ============================================================================


class TestConfiguration:
    """Test configuration propagation"""

    @pytest.mark.asyncio
    async def test_run_job_skip_lock_enabled(self, test_college, mock_db):
        """Test that CLI runs use skip_lock=True"""
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=test_college)
        mock_db.execute = Mock(return_value=mock_result)

        with patch("scraper.run_scraper.SessionLocal", return_value=MagicMock(__enter__=Mock(return_value=mock_db), __exit__=Mock())):
            with patch("scraper.run_scraper.ScraperJob") as MockJob:
                mock_job = Mock()
                mock_job.execute = AsyncMock(return_value=JobResult(success=True))
                mock_job.cleanup = Mock()
                MockJob.return_value = mock_job

                cli = ScraperCLI()
                await cli.run_job("test")

                # Verify skip_lock=True in config
                call_args = MockJob.call_args
                config = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("config")
                assert config.skip_lock is True

    @pytest.mark.asyncio
    async def test_run_job_config_parameters(self, test_college, mock_db):
        """Test all config parameters are passed correctly"""
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=test_college)
        mock_db.execute = Mock(return_value=mock_result)

        with patch("scraper.run_scraper.SessionLocal", return_value=MagicMock(__enter__=Mock(return_value=mock_db), __exit__=Mock())):
            with patch("scraper.run_scraper.ScraperJob") as MockJob:
                mock_job = Mock()
                mock_job.execute = AsyncMock(return_value=JobResult(success=True))
                mock_job.cleanup = Mock()
                MockJob.return_value = mock_job

                cli = ScraperCLI()
                await cli.run_job("test", subject="CS", limit=500)

                call_args = MockJob.call_args
                config = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("config")
                assert config.subject == "CS"
                assert config.limit == 500
                assert config.skip_lock is True


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for complete workflows"""

    @pytest.mark.asyncio
    async def test_full_single_job_workflow(self, test_college, mock_db):
        """Test complete workflow for single job"""
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=test_college)
        mock_db.execute = Mock(return_value=mock_result)

        mock_job = Mock()
        mock_job.execute = AsyncMock(
            return_value=JobResult(
                success=True,
                stats={"courses_saved": 20, "classes_saved": 100, "enrollments_saved": 500},
                duration_ms=8000,
            )
        )
        mock_job.cleanup = Mock()

        with patch("scraper.run_scraper.SessionLocal", return_value=MagicMock(__enter__=Mock(return_value=mock_db), __exit__=Mock())):
            with patch("scraper.run_scraper.ScraperJob", return_value=mock_job):
                cli = ScraperCLI()
                result = await cli.run_job("test", subject="ALL", limit=1000)

                assert result is True
                mock_job.execute.assert_called_once()
                mock_job.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_parallel_workflow(self, mock_db):
        """Test complete parallel execution workflow"""
        colleges = [
            College(id=i, name=f"College {i}", short_name=f"c{i}", is_active=True)
            for i in range(1, 6)
        ]

        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=colleges)))
        mock_db.execute = Mock(return_value=mock_result)

        with patch("scraper.run_scraper.SessionLocal", return_value=MagicMock(__enter__=Mock(return_value=mock_db), __exit__=Mock())):
            with patch.object(ScraperCLI, "_run_single_job", new_callable=AsyncMock) as mock_run:
                # 4 succeed, 1 fails
                mock_run.side_effect = [True, True, False, True, True]

                cli = ScraperCLI()
                result = await cli.run_all_jobs(subject="ALL")

                assert result["total"] == 5
                assert result["successful"] == 4
                assert result["failed"] == 1
                assert mock_run.call_count == 5
