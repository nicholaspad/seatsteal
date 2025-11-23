"""Tests for University of Southern California course scraper."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from sqlalchemy.orm import Session

import sys
from pathlib import Path

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from scraper.scrapers.usc import UscScraper
from models.college import College


# Sample USC Schools API response data
SAMPLE_USC_SCHOOLS = [
    {
        "prefix": "DENT",
        "name": "School of Dentistry",
        "programs": [
            {"prefix": "DENT", "name": "Dentistry"},
        ],
    },
    {
        "prefix": "ENG",
        "name": "Viterbi School of Engineering",
        "programs": [
            {"prefix": "CSCI", "name": "Computer Science"},
            {"prefix": "EE", "name": "Electrical Engineering"},
        ],
    },
]

# Sample USC Courses API response data
SAMPLE_USC_COURSES_RESPONSE = {
    "courses": [
        {
            "fullCourseName": "CSCI 101",
            "name": "Fundamentals of Computer Programming",
            "sections": [
                {
                    "sisSectionId": "29510",
                    "totalSeats": 30,
                    "registeredSeats": 15,
                },
                {
                    "sisSectionId": "29511",
                    "totalSeats": 30,
                    "registeredSeats": 30,
                },
            ],
        },
        {
            "fullCourseName": "CSCI 102",
            "name": "Data Structures and Object Oriented Design",
            "sections": [
                {
                    "sisSectionId": "29520",
                    "totalSeats": 25,
                    "registeredSeats": 10,
                },
            ],
        },
    ]
}

SAMPLE_USC_EMPTY_COURSES_RESPONSE = {"courses": []}


@pytest.fixture
def mock_usc_db_session():
    """Create a mock database session for USC scraper."""
    mock_session = MagicMock(spec=Session)
    mock_college = College(
        id=1,
        name="University of Southern California",
        short_name="usc",
        term_code="20253",
        term_name="Fall 2025",
        is_active=True,
    )

    # Mock the query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_college
    mock_session.execute.return_value = mock_result

    return mock_session


class TestUscScraper:
    """Tests for UscScraper class."""

    @pytest.mark.unit
    def test_init_sets_college_short_name(self, mock_usc_db_session):
        """Test that scraper correctly sets college short name."""
        scraper = UscScraper(mock_usc_db_session)

        assert scraper.college_short_name == "usc"

    @pytest.mark.unit
    def test_init_gets_term_code_from_db(self, mock_usc_db_session):
        """Test that scraper correctly retrieves term code from database."""
        scraper = UscScraper(mock_usc_db_session)

        assert scraper.current_term == "20253"

    @pytest.mark.unit
    def test_transform_section_to_class_open(self, mock_usc_db_session):
        """Test transformation of section with available seats (open status)."""
        scraper = UscScraper(mock_usc_db_session)

        course = {
            "fullCourseName": "CSCI 101",
            "name": "Fundamentals of Computer Programming",
        }
        section = {
            "sisSectionId": "29510",
            "totalSeats": 30,
            "registeredSeats": 15,
        }

        result = scraper._transform_section_to_class(course, section)

        assert result is not None
        assert result["class_number"] == "29510"
        assert result["section"] == "29510"
        assert result["course_code"] == "CSCI 101"
        assert result["title"] == "Fundamentals of Computer Programming"
        assert result["status"] == "open"

    @pytest.mark.unit
    def test_transform_section_to_class_closed(self, mock_usc_db_session):
        """Test transformation of section with no available seats (closed status)."""
        scraper = UscScraper(mock_usc_db_session)

        course = {
            "fullCourseName": "CSCI 101",
            "name": "Fundamentals of Computer Programming",
        }
        section = {
            "sisSectionId": "29511",
            "totalSeats": 30,
            "registeredSeats": 30,
        }

        result = scraper._transform_section_to_class(course, section)

        assert result is not None
        assert result["class_number"] == "29511"
        assert result["status"] == "closed"

    @pytest.mark.unit
    def test_transform_section_to_class_missing_fields(self, mock_usc_db_session):
        """Test that section with missing required fields returns None."""
        scraper = UscScraper(mock_usc_db_session)

        course = {"fullCourseName": "CSCI 101", "name": "Test Course"}

        # Missing sisSectionId
        section_no_id = {"totalSeats": 30, "registeredSeats": 15}
        result = scraper._transform_section_to_class(course, section_no_id)
        assert result is None

        # Missing course name
        course_no_name = {"fullCourseName": ""}
        section_valid = {
            "sisSectionId": "29510",
            "totalSeats": 30,
            "registeredSeats": 15,
        }
        result = scraper._transform_section_to_class(course_no_name, section_valid)
        assert result is None

    @pytest.mark.unit
    def test_group_classes_by_course(self, mock_usc_db_session):
        """Test grouping individual class sections by course code."""
        scraper = UscScraper(mock_usc_db_session)

        classes = [
            {
                "class_number": "29510",
                "course_code": "CSCI 101",
                "title": "Fundamentals of Computer Programming",
                "section": "29510",
                "status": "open",
            },
            {
                "class_number": "29511",
                "course_code": "CSCI 101",
                "title": "Fundamentals of Computer Programming",
                "section": "29511",
                "status": "closed",
            },
            {
                "class_number": "29520",
                "course_code": "CSCI 102",
                "title": "Data Structures",
                "section": "29520",
                "status": "open",
            },
        ]

        result = scraper._group_classes_by_course(classes)

        assert len(result) == 2

        # Check CSCI 101 (should have 2 classes)
        csci_101 = next(c for c in result if c["course_code"] == "CSCI 101")
        assert csci_101["title"] == "Fundamentals of Computer Programming"
        assert len(csci_101["classes"]) == 2
        assert csci_101["classes"][0]["class_number"] == "29510"
        assert csci_101["classes"][1]["class_number"] == "29511"

        # Check CSCI 102 (should have 1 class)
        csci_102 = next(c for c in result if c["course_code"] == "CSCI 102")
        assert csci_102["title"] == "Data Structures"
        assert len(csci_102["classes"]) == 1

    @pytest.mark.unit
    def test_group_classes_skips_missing_course_code(self, mock_usc_db_session):
        """Test that classes with missing course code are skipped."""
        scraper = UscScraper(mock_usc_db_session)

        classes = [
            {
                "class_number": "29510",
                "course_code": "CSCI 101",
                "title": "Valid Course",
                "section": "29510",
                "status": "open",
            },
            {
                "class_number": "99999",
                "course_code": "",  # Missing course code
                "title": "Invalid Course",
                "section": "99999",
                "status": "open",
            },
        ]

        result = scraper._group_classes_by_course(classes)

        # Should only have 1 course (the valid one)
        assert len(result) == 1
        assert result[0]["course_code"] == "CSCI 101"

    @pytest.mark.unit
    async def test_fetch_school_programs(self, mock_usc_db_session):
        """Test fetching school/program combinations from Schools API."""
        scraper = UscScraper(mock_usc_db_session)

        # Mock the HTTP client and response
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_USC_SCHOOLS
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        result = await scraper._fetch_school_programs("20253")

        # Should flatten to 3 school/program combinations
        assert len(result) == 3
        assert result[0]["school"] == "DENT"
        assert result[0]["program"] == "DENT"
        assert result[1]["school"] == "ENG"
        assert result[1]["program"] == "CSCI"
        assert result[2]["school"] == "ENG"
        assert result[2]["program"] == "EE"

    @pytest.mark.unit
    async def test_fetch_school_programs_invalid_response(self, mock_usc_db_session):
        """Test handling of invalid Schools API response."""
        scraper = UscScraper(mock_usc_db_session)

        # Mock response that's not a list
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "Invalid"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        scraper.client = mock_client

        with pytest.raises(Exception, match="Invalid response format"):
            await scraper._fetch_school_programs("20253")

    @pytest.mark.unit
    async def test_fetch_program_courses(self, mock_usc_db_session):
        """Test fetching courses for a specific school/program."""
        scraper = UscScraper(mock_usc_db_session)

        # Mock the HTTP client and response
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_USC_COURSES_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        school_program = {"school": "ENG", "program": "CSCI"}
        result = await scraper._fetch_program_courses("20253", school_program)

        # Should return 3 classes (2 sections for CSCI 101, 1 for CSCI 102)
        assert len(result) == 3
        assert result[0]["course_code"] == "CSCI 101"
        assert result[1]["course_code"] == "CSCI 101"
        assert result[2]["course_code"] == "CSCI 102"

    @pytest.mark.unit
    async def test_fetch_program_courses_empty(self, mock_usc_db_session):
        """Test handling of empty courses response."""
        scraper = UscScraper(mock_usc_db_session)

        # Mock empty response
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_USC_EMPTY_COURSES_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        scraper.client = mock_client

        school_program = {"school": "ENG", "program": "CSCI"}
        result = await scraper._fetch_program_courses("20253", school_program)

        assert len(result) == 0

    @pytest.mark.unit
    async def test_fetch_program_courses_invalid_response(self, mock_usc_db_session):
        """Test handling of invalid program courses response."""
        scraper = UscScraper(mock_usc_db_session)

        # Mock response without "courses" key
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "Invalid"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        scraper.client = mock_client

        school_program = {"school": "ENG", "program": "CSCI"}
        result = await scraper._fetch_program_courses("20253", school_program)

        # Should handle gracefully and return empty list
        assert len(result) == 0

    @pytest.mark.unit
    async def test_scrape_courses_all(self, mock_usc_db_session):
        """Test scraping all courses with batch processing."""
        scraper = UscScraper(mock_usc_db_session)

        # Mock schools API response
        mock_schools_response = MagicMock()
        mock_schools_response.json.return_value = SAMPLE_USC_SCHOOLS
        mock_schools_response.raise_for_status = MagicMock()

        # Mock courses API response
        mock_courses_response = MagicMock()
        mock_courses_response.json.return_value = SAMPLE_USC_COURSES_RESPONSE
        mock_courses_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        # First call gets schools, subsequent calls get courses
        mock_client.get.side_effect = [
            mock_schools_response,  # Schools API call
            mock_courses_response,  # DENT program
            mock_courses_response,  # CSCI program
            mock_courses_response,  # EE program
        ]
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        result = await scraper.scrape_courses("ALL")

        # Should group the 3 classes into 2 courses (CSCI 101 and CSCI 102)
        # Each program returns the same courses, so we'll have duplicates grouped
        assert len(result) >= 2  # At least CSCI 101 and CSCI 102

    @pytest.mark.unit
    async def test_scrape_courses_by_subject(self, mock_usc_db_session):
        """Test scraping courses for specific subject."""
        scraper = UscScraper(mock_usc_db_session)

        # Mock schools API response
        mock_schools_response = MagicMock()
        mock_schools_response.json.return_value = SAMPLE_USC_SCHOOLS
        mock_schools_response.raise_for_status = MagicMock()

        # Mock courses API response
        mock_courses_response = MagicMock()
        mock_courses_response.json.return_value = SAMPLE_USC_COURSES_RESPONSE
        mock_courses_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.side_effect = [
            mock_schools_response,  # Schools API call
            mock_courses_response,  # CSCI program courses
        ]
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        result = await scraper.scrape_courses("CSCI")

        # Should only fetch CSCI program courses
        assert len(result) == 2  # CSCI 101 and CSCI 102
        assert all(c["course_code"].startswith("CSCI") for c in result)

    @pytest.mark.unit
    async def test_scrape_courses_with_limit(self, mock_usc_db_session):
        """Test scraping with course limit."""
        scraper = UscScraper(mock_usc_db_session)

        # Mock schools API response
        mock_schools_response = MagicMock()
        mock_schools_response.json.return_value = SAMPLE_USC_SCHOOLS
        mock_schools_response.raise_for_status = MagicMock()

        # Mock courses API response
        mock_courses_response = MagicMock()
        mock_courses_response.json.return_value = SAMPLE_USC_COURSES_RESPONSE
        mock_courses_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.side_effect = [
            mock_schools_response,  # Schools API call
            mock_courses_response,  # First program
            mock_courses_response,  # Second program
            mock_courses_response,  # Third program
        ]
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        result = await scraper.scrape_courses("ALL", limit=1)

        # Should only return 1 course
        assert len(result) == 1

    @pytest.mark.unit
    async def test_scrape_courses_subject_not_found(self, mock_usc_db_session):
        """Test scraping with non-existent subject."""
        scraper = UscScraper(mock_usc_db_session)

        # Mock schools API response
        mock_schools_response = MagicMock()
        mock_schools_response.json.return_value = SAMPLE_USC_SCHOOLS
        mock_schools_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_schools_response
        mock_client.aclose = AsyncMock()

        scraper.client = mock_client

        result = await scraper.scrape_courses("NONEXISTENT")

        # Should return empty list
        assert len(result) == 0
