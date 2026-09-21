"""Tests for Ohio State University course scraper."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import sys
from pathlib import Path
import httpx

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from scraper.scrapers.osu import (
    OsuScraper,
    PAGE_MAX_ATTEMPTS,
    format_osu_request_error,
)
from models.college import College

# Sample OSU API response data with classNumber field
SAMPLE_OSU_API_RESPONSE = {
    "data": {
        "courses": [
            {
                "course": {
                    "subject": "CSE",
                    "catalogNumber": "2221",
                    "title": "Software I: Software Components",
                },
                "sections": [
                    {
                        "classNumber": "5458",  # CRITICAL: Use classNumber, not section
                        "section": "0010",
                        "enrollmentStatus": "Open",
                    },
                    {
                        "classNumber": "5459",
                        "section": "0020",
                        "enrollmentStatus": "Closed",
                    },
                ],
            },
            {
                "course": {
                    "subject": "CSE",
                    "catalogNumber": "2231",
                    "title": "Software II: Software Development and Design",
                },
                "sections": [
                    {
                        "classNumber": "6789",
                        "section": "0010",
                        "enrollmentStatus": "Open",
                    },
                ],
            },
        ]
    }
}


@pytest.fixture
def mock_db_session():
    """Create a mock database session for OSU scraper."""
    mock_session = MagicMock()
    mock_college = College(
        id=1,
        name="Ohio State University",
        short_name="osu",
        term_code="1268",  # Autumn 2026
        term_name="Autumn 2026",
        is_active=True,
    )

    # Mock the query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_college
    mock_session.execute.return_value = mock_result

    return mock_session


@pytest.fixture
def scraper(mock_db_session):
    """Create an OSU scraper instance."""
    return OsuScraper(db_session=mock_db_session)


@pytest.mark.asyncio
async def test_scrape_all_courses(scraper):
    """Test scraping all OSU courses using catalog-number shard strategy."""
    with patch.object(
        scraper, "_fetch_all_courses", new_callable=AsyncMock
    ) as mock_fetch:
        # Mock API response
        mock_fetch.return_value = SAMPLE_OSU_API_RESPONSE["data"]["courses"]

        # Scrape courses
        courses = await scraper.scrape_courses("ALL")

        # Verify results
        assert len(courses) == 2
        assert courses[0]["course_code"] == "CSE 2221"
        assert courses[0]["title"] == "Software I: Software Components"
        assert len(courses[0]["classes"]) == 2
        # CRITICAL: Verify classNumber is used, not section code
        assert courses[0]["classes"][0]["class_number"] == "5458"
        assert courses[0]["classes"][0]["section"] == "0010"
        assert courses[0]["classes"][0]["status"] == "Open"
        assert courses[0]["classes"][1]["class_number"] == "5459"
        assert courses[0]["classes"][1]["status"] == "Closed"


@pytest.mark.asyncio
async def test_scrape_department_courses(scraper):
    """Test scraping courses for a specific department."""
    with patch.object(
        scraper, "_fetch_department_courses", new_callable=AsyncMock
    ) as mock_fetch:
        # Mock API response
        mock_fetch.return_value = SAMPLE_OSU_API_RESPONSE["data"]["courses"]

        # Scrape courses
        courses = await scraper.scrape_courses("CSE")

        # Verify results
        assert len(courses) == 2
        mock_fetch.assert_called_once_with("CSE", None)


@pytest.mark.asyncio
async def test_transform_courses(scraper):
    """Test course transformation."""
    raw_courses = SAMPLE_OSU_API_RESPONSE["data"]["courses"]
    courses = scraper._transform_courses(raw_courses)

    assert len(courses) == 2
    assert courses[0]["course_code"] == "CSE 2221"
    assert courses[1]["course_code"] == "CSE 2231"


def test_transform_single_course(scraper):
    """Test single course transformation."""
    raw_course = SAMPLE_OSU_API_RESPONSE["data"]["courses"][0]
    course = scraper._transform_single_course(raw_course)

    assert course is not None
    assert course["course_code"] == "CSE 2221"
    assert course["title"] == "Software I: Software Components"
    assert len(course["classes"]) == 2


def test_transform_section(scraper):
    """Test section transformation with classNumber."""
    section = SAMPLE_OSU_API_RESPONSE["data"]["courses"][0]["sections"][0]
    class_data = scraper._transform_section(section)

    assert class_data is not None
    # CRITICAL: Verify classNumber (5458) is used, not section code (0010)
    assert class_data["class_number"] == "5458"
    assert class_data["section"] == "0010"
    assert class_data["status"] == "Open"


def test_transform_section_closed(scraper):
    """Test section transformation with closed status."""
    section = SAMPLE_OSU_API_RESPONSE["data"]["courses"][0]["sections"][1]
    class_data = scraper._transform_section(section)

    assert class_data is not None
    assert class_data["class_number"] == "5459"
    assert class_data["status"] == "Closed"


@pytest.mark.asyncio
async def test_catalog_shard_strategy(scraper):
    """Test that catalog-number shard strategy queries multiple shards."""
    with patch.object(
        scraper, "_fetch_by_catalog_shard", new_callable=AsyncMock
    ) as mock_fetch_shard:
        # Mock response for each shard (return empty for most, sample data for shard 2)
        def shard_response(shard, max_pages=50):
            if shard == 2:
                return SAMPLE_OSU_API_RESPONSE["data"]["courses"]
            return []

        mock_fetch_shard.side_effect = shard_response

        # Call _fetch_all_courses which should query shards 1-8
        result = await scraper._fetch_all_courses()

        # Verify all 8 shards were queried (1xxx through 8xxx)
        assert mock_fetch_shard.call_count == 8

        # Verify shards 1-8 were called
        for i in range(1, 9):
            assert mock_fetch_shard.call_args_list[i - 1][0][0] == i

        # Verify results from shard 2 were returned
        assert len(result) == 2


@pytest.mark.asyncio
async def test_fetch_by_catalog_shard(scraper):
    """Test fetching courses for a specific catalog number shard."""
    with patch.object(
        scraper, "_make_api_request", new_callable=AsyncMock
    ) as mock_request:
        # Mock API response for shard 2 (2xxx courses)
        mock_request.return_value = SAMPLE_OSU_API_RESPONSE

        # Fetch shard 2 courses (catalog numbers 2xxx)
        result = await scraper._fetch_by_catalog_shard(2, max_pages=1)

        # Verify request was made with correct parameters
        mock_request.assert_called_once()
        call_params = mock_request.call_args[0][0]
        assert call_params["q"] == ""
        assert call_params["catalog-number"] == "2xxx"  # Catalog number shard
        assert call_params["term"] == "1268"
        assert call_params["p"] == "1"

        # Verify result
        assert len(result) == 2


@pytest.mark.asyncio
async def test_max_pages_hard_limit(scraper):
    """Test that max_pages is hard limited to 50 to prevent API 503 errors."""
    with patch.object(
        scraper, "_make_api_request", new_callable=AsyncMock
    ) as mock_request:
        # Mock empty response to stop iteration
        mock_request.return_value = {"data": {"courses": []}}

        # Try to fetch with max_pages > 50
        result = await scraper._fetch_by_catalog_shard(1, max_pages=100)

        # Should have been capped at 50 pages max
        # With 3 consecutive empty pages stopping condition, it stops at page 3
        assert mock_request.call_count <= 3


def test_class_number_from_api_field(scraper):
    """Test that class_number comes from API's classNumber field, not section."""
    section_data = {
        "classNumber": "12345",  # This should be used
        "section": "0010",  # This should NOT be used for class_number
        "enrollmentStatus": "Open",
    }

    class_data = scraper._transform_section(section_data)

    # CRITICAL: Verify classNumber is used for class_number
    assert class_data["class_number"] == "12345"
    # And section code is preserved separately
    assert class_data["section"] == "0010"


