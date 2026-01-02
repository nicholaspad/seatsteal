"""Tests for Boston University course scraper."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from sqlalchemy.orm import Session

import sys
from pathlib import Path

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from scraper.scrapers.bu import BuScraper
from models.college import College
from tests.test_scrapers.conftest import create_mock_response


# Sample BU API response data
SAMPLE_BU_CLASSES = [
    {
        "class_nbr": "10001",
        "subject": "CAS",
        "catalog_nbr": "CS111",
        "class_section": "A1",
        "descr": "INTRODUCTION TO COMPUTER SCIENCE I",
        "enrollment_available": 5,
    },
    {
        "class_nbr": "10002",
        "subject": "CAS",
        "catalog_nbr": "CS111",
        "class_section": "A2",
        "descr": "INTRODUCTION TO COMPUTER SCIENCE I",
        "enrollment_available": 0,
    },
    {
        "class_nbr": "10003",
        "subject": "CAS",
        "catalog_nbr": "CS112",
        "class_section": "A1",
        "descr": "DATA STRUCTURES AND ALGORITHMS",
        "enrollment_available": 10,
    },
    {
        "class_nbr": "20001",
        "subject": "CAS",
        "catalog_nbr": "MA123",
        "class_section": "A1",
        "descr": "CALCULUS I",
        "enrollment_available": 3,
    },
]


@pytest.fixture
def mock_bu_db_session():
    """Create a mock database session for BU scraper."""
    mock_session = MagicMock(spec=Session)
    mock_college = College(
        id=1,
        name="Boston University",
        short_name="bu",
        term_code="2258",
        term_name="Fall 2025",
        is_active=True,
    )

    # Mock the query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_college
    mock_session.execute.return_value = mock_result

    return mock_session


class TestBuScraper:
    """Tests for BuScraper class."""

    @pytest.mark.unit
    def test_init_sets_college_short_name(self, mock_bu_db_session):
        """Test that scraper correctly sets college short name."""
        scraper = BuScraper(mock_bu_db_session)

        assert scraper.college_short_name == "bu"

    @pytest.mark.unit
    def test_init_gets_term_code_from_db(self, mock_bu_db_session):
        """Test that scraper correctly retrieves term code from database."""
        scraper = BuScraper(mock_bu_db_session)

        assert scraper.current_term == "2258"

    @pytest.mark.unit
    def test_build_page_url(self, mock_bu_db_session):
        """Test URL building for pagination."""
        scraper = BuScraper(mock_bu_db_session)

        url = scraper._build_page_url(1)

        assert "institution=BU001" in url
        assert "term=2258" in url
        assert "page=1" in url

    @pytest.mark.unit
    def test_build_page_url_multiple_pages(self, mock_bu_db_session):
        """Test URL building for different page numbers."""
        scraper = BuScraper(mock_bu_db_session)

        url1 = scraper._build_page_url(1)
        url2 = scraper._build_page_url(5)

        assert "page=1" in url1
        assert "page=5" in url2

    @pytest.mark.unit
    def test_transform_to_class_dict(self, mock_bu_db_session):
        """Test transformation of BU class to standard format."""
        scraper = BuScraper(mock_bu_db_session)

        bu_class = SAMPLE_BU_CLASSES[0]
        result = scraper._transform_to_class_dict(bu_class)

        assert result is not None
        assert result["class_number"] == "10001"
        assert result["section"] == "A1"
        assert result["status"] == "open"

    @pytest.mark.unit
    def test_transform_to_class_dict_open_status(self, mock_bu_db_session):
        """Test transformation with open enrollment status."""
        scraper = BuScraper(mock_bu_db_session)

        bu_class = {
            "class_nbr": "12345",
            "class_section": "B1",
            "enrollment_available": 5,
        }
        result = scraper._transform_to_class_dict(bu_class)

        assert result is not None
        assert result["status"] == "open"

    @pytest.mark.unit
    def test_transform_to_class_dict_closed_status(self, mock_bu_db_session):
        """Test transformation with closed enrollment status."""
        scraper = BuScraper(mock_bu_db_session)

        bu_class = {
            "class_nbr": "12345",
            "class_section": "B1",
            "enrollment_available": 0,
        }
        result = scraper._transform_to_class_dict(bu_class)

        assert result is not None
        assert result["status"] == "closed"

    @pytest.mark.unit
    def test_transform_to_class_dict_missing_class_number(self, mock_bu_db_session):
        """Test that class without class_nbr returns None."""
        scraper = BuScraper(mock_bu_db_session)

        bu_class = {
            "class_nbr": "",
            "class_section": "A1",
            "enrollment_available": 5,
        }
        result = scraper._transform_to_class_dict(bu_class)

        assert result is None

    @pytest.mark.unit
    def test_group_classes_by_course(self, mock_bu_db_session):
        """Test grouping classes by course code."""
        scraper = BuScraper(mock_bu_db_session)

        result = scraper._group_classes_by_course(SAMPLE_BU_CLASSES)

        assert len(result) == 3  # CS111, CS112, MA123
        cs111 = next(c for c in result if c["course_code"] == "CAS CS111")
        assert len(cs111["classes"]) == 2  # Two sections

    @pytest.mark.unit
    def test_group_classes_by_course_multiple_sections(self, mock_bu_db_session):
        """Test grouping multiple sections of same course."""
        scraper = BuScraper(mock_bu_db_session)

        result = scraper._group_classes_by_course(SAMPLE_BU_CLASSES)

        cs111 = next(c for c in result if c["course_code"] == "CAS CS111")
        assert cs111["title"] == "INTRODUCTION TO COMPUTER SCIENCE I"
        assert len(cs111["classes"]) == 2
        assert cs111["classes"][0]["class_number"] == "10001"
        assert cs111["classes"][1]["class_number"] == "10002"

    @pytest.mark.unit
    def test_group_classes_filters_invalid(self, mock_bu_db_session):
        """Test that grouping filters out invalid classes."""
        scraper = BuScraper(mock_bu_db_session)

        classes_with_invalid = SAMPLE_BU_CLASSES + [
            {
                "class_nbr": "",  # Missing class number
                "subject": "CAS",
                "catalog_nbr": "CS999",
                "enrollment_available": 5,
            },
            {
                "class_nbr": "99999",
                "subject": "",  # Missing subject
                "catalog_nbr": "999",
                "enrollment_available": 5,
            },
        ]

        result = scraper._group_classes_by_course(classes_with_invalid)

        # Should still have only 3 valid courses
        assert len(result) == 3

    @pytest.mark.unit
    async def test_fetch_single_page(self, mock_bu_db_session):
        """Test fetching a single page successfully."""
        scraper = BuScraper(mock_bu_db_session)

        # Mock the HTTP client and response
        mock_response = create_mock_response(
            {
                "pageCount": 1,
                "classes": SAMPLE_BU_CLASSES,
            }
        )
        mock_response.headers = {"content-type": "application/json"}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        result = await scraper._fetch_single_page(1)

        assert result is not None
        assert "classes" in result
        assert len(result["classes"]) == 4

    @pytest.mark.unit
    async def test_fetch_single_page_invalid_response(self, mock_bu_db_session):
        """Test handling invalid response format."""
        scraper = BuScraper(mock_bu_db_session)

        # Mock response without "classes" key
        mock_response = create_mock_response({})
        mock_response.headers = {"content-type": "application/json"}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        scraper.client = mock_client

        result = await scraper._fetch_single_page(1)

        assert result is None

    @pytest.mark.unit
    async def test_fetch_single_page_non_json_response(self, mock_bu_db_session):
        """Test handling non-JSON response."""
        scraper = BuScraper(mock_bu_db_session)

        # Mock non-JSON response
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {"content-type": "text/html"}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        scraper.client = mock_client

        result = await scraper._fetch_single_page(1)

        assert result is None

    @pytest.mark.unit
    async def test_fetch_all_pages_stops_on_empty(self, mock_bu_db_session):
        """Test that pagination stops when empty page is found."""
        scraper = BuScraper(mock_bu_db_session)

        call_count = 0

        async def mock_get(url):
            nonlocal call_count
            call_count += 1

            # Return classes for first 2 pages, empty for rest
            if call_count <= 2:
                mock_response = create_mock_response(
                    {
                        "pageCount": 100,
                        "classes": SAMPLE_BU_CLASSES,
                    }
                )
            else:
                mock_response = create_mock_response({"pageCount": 100, "classes": []})

            mock_response.headers = {"content-type": "application/json"}
            return mock_response

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        result = await scraper._fetch_all_pages()

        # Should have fetched and stopped when hitting empty page
        assert len(result) == 3  # Grouped into 3 courses

    @pytest.mark.unit
    async def test_scrape_courses_all(self, mock_bu_db_session):
        """Test scraping all courses."""
        scraper = BuScraper(mock_bu_db_session)

        # Mock single page with data, then empty page
        call_count = 0

        async def mock_get(url):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                mock_response = create_mock_response(
                    {
                        "pageCount": 1,
                        "classes": SAMPLE_BU_CLASSES,
                    }
                )
            else:
                mock_response = create_mock_response({"pageCount": 1, "classes": []})

            mock_response.headers = {"content-type": "application/json"}
            return mock_response

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        result = await scraper.scrape_courses("ALL")

        assert len(result) == 3
        assert any(c["course_code"] == "CAS CS111" for c in result)

    @pytest.mark.unit
    async def test_scrape_courses_by_subject(self, mock_bu_db_session):
        """Test scraping courses for specific subject."""
        scraper = BuScraper(mock_bu_db_session)

        # Mock single page with data, then empty page
        call_count = 0

        async def mock_get(url):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                mock_response = create_mock_response(
                    {
                        "pageCount": 1,
                        "classes": SAMPLE_BU_CLASSES,
                    }
                )
            else:
                mock_response = create_mock_response({"pageCount": 1, "classes": []})

            mock_response.headers = {"content-type": "application/json"}
            return mock_response

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        result = await scraper.scrape_courses("CAS CS")

        # Should only return CS courses (not MA)
        assert len(result) == 2
        assert all(c["course_code"].startswith("CAS CS") for c in result)

    @pytest.mark.unit
    async def test_scrape_courses_with_limit(self, mock_bu_db_session):
        """Test scraping with course limit."""
        scraper = BuScraper(mock_bu_db_session)

        # Mock single page with data, then empty page
        call_count = 0

        async def mock_get(url):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                mock_response = create_mock_response(
                    {
                        "pageCount": 1,
                        "classes": SAMPLE_BU_CLASSES,
                    }
                )
            else:
                mock_response = create_mock_response({"pageCount": 1, "classes": []})

            mock_response.headers = {"content-type": "application/json"}
            return mock_response

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        result = await scraper.scrape_courses("ALL", limit=1)

        assert len(result) == 1
