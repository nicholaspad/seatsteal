"""Tests for University of Florida course scraper."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy.orm import Session

import sys
from pathlib import Path

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from scraper.scrapers.uf import UfScraper
from models.college import College
from tests.test_scrapers.conftest import create_mock_response


# Sample UF API response data

SAMPLE_UF_API_RESPONSE = [
    {
        "COURSES": [
            {
                "code": "COP3502",
                "name": "Programming Fundamentals 1",
                "sections": [
                    {
                        "classNumber": "12345",
                        "number": "001",
                        "addEligible": "Y",
                        "waitList": {"isEligible": "N"},
                    },
                    {
                        "classNumber": "12346",
                        "number": "002",
                        "addEligible": "N",
                        "waitList": {"isEligible": "Y"},
                    },
                    {
                        "classNumber": "12347",
                        "number": "003",
                        "addEligible": "N",
                        "waitList": {"isEligible": "N"},
                    },
                ],
            },
            {
                "code": "COP3503",
                "name": "Programming Fundamentals 2",
                "sections": [
                    {
                        "classNumber": "23456",
                        "number": "001",
                        "addEligible": "Y",
                        "waitList": {"isEligible": "N"},
                    }
                ],
            },
        ],
        "LASTCONTROLNUMBER": 0,
        "TOTALROWS": 2,
        "RETRIEVEDROWS": 2,
    }
]

SAMPLE_UF_API_RESPONSE_PAGE1 = [
    {
        "COURSES": [
            {
                "code": "COP3502",
                "name": "Programming Fundamentals 1",
                "sections": [
                    {
                        "classNumber": "12345",
                        "number": "001",
                        "addEligible": "Y",
                        "waitList": {"isEligible": "N"},
                    }
                ],
            }
        ],
        "LASTCONTROLNUMBER": 12345,
        "TOTALROWS": 100,
        "RETRIEVEDROWS": 50,
    }
]

SAMPLE_UF_API_RESPONSE_PAGE2 = [
    {
        "COURSES": [
            {
                "code": "COP3503",
                "name": "Programming Fundamentals 2",
                "sections": [
                    {
                        "classNumber": "23456",
                        "number": "001",
                        "addEligible": "Y",
                        "waitList": {"isEligible": "N"},
                    }
                ],
            }
        ],
        "LASTCONTROLNUMBER": 12345,  # Same as previous (end of pagination)
        "TOTALROWS": 100,
        "RETRIEVEDROWS": 50,
    }
]

SAMPLE_UF_API_RESPONSE_EMPTY = []

SAMPLE_UF_API_RESPONSE_MIXED_DEPTS = [
    {
        "COURSES": [
            {
                "code": "COP3502",
                "name": "Programming Fundamentals 1",
                "sections": [
                    {
                        "classNumber": "12345",
                        "number": "001",
                        "addEligible": "Y",
                        "waitList": {"isEligible": "N"},
                    }
                ],
            },
            {
                "code": "MAC2311",
                "name": "Calculus 1",
                "sections": [
                    {
                        "classNumber": "34567",
                        "number": "001",
                        "addEligible": "Y",
                        "waitList": {"isEligible": "N"},
                    }
                ],
            },
        ],
        "LASTCONTROLNUMBER": 0,
        "TOTALROWS": 2,
        "RETRIEVEDROWS": 2,
    }
]


@pytest.fixture
def mock_uf_db_session():
    """Create a mock database session for UF scraper."""
    mock_session = MagicMock(spec=Session)
    mock_college = College(
        id=1,
        name="University of Florida",
        short_name="uf",
        term_code="2024SP",
        term_name="Spring 2024",
        is_active=True,
    )

    # Mock the query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_college
    mock_session.execute.return_value = mock_result

    return mock_session


class TestUfScraper:
    """Tests for UfScraper class."""

    @pytest.mark.unit
    def test_init_sets_college_and_term(self, mock_uf_db_session):
        """Test that scraper correctly initializes with college and term code."""
        scraper = UfScraper(mock_uf_db_session)

        assert scraper.college_short_name == "uf"
        assert scraper.current_term == "2024SP"

    # Section transformation tests

    @pytest.mark.unit
    def test_transform_section_open_status(self, mock_uf_db_session):
        """Test section with addEligible='Y' gets 'Open' status."""
        scraper = UfScraper(mock_uf_db_session)

        section = {
            "classNumber": "12345",
            "number": "001",
            "addEligible": "Y",
            "waitList": {"isEligible": "N"},
        }

        result = scraper._transform_section(section)

        assert result is not None
        assert result["class_number"] == "12345"
        assert result["section"] == "001"
        assert result["status"] == "Open"

    @pytest.mark.unit
    def test_transform_section_waitlist_status(self, mock_uf_db_session):
        """Test section with addEligible='N' and waitlist eligible gets 'Waitlist' status."""
        scraper = UfScraper(mock_uf_db_session)

        section = {
            "classNumber": "12346",
            "number": "002",
            "addEligible": "N",
            "waitList": {"isEligible": "Y"},
        }

        result = scraper._transform_section(section)

        assert result is not None
        assert result["class_number"] == "12346"
        assert result["section"] == "002"
        assert result["status"] == "Waitlist"

    @pytest.mark.unit
    def test_transform_section_closed_status(self, mock_uf_db_session):
        """Test section with addEligible='N' and no waitlist gets 'Closed' status."""
        scraper = UfScraper(mock_uf_db_session)

        section = {
            "classNumber": "12347",
            "number": "003",
            "addEligible": "N",
            "waitList": {"isEligible": "N"},
        }

        result = scraper._transform_section(section)

        assert result is not None
        assert result["class_number"] == "12347"
        assert result["section"] == "003"
        assert result["status"] == "Closed"

    @pytest.mark.unit
    def test_transform_section_unknown_status(self, mock_uf_db_session):
        """Test section with missing addEligible gets 'Unknown' status."""
        scraper = UfScraper(mock_uf_db_session)

        section = {
            "classNumber": "12348",
            "number": "004",
            "waitList": {"isEligible": "N"},
        }

        result = scraper._transform_section(section)

        assert result is not None
        assert result["class_number"] == "12348"
        assert result["section"] == "004"
        assert result["status"] == "Unknown"

    @pytest.mark.unit
    def test_transform_section_missing_class_number(self, mock_uf_db_session):
        """Test that section without class number returns None."""
        scraper = UfScraper(mock_uf_db_session)

        section = {
            "number": "001",
            "addEligible": "Y",
            "waitList": {"isEligible": "N"},
        }

        result = scraper._transform_section(section)

        assert result is None

    @pytest.mark.unit
    def test_transform_section_empty_section_code(self, mock_uf_db_session):
        """Test that section handles missing section number gracefully."""
        scraper = UfScraper(mock_uf_db_session)

        section = {
            "classNumber": "12345",
            "addEligible": "Y",
            "waitList": {"isEligible": "N"},
        }

        result = scraper._transform_section(section)

        assert result is not None
        assert result["class_number"] == "12345"
        assert result["section"] == ""

    # Single course transformation tests

    @pytest.mark.unit
    def test_transform_single_course_valid(self, mock_uf_db_session):
        """Test transforming a valid course with sections."""
        scraper = UfScraper(mock_uf_db_session)

        raw_course = {
            "code": "COP3502",
            "name": "Programming Fundamentals 1",
            "sections": [
                {
                    "classNumber": "12345",
                    "number": "001",
                    "addEligible": "Y",
                    "waitList": {"isEligible": "N"},
                }
            ],
        }

        result = scraper._transform_single_course(raw_course)

        assert result is not None
        assert result["course_code"] == "COP3502"
        assert result["title"] == "Programming Fundamentals 1"
        assert len(result["classes"]) == 1
        assert result["classes"][0]["class_number"] == "12345"
        assert result["classes"][0]["status"] == "Open"

    @pytest.mark.unit
    def test_transform_single_course_missing_code(self, mock_uf_db_session):
        """Test that course without code returns None."""
        scraper = UfScraper(mock_uf_db_session)

        raw_course = {
            "name": "Programming Fundamentals 1",
            "sections": [
                {
                    "classNumber": "12345",
                    "number": "001",
                    "addEligible": "Y",
                    "waitList": {"isEligible": "N"},
                }
            ],
        }

        result = scraper._transform_single_course(raw_course)

        assert result is None

    @pytest.mark.unit
    def test_transform_single_course_missing_title(self, mock_uf_db_session):
        """Test that course without title returns None."""
        scraper = UfScraper(mock_uf_db_session)

        raw_course = {
            "code": "COP3502",
            "sections": [
                {
                    "classNumber": "12345",
                    "number": "001",
                    "addEligible": "Y",
                    "waitList": {"isEligible": "N"},
                }
            ],
        }

        result = scraper._transform_single_course(raw_course)

        assert result is None

    @pytest.mark.unit
    def test_transform_single_course_no_sections(self, mock_uf_db_session):
        """Test that course with no sections returns None."""
        scraper = UfScraper(mock_uf_db_session)

        raw_course = {
            "code": "COP3502",
            "name": "Programming Fundamentals 1",
            "sections": [],
        }

        result = scraper._transform_single_course(raw_course)

        assert result is None

    @pytest.mark.unit
    def test_transform_single_course_invalid_sections(self, mock_uf_db_session):
        """Test that course filters out invalid sections."""
        scraper = UfScraper(mock_uf_db_session)

        raw_course = {
            "code": "COP3502",
            "name": "Programming Fundamentals 1",
            "sections": [
                # Valid section
                {
                    "classNumber": "12345",
                    "number": "001",
                    "addEligible": "Y",
                    "waitList": {"isEligible": "N"},
                },
                # Invalid section (no class number)
                {"number": "002", "addEligible": "Y", "waitList": {"isEligible": "N"}},
            ],
        }

        result = scraper._transform_single_course(raw_course)

        assert result is not None
        assert len(result["classes"]) == 1
        assert result["classes"][0]["class_number"] == "12345"

    # Courses transformation tests

    @pytest.mark.unit
    def test_transform_courses_deduplication(self, mock_uf_db_session):
        """Test that duplicate course codes are removed (keeps first occurrence)."""
        scraper = UfScraper(mock_uf_db_session)

        raw_courses = [
            {
                "code": "COP3502",
                "name": "Programming Fundamentals 1",
                "sections": [
                    {
                        "classNumber": "12345",
                        "number": "001",
                        "addEligible": "Y",
                        "waitList": {"isEligible": "N"},
                    }
                ],
            },
            {
                "code": "COP3502",  # Duplicate
                "name": "Programming Fundamentals 1 - Duplicate",
                "sections": [
                    {
                        "classNumber": "99999",
                        "number": "002",
                        "addEligible": "Y",
                        "waitList": {"isEligible": "N"},
                    }
                ],
            },
        ]

        result = scraper._transform_courses(raw_courses)

        assert len(result) == 1
        assert result[0]["course_code"] == "COP3502"
        # Should keep first occurrence
        assert result[0]["classes"][0]["class_number"] == "12345"

    @pytest.mark.unit
    def test_transform_courses_with_limit(self, mock_uf_db_session):
        """Test that limiting stops at specified count."""
        scraper = UfScraper(mock_uf_db_session)

        raw_courses = [
            {
                "code": f"COP350{i}",
                "name": f"Course {i}",
                "sections": [
                    {
                        "classNumber": f"1234{i}",
                        "number": "001",
                        "addEligible": "Y",
                        "waitList": {"isEligible": "N"},
                    }
                ],
            }
            for i in range(10)
        ]

        result = scraper._transform_courses(raw_courses, limit=3)

        assert len(result) == 3

    @pytest.mark.unit
    def test_transform_courses_handles_errors(self, mock_uf_db_session):
        """Test that transformation continues when individual courses fail."""
        scraper = UfScraper(mock_uf_db_session)

        raw_courses = [
            # Valid course
            {
                "code": "COP3502",
                "name": "Programming Fundamentals 1",
                "sections": [
                    {
                        "classNumber": "12345",
                        "number": "001",
                        "addEligible": "Y",
                        "waitList": {"isEligible": "N"},
                    }
                ],
            },
            # Invalid course (missing code)
            {
                "name": "Invalid Course",
                "sections": [
                    {
                        "classNumber": "99999",
                        "number": "001",
                        "addEligible": "Y",
                        "waitList": {"isEligible": "N"},
                    }
                ],
            },
            # Another valid course
            {
                "code": "COP3503",
                "name": "Programming Fundamentals 2",
                "sections": [
                    {
                        "classNumber": "23456",
                        "number": "001",
                        "addEligible": "Y",
                        "waitList": {"isEligible": "N"},
                    }
                ],
            },
        ]

        result = scraper._transform_courses(raw_courses)

        # Should skip the invalid course and continue
        assert len(result) == 2
        assert result[0]["course_code"] == "COP3502"
        assert result[1]["course_code"] == "COP3503"

    # Integration tests for category fetching

    @pytest.mark.asyncio
    async def test_fetch_category_single_page(self, mock_uf_db_session):
        """Test fetching a category with one page of results."""
        scraper = UfScraper(mock_uf_db_session)
        await scraper._ensure_client()

        # Mock the HTTP response
        mock_response = create_mock_response(SAMPLE_UF_API_RESPONSE)
        scraper.client.get = AsyncMock(return_value=mock_response)

        result = await scraper._fetch_category("CWSP")

        assert len(result) == 2
        assert result[0]["code"] == "COP3502"
        assert result[1]["code"] == "COP3503"

        # Verify the URL and params
        scraper.client.get.assert_called()
        call_args = scraper.client.get.call_args
        assert "https://one.uf.edu/apix/soc/schedule" in str(call_args)

        # Clean up
        await scraper.client.aclose()

    @pytest.mark.asyncio
    async def test_fetch_category_pagination(self, mock_uf_db_session):
        """Test multi-page pagination with control numbers."""
        scraper = UfScraper(mock_uf_db_session)
        await scraper._ensure_client()

        # Mock responses for concurrent batch pagination (BATCH_SIZE=5)
        # First call gets PAGE1, batch calls get PAGE2 and empty responses
        mock_response1 = create_mock_response(SAMPLE_UF_API_RESPONSE_PAGE1)
        mock_response2 = create_mock_response(SAMPLE_UF_API_RESPONSE_PAGE2)
        mock_response_empty = create_mock_response(SAMPLE_UF_API_RESPONSE_EMPTY)
        scraper.client.get = AsyncMock(
            side_effect=[
                mock_response1,  # Initial call (control=0)
                mock_response2,  # Batch call 1 (control=12346) - has COP3503
                mock_response_empty,  # Batch call 2 (control=12347) - empty, signals end
                mock_response_empty,  # Batch call 3 (control=12348) - empty
                mock_response_empty,  # Batch call 4 (control=12349) - empty
            ]
        )

        result = await scraper._fetch_category("CWSP")

        # Should have accumulated courses from both pages
        assert len(result) == 2
        assert result[0]["code"] == "COP3502"
        assert result[1]["code"] == "COP3503"

        # Scraper uses concurrent batch pagination with BATCH_SIZE=5
        # Makes 1 initial call + up to 4 concurrent calls in batch = 5 total
        assert scraper.client.get.call_count == 5

        # Clean up
        await scraper.client.aclose()

    @pytest.mark.asyncio
    async def test_fetch_category_empty_response(self, mock_uf_db_session):
        """Test handling empty response."""
        scraper = UfScraper(mock_uf_db_session)
        await scraper._ensure_client()

        # Mock empty response
        mock_response = create_mock_response(SAMPLE_UF_API_RESPONSE_EMPTY)
        scraper.client.get = AsyncMock(return_value=mock_response)

        result = await scraper._fetch_category("CWSP")

        assert len(result) == 0

        # Clean up
        await scraper.client.aclose()

    @pytest.mark.asyncio
    @patch("asyncio.sleep", new_callable=AsyncMock)
    async def test_fetch_all_categories(self, mock_sleep, mock_uf_db_session):
        """Test fetching all three categories."""
        scraper = UfScraper(mock_uf_db_session)
        await scraper._ensure_client()

        # Mock responses for each category
        mock_response = create_mock_response(SAMPLE_UF_API_RESPONSE)
        scraper.client.get = AsyncMock(return_value=mock_response)

        result = await scraper._fetch_all_categories()

        # Should have courses from all 3 categories (CWSP, RES, HUR)
        # Each category returns 2 courses, so total should be 6
        assert len(result) == 6

        # Should have made 3 HTTP calls (one per category)
        assert scraper.client.get.call_count == 3

        # Verify 1-second delay called after each category (3 times for 3 categories)
        assert mock_sleep.call_count == 3
        # Check that the 1.0 second sleep was called
        assert any(call[0][0] == 1.0 for call in mock_sleep.call_args_list)

        # Clean up
        await scraper.client.aclose()

    # Integration tests for main scraping method

    @pytest.mark.asyncio
    async def test_scrape_courses_specific_department(self, mock_uf_db_session):
        """Test department filtering."""
        scraper = UfScraper(mock_uf_db_session)

        # Mock _fetch_all_categories to return mixed departments
        with patch.object(
            scraper,
            "_fetch_all_categories",
            new_callable=AsyncMock,
            return_value=SAMPLE_UF_API_RESPONSE_MIXED_DEPTS[0]["COURSES"],
        ):
            result = await scraper.scrape_courses("COP")

            # Should only return COP courses
            assert len(result) == 1
            assert result[0]["course_code"] == "COP3502"

    @pytest.mark.asyncio
    async def test_scrape_courses_all_departments(self, mock_uf_db_session):
        """Test scraping all departments."""
        scraper = UfScraper(mock_uf_db_session)

        # Mock _fetch_all_categories
        with patch.object(
            scraper,
            "_fetch_all_categories",
            new_callable=AsyncMock,
            return_value=SAMPLE_UF_API_RESPONSE_MIXED_DEPTS[0]["COURSES"],
        ):
            result = await scraper.scrape_courses("ALL")

            # Should return all courses (no filtering)
            assert len(result) == 2
            assert result[0]["course_code"] == "COP3502"
            assert result[1]["course_code"] == "MAC2311"

    @pytest.mark.asyncio
    async def test_scrape_courses_with_limit(self, mock_uf_db_session):
        """Test limit parameter propagates correctly."""
        scraper = UfScraper(mock_uf_db_session)

        # Mock _fetch_all_categories
        with patch.object(
            scraper,
            "_fetch_all_categories",
            new_callable=AsyncMock,
            return_value=SAMPLE_UF_API_RESPONSE_MIXED_DEPTS[0]["COURSES"],
        ):
            result = await scraper.scrape_courses("ALL", limit=1)

            # Should only return 1 course due to limit
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_scrape_courses_client_cleanup(self, mock_uf_db_session):
        """Test HTTP client is properly closed after scraping."""
        scraper = UfScraper(mock_uf_db_session)

        # Mock _fetch_all_categories
        with patch.object(
            scraper,
            "_fetch_all_categories",
            new_callable=AsyncMock,
            return_value=SAMPLE_UF_API_RESPONSE[0]["COURSES"],
        ):
            await scraper.scrape_courses("ALL")

            # Client should be closed
            assert scraper.client is None

    @pytest.mark.asyncio
    async def test_scrape_courses_client_cleanup_on_error(self, mock_uf_db_session):
        """Test HTTP client is properly closed even on error."""
        scraper = UfScraper(mock_uf_db_session)

        # Mock _fetch_all_categories to raise an exception
        with patch.object(
            scraper,
            "_fetch_all_categories",
            new_callable=AsyncMock,
            side_effect=Exception("Test error"),
        ):
            with pytest.raises(Exception, match="Test error"):
                await scraper.scrape_courses("ALL")

            # Client should still be closed
            assert scraper.client is None
