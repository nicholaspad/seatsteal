"""Tests for Ohio State University course scraper."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import sys
from pathlib import Path

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from scraper.scrapers.osu import OsuScraper


# Sample OSU API response data
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
                        "section": "12345",
                        "enrollmentStatus": "Open",
                    },
                    {
                        "section": "12346",
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
                        "section": "23456",
                        "enrollmentStatus": "Open",
                    },
                ],
            },
        ]
    }
}


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    mock_session = MagicMock()
    mock_session.execute.return_value.scalar_one_or_none.return_value = MagicMock(
        term_code="1262"  # Spring 2026
    )
    return mock_session


@pytest.fixture
def scraper(mock_db_session):
    """Create an OSU scraper instance."""
    return OsuScraper(db_session=mock_db_session)


@pytest.mark.asyncio
async def test_scrape_all_courses(scraper):
    """Test scraping all OSU courses."""
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
        assert courses[0]["classes"][0]["class_number"] == "12345"
        assert courses[0]["classes"][0]["status"] == "Open"
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
    """Test section transformation."""
    section = SAMPLE_OSU_API_RESPONSE["data"]["courses"][0]["sections"][0]
    class_data = scraper._transform_section(section)

    assert class_data is not None
    assert class_data["class_number"] == "12345"
    assert class_data["section"] == "12345"
    assert class_data["status"] == "Open"


def test_transform_section_closed(scraper):
    """Test section transformation with closed status."""
    section = SAMPLE_OSU_API_RESPONSE["data"]["courses"][0]["sections"][1]
    class_data = scraper._transform_section(section)

    assert class_data is not None
    assert class_data["status"] == "Closed"
