"""Tests for Rutgers University course scraper."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from sqlalchemy.orm import Session

import sys
from pathlib import Path

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from scraper.scrapers.rutgers import RutgersScraper
from models.college import College


# Sample Rutgers API response data
SAMPLE_RUTGERS_COURSES = [
    {
        "courseString": "01:198:111",
        "title": "INTRO TO COMPUTER SCI",
        "subject": "198",
        "courseNumber": "111",
        "school": {"code": "01", "description": "School of Arts and Sciences"},
        "subjectDescription": "Computer Science",
        "sections": [
            {
                "index": "10001",
                "number": "01",
                "openStatus": True,
                "openStatusText": "OPEN",
                "instructors": [{"name": "Smith, John"}],
            },
            {
                "index": "10002",
                "number": "02",
                "openStatus": False,
                "openStatusText": "CLOSED",
                "instructors": [{"name": "Doe, Jane"}],
            },
        ],
    },
    {
        "courseString": "01:198:112",
        "title": "DATA STRUCTURES",
        "subject": "198",
        "courseNumber": "112",
        "school": {"code": "01", "description": "School of Arts and Sciences"},
        "subjectDescription": "Computer Science",
        "sections": [
            {
                "index": "10003",
                "number": "01",
                "openStatus": True,
                "openStatusText": "OPEN",
                "instructors": [],
            },
        ],
    },
    {
        "courseString": "01:640:151",
        "title": "CALC I FOR MATH & SCI",
        "subject": "640",
        "courseNumber": "151",
        "school": {"code": "01", "description": "School of Arts and Sciences"},
        "subjectDescription": "Mathematics",
        "sections": [
            {
                "index": "20001",
                "number": "01",
                "openStatus": False,
                "openStatusText": "CLOSED",
                "instructors": [{"name": "Math, Prof"}],
            },
        ],
    },
]


@pytest.fixture
def mock_rutgers_db_session():
    """Create a mock database session for Rutgers scraper."""
    mock_session = MagicMock(spec=Session)
    mock_college = College(
        id=1,
        name="Rutgers University",
        short_name="rutgers",
        term_code="2025:9:NB",
        term_name="Fall 2025",
        is_active=True,
    )

    # Mock the query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_college
    mock_session.execute.return_value = mock_result

    return mock_session


class TestRutgersScraper:
    """Tests for RutgersScraper class."""

    @pytest.mark.unit
    def test_init_parses_term_code(self, mock_rutgers_db_session):
        """Test that scraper correctly parses term code from database."""
        scraper = RutgersScraper(mock_rutgers_db_session)

        assert scraper.college_short_name == "rutgers"
        assert scraper.year == "2025"
        assert scraper.term == "9"
        assert scraper.campus == "NB"

    @pytest.mark.unit
    def test_init_invalid_term_code_format(self, mock_rutgers_db_session):
        """Test that scraper raises error for invalid term code format."""
        mock_college = College(
            id=1,
            name="Rutgers University",
            short_name="rutgers",
            term_code="invalid",  # Invalid format
            term_name="Fall 2025",
            is_active=True,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_college
        mock_rutgers_db_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Invalid Rutgers term code format"):
            RutgersScraper(mock_rutgers_db_session)

    @pytest.mark.unit
    def test_transform_single_course(self, mock_rutgers_db_session):
        """Test transformation of a single course from Rutgers API format."""
        scraper = RutgersScraper(mock_rutgers_db_session)

        raw_course = SAMPLE_RUTGERS_COURSES[0]
        result = scraper._transform_single_course(raw_course)

        assert result is not None
        assert result["course_code"] == "01:198:111"
        assert result["title"] == "INTRO TO COMPUTER SCI"
        assert len(result["classes"]) == 2

        # Check first section (open)
        assert result["classes"][0]["class_number"] == "10001"
        assert result["classes"][0]["section"] == "01"
        assert result["classes"][0]["status"] == "open"

        # Check second section (closed)
        assert result["classes"][1]["class_number"] == "10002"
        assert result["classes"][1]["section"] == "02"
        assert result["classes"][1]["status"] == "closed"

    @pytest.mark.unit
    def test_transform_section_open(self, mock_rutgers_db_session):
        """Test transformation of an open section."""
        scraper = RutgersScraper(mock_rutgers_db_session)

        section = {
            "index": "12345",
            "number": "01",
            "openStatus": True,
            "openStatusText": "OPEN",
        }
        result = scraper._transform_section(section)

        assert result is not None
        assert result["class_number"] == "12345"
        assert result["section"] == "01"
        assert result["status"] == "open"

    @pytest.mark.unit
    def test_transform_section_closed(self, mock_rutgers_db_session):
        """Test transformation of a closed section."""
        scraper = RutgersScraper(mock_rutgers_db_session)

        section = {
            "index": "12346",
            "number": "02",
            "openStatus": False,
            "openStatusText": "CLOSED",
        }
        result = scraper._transform_section(section)

        assert result is not None
        assert result["class_number"] == "12346"
        assert result["section"] == "02"
        assert result["status"] == "closed"

    @pytest.mark.unit
    def test_transform_section_missing_index(self, mock_rutgers_db_session):
        """Test that section without index is skipped."""
        scraper = RutgersScraper(mock_rutgers_db_session)

        section = {
            "number": "01",
            "openStatus": True,
        }
        result = scraper._transform_section(section)

        assert result is None

    @pytest.mark.unit
    def test_transform_courses_with_limit(self, mock_rutgers_db_session):
        """Test transformation with course limit."""
        scraper = RutgersScraper(mock_rutgers_db_session)

        result = scraper._transform_courses(SAMPLE_RUTGERS_COURSES, limit=2)

        assert len(result) == 2
        assert result[0]["course_code"] == "01:198:111"
        assert result[1]["course_code"] == "01:198:112"

    @pytest.mark.unit
    def test_transform_courses_filters_by_subject(self, mock_rutgers_db_session):
        """Test filtering courses by subject code."""
        scraper = RutgersScraper(mock_rutgers_db_session)

        # Filter to only CS courses (subject 198)
        cs_courses = [c for c in SAMPLE_RUTGERS_COURSES if c.get("subject") == "198"]
        result = scraper._transform_courses(cs_courses, limit=None)

        assert len(result) == 2
        assert all("198" in c["course_code"] for c in result)

    @pytest.mark.unit
    def test_transform_course_without_sections(self, mock_rutgers_db_session):
        """Test that course without sections returns None."""
        scraper = RutgersScraper(mock_rutgers_db_session)

        raw_course = {
            "courseString": "01:198:999",
            "title": "NO SECTIONS COURSE",
            "subject": "198",
            "sections": [],
        }
        result = scraper._transform_single_course(raw_course)

        assert result is None

    @pytest.mark.unit
    def test_transform_course_without_course_string(self, mock_rutgers_db_session):
        """Test that course without courseString returns None."""
        scraper = RutgersScraper(mock_rutgers_db_session)

        raw_course = {
            "title": "MISSING CODE",
            "subject": "198",
            "sections": [{"index": "12345", "number": "01", "openStatus": True}],
        }
        result = scraper._transform_single_course(raw_course)

        assert result is None

    @pytest.mark.unit
    async def test_scrape_courses_all(self, mock_rutgers_db_session):
        """Test scraping all courses."""
        scraper = RutgersScraper(mock_rutgers_db_session)

        # Mock the HTTP client and response
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_RUTGERS_COURSES
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        result = await scraper.scrape_courses("ALL")

        assert len(result) == 3
        assert result[0]["course_code"] == "01:198:111"
        assert result[1]["course_code"] == "01:198:112"
        assert result[2]["course_code"] == "01:640:151"

    @pytest.mark.unit
    async def test_scrape_courses_by_department(self, mock_rutgers_db_session):
        """Test scraping courses for specific department."""
        scraper = RutgersScraper(mock_rutgers_db_session)

        # Mock the HTTP client and response
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_RUTGERS_COURSES
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        # Request only CS courses (subject 198)
        result = await scraper.scrape_courses("198")

        assert len(result) == 2
        assert all("198" in c["course_code"] for c in result)

    @pytest.mark.unit
    async def test_scrape_courses_with_limit(self, mock_rutgers_db_session):
        """Test scraping with course limit."""
        scraper = RutgersScraper(mock_rutgers_db_session)

        # Mock the HTTP client and response
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_RUTGERS_COURSES
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        result = await scraper.scrape_courses("ALL", limit=1)

        assert len(result) == 1

    @pytest.mark.unit
    async def test_fetch_all_courses_builds_correct_url(self, mock_rutgers_db_session):
        """Test that API request uses correct URL and parameters."""
        scraper = RutgersScraper(mock_rutgers_db_session)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_RUTGERS_COURSES
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        await scraper._fetch_all_courses()

        # Verify the API was called with correct parameters
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert "courses.json" in call_args[0][0]
        assert call_args[1]["params"] == {
            "year": "2025",
            "term": "9",
            "campus": "NB",
        }
