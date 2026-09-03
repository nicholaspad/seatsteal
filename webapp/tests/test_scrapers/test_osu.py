"""Tests for Ohio State University course scraper."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import sys
from pathlib import Path

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from scraper.scrapers.osu import OsuScraper
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
