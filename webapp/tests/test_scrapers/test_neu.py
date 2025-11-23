"""Tests for Northeastern University course scraper."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.orm import Session

import sys
from pathlib import Path

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from scraper.scrapers.neu import NeuScraper
from models.college import College


# Sample NEU Banner API response data
SAMPLE_NEU_SECTIONS = [
    {
        "courseReferenceNumber": "10001",
        "subject": "CS",
        "courseNumber": "2500",
        "courseTitle": "Fundamentals of Computer Science 1",
        "sequenceNumber": "01",
        "openSection": True,
    },
    {
        "courseReferenceNumber": "10002",
        "subject": "CS",
        "courseNumber": "2500",
        "courseTitle": "Fundamentals of Computer Science 1",
        "sequenceNumber": "02",
        "openSection": False,
    },
    {
        "courseReferenceNumber": "10003",
        "subject": "CS",
        "courseNumber": "2510",
        "courseTitle": "Fundamentals of Computer Science 2",
        "sequenceNumber": "01",
        "openSection": True,
    },
    {
        "courseReferenceNumber": "20001",
        "subject": "MATH",
        "courseNumber": "1341",
        "courseTitle": "Calculus 1 for Science and Engineering",
        "sequenceNumber": "01",
        "openSection": False,
    },
]

SAMPLE_NEU_API_RESPONSE = {
    "success": True,
    "totalCount": 4,
    "data": SAMPLE_NEU_SECTIONS,
    "pageOffset": 0,
    "pageMaxSize": 500,
}


@pytest.fixture
def mock_neu_db_session():
    """Create a mock database session for NEU scraper."""
    mock_session = MagicMock(spec=Session)
    mock_college = College(
        id=1,
        name="Northeastern University",
        short_name="neu",
        term_code="202510",
        term_name="Fall 2025",
        is_active=True,
    )

    # Mock the query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_college
    mock_session.execute.return_value = mock_result

    return mock_session


class TestNeuScraper:
    """Tests for NeuScraper class."""

    @pytest.mark.unit
    def test_init_sets_college_and_term(self, mock_neu_db_session):
        """Test that scraper correctly initializes with college and term code."""
        scraper = NeuScraper(mock_neu_db_session)

        assert scraper.college_short_name == "neu"
        assert scraper.current_term == "202510"
        assert scraper.client is None
        assert scraper.session_cookies == {}

    @pytest.mark.unit
    async def test_ensure_client_initializes(self, mock_neu_db_session):
        """Test that _ensure_client creates httpx client."""
        scraper = NeuScraper(mock_neu_db_session)

        assert scraper.client is None
        await scraper._ensure_client()
        assert scraper.client is not None

        # Clean up
        await scraper.client.aclose()

    @pytest.mark.unit
    def test_transform_section_to_class_open(self, mock_neu_db_session):
        """Test transformation of an open section."""
        scraper = NeuScraper(mock_neu_db_session)

        section = {
            "courseReferenceNumber": "12345",
            "subject": "CS",
            "courseNumber": "2500",
            "courseTitle": "Fundamentals of CS 1",
            "sequenceNumber": "01",
            "openSection": True,
        }

        result = scraper._transform_sections_to_classes([section])

        assert len(result) == 1
        assert result[0]["class_number"] == "12345"
        assert result[0]["course_code"] == "CS 2500"
        assert result[0]["title"] == "Fundamentals of CS 1"
        assert result[0]["section"] == "01"
        assert result[0]["status"] == "open"

    @pytest.mark.unit
    def test_transform_section_to_class_closed(self, mock_neu_db_session):
        """Test transformation of a closed section."""
        scraper = NeuScraper(mock_neu_db_session)

        section = {
            "courseReferenceNumber": "12346",
            "subject": "MATH",
            "courseNumber": "1341",
            "courseTitle": "Calculus 1",
            "sequenceNumber": "02",
            "openSection": False,
        }

        result = scraper._transform_sections_to_classes([section])

        assert len(result) == 1
        assert result[0]["class_number"] == "12346"
        assert result[0]["course_code"] == "MATH 1341"
        assert result[0]["status"] == "closed"

    @pytest.mark.unit
    def test_transform_sections_to_classes_multiple(self, mock_neu_db_session):
        """Test transformation of multiple sections."""
        scraper = NeuScraper(mock_neu_db_session)

        result = scraper._transform_sections_to_classes(SAMPLE_NEU_SECTIONS)

        assert len(result) == 4
        assert result[0]["course_code"] == "CS 2500"
        assert result[1]["course_code"] == "CS 2500"
        assert result[2]["course_code"] == "CS 2510"
        assert result[3]["course_code"] == "MATH 1341"

    @pytest.mark.unit
    def test_transform_sections_skips_empty_course_code(self, mock_neu_db_session):
        """Test that sections without course code are skipped."""
        scraper = NeuScraper(mock_neu_db_session)

        section = {
            "courseReferenceNumber": "99999",
            "subject": "",
            "courseNumber": "",
            "courseTitle": "Missing Data",
            "sequenceNumber": "01",
            "openSection": True,
        }

        result = scraper._transform_sections_to_classes([section])

        assert len(result) == 0

    @pytest.mark.unit
    def test_group_classes_by_course(self, mock_neu_db_session):
        """Test grouping individual classes by course code."""
        scraper = NeuScraper(mock_neu_db_session)

        classes = [
            {
                "class_number": "10001",
                "course_code": "CS 2500",
                "title": "Fundamentals of CS 1",
                "section": "01",
                "status": "open",
            },
            {
                "class_number": "10002",
                "course_code": "CS 2500",
                "title": "Fundamentals of CS 1",
                "section": "02",
                "status": "closed",
            },
            {
                "class_number": "10003",
                "course_code": "CS 2510",
                "title": "Fundamentals of CS 2",
                "section": "01",
                "status": "open",
            },
        ]

        result = scraper._group_classes_by_course(classes)

        assert len(result) == 2
        # Check first course (CS 2500 with 2 sections)
        assert result[0]["course_code"] == "CS 2500"
        assert result[0]["title"] == "Fundamentals of CS 1"
        assert len(result[0]["classes"]) == 2
        assert result[0]["classes"][0]["class_number"] == "10001"
        assert result[0]["classes"][1]["class_number"] == "10002"

        # Check second course (CS 2510 with 1 section)
        assert result[1]["course_code"] == "CS 2510"
        assert len(result[1]["classes"]) == 1

    @pytest.mark.unit
    def test_group_classes_skips_missing_course_code(self, mock_neu_db_session):
        """Test that classes without course code are skipped during grouping."""
        scraper = NeuScraper(mock_neu_db_session)

        classes = [
            {
                "class_number": "10001",
                "course_code": "CS 2500",
                "title": "Fundamentals of CS 1",
                "section": "01",
                "status": "open",
            },
            {
                "class_number": "99999",
                "course_code": "",
                "title": "Missing",
                "section": "01",
                "status": "open",
            },
        ]

        result = scraper._group_classes_by_course(classes)

        assert len(result) == 1
        assert result[0]["course_code"] == "CS 2500"

    @pytest.mark.unit
    async def test_setup_session_for_term(self, mock_neu_db_session):
        """Test session setup with Banner API."""
        scraper = NeuScraper(mock_neu_db_session)

        # Mock HTTP client and response
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.headers.get_list.return_value = [
            "JSESSIONID=ABC123; Path=/; HttpOnly",
            "BIGipServer=xyz789; Path=/",
        ]

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        scraper.client = mock_client

        await scraper._setup_session_for_term("202510")

        # Verify session cookies were captured
        assert "JSESSIONID" in scraper.session_cookies
        assert "BIGipServer" in scraper.session_cookies
        assert scraper.session_cookies["JSESSIONID"] == "ABC123"

        # Verify API was called correctly
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "/term/search" in call_args[0][0]
        assert call_args[1]["data"]["term"] == "202510"

    @pytest.mark.unit
    async def test_fetch_sections_page_success(self, mock_neu_db_session):
        """Test fetching a single page of sections."""
        scraper = NeuScraper(mock_neu_db_session)
        scraper.session_cookies = {"JSESSIONID": "test123"}

        # Mock HTTP client and response
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_NEU_API_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        scraper.client = mock_client

        result = await scraper._fetch_sections_page(0, 500)

        assert result is not None
        assert len(result) == 4
        assert result == SAMPLE_NEU_SECTIONS

        # Verify API was called with correct parameters
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert "/searchResults/searchResults" in call_args[0][0]
        assert call_args[1]["params"]["txt_term"] == "202510"
        assert call_args[1]["params"]["pageOffset"] == "0"
        assert call_args[1]["params"]["pageMaxSize"] == "500"

    @pytest.mark.unit
    async def test_fetch_sections_page_empty_response(self, mock_neu_db_session):
        """Test fetching page that returns no data."""
        scraper = NeuScraper(mock_neu_db_session)
        scraper.session_cookies = {"JSESSIONID": "test123"}

        # Mock HTTP client with empty response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "totalCount": 0,
            "data": [],
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        scraper.client = mock_client

        result = await scraper._fetch_sections_page(0, 500)

        assert result == []

    @pytest.mark.unit
    async def test_fetch_sections_page_api_failure(self, mock_neu_db_session):
        """Test handling of API failure response."""
        scraper = NeuScraper(mock_neu_db_session)
        scraper.session_cookies = {"JSESSIONID": "test123"}

        # Mock HTTP client with failure response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": False,
            "totalCount": 0,
            "data": [],
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        scraper.client = mock_client

        result = await scraper._fetch_sections_page(0, 500)

        assert result == []

    @pytest.mark.unit
    async def test_fetch_api_response_for_validation(self, mock_neu_db_session):
        """Test fetching raw API response for validation."""
        scraper = NeuScraper(mock_neu_db_session)
        scraper.session_cookies = {"JSESSIONID": "test123"}

        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_NEU_API_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        scraper.client = mock_client

        result = await scraper._fetch_api_response(0, 1)

        assert result is not None
        assert result["success"] is True
        assert result["totalCount"] == 4

    @pytest.mark.unit
    async def test_fetch_all_courses_single_page(self, mock_neu_db_session):
        """Test fetching all courses when data fits in single page."""
        scraper = NeuScraper(mock_neu_db_session)

        # Mock _fetch_sections_page to return data on first call, empty on second
        with patch.object(
            scraper, "_fetch_sections_page"
        ) as mock_fetch:
            mock_fetch.side_effect = [SAMPLE_NEU_SECTIONS, []]

            result = await scraper._fetch_all_courses()

            # Should have made 2 calls (first batch of 5 pages, first returns data, second empty)
            assert mock_fetch.call_count >= 2
            # Should have transformed all sections
            assert len(result) == 4

    @pytest.mark.unit
    async def test_scrape_courses_all(self, mock_neu_db_session):
        """Test scraping all courses."""
        scraper = NeuScraper(mock_neu_db_session)

        # Mock internal methods instead of HTTP client
        with patch.object(scraper, "_setup_session_for_term", new_callable=AsyncMock):
            with patch.object(scraper, "_fetch_api_response") as mock_api_response:
                with patch.object(scraper, "_fetch_all_courses") as mock_fetch_all:
                    # Setup validation response
                    mock_api_response.return_value = {
                        "success": True,
                        "totalCount": 4,
                    }

                    # Mock _fetch_all_courses to return transformed classes
                    mock_classes = scraper._transform_sections_to_classes(SAMPLE_NEU_SECTIONS)
                    mock_fetch_all.return_value = mock_classes

                    # Mock the client
                    mock_client = AsyncMock()
                    mock_client.aclose = AsyncMock()
                    scraper.client = mock_client

                    result = await scraper.scrape_courses("ALL")

                    # Should return 3 unique courses (CS 2500, CS 2510, MATH 1341)
                    assert len(result) == 3
                    assert result[0]["course_code"] == "CS 2500"
                    assert len(result[0]["classes"]) == 2  # Two sections
                    assert result[1]["course_code"] == "CS 2510"
                    assert result[2]["course_code"] == "MATH 1341"

    @pytest.mark.unit
    async def test_scrape_courses_by_department(self, mock_neu_db_session):
        """Test scraping courses for specific department."""
        scraper = NeuScraper(mock_neu_db_session)

        # Mock internal methods instead of HTTP client
        with patch.object(scraper, "_setup_session_for_term", new_callable=AsyncMock):
            with patch.object(scraper, "_fetch_api_response") as mock_api_response:
                with patch.object(scraper, "_fetch_all_courses") as mock_fetch_all:
                    # Setup validation response
                    mock_api_response.return_value = {
                        "success": True,
                        "totalCount": 4,
                    }

                    # Mock _fetch_all_courses to return transformed classes
                    mock_classes = scraper._transform_sections_to_classes(SAMPLE_NEU_SECTIONS)
                    mock_fetch_all.return_value = mock_classes

                    # Mock the client
                    mock_client = AsyncMock()
                    mock_client.aclose = AsyncMock()
                    scraper.client = mock_client

                    result = await scraper.scrape_courses("CS")

                    # Should only return CS courses
                    assert len(result) == 2
                    assert all(course["course_code"].startswith("CS") for course in result)

    @pytest.mark.unit
    async def test_scrape_courses_with_limit(self, mock_neu_db_session):
        """Test scraping with course limit."""
        scraper = NeuScraper(mock_neu_db_session)

        # Mock internal methods instead of HTTP client
        with patch.object(scraper, "_setup_session_for_term", new_callable=AsyncMock):
            with patch.object(scraper, "_fetch_api_response") as mock_api_response:
                with patch.object(scraper, "_fetch_all_courses") as mock_fetch_all:
                    # Setup validation response
                    mock_api_response.return_value = {
                        "success": True,
                        "totalCount": 4,
                    }

                    # Mock _fetch_all_courses to return transformed classes
                    mock_classes = scraper._transform_sections_to_classes(SAMPLE_NEU_SECTIONS)
                    mock_fetch_all.return_value = mock_classes

                    # Mock the client
                    mock_client = AsyncMock()
                    mock_client.aclose = AsyncMock()
                    scraper.client = mock_client

                    result = await scraper.scrape_courses("ALL", limit=1)

                    assert len(result) == 1
