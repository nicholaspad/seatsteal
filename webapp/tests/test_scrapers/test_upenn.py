"""Tests for University of Pennsylvania course scraper."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from sqlalchemy.orm import Session

import sys
from pathlib import Path

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from scraper.scrapers.upenn import UPennScraper
from models.college import College
from tests.test_scrapers.conftest import create_mock_response


# Sample UPenn FOSE API response data
SAMPLE_UPENN_COURSE_LIST = [
    {
        "code": "CIS 1100",
        "title": "Introduction to Computer Programming",
        "crn": "12345",
        "no": "001",
        "stat": "A",
        "linked_crns": [],
    },
    {
        "code": "CIS 1100",
        "title": "Intro to Computer Programming",
        "crn": "12346",
        "no": "002",
        "stat": "C",
        "linked_crns": [],
    },
    {
        "code": "CIS 1200",
        "title": "Programming Languages and Techniques",
        "crn": "12347",
        "no": "001",
        "stat": "A",
        "linked_crns": [],
    },
    {
        "code": "MATH 1400",
        "title": "Calculus I",
        "crn": "20001",
        "no": "001",
        "stat": "X",
        "linked_crns": [],
    },
]


@pytest.fixture
def mock_upenn_db_session():
    """Create a mock database session for UPenn scraper."""
    mock_session = MagicMock(spec=Session)
    mock_college = College(
        id=1,
        name="University of Pennsylvania",
        short_name="upenn",
        term_code="202510",
        term_name="Fall 2025",
        is_active=True,
    )

    # Mock the query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_college
    mock_session.execute.return_value = mock_result

    return mock_session


class TestUPennScraper:
    """Tests for UPennScraper class."""

    @pytest.mark.unit
    def test_init_sets_college_short_name(self, mock_upenn_db_session):
        """Test that scraper correctly sets college short name."""
        scraper = UPennScraper(mock_upenn_db_session)

        assert scraper.college_short_name == "upenn"

    @pytest.mark.unit
    def test_init_gets_term_code_from_db(self, mock_upenn_db_session):
        """Test that scraper correctly retrieves term code from database."""
        scraper = UPennScraper(mock_upenn_db_session)

        assert scraper.current_term == "202510"

    @pytest.mark.unit
    def test_transform_course_to_class(self, mock_upenn_db_session):
        """Test transformation of course to class dictionary."""
        scraper = UPennScraper(mock_upenn_db_session)

        course = SAMPLE_UPENN_COURSE_LIST[0]
        result = scraper._transform_course_to_class(course)

        assert result is not None
        assert result["class_number"] == "12345"
        assert result["section"] == "001"
        assert result["status"] == "Open"

    @pytest.mark.unit
    def test_transform_course_to_class_with_missing_crn(self, mock_upenn_db_session):
        """Test that course with missing CRN returns None."""
        scraper = UPennScraper(mock_upenn_db_session)

        course = {
            "code": "CIS 1100",
            "title": "No CRN Course",
            "crn": "",
            "no": "001",
            "stat": "A",
        }
        result = scraper._transform_course_to_class(course)

        assert result is None

    @pytest.mark.unit
    def test_map_status_code_active(self, mock_upenn_db_session):
        """Test status code mapping for active status."""
        scraper = UPennScraper(mock_upenn_db_session)

        assert scraper._map_status_code("A") == "Open"
        assert scraper._map_status_code("a") == "Open"

    @pytest.mark.unit
    def test_map_status_code_closed(self, mock_upenn_db_session):
        """Test status code mapping for closed status."""
        scraper = UPennScraper(mock_upenn_db_session)

        assert scraper._map_status_code("C") == "Closed"
        assert scraper._map_status_code("c") == "Closed"

    @pytest.mark.unit
    def test_map_status_code_cancelled(self, mock_upenn_db_session):
        """Test status code mapping for cancelled status."""
        scraper = UPennScraper(mock_upenn_db_session)

        assert scraper._map_status_code("X") == "Closed"
        assert scraper._map_status_code("x") == "Closed"

    @pytest.mark.unit
    def test_map_status_code_unknown(self, mock_upenn_db_session):
        """Test status code mapping for unknown status."""
        scraper = UPennScraper(mock_upenn_db_session)

        assert scraper._map_status_code("Z") == "Unknown"
        assert scraper._map_status_code("") == "Unknown"

    @pytest.mark.unit
    def test_deduplicate_courses_merges_classes(self, mock_upenn_db_session):
        """Test deduplication merges classes with same course code."""
        scraper = UPennScraper(mock_upenn_db_session)

        # Create duplicate courses with different classes
        courses_data = [
            {
                "course_code": "CIS 1100",
                "title": "Introduction to Computer Programming",
                "classes": [
                    {"class_number": "12345", "section": "001", "status": "Open"}
                ],
            },
            {
                "course_code": "CIS 1100",
                "title": "Intro to Computer Programming",
                "classes": [
                    {"class_number": "12346", "section": "002", "status": "Closed"}
                ],
            },
        ]

        result = scraper._deduplicate_courses(courses_data)

        assert len(result) == 1
        assert result[0]["course_code"] == "CIS 1100"
        assert len(result[0]["classes"]) == 2
        assert result[0]["classes"][0]["class_number"] == "12345"
        assert result[0]["classes"][1]["class_number"] == "12346"

    @pytest.mark.unit
    def test_deduplicate_courses_no_duplicates(self, mock_upenn_db_session):
        """Test deduplication with no duplicate course codes."""
        scraper = UPennScraper(mock_upenn_db_session)

        courses_data = [
            {
                "course_code": "CIS 1100",
                "title": "Intro to Programming",
                "classes": [
                    {"class_number": "12345", "section": "001", "status": "Open"}
                ],
            },
            {
                "course_code": "CIS 1200",
                "title": "Data Structures",
                "classes": [
                    {"class_number": "12347", "section": "001", "status": "Open"}
                ],
            },
        ]

        result = scraper._deduplicate_courses(courses_data)

        assert len(result) == 2
        assert result[0]["course_code"] == "CIS 1100"
        assert result[1]["course_code"] == "CIS 1200"

    @pytest.mark.unit
    async def test_fetch_course_list(self, mock_upenn_db_session):
        """Test fetching course list from API."""
        scraper = UPennScraper(mock_upenn_db_session)

        # Mock the HTTP client and response
        mock_response = create_mock_response({"results": SAMPLE_UPENN_COURSE_LIST})
        mock_response.headers = {"content-type": "application/json"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        result = await scraper._fetch_course_list()

        assert len(result) == 4
        assert result[0]["code"] == "CIS 1100"
        assert result[2]["code"] == "CIS 1200"

    @pytest.mark.unit
    async def test_fetch_course_list_invalid_response(self, mock_upenn_db_session):
        """Test handling of invalid API response."""
        scraper = UPennScraper(mock_upenn_db_session)

        # Mock response without "results" key
        mock_response = create_mock_response({})
        mock_response.headers = {"content-type": "application/json"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        scraper.client = mock_client

        with pytest.raises(ValueError, match="Invalid response format"):
            await scraper._fetch_course_list()

    @pytest.mark.unit
    async def test_fetch_course_classes(self, mock_upenn_db_session):
        """Test extracting classes from course data."""
        scraper = UPennScraper(mock_upenn_db_session)

        course = SAMPLE_UPENN_COURSE_LIST[0]
        result = await scraper._fetch_course_classes(course)

        assert result is not None
        assert result["course_code"] == "CIS 1100"
        assert result["title"] == "Introduction to Computer Programming"
        assert len(result["classes"]) == 1
        assert result["classes"][0]["class_number"] == "12345"

    @pytest.mark.unit
    async def test_fetch_course_classes_skips_unknown_status(
        self, mock_upenn_db_session
    ):
        """Test that classes with unknown status are skipped."""
        scraper = UPennScraper(mock_upenn_db_session)

        # Course with unknown status code
        course = {
            "code": "CIS 9999",
            "title": "Unknown Status Course",
            "crn": "99999",
            "no": "001",
            "stat": "Z",  # Unknown status
            "linked_crns": [],
        }

        result = await scraper._fetch_course_classes(course)

        # Should return None because the only class has Unknown status
        assert result is None

    @pytest.mark.unit
    async def test_fetch_course_classes_with_missing_code(self, mock_upenn_db_session):
        """Test handling course with missing code field."""
        scraper = UPennScraper(mock_upenn_db_session)

        # Pass course data without required 'code' field
        invalid_course = {
            "title": "Missing Code Course",
            "crn": "12345",
            "no": "001",
            "stat": "A",
        }

        result = await scraper._fetch_course_classes(invalid_course)

        # Should handle exception gracefully and return None
        assert result is None

    @pytest.mark.unit
    async def test_scrape_courses_all(self, mock_upenn_db_session):
        """Test scraping all courses."""
        scraper = UPennScraper(mock_upenn_db_session)

        # Mock the HTTP client and response
        mock_response = create_mock_response({"results": SAMPLE_UPENN_COURSE_LIST})
        mock_response.headers = {"content-type": "application/json"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        result = await scraper.scrape_courses("ALL")

        # Should deduplicate CIS 1100 (appears twice)
        assert len(result) == 3
        cis_1100 = next(c for c in result if c["course_code"] == "CIS 1100")
        assert len(cis_1100["classes"]) == 2

    @pytest.mark.unit
    async def test_scrape_courses_by_department(self, mock_upenn_db_session):
        """Test scraping courses for specific department."""
        scraper = UPennScraper(mock_upenn_db_session)

        # Mock the HTTP client and response
        mock_response = create_mock_response({"results": SAMPLE_UPENN_COURSE_LIST})
        mock_response.headers = {"content-type": "application/json"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        result = await scraper.scrape_courses("CIS")

        # Should only include CIS courses
        assert len(result) == 2
        assert all(c["course_code"].startswith("CIS") for c in result)

    @pytest.mark.unit
    async def test_scrape_courses_with_limit(self, mock_upenn_db_session):
        """Test scraping with course limit."""
        scraper = UPennScraper(mock_upenn_db_session)

        # Mock the HTTP client and response
        mock_response = create_mock_response({"results": SAMPLE_UPENN_COURSE_LIST})
        mock_response.headers = {"content-type": "application/json"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        result = await scraper.scrape_courses("ALL", limit=2)

        # Should only return first 2 courses from the list before deduplication
        assert (
            len(result) == 1
        )  # CIS 1100 appears twice in the first 2, so deduplicated to 1

    @pytest.mark.unit
    async def test_make_api_request_builds_correct_body(self, mock_upenn_db_session):
        """Test that API request builds URL-encoded JSON body correctly."""
        scraper = UPennScraper(mock_upenn_db_session)

        # Mock the HTTP client and response
        mock_response = create_mock_response({"success": True})
        mock_response.headers = {"content-type": "application/json"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        request_body = {
            "other": {"srcdb": "202510"},
            "criteria": [{"field": "test", "value": "value"}],
        }

        result = await scraper._make_api_request(
            "https://test.api/endpoint", request_body
        )

        # Verify the API was called
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args

        # Verify URL
        assert call_args[0][0] == "https://test.api/endpoint"

        # Verify body is URL-encoded (the content parameter should be a string)
        assert "content" in call_args[1]
        assert isinstance(call_args[1]["content"], str)

        # Result should be the JSON response
        assert result == {"success": True}