@pytest.mark.asyncio
async def test_department_fetch_paginates_past_small_pages(scraper):
    """Test that department fetch continues paginating when pages return ~50-55 items.

    REGRESSION TEST: Previously stopped when len(courses) < 200, which broke after
    page 1 since OSU API returns ~50-55 courses per page for departments like CSE.
    """
    with patch.object(
        scraper, "_make_api_request", new_callable=AsyncMock
    ) as mock_request:
        # Simulate OSU API behavior for CSE:
        # - Page 1: 55 courses (typical page size)
        # - Page 2: 50 courses (still full page)
        # - Page 3: 15 courses (small page, end of results)

        def mock_api_response(params):
            page = int(params.get("p", "1"))

            # Create mock course data with unique class numbers per page
            def make_course(class_num, page_num):
                return {
                    "course": {
                        "subject": "CSE",
                        "catalogNumber": f"{2000 + class_num}",
                        "title": f"Course {class_num} Page {page_num}",
                    },
                    "sections": [
                        {
                            "classNumber": f"{page_num}{class_num:03d}",
                            "section": "0010",
                            "enrollmentStatus": "Open",
                        }
                    ],
                }

            if page == 1:
                # Page 1: 55 courses
                courses = [make_course(i, page) for i in range(55)]
            elif page == 2:
                # Page 2: 50 courses
                courses = [make_course(i, page) for i in range(50)]
            elif page == 3:
                # Page 3: 15 courses (small page, should stop here)
                courses = [make_course(i, page) for i in range(15)]
            else:
                # No page 4+
                courses = []

            return {"data": {"courses": courses}}

        mock_request.side_effect = mock_api_response

        # Fetch department courses
        result = await scraper._fetch_department_courses("CSE")

        # Should have fetched 3 pages (55 + 50 + 15 = 120 raw courses)
        assert mock_request.call_count == 3
        assert len(result) == 120

        # Verify the pages were requested in order
        assert mock_request.call_args_list[0][0][0]["p"] == "1"
        assert mock_request.call_args_list[1][0][0]["p"] == "2"
        assert mock_request.call_args_list[2][0][0]["p"] == "3"


