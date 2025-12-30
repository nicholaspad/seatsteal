"""Tests for University of Maryland course scraper."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from sqlalchemy.orm import Session

import sys
from pathlib import Path

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from scraper.scrapers.umd import UmdScraper
from models.college import College


# Sample UMD API response data
SAMPLE_UMD_COURSES_LIST = ["CMSC131", "CMSC132", "MATH140", "ENGL101"]

SAMPLE_UMD_COURSE_DETAILS = {
    "course_id": "CMSC131",
    "name": "Object-Oriented Programming I",
    "dept_id": "CMSC",
    "department": "Computer Science",
    "semester": "202408",
    "credits": "4",
    "description": "Introduction to programming and computer science.",
    "sections": [
        {
            "section_id": "CMSC131-0101",
            "number": "0101",
            "seats": "30",
            "open_seats": "5",
            "waitlist": "0",
            "instructors": ["John Doe"],
        },
        {
            "section_id": "CMSC131-0102",
            "number": "0102",
            "seats": "30",
            "open_seats": "0",
            "waitlist": "5",
            "instructors": ["Jane Smith"],
        },
    ],
}

SAMPLE_UMD_DEPARTMENT_COURSES = [
    {
        "course_id": "CMSC131",
        "name": "Object-Oriented Programming I",
        "dept_id": "CMSC",
        "semester": "202408",
    },
    {
        "course_id": "CMSC132",
        "name": "Object-Oriented Programming II",
        "dept_id": "CMSC",
        "semester": "202408",
    },
]


@pytest.fixture
def mock_umd_db_session():
    """Create a mock database session for UMD scraper."""
    mock_session = MagicMock(spec=Session)
    mock_college = College(
        id=1,
        name="University of Maryland",
        short_name="umd",
        term_code="202408",
        term_name="Fall 2024",
        is_active=True,
    )

    # Mock the query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_college
    mock_session.execute.return_value = mock_result

    return mock_session


class TestUmdScraper:
    """Tests for UmdScraper class."""

    @pytest.mark.unit
    def test_init_sets_college_short_name(self, mock_umd_db_session):
        """Test that scraper initializes with correct college."""
        with patch("scraper.scrapers.umd.get_term_code_from_db", return_value="202408"):
            scraper = UmdScraper(db_session=mock_umd_db_session)
            assert scraper.college_short_name == "umd"

    @pytest.mark.unit
    def test_init_sets_current_term(self, mock_umd_db_session):
        """Test that scraper fetches current term from database."""
        with patch("scraper.scrapers.umd.get_term_code_from_db", return_value="202408"):
            scraper = UmdScraper(db_session=mock_umd_db_session)
            assert scraper.current_term == "202408"

    @pytest.mark.unit
    async def test_ensure_client_creates_client(self, mock_umd_db_session):
        """Test that HTTP client is created when needed."""
        scraper = UmdScraper(db_session=mock_umd_db_session)
        assert scraper.client is None

        await scraper._ensure_client()

        assert scraper.client is not None
        assert scraper.client.timeout.read == 30.0
        await scraper.client.aclose()

    @pytest.mark.unit
    async def test_scrape_courses_single_department(self, mock_umd_db_session):
        """Test scraping courses for a single department."""
        scraper = UmdScraper(db_session=mock_umd_db_session)

        # Mock API responses
        mock_response = MagicMock()
        mock_response.json.return_value = [SAMPLE_UMD_COURSE_DETAILS]

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            scraper.client = mock_client

            courses = await scraper.scrape_courses("CMSC", limit=10)

            assert len(courses) > 0
            mock_client.get.assert_called()
            assert scraper.request_count > 0

    @pytest.mark.unit
    async def test_scrape_courses_all_departments(self, mock_umd_db_session):
        """Test scraping all courses across all departments."""
        scraper = UmdScraper(db_session=mock_umd_db_session)

        # Mock courses list API response
        mock_list_response = MagicMock()
        mock_list_response.json.return_value = SAMPLE_UMD_COURSES_LIST
        mock_list_response.raise_for_status = MagicMock()

        # Mock course details API response
        mock_details_response = MagicMock()
        mock_details_response.json.return_value = SAMPLE_UMD_COURSE_DETAILS
        mock_details_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()

            # First call returns list, subsequent calls return details
            mock_client.get.side_effect = [
                mock_list_response,
                mock_details_response,
                mock_details_response,
            ]
            mock_client_class.return_value = mock_client

            scraper.client = mock_client

            courses = await scraper.scrape_courses("ALL", limit=2)

            # Should have made at least one API call
            assert mock_client.get.call_count >= 1

    @pytest.mark.unit
    async def test_scrape_courses_with_limit(self, mock_umd_db_session):
        """Test that limit parameter restricts number of courses."""
        scraper = UmdScraper(db_session=mock_umd_db_session)

        mock_list_response = MagicMock()
        mock_list_response.json.return_value = SAMPLE_UMD_COURSES_LIST
        mock_list_response.raise_for_status = MagicMock()

        mock_details_response = MagicMock()
        mock_details_response.json.return_value = SAMPLE_UMD_COURSE_DETAILS
        mock_details_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = [
                mock_list_response,
                mock_details_response,
                mock_details_response,
            ]
            mock_client_class.return_value = mock_client

            scraper.client = mock_client

            # Limit to 2 courses
            courses = await scraper.scrape_courses("ALL", limit=2)

            # Should respect the limit
            assert len(courses) <= 2

    @pytest.mark.unit
    async def test_scrape_courses_network_error(self, mock_umd_db_session):
        """Test handling of network errors during scraping."""
        scraper = UmdScraper(db_session=mock_umd_db_session)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Network error")
            mock_client_class.return_value = mock_client

            scraper.client = mock_client

            with pytest.raises(Exception, match="Network error"):
                await scraper.scrape_courses("CMSC")

    @pytest.mark.unit
    async def test_scrape_courses_api_error(self, mock_umd_db_session):
        """Test handling of API errors (non-200 status)."""
        scraper = UmdScraper(db_session=mock_umd_db_session)

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("404 Not Found")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            scraper.client = mock_client

            with pytest.raises(Exception):
                await scraper.scrape_courses("CMSC")

    @pytest.mark.unit
    async def test_fetch_department_courses(self, mock_umd_db_session):
        """Test fetching courses for a specific department."""
        scraper = UmdScraper(db_session=mock_umd_db_session)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_UMD_DEPARTMENT_COURSES
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            scraper.client = mock_client

            courses = await scraper._fetch_department_courses("CMSC", limit=None)

            # Should have called the courses API
            mock_client.get.assert_called()
            call_args = mock_client.get.call_args
            assert "courses" in call_args[0][0]

    @pytest.mark.unit
    async def test_fetch_all_courses(self, mock_umd_db_session):
        """Test fetching all courses."""
        scraper = UmdScraper(db_session=mock_umd_db_session)

        mock_list_response = MagicMock()
        mock_list_response.json.return_value = SAMPLE_UMD_COURSES_LIST
        mock_list_response.raise_for_status = MagicMock()

        mock_details_response = MagicMock()
        mock_details_response.json.return_value = SAMPLE_UMD_COURSE_DETAILS
        mock_details_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = [
                mock_list_response,
                mock_details_response,
                mock_details_response,
            ]
            mock_client_class.return_value = mock_client

            scraper.client = mock_client

            courses = await scraper._fetch_all_courses(limit=2)

            # Should have called the list API first
            first_call = mock_client.get.call_args_list[0]
            assert "courses/list" in first_call[0][0]

    @pytest.mark.unit
    async def test_client_cleanup_on_error(self, mock_umd_db_session):
        """Test that HTTP client is properly closed even on error."""
        scraper = UmdScraper(db_session=mock_umd_db_session)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Test error")
            mock_client_class.return_value = mock_client

            scraper.client = mock_client

            with pytest.raises(Exception):
                await scraper.scrape_courses("CMSC")

            # Client should be closed and set to None
            mock_client.aclose.assert_called_once()
            assert scraper.client is None

    @pytest.mark.unit
    async def test_request_count_increments(self, mock_umd_db_session):
        """Test that request count is tracked correctly."""
        scraper = UmdScraper(db_session=mock_umd_db_session)
        initial_count = scraper.request_count

        mock_list_response = MagicMock()
        mock_list_response.json.return_value = ["CMSC131"]
        mock_list_response.raise_for_status = MagicMock()

        mock_details_response = MagicMock()
        mock_details_response.json.return_value = SAMPLE_UMD_COURSE_DETAILS
        mock_details_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = [mock_list_response, mock_details_response]
            mock_client_class.return_value = mock_client

            scraper.client = mock_client

            await scraper.scrape_courses("ALL", limit=1)

            # Request count should have increased
            assert scraper.request_count > initial_count

    @pytest.mark.unit
    async def test_empty_course_list(self, mock_umd_db_session):
        """Test handling of empty course list."""
        scraper = UmdScraper(db_session=mock_umd_db_session)

        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            scraper.client = mock_client

            courses = await scraper._fetch_all_courses(limit=None)

            assert courses == []

    @pytest.mark.unit
    async def test_course_with_no_sections(self, mock_umd_db_session):
        """Test handling of courses with no sections."""
        scraper = UmdScraper(db_session=mock_umd_db_session)

        course_no_sections = {
            "course_id": "CMSC999",
            "name": "Test Course",
            "dept_id": "CMSC",
            "sections": [],
        }

        mock_response = MagicMock()
        mock_response.json.return_value = [course_no_sections]
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            scraper.client = mock_client

            # Should handle courses with no sections gracefully
            courses = await scraper._fetch_department_courses("CMSC", limit=None)

            # Depending on implementation, may return empty or filtered list
            assert isinstance(courses, list)
