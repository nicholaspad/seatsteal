"""Tests for UC Irvine course scraper."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.orm import Session

import sys
from pathlib import Path

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from scraper.scrapers.uci import UciScraper
from models.college import College
from tests.test_scrapers.conftest import create_mock_response


# Sample UCI API response data
SAMPLE_UCI_API_RESPONSE = {
    "ok": True,
    "data": {
        "schools": [
            {
                "departments": [
                    {
                        "courses": [
                            {
                                "deptCode": "COMPSCI",
                                "courseNumber": "161",
                                "courseTitle": "Design of Very Large Scale Systems",
                                "sections": [
                                    {
                                        "sectionCode": "51234",
                                        "sectionType": "Lec",
                                        "sectionNum": "A",
                                        "status": "OPEN",
                                    },
                                    {
                                        "sectionCode": "51235",
                                        "sectionType": "Dis",
                                        "sectionNum": "1",
                                        "status": "FULL",
                                    },
                                ],
                            },
                            {
                                "deptCode": "COMPSCI",
                                "courseNumber": "171",
                                "courseTitle": "Introduction to AI",
                                "sections": [
                                    {
                                        "sectionCode": "51240",
                                        "sectionType": "Lec",
                                        "sectionNum": "A",
                                        "status": "WAITL",
                                    }
                                ],
                            },
                            {
                                "deptCode": "I&C SCI",
                                "courseNumber": "45C",
                                "courseTitle": "Programming in C/C++",
                                "sections": [
                                    {
                                        "sectionCode": "51250",
                                        "sectionType": "Lec",
                                        "sectionNum": "A",
                                        "status": "NEWONLY",
                                    }
                                ],
                            },
                        ]
                    }
                ]
            }
        ]
    },
}

# Sample response with variable topic courses (same course code, different titles)
SAMPLE_UCI_VARIABLE_TOPIC_RESPONSE = {
    "ok": True,
    "data": {
        "schools": [
            {
                "departments": [
                    {
                        "courses": [
                            {
                                "deptCode": "ECO EVO",
                                "courseNumber": "200B",
                                "courseTitle": "Advanced Topics in Ecology",
                                "sections": [
                                    {
                                        "sectionCode": "12345",
                                        "sectionType": "Sem",
                                        "sectionNum": "1",
                                        "status": "OPEN",
                                    }
                                ],
                            },
                            {
                                "deptCode": "ECO EVO",
                                "courseNumber": "200B",
                                "courseTitle": "Advanced Topics in Evolution",
                                "sections": [
                                    {
                                        "sectionCode": "12346",
                                        "sectionType": "Sem",
                                        "sectionNum": "2",
                                        "status": "OPEN",
                                    }
                                ],
                            },
                        ]
                    }
                ]
            }
        ]
    },
}


@pytest.fixture
def mock_uci_db_session():
    """Create a mock database session for UCI scraper."""
    mock_session = MagicMock(spec=Session)
    mock_college = College(
        id=1,
        name="University of California, Irvine",
        short_name="uci",
        term_code="2026:Spring",
        term_name="Spring 2026",
        is_active=True,
    )

    # Mock the query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_college
    mock_session.execute.return_value = mock_result

    return mock_session


class TestUciScraper:
    """Tests for UciScraper class."""

    @pytest.mark.unit
    def test_init_sets_college_short_name(self, mock_uci_db_session):
        """Test that scraper correctly sets college short name."""
        scraper = UciScraper(mock_uci_db_session)

        assert scraper.college_short_name == "uci"

    @pytest.mark.unit
    def test_init_gets_term_code_from_db(self, mock_uci_db_session):
        """Test that scraper correctly retrieves term code from database."""
        scraper = UciScraper(mock_uci_db_session)

        assert scraper.current_term == "2026:Spring"

    @pytest.mark.unit
    def test_parse_term_code_valid_spring(self, mock_uci_db_session):
        """Test parsing valid Spring term code."""
        scraper = UciScraper(mock_uci_db_session)

        assert scraper.year == "2026"
        assert scraper.quarter == "Spring"

    @pytest.mark.unit
    def test_parse_term_code_valid_fall(self, mock_uci_db_session):
        """Test parsing valid Fall term code."""
        mock_session = MagicMock(spec=Session)
        mock_college = College(
            id=1,
            name="University of California, Irvine",
            short_name="uci",
            term_code="2026:Fall",
            term_name="Fall 2026",
            is_active=True,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_college
        mock_session.execute.return_value = mock_result

        scraper = UciScraper(mock_session)

        assert scraper.year == "2026"
        assert scraper.quarter == "Fall"

    @pytest.mark.unit
    def test_parse_term_code_valid_summer(self, mock_uci_db_session):
        """Test parsing valid Summer term codes."""
        for summer_term in ["Summer1", "Summer10wk", "Summer2"]:
            mock_session = MagicMock(spec=Session)
            mock_college = College(
                id=1,
                name="University of California, Irvine",
                short_name="uci",
                term_code=f"2026:{summer_term}",
                term_name=f"{summer_term} 2026",
                is_active=True,
            )
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_college
            mock_session.execute.return_value = mock_result

            scraper = UciScraper(mock_session)

            assert scraper.year == "2026"
            assert scraper.quarter == summer_term

    @pytest.mark.unit
    def test_parse_term_code_invalid_format(self, mock_uci_db_session):
        """Test that invalid term code format raises ValueError."""
        mock_session = MagicMock(spec=Session)
        mock_college = College(
            id=1,
            name="University of California, Irvine",
            short_name="uci",
            term_code="2026Spring",  # Missing colon
            term_name="Spring 2026",
            is_active=True,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_college
        mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError) as exc_info:
            UciScraper(mock_session)

        assert "Invalid UCI term code format" in str(exc_info.value)
        assert "2026Spring" in str(exc_info.value)

    @pytest.mark.unit
    def test_transform_section_status_open(self, mock_uci_db_session):
        """Test transformation with OPEN status."""
        scraper = UciScraper(mock_uci_db_session)

        section = {
            "sectionCode": "12345",
            "sectionType": "Lec",
            "sectionNum": "A",
            "status": "OPEN",
        }
        result = scraper._transform_section(section)

        assert result is not None
        assert result["class_number"] == "12345"
        assert result["section"] == "Lec A"
        assert result["status"] == "Open"

    @pytest.mark.unit
    def test_transform_section_status_full(self, mock_uci_db_session):
        """Test transformation with FULL status."""
        scraper = UciScraper(mock_uci_db_session)

        section = {
            "sectionCode": "12345",
            "sectionType": "Dis",
            "sectionNum": "1",
            "status": "FULL",
        }
        result = scraper._transform_section(section)

        assert result is not None
        assert result["status"] == "Closed"

    @pytest.mark.unit
    def test_transform_section_status_waitlist(self, mock_uci_db_session):
        """Test transformation with WAITL and WAITLIST status."""
        scraper = UciScraper(mock_uci_db_session)

        for status in ["WAITL", "WAITLIST"]:
            section = {
                "sectionCode": "12345",
                "sectionType": "Lec",
                "sectionNum": "A",
                "status": status,
            }
            result = scraper._transform_section(section)

            assert result is not None
            assert result["status"] == "Waitlist"

    @pytest.mark.unit
    def test_transform_section_status_newonly(self, mock_uci_db_session):
        """Test transformation with NEWONLY status."""
        scraper = UciScraper(mock_uci_db_session)

        section = {
            "sectionCode": "12345",
            "sectionType": "Lec",
            "sectionNum": "A",
            "status": "NEWONLY",
        }
        result = scraper._transform_section(section)

        assert result is not None
        assert result["status"] == "Open"

    @pytest.mark.unit
    def test_transform_section_status_unknown(self, mock_uci_db_session):
        """Test transformation with unknown status defaults to Closed."""
        scraper = UciScraper(mock_uci_db_session)

        section = {
            "sectionCode": "12345",
            "sectionType": "Lec",
            "sectionNum": "A",
            "status": "UNKNOWN_STATUS",
        }
        result = scraper._transform_section(section)

        assert result is not None
        assert result["status"] == "Closed"

    @pytest.mark.unit
    def test_transform_section_missing_code(self, mock_uci_db_session):
        """Test that section without sectionCode returns None."""
        scraper = UciScraper(mock_uci_db_session)

        section = {
            "sectionCode": "",
            "sectionType": "Lec",
            "sectionNum": "A",
            "status": "OPEN",
        }
        result = scraper._transform_section(section)

        assert result is None

    @pytest.mark.unit
    def test_transform_single_course_valid(self, mock_uci_db_session):
        """Test transformation of valid course."""
        scraper = UciScraper(mock_uci_db_session)

        course = {
            "deptCode": "COMPSCI",
            "courseNumber": "161",
            "courseTitle": "Design of Very Large Scale Systems",
            "sections": [
                {
                    "sectionCode": "51234",
                    "sectionType": "Lec",
                    "sectionNum": "A",
                    "status": "OPEN",
                }
            ],
        }
        result = scraper._transform_single_course(course)

        assert result is not None
        assert result["course_code"] == "COMPSCI 161"
        assert result["title"] == "Design of Very Large Scale Systems"
        assert len(result["classes"]) == 1
        assert result["classes"][0]["class_number"] == "51234"

    @pytest.mark.unit
    def test_transform_single_course_missing_dept_code(self, mock_uci_db_session):
        """Test that course without deptCode returns None."""
        scraper = UciScraper(mock_uci_db_session)

        course = {
            "deptCode": "",
            "courseNumber": "161",
            "courseTitle": "Test Course",
            "sections": [
                {
                    "sectionCode": "51234",
                    "sectionType": "Lec",
                    "sectionNum": "A",
                    "status": "OPEN",
                }
            ],
        }
        result = scraper._transform_single_course(course)

        assert result is None

    @pytest.mark.unit
    def test_transform_single_course_missing_course_number(self, mock_uci_db_session):
        """Test that course without courseNumber returns None."""
        scraper = UciScraper(mock_uci_db_session)

        course = {
            "deptCode": "COMPSCI",
            "courseNumber": "",
            "courseTitle": "Test Course",
            "sections": [
                {
                    "sectionCode": "51234",
                    "sectionType": "Lec",
                    "sectionNum": "A",
                    "status": "OPEN",
                }
            ],
        }
        result = scraper._transform_single_course(course)

        assert result is None

    @pytest.mark.unit
    def test_transform_single_course_no_sections(self, mock_uci_db_session):
        """Test that course with no valid sections returns None."""
        scraper = UciScraper(mock_uci_db_session)

        course = {
            "deptCode": "COMPSCI",
            "courseNumber": "161",
            "courseTitle": "Test Course",
            "sections": [],
        }
        result = scraper._transform_single_course(course)

        assert result is None

    @pytest.mark.unit
    def test_transform_courses_aggregates_variable_topics(self, mock_uci_db_session):
        """Test that variable topic courses are aggregated by course code."""
        scraper = UciScraper(mock_uci_db_session)

        result = scraper._transform_courses(SAMPLE_UCI_VARIABLE_TOPIC_RESPONSE["data"])

        # Should have only 1 course (ECO EVO 200B) with 2 sections
        assert len(result) == 1
        assert result[0]["course_code"] == "ECO EVO 200B"
        assert len(result[0]["classes"]) == 2
        assert result[0]["classes"][0]["class_number"] == "12345"
        assert result[0]["classes"][1]["class_number"] == "12346"

    @pytest.mark.unit
    def test_transform_courses_respects_limit(self, mock_uci_db_session):
        """Test that course limit is applied correctly."""
        scraper = UciScraper(mock_uci_db_session)

        result = scraper._transform_courses(SAMPLE_UCI_API_RESPONSE["data"], limit=2)

        assert len(result) == 2

    @pytest.mark.unit
    def test_transform_courses_empty_response(self, mock_uci_db_session):
        """Test that empty response returns empty list."""
        scraper = UciScraper(mock_uci_db_session)

        result = scraper._transform_courses({"schools": []})

        assert result == []

    @pytest.mark.unit
    async def test_make_api_request_success(self, mock_uci_db_session):
        """Test successful API request."""
        scraper = UciScraper(mock_uci_db_session)

        # Mock the HTTP client and response
        mock_response = create_mock_response(
            {
                "ok": True,
                "data": {"schools": []},
            }
        )

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        scraper.client = mock_client

        result = await scraper._make_api_request({"year": "2026", "quarter": "Spring"})

        assert result == {"schools": []}
        assert scraper.request_count == 1

    @pytest.mark.unit
    async def test_make_api_request_api_error(self, mock_uci_db_session):
        """Test handling API error (ok: false)."""
        scraper = UciScraper(mock_uci_db_session)

        # Mock the HTTP client and response
        mock_response = create_mock_response(
            {
                "ok": False,
                "message": "Invalid term code",
            }
        )

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        scraper.client = mock_client

        with pytest.raises(Exception) as exc_info:
            await scraper._make_api_request({"year": "2026", "quarter": "Invalid"})

        assert "Anteater API error" in str(exc_info.value)
        assert "Invalid term code" in str(exc_info.value)

    @pytest.mark.unit
    async def test_make_api_request_http_error(self, mock_uci_db_session):
        """Test handling HTTP error."""
        scraper = UciScraper(mock_uci_db_session)

        # Mock HTTP error
        import httpx

        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=MagicMock(), response=MagicMock()
        )

        scraper.client = mock_client

        with pytest.raises(httpx.HTTPStatusError):
            await scraper._make_api_request({"year": "2026", "quarter": "Spring"})

    @pytest.mark.unit
    async def test_fetch_all_courses(self, mock_uci_db_session):
        """Test fetching all courses (no department param)."""
        scraper = UciScraper(mock_uci_db_session)

        # Mock the HTTP client and response
        mock_response = create_mock_response(
            {
                "ok": True,
                "data": {"schools": []},
            }
        )

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        scraper.client = mock_client

        await scraper._fetch_all_courses()

        # Verify API was called without department param
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        params = call_args[1]["params"]
        assert "department" not in params
        assert params["year"] == "2026"
        assert params["quarter"] == "Spring"

    @pytest.mark.unit
    async def test_fetch_department_courses(self, mock_uci_db_session):
        """Test fetching courses for specific department."""
        scraper = UciScraper(mock_uci_db_session)

        # Mock the HTTP client and response
        mock_response = create_mock_response(
            {
                "ok": True,
                "data": {"schools": []},
            }
        )

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        scraper.client = mock_client

        await scraper._fetch_department_courses("COMPSCI")

        # Verify API was called with department param
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        params = call_args[1]["params"]
        assert params["department"] == "COMPSCI"
        assert params["year"] == "2026"
        assert params["quarter"] == "Spring"

    @pytest.mark.unit
    async def test_scrape_courses_all(self, mock_uci_db_session):
        """Test scraping all courses."""
        scraper = UciScraper(mock_uci_db_session)

        # Mock the HTTP client and response
        mock_response = create_mock_response(SAMPLE_UCI_API_RESPONSE)

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        result = await scraper.scrape_courses("ALL")

        assert len(result) == 3
        assert any(c["course_code"] == "COMPSCI 161" for c in result)
        assert any(c["course_code"] == "COMPSCI 171" for c in result)
        assert any(c["course_code"] == "I&C SCI 45C" for c in result)

    @pytest.mark.unit
    async def test_scrape_courses_specific_department(self, mock_uci_db_session):
        """Test scraping specific department."""
        scraper = UciScraper(mock_uci_db_session)

        # Mock the HTTP client and response
        mock_response = create_mock_response(SAMPLE_UCI_API_RESPONSE)

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        result = await scraper.scrape_courses("COMPSCI")

        assert len(result) == 3  # Should return all courses from the mock

    @pytest.mark.unit
    async def test_scrape_courses_with_limit(self, mock_uci_db_session):
        """Test scraping with course limit."""
        scraper = UciScraper(mock_uci_db_session)

        # Mock the HTTP client and response
        mock_response = create_mock_response(SAMPLE_UCI_API_RESPONSE)

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        result = await scraper.scrape_courses("ALL", limit=1)

        assert len(result) == 1

    @pytest.mark.unit
    async def test_scrape_courses_closes_client(self, mock_uci_db_session):
        """Test that client is closed after scraping."""
        scraper = UciScraper(mock_uci_db_session)

        # Mock the HTTP client and response
        mock_response = create_mock_response(SAMPLE_UCI_API_RESPONSE)

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        await scraper.scrape_courses("ALL")

        # Verify client was closed
        mock_client.aclose.assert_called_once()
        assert scraper.client is None