class _EmptyStrError(Exception):
    """Mirrors httpx/httpcore transport disconnects whose str(e) is empty."""

    def __str__(self) -> str:
        return ""


def test_format_empty_str_exception_includes_type_and_repr():
    """Empty str(e) must still log type, repr, and the request shard/page."""
    exc = _EmptyStrError()
    params = {"q": "", "term": "1268", "catalog-number": "3xxx", "p": "12"}

    formatted = format_osu_request_error(exc, params)

    assert type(exc).__name__ in formatted
    assert repr(exc) in formatted
    assert "catalog-number" in formatted
    assert "3xxx" in formatted
    assert "p" in formatted
    assert "12" in formatted
    assert "https://content.osu.edu/v2/classes/search" in formatted
    # Must not collapse to a blank / unknown-style message
    assert formatted.strip() != ""
    assert "Unknown error" not in formatted


def test_format_named_http_error_surfaces_message():
    """Known HTTP errors keep their original message (not type-only)."""
    request = httpx.Request("GET", "https://content.osu.edu/v2/classes/search")
    response = httpx.Response(503, request=request)
    exc = httpx.HTTPStatusError(
        "Server error '503 Service Unavailable' for url 'https://content.osu.edu/v2/classes/search'",
        request=request,
        response=response,
    )
    params = {"catalog-number": "1xxx", "p": "51"}

    formatted = format_osu_request_error(exc, params)

    assert "503" in formatted
    assert "Service Unavailable" in formatted or "HTTPStatusError" in formatted
    assert "1xxx" in formatted
    assert str(exc).strip() != ""
    assert str(exc) in formatted or "503" in formatted


