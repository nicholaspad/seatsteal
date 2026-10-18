"""Tests for Boston University course scraper."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.orm import Session

import sys
from pathlib import Path

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from scraper.scrapers.bu import BuFetchError, BuScraper
from models.college import College
from tests.test_scrapers.conftest import create_mock_response

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "bu"


def fixture_path(filename: str) -> Path:
    path = FIXTURES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Fixture {filename} not found at {path}. "
            f"Tests require live-captured BU responses."
        )
    return path


def load_fixture_text(filename: str) -> str:
    """Load a text fixture. Tests fail if the live-captured file is missing."""
    return fixture_path(filename).read_text()


def load_fixture_bytes(filename: str) -> bytes:
    """Load a fixture as raw bytes so HTTP size assertions stay exact."""
    return fixture_path(filename).read_bytes()


def load_fixture_json(filename: str):
    """Load a JSON fixture. Tests fail if the file is missing."""
    return json.loads(load_fixture_bytes(filename))


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
        """Invalid JSON objects must fail loud, not look like an empty catalog."""
        scraper = BuScraper(mock_bu_db_session)

        # Mock response without "classes" key
        mock_response = create_mock_response({})
        mock_response.headers = {"content-type": "application/json"}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        scraper.client = mock_client

        with pytest.raises(BuFetchError) as exc_info:
            await scraper._fetch_single_page(1)

        message = str(exc_info.value)
        assert "invalid JSON format" in message
        assert "status=200" in message
        assert "response_size=" in message

    @pytest.mark.unit
    async def test_fetch_single_page_non_json_response(self, mock_bu_db_session):
        """Non-JSON 200s must fail loud with HTTP status and body size."""
        scraper = BuScraper(mock_bu_db_session)

        html = "<html><title>PeopleSoft</title><body>cookies enabled</body></html>"
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.status_code = 200
        mock_response.content = html.encode("utf-8")
        mock_response.headers = {"content-type": "text/html"}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        scraper.client = mock_client

        with pytest.raises(BuFetchError) as exc_info:
            await scraper._fetch_single_page(1)

        message = str(exc_info.value)
        assert "non-JSON" in message
        assert "status=200" in message
        assert f"response_size={len(html.encode('utf-8'))}" in message

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

    @pytest.mark.unit
    def test_extract_wrapped_fixture_page(self, mock_bu_db_session):
        """Parser accepts the wrapped {pageCount, classes} ClassSearch shape."""
        scraper = BuScraper(mock_bu_db_session)
        data = load_fixture_json("classsearch_page.json")

        payload = scraper._extract_classes_payload(data)

        assert payload is not None
        assert len(payload["classes"]) == 3
        courses = scraper._group_classes_by_course(payload["classes"])
        assert len(courses) == 2
        cs111 = next(c for c in courses if c["course_code"] == "CAS CS 111")
        assert len(cs111["classes"]) == 2
        assert cs111["classes"][0]["status"] == "open"
        assert cs111["classes"][1]["status"] == "closed"

    @pytest.mark.unit
    def test_extract_raw_list_fixture(self, mock_bu_db_session):
        """Parser accepts a raw list of class dicts (older/alternate iScript)."""
        scraper = BuScraper(mock_bu_db_session)
        data = load_fixture_json("classsearch_list.json")

        payload = scraper._extract_classes_payload(data)

        assert payload is not None
        assert len(payload["classes"]) == 2
        courses = scraper._group_classes_by_course(payload["classes"])
        assert {c["course_code"] for c in courses} == {"CAS CS 111", "CAS MA 123"}

    @pytest.mark.unit
    def test_extract_nested_data_classes(self, mock_bu_db_session):
        """Parser accepts {"data": {"classes": [...]}} wrappers."""
        scraper = BuScraper(mock_bu_db_session)
        inner = load_fixture_json("classsearch_page.json")

        payload = scraper._extract_classes_payload({"data": inner})

        assert payload is not None
        assert len(payload["classes"]) == 3

    @pytest.mark.unit
    async def test_live_502_fixture_fails_loud_with_status_and_size(
        self, mock_bu_db_session
    ):
        """
        Live capture (2026-10-18): ClassSearch term=2268 page=1 returns HTTP 502
        HTML (145 bytes). That must not be treated as an empty catalog page.
        """
        scraper = BuScraper(mock_bu_db_session)
        html = load_fixture_bytes("classsearch_502.html")
        assert len(html) == 145
        assert b"502 Bad Gateway" in html

        mock_response = MagicMock()
        mock_response.status_code = 502
        mock_response.content = html
        mock_response.headers = {"content-type": "text/html"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        scraper.client = mock_client

        with pytest.raises(BuFetchError) as exc_info:
            await scraper._fetch_single_page(1)

        message = str(exc_info.value)
        assert "HTTP 502" in message
        assert "response_size=145" in message
        assert scraper.last_fetch["status"] == 502
        assert scraper.last_fetch["size"] == 145
        assert "502" in scraper.format_empty_reason()
        assert "response_size=145" in scraper.format_empty_reason()

    @pytest.mark.unit
    async def test_live_502_scrape_does_not_return_zero_courses(
        self, mock_bu_db_session
    ):
        """A 502 on page 1 must raise, not return [] (which becomes outcome=partial)."""
        scraper = BuScraper(mock_bu_db_session)
        html = load_fixture_bytes("classsearch_502.html")

        mock_response = MagicMock()
        mock_response.status_code = 502
        mock_response.content = html
        mock_response.headers = {"content-type": "text/html"}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.aclose = AsyncMock()
        scraper.client = mock_client

        with pytest.raises(BuFetchError) as exc_info:
            await scraper.scrape_courses("ALL")

        assert "HTTP 502" in str(exc_info.value)
        assert "response_size=145" in str(exc_info.value)

    @pytest.mark.unit
    async def test_empty_json_logs_status_and_size(self, mock_bu_db_session):
        """Valid empty JSON still returns 0 courses but logs HTTP status + size."""
        scraper = BuScraper(mock_bu_db_session)
        empty = load_fixture_json("classsearch_empty.json")

        async def mock_get(url):
            mock_response = create_mock_response(empty)
            mock_response.headers = {"content-type": "application/json"}
            return mock_response

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.aclose = AsyncMock()
        scraper.client = mock_client

        with patch("scraper.scrapers.bu.logger") as mock_logger:
            result = await scraper.scrape_courses("ALL")

        assert result == []
        logged = " ".join(
            str(call)
            for call in mock_logger.warning.call_args_list
            + mock_logger.info.call_args_list
        )
        assert "status=200" in logged
        assert "response_size=" in logged
        assert "0 courses" in logged or "0 classes" in logged
        assert scraper.last_fetch["status"] == 200
        assert scraper.last_fetch["reason"] == "empty_classes"

    @pytest.mark.unit
    async def test_fetch_single_page_parses_list_json_even_if_html_content_type(
        self, mock_bu_db_session
    ):
        """JSON list bodies parse even when the gateway labels them text/html."""
        scraper = BuScraper(mock_bu_db_session)
        data = load_fixture_json("classsearch_list.json")
        body = json.dumps(data).encode("utf-8")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = body
        mock_response.headers = {"content-type": "text/html"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        scraper.client = mock_client

        result = await scraper._fetch_single_page(1)

        assert result is not None
        assert len(result["classes"]) == 2
        assert result["classes"][0]["class_nbr"] == "10847"

    @pytest.mark.unit
    async def test_fetch_all_pages_fails_loud_when_first_batch_errors(
        self, mock_bu_db_session
    ):
        """HTTP failures on the first batch must not look like an empty catalog."""
        scraper = BuScraper(mock_bu_db_session)
        html = load_fixture_bytes("classsearch_502.html")

        async def mock_get(url):
            mock_response = MagicMock()
            mock_response.status_code = 502
            mock_response.content = html
            mock_response.headers = {"content-type": "text/html"}
            return mock_response

        mock_client = AsyncMock()
        mock_client.get = mock_get
        scraper.client = mock_client

        with pytest.raises(BuFetchError) as exc_info:
            await scraper._fetch_all_pages()

        assert "HTTP 502" in str(exc_info.value)
        assert "response_size=145" in str(exc_info.value)
