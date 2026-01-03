"""Tests for Brown University course scraper."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from sqlalchemy.orm import Session

import sys
from pathlib import Path

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from scraper.scrapers.brown import BrownScraper
from models.college import College
from tests.test_scrapers.conftest import create_mock_response


# Sample Brown API response data for course search
SAMPLE_BROWN_COURSE_LIST = [
    {
        "code": "CSCI 0150",
        "title": "Introduction to Object-Oriented Programming and Computer Science",
        "crn": "12345",
        "no": "S01",
        "stat": "A",
        "linked_crns": [],
    },
    {
        "code": "CSCI 0150",
        "title": "Intro to OOP and Computer Science",
        "crn": "12346",
        "no": "S02",
        "stat": "C",
        "linked_crns": [],
    },
    {
        "code": "CSCI 0200",
        "title": "Program Design with Data Structures and Algorithms",
        "crn": "12347",
        "no": "S01",
        "stat": "A",
        "linked_crns": [],
    },
    {
        "code": "MATH 0100",
        "title": "Introductory Calculus, Part II",
        "crn": "20001",
        "no": "S01",
        "stat": "X",
        "linked_crns": [],
    },
]


@pytest.fixture
def mock_brown_db_session():
    """Create a mock database session for Brown scraper."""
    mock_session = MagicMock(spec=Session)
    mock_college = College(
        id=1,
        name="Brown University",
        short_name="brown",
        term_code="202510",
        term_name="Fall 2025",
        is_active=True,
    )

    # Mock the query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_college
    mock_session.execute.return_value = mock_result

    return mock_session


class TestBrownScraper:
    """Tests for BrownScraper class."""

    @pytest.mark.unit
    def test_init_sets_college_short_name(self, mock_brown_db_session):
        """Test that scraper correctly sets college short name."""
        scraper = BrownScraper(mock_brown_db_session)

        assert scraper.college_short_name == "brown"

    @pytest.mark.unit
    def test_init_gets_term_code_from_db(self, mock_brown_db_session):
        """Test that scraper correctly retrieves term code from database."""
        scraper = BrownScraper(mock_brown_db_session)

        assert scraper.current_term == "202510"

    @pytest.mark.unit
    def test_transform_course_to_class(self, mock_brown_db_session):
        """Test transformation of course to class dictionary."""
        scraper = BrownScraper(mock_brown_db_session)

        course = SAMPLE_BROWN_COURSE_LIST[0]
        result = scraper._transform_course_to_class(course)

        assert result is not None
        assert result["class_number"] == "12345"
        assert result["section"] == "S01"
        assert result["status"] == "Open"

    @pytest.mark.unit
    def test_transform_course_to_class_with_missing_crn(self, mock_brown_db_session):
        """Test that course with missing CRN returns None."""
        scraper = BrownScraper(mock_brown_db_session)

        course = {
            "code": "CSCI 0150",
            "title": "No CRN Course",
            "crn": "",
            "no": "S01",
            "stat": "A",
        }
        result = scraper._transform_course_to_class(course)

        assert result is None

    @pytest.mark.unit
    def test_map_status_code_active(self, mock_brown_db_session):
        """Test status code mapping for active status."""
        scraper = BrownScraper(mock_brown_db_session)

        assert scraper._map_status_code("A") == "Open"
        assert scraper._map_status_code("a") == "Open"

    @pytest.mark.unit
    def test_map_status_code_closed(self, mock_brown_db_session):
        """Test status code mapping for closed status."""
        scraper = BrownScraper(mock_brown_db_session)

        assert scraper._map_status_code("C") == "Closed"
        assert scraper._map_status_code("c") == "Closed"

    @pytest.mark.unit
    def test_map_status_code_cancelled(self, mock_brown_db_session):
        """Test status code mapping for cancelled status."""
        scraper = BrownScraper(mock_brown_db_session)

        assert scraper._map_status_code("X") == "Closed"
        assert scraper._map_status_code("x") == "Closed"

    @pytest.mark.unit
    def test_map_status_code_unknown(self, mock_brown_db_session):
        """Test status code mapping for unknown status."""
        scraper = BrownScraper(mock_brown_db_session)

        assert scraper._map_status_code("Z") == "Unknown"
        assert scraper._map_status_code("") == "Unknown"

    @pytest.mark.unit
    def test_deduplicate_courses_merges_classes(self, mock_brown_db_session):
        """Test deduplication merges classes with same course code."""
        scraper = BrownScraper(mock_brown_db_session)

        # Create duplicate courses with different classes
        courses_data = [
            {
                "course_code": "CSCI 0150",
                "title": "Introduction to OOP",
                "classes": [
                    {"class_number": "12345", "section": "S01", "status": "Open"}
                ],
            },
            {
                "course_code": "CSCI 0150",
                "title": "Intro to OOP",
                "classes": [
                    {"class_number": "12346", "section": "S02", "status": "Closed"}
                ],
            },
        ]

        result = scraper._deduplicate_courses(courses_data)

        assert len(result) == 1
        assert result[0]["course_code"] == "CSCI 0150"
        assert len(result[0]["classes"]) == 2
        assert result[0]["classes"][0]["class_number"] == "12345"
        assert result[0]["classes"][1]["class_number"] == "12346"

    @pytest.mark.unit
    def test_deduplicate_courses_no_duplicates(self, mock_brown_db_session):
        """Test deduplication with no duplicate course codes."""
        scraper = BrownScraper(mock_brown_db_session)

        courses_data = [
            {
                "course_code": "CSCI 0150",
                "title": "Intro to OOP",
                "classes": [
                    {"class_number": "12345", "section": "S01", "status": "Open"}
                ],
            },
            {
                "course_code": "CSCI 0200",
                "title": "Data Structures",
                "classes": [
                    {"class_number": "12347", "section": "S01", "status": "Open"}
                ],
            },
        ]

        result = scraper._deduplicate_courses(courses_data)

        assert len(result) == 2
        assert result[0]["course_code"] == "CSCI 0150"
        assert result[1]["course_code"] == "CSCI 0200"

    @pytest.mark.unit
    async def test_fetch_course_list(self, mock_brown_db_session):
        """Test fetching course list from API."""
        scraper = BrownScraper(mock_brown_db_session)

        # Mock the HTTP client and response
        mock_response = create_mock_response({"results": SAMPLE_BROWN_COURSE_LIST})
        mock_response.headers = {"content-type": "application/json"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        result = await scraper._fetch_course_list()

        assert len(result) == 4
        assert result[0]["code"] == "CSCI 0150"
        assert result[2]["code"] == "CSCI 0200"

    @pytest.mark.unit
    async def test_fetch_course_list_invalid_response(self, mock_brown_db_session):
        """Test handling of invalid API response."""
        scraper = BrownScraper(mock_brown_db_session)

        # Mock response without "results" key
        mock_response = create_mock_response({})
        mock_response.headers = {"content-type": "application/json"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        scraper.client = mock_client

        with pytest.raises(ValueError, match="Invalid response format"):
            await scraper._fetch_course_list()

    @pytest.mark.unit
    async def test_fetch_course_classes(self, mock_brown_db_session):
        """Test extracting classes from course data."""
        scraper = BrownScraper(mock_brown_db_session)

        course = SAMPLE_BROWN_COURSE_LIST[0]
        result = await scraper._fetch_course_classes(course)

        assert result is not None
        assert result["course_code"] == "CSCI 0150"
        assert (
            result["title"]
            == "Introduction to Object-Oriented Programming and Computer Science"
        )
        assert len(result["classes"]) == 1
        assert result["classes"][0]["class_number"] == "12345"

    @pytest.mark.unit
    async def test_fetch_course_classes_with_missing_code(self, mock_brown_db_session):
        """Test handling course with missing code field."""
        scraper = BrownScraper(mock_brown_db_session)

        # Pass course data without required 'code' field
        invalid_course = {
            "title": "Missing Code Course",
            "crn": "12345",
            "no": "S01",
            "stat": "A",
        }

        result = await scraper._fetch_course_classes(invalid_course)

        # Should handle exception gracefully and return None
        assert result is None

    @pytest.mark.unit
    async def test_scrape_courses_all(self, mock_brown_db_session):
        """Test scraping all courses."""
        scraper = BrownScraper(mock_brown_db_session)

        # Mock the HTTP client and response
        mock_response = create_mock_response({"results": SAMPLE_BROWN_COURSE_LIST})
        mock_response.headers = {"content-type": "application/json"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        result = await scraper.scrape_courses("ALL")

        # Should deduplicate CSCI 0150 (appears twice)
        assert len(result) == 3
        csci_150 = next(c for c in result if c["course_code"] == "CSCI 0150")
        assert len(csci_150["classes"]) == 2

    @pytest.mark.unit
    async def test_scrape_courses_by_department(self, mock_brown_db_session):
        """Test scraping courses for specific department."""
        scraper = BrownScraper(mock_brown_db_session)

        # Mock the HTTP client and response
        mock_response = create_mock_response({"results": SAMPLE_BROWN_COURSE_LIST})
        mock_response.headers = {"content-type": "application/json"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        result = await scraper.scrape_courses("CSCI")

        # Should only include CSCI courses
        assert len(result) == 2
        assert all(c["course_code"].startswith("CSCI") for c in result)

    @pytest.mark.unit
    async def test_scrape_courses_with_limit(self, mock_brown_db_session):
        """Test scraping with course limit."""
        scraper = BrownScraper(mock_brown_db_session)

        # Mock the HTTP client and response
        mock_response = create_mock_response({"results": SAMPLE_BROWN_COURSE_LIST})
        mock_response.headers = {"content-type": "application/json"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        result = await scraper.scrape_courses("ALL", limit=2)

        # Should only return first 2 courses from the list before deduplication
        assert (
            len(result) == 1
        )  # CSCI 0150 appears twice in the first 2, so deduplicated to 1