@pytest.mark.asyncio
async def test_make_api_request_retries_then_aborts_on_empty_transport(scraper):
    """Page-level retry on empty transport errors, then abort the attempt."""
    empty_exc = httpx.RemoteProtocolError("")
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=empty_exc)
    mock_client.aclose = AsyncMock()
    scraper.client = mock_client
    params = {"q": "", "term": "1268", "catalog-number": "2xxx", "p": "7"}

    with patch.object(scraper, "_reset_client", new_callable=AsyncMock) as mock_reset:
        with patch("scraper.scrapers.osu.asyncio.sleep", new_callable=AsyncMock):
            with patch("scraper.scrapers.osu.logger") as mock_logger:
                with pytest.raises(RuntimeError) as exc_info:
                    await scraper._make_api_request(params)

    assert mock_client.get.call_count == PAGE_MAX_ATTEMPTS
    # Reset before each retry, not after the final abort
    assert mock_reset.call_count == PAGE_MAX_ATTEMPTS - 1

    error_text = str(exc_info.value)
    assert "RemoteProtocolError" in error_text
    assert repr(empty_exc) in error_text or "RemoteProtocolError" in error_text
    assert "2xxx" in error_text
    assert "7" in error_text

    logged = " ".join(
        str(call)
        for call in mock_logger.warning.call_args_list
        + mock_logger.error.call_args_list
    )
    assert "RemoteProtocolError" in logged
    assert "2xxx" in logged


@pytest.mark.asyncio
async def test_make_api_request_recovers_after_page_retry(scraper):
    """A single transport blip should retry the same page and continue."""
    mock_response = MagicMock()
    mock_response.content = b'{"data": {"courses": []}}'
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(
        side_effect=[httpx.RemoteProtocolError(""), mock_response]
    )
    mock_client.aclose = AsyncMock()
    scraper.client = mock_client

    with patch.object(scraper, "_reset_client", new_callable=AsyncMock):
        with patch("scraper.scrapers.osu.asyncio.sleep", new_callable=AsyncMock):
            result = await scraper._make_api_request(
                {"catalog-number": "4xxx", "p": "1"}
            )

    assert result == {"data": {"courses": []}}
    assert mock_client.get.call_count == 2
    assert scraper.request_count == 1


@pytest.mark.asyncio
async def test_make_api_request_http_error_surfaces_message_without_retry(scraper):
    """Named HTTP errors surface their message and do not burn page retries."""
    request = httpx.Request("GET", "https://content.osu.edu/v2/classes/search")
    response = httpx.Response(404, request=request)
    http_error = httpx.HTTPStatusError(
        "Client error '404 Not Found' for url 'https://content.osu.edu/v2/classes/search'",
        request=request,
        response=response,
    )

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=http_error)
    scraper.client = mock_client
    params = {"q": "CSE", "term": "1268", "p": "1"}

    with patch.object(scraper, "_reset_client", new_callable=AsyncMock) as mock_reset:
        with patch("scraper.scrapers.osu.logger") as mock_logger:
            with pytest.raises(httpx.HTTPStatusError) as exc_info:
                await scraper._make_api_request(params)

    assert mock_client.get.call_count == 1
    mock_reset.assert_not_called()
    assert "404" in str(exc_info.value)
    assert "Not Found" in str(exc_info.value)

    logged = " ".join(str(call) for call in mock_logger.error.call_args_list)
    assert "404" in logged
    assert "HTTPStatusError" in logged or "404" in logged
    assert "CSE" in logged or "p" in logged


@pytest.mark.asyncio
async def test_fetch_all_courses_aborts_remaining_shards_after_page_failure(scraper):
    """Unrecoverable page error must abort the attempt, not finish 8 shards."""
    with patch.object(
        scraper,
        "_make_api_request",
        new_callable=AsyncMock,
        side_effect=RuntimeError(
            "RemoteProtocolError: RemoteProtocolError('') "
            "[url=https://content.osu.edu/v2/classes/search "
            "params={'catalog-number': '1xxx', 'p': '3'}]"
        ),
    ) as mock_request:
        with pytest.raises(RuntimeError) as exc_info:
            await scraper._fetch_all_courses()

    # Failed on shard 1 page 1 — do not walk shards 2-8
    assert mock_request.call_count == 1
    assert "RemoteProtocolError" in str(exc_info.value)
