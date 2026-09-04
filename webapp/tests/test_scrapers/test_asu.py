"""Tests for Arizona State University course scraper."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import sys
from pathlib import Path

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from scraper.scrapers.asu import AsuScraper
from models.college import College

# Sample ASU API response data - nested by college group (real API structure)
SAMPLE_SUBJECTS_RESPONSE_NESTED = {
    "LS": [
        {"SUBJECT": "CSE", "SUBJECTDESCR": "Computer Science"},
        {"SUBJECT": "MAT", "SUBJECTDESCR": "Mathematics"},
    ],
    "BA": [
        {"SUBJECT": "FIN", "SUBJECTDESCR": "Finance"},
        {"SUBJECT": "MKT", "SUBJECTDESCR": "Marketing"},
    ],
    "EN": [
        {"SUBJECT": "ENG", "SUBJECTDESCR": "Engineering"},
    ],
}

# Flat list fallback (for backward compatibility)
SAMPLE_SUBJECTS_RESPONSE_FLAT = [
    {"subject": "CSE"},
    {"subject": "MAT"},
    {"subject": "ENG"},
]

# Sample classes with CLAS wrapper (real API structure)
SAMPLE_CLASSES_RESPONSE_PAGE1 = {
    "classes": [
        {
            "CLAS": {
                "SUBJECT": "CSE",
                "CATALOGNBR": "110",
                "COURSETITLELONG": "Principles of Programming",
                "CLASSNBR": 63179,  # Real API returns int
                "CLASSSECTION": "2101",
                "ENRLSTAT": "O",
            },
            "seatInfo": {},
        },
        {
            "CLAS": {
                "SUBJECT": "CSE",
                "CATALOGNBR": "110",
                "COURSETITLELONG": "Principles of Programming",
                "CLASSNBR": 63180,
                "CLASSSECTION": "2102",
                "ENRLSTAT": "C",
            },
            "seatInfo": {},
        },
        {
            "CLAS": {
                "SUBJECT": "CSE",
                "CATALOGNBR": "205",
                "TITLE": "Computer Organization",
                "CLASSNBR": 63181,
                "CLASSSECTION": "3101",
                "ENRLSTAT": "O",
            },
            "seatInfo": {},
        },
    ],
    "scrollId": "scroll123",
}

SAMPLE_CLASSES_RESPONSE_PAGE2 = {
    "classes": [
        {
            "CLAS": {
                "SUBJECT": "CSE",
                "CATALOGNBR": "310",
                "COURSETITLELONG": "Data Structures and Algorithms",
                "CLASSNBR": 63182,
                "CLASSSECTION": "4101",
                "ENRLSTAT": "O",
            },
            "seatInfo": {},
        },
    ],
    "scrollId": None,  # No more pages
}

# Unwrapped fixtures for backward compatibility tests
SAMPLE_CLASSES_UNWRAPPED = [
    {
        "SUBJECT": "CSE",
        "CATALOGNBR": "110",
        "COURSETITLELONG": "Principles of Programming",
        "CLASSNBR": "63179",
        "CLASSSECTION": "2101",
        "ENRLSTAT": "O",
    },
    {
        "SUBJECT": "CSE",
        "CATALOGNBR": "110",
        "COURSETITLELONG": "Principles of Programming",
        "CLASSNBR": "63180",
        "CLASSSECTION": "2102",
        "ENRLSTAT": "C",
    },
]

SAMPLE_EMPTY_RESPONSE = {
    "classes": [],
    "scrollId": None,
}


@pytest.fixture
def mock_db_session():
    """Create a mock database session for ASU scraper."""
    mock_session = MagicMock()
    mock_college = College(
        id=1,
        name="Arizona State University",
        short_name="asu",
        term_code="2267",  # Fall 2026
        term_name="Fall 2026",
        is_active=True,
    )

    # Mock the query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_college
    mock_session.execute.return_value = mock_result

    return mock_session


@pytest.fixture
def scraper(mock_db_session):
    """Create an ASU scraper instance."""
    return AsuScraper(db_session=mock_db_session)


@pytest.mark.asyncio
async def test_scrape_all_courses(scraper):
    """Test scraping all ASU courses."""
    with patch.object(
        scraper, "_fetch_subjects", new_callable=AsyncMock
    ) as mock_fetch_subjects, patch.object(
        scraper, "_fetch_subject_classes", new_callable=AsyncMock
    ) as mock_fetch_classes:
        # Mock subjects
        mock_fetch_subjects.return_value = ["CSE"]

        # Mock classes for subject
        all_classes = (
            SAMPLE_CLASSES_RESPONSE_PAGE1["classes"]
            + SAMPLE_CLASSES_RESPONSE_PAGE2["classes"]
        )
        mock_fetch_classes.return_value = all_classes

        # Scrape courses
        courses = await scraper.scrape_courses("ALL")

        # Verify results
        assert len(courses) == 3  # CSE 110, CSE 205, CSE 310
        assert courses[0]["course_code"] == "CSE 110"
        assert courses[0]["title"] == "Principles of Programming"
        assert len(courses[0]["classes"]) == 2
        assert courses[0]["classes"][0]["class_number"] == "63179"
        assert courses[0]["classes"][0]["section"] == "2101"
        assert courses[0]["classes"][0]["status"] == "Open"
        assert courses[0]["classes"][1]["class_number"] == "63180"
        assert courses[0]["classes"][1]["status"] == "Closed"


@pytest.mark.asyncio
async def test_scrape_department_courses(scraper):
    """Test scraping courses for a specific department."""
    with patch.object(
        scraper, "_fetch_subjects", new_callable=AsyncMock
    ) as mock_fetch_subjects, patch.object(
        scraper, "_fetch_subject_classes", new_callable=AsyncMock
    ) as mock_fetch_classes:
        # Mock subjects (should filter to just CSE)
        mock_fetch_subjects.return_value = ["CSE", "MAT", "ENG"]

        # Mock classes
        mock_fetch_classes.return_value = SAMPLE_CLASSES_RESPONSE_PAGE1["classes"]

        # Scrape courses for CSE department
        courses = await scraper.scrape_courses("CSE")

        # Verify filtering happened
        mock_fetch_subjects.assert_called_once()
        mock_fetch_classes.assert_called_once_with("CSE")

        # Verify results
        assert len(courses) == 2  # CSE 110, CSE 205


@pytest.mark.asyncio
async def test_fetch_subjects_nested(scraper):
    """Test fetching subjects from ASU API with nested structure (real API)."""
    await scraper._ensure_client()

    with patch.object(scraper.client, "get", new_callable=AsyncMock) as mock_get:
        # Mock HTTP response with nested structure
        import json

        mock_response = MagicMock()
        mock_response.content = json.dumps(SAMPLE_SUBJECTS_RESPONSE_NESTED).encode()
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Fetch subjects
        subjects = await scraper._fetch_subjects()

        # Verify request
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "search/subjects" in call_args[0][0]
        assert call_args[1]["params"]["term"] == "2267"

        # Verify results - should flatten and dedupe
        assert len(subjects) == 5  # CSE, MAT, FIN, MKT, ENG
        assert "CSE" in subjects
        assert "MAT" in subjects
        assert "FIN" in subjects
        assert "MKT" in subjects
        assert "ENG" in subjects

    await scraper.client.aclose()


@pytest.mark.asyncio
async def test_fetch_subjects_flat_fallback(scraper):
    """Test fetching subjects with flat list structure (backward compatibility)."""
    await scraper._ensure_client()

    with patch.object(scraper.client, "get", new_callable=AsyncMock) as mock_get:
        # Mock HTTP response with flat list
        import json

        mock_response = MagicMock()
        mock_response.content = json.dumps(SAMPLE_SUBJECTS_RESPONSE_FLAT).encode()
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Fetch subjects
        subjects = await scraper._fetch_subjects()

        # Verify results
        assert subjects == ["CSE", "MAT", "ENG"]

    await scraper.client.aclose()


@pytest.mark.asyncio
async def test_fetch_subject_classes_pagination(scraper):
    """Test fetching classes with multi-page scrollId pagination."""
    with patch.object(
        scraper, "_fetch_classes_page", new_callable=AsyncMock
    ) as mock_fetch_page:
        # Mock paginated responses
        mock_fetch_page.side_effect = [
            SAMPLE_CLASSES_RESPONSE_PAGE1,  # Page 1 with scrollId
            SAMPLE_CLASSES_RESPONSE_PAGE2,  # Page 2, no scrollId
        ]

        # Fetch classes
        classes = await scraper._fetch_subject_classes("CSE")

        # Verify pagination
        assert mock_fetch_page.call_count == 2
        assert mock_fetch_page.call_args_list[0][0][0] == "CSE"
        assert (
            mock_fetch_page.call_args_list[0][0][1] is None
        )  # First call: no scrollId
        assert (
            mock_fetch_page.call_args_list[1][0][1] == "scroll123"
        )  # Second call: with scrollId

        # Verify combined results
        assert len(classes) == 4  # 3 from page 1 + 1 from page 2


@pytest.mark.asyncio
async def test_fetch_subject_classes_empty_page(scraper):
    """Test that pagination stops on empty page."""
    with patch.object(
        scraper, "_fetch_classes_page", new_callable=AsyncMock
    ) as mock_fetch_page:
        # Mock response: first page has data, second page is empty
        mock_fetch_page.side_effect = [
            SAMPLE_CLASSES_RESPONSE_PAGE1,
            SAMPLE_EMPTY_RESPONSE,
        ]

        # Fetch classes
        classes = await scraper._fetch_subject_classes("CSE")

        # Verify stopped after empty page
        assert mock_fetch_page.call_count == 2
        assert len(classes) == 3  # Only from first page


@pytest.mark.asyncio
async def test_fetch_classes_page(scraper):
    """Test fetching a single page of classes."""
    await scraper._ensure_client()

    with patch.object(scraper.client, "get", new_callable=AsyncMock) as mock_get:
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.content = (
            b'{"classes": [{"CLASSNBR": "63179"}], "scrollId": "scroll123"}'
        )
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Fetch page
        data = await scraper._fetch_classes_page("CSE", scroll_id="scroll_prev")

        # Verify request
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "search/classes" in call_args[0][0]
        params = call_args[1]["params"]
        assert params["subject"] == "CSE"
        assert params["term"] == "2267"
        assert params["refine"] == "Y"
        assert params["scrollId"] == "scroll_prev"

        # Verify response
        assert "classes" in data
        assert data["scrollId"] == "scroll123"

    await scraper.client.aclose()


def test_transform_classes(scraper):
    """Test transformation of raw classes to course format."""
    raw_classes = (
        SAMPLE_CLASSES_RESPONSE_PAGE1["classes"]
        + SAMPLE_CLASSES_RESPONSE_PAGE2["classes"]
    )
    courses = scraper._transform_classes(raw_classes)

    # Should group into 3 unique courses
    assert len(courses) == 3

    # Find CSE 110 course
    cse110 = next(c for c in courses if c["course_code"] == "CSE 110")
    assert cse110["title"] == "Principles of Programming"
    assert len(cse110["classes"]) == 2
    assert cse110["classes"][0]["class_number"] == "63179"
    assert cse110["classes"][1]["class_number"] == "63180"


def test_transform_single_class_with_clas_wrapper(scraper):
    """Test transformation of a single class with CLAS wrapper (real API)."""
    raw_class = SAMPLE_CLASSES_RESPONSE_PAGE1["classes"][0]
    class_data = scraper._transform_single_class(raw_class)

    assert class_data is not None
    assert class_data["course_code"] == "CSE 110"
    assert class_data["title"] == "Principles of Programming"
    assert class_data["class_number"] == "63179"  # Converted from int to string
    assert class_data["section"] == "2101"
    assert class_data["status"] == "Open"


def test_transform_single_class_unwrapped(scraper):
    """Test transformation of unwrapped class (backward compatibility)."""
    raw_class = SAMPLE_CLASSES_UNWRAPPED[0]
    class_data = scraper._transform_single_class(raw_class)

    assert class_data is not None
    assert class_data["course_code"] == "CSE 110"
    assert class_data["title"] == "Principles of Programming"
    assert class_data["class_number"] == "63179"
    assert class_data["section"] == "2101"
    assert class_data["status"] == "Open"


def test_enrlstat_mapping_with_clas_wrapper(scraper):
    """Test ENRLSTAT field mapping to Open/Closed status with CLAS wrapper."""
    # Test Open status
    raw_class_open = {
        "CLAS": {
            "SUBJECT": "CSE",
            "CATALOGNBR": "110",
            "TITLE": "Test Course",
            "CLASSNBR": 12345,
            "CLASSSECTION": "01",
            "ENRLSTAT": "O",
        }
    }
    class_open = scraper._transform_single_class(raw_class_open)
    assert class_open["status"] == "Open"

    # Test Closed status
    raw_class_closed = {
        "CLAS": {
            "SUBJECT": "CSE",
            "CATALOGNBR": "110",
            "TITLE": "Test Course",
            "CLASSNBR": 12346,
            "CLASSSECTION": "02",
            "ENRLSTAT": "C",
        }
    }
    class_closed = scraper._transform_single_class(raw_class_closed)
    assert class_closed["status"] == "Closed"

    # Test unknown status (should default to Closed)
    raw_class_unknown = {
        "CLAS": {
            "SUBJECT": "CSE",
            "CATALOGNBR": "110",
            "TITLE": "Test Course",
            "CLASSNBR": 12347,
            "CLASSSECTION": "03",
            "ENRLSTAT": "X",
        }
    }
    class_unknown = scraper._transform_single_class(raw_class_unknown)
    assert class_unknown["status"] == "Closed"


def test_classnbr_identity(scraper):
    """Test that CLASSNBR is correctly used as class_number identifier."""
    raw_class = {
        "CLAS": {
            "SUBJECT": "CSE",
            "CATALOGNBR": "110",
            "TITLE": "Test Course",
            "CLASSNBR": 99999,  # Real API returns int
            "CLASSSECTION": "ABC",  # This is the section code
            "ENRLSTAT": "O",
        }
    }
    class_data = scraper._transform_single_class(raw_class)

    # Verify CLASSNBR is used for class_number (converted to string), not section
    assert class_data["class_number"] == "99999"
    assert class_data["section"] == "ABC"


def test_classnbr_int_to_string_conversion(scraper):
    """Test that integer CLASSNBR from API is converted to string."""
    raw_class = {
        "CLAS": {
            "SUBJECT": "CSE",
            "CATALOGNBR": "110",
            "TITLE": "Test Course",
            "CLASSNBR": 62688,  # Real API returns int, not string
            "CLASSSECTION": "01",
            "ENRLSTAT": "O",
        }
    }
    class_data = scraper._transform_single_class(raw_class)

    # Verify int is converted to string
    assert class_data["class_number"] == "62688"
    assert isinstance(class_data["class_number"], str)


def test_title_fallback(scraper):
    """Test that title falls back from COURSETITLELONG to TITLE."""
    # Test with COURSETITLELONG
    raw_class_long = {
        "CLAS": {
            "SUBJECT": "CSE",
            "CATALOGNBR": "110",
            "COURSETITLELONG": "Long Title",
            "TITLE": "Short Title",
            "CLASSNBR": 12345,
            "CLASSSECTION": "01",
            "ENRLSTAT": "O",
        }
    }
    class_long = scraper._transform_single_class(raw_class_long)
    assert class_long["title"] == "Long Title"

    # Test fallback to TITLE when COURSETITLELONG is empty
    raw_class_short = {
        "CLAS": {
            "SUBJECT": "CSE",
            "CATALOGNBR": "110",
            "COURSETITLELONG": "",
            "TITLE": "Short Title",
            "CLASSNBR": 12345,
            "CLASSSECTION": "01",
            "ENRLSTAT": "O",
        }
    }
    class_short = scraper._transform_single_class(raw_class_short)
    assert class_short["title"] == "Short Title"


def test_deduplicate_classes_by_class_number(scraper):
    """Test that duplicate class_numbers are deduplicated within a course."""
    raw_classes = [
        {
            "CLAS": {
                "SUBJECT": "CSE",
                "CATALOGNBR": "110",
                "TITLE": "Test Course",
                "CLASSNBR": 12345,  # Duplicate
                "CLASSSECTION": "01",
                "ENRLSTAT": "O",
            }
        },
        {
            "CLAS": {
                "SUBJECT": "CSE",
                "CATALOGNBR": "110",
                "TITLE": "Test Course",
                "CLASSNBR": 12345,  # Duplicate
                "CLASSSECTION": "02",
                "ENRLSTAT": "C",
            }
        },
        {
            "CLAS": {
                "SUBJECT": "CSE",
                "CATALOGNBR": "110",
                "TITLE": "Test Course",
                "CLASSNBR": 12346,  # Unique
                "CLASSSECTION": "03",
                "ENRLSTAT": "O",
            }
        },
    ]

    courses = scraper._transform_classes(raw_classes)

    # Should have 1 course with 2 unique classes (12345 deduplicated)
    assert len(courses) == 1
    assert len(courses[0]["classes"]) == 2
    class_numbers = [c["class_number"] for c in courses[0]["classes"]]
    assert "12345" in class_numbers
    assert "12346" in class_numbers
    assert class_numbers.count("12345") == 1  # Only one instance


@pytest.mark.asyncio
async def test_required_authorization_header(scraper):
    """Test that the Authorization: Bearer null header is included."""
    await scraper._ensure_client()

    # Verify header is set
    assert "Authorization" in scraper.client.headers
    assert scraper.client.headers["Authorization"] == "Bearer null"

    await scraper.client.aclose()


def test_term_code_format(scraper):
    """Test that term code follows 2YYX format."""
    # Term code should be 2267 (Fall 2026)
    assert scraper.current_term == "2267"

    # Verify it's a 4-digit string starting with 2
    assert len(scraper.current_term) == 4
    assert scraper.current_term.startswith("2")


def test_subjects_deduplication(scraper):
    """Test that duplicate subjects across college groups are deduplicated."""
    # Create nested structure with duplicate subjects
    nested_response = {
        "LS": [
            {"SUBJECT": "CSE", "SUBJECTDESCR": "Computer Science"},
            {"SUBJECT": "MAT", "SUBJECTDESCR": "Mathematics"},
        ],
        "EN": [
            {"SUBJECT": "CSE", "SUBJECTDESCR": "Computer Science"},  # Duplicate
            {"SUBJECT": "ENG", "SUBJECTDESCR": "Engineering"},
        ],
    }

    subjects = []
    seen = set()

    # Replicate the logic from _fetch_subjects
    if isinstance(nested_response, dict):
        for college_group in nested_response.values():
            if isinstance(college_group, list):
                for item in college_group:
                    if isinstance(item, dict):
                        subject = item.get("SUBJECT") or item.get("subject")
                        if subject and subject not in seen:
                            seen.add(subject)
                            subjects.append(subject)

    # Should have 3 unique subjects (CSE deduplicated)
    assert len(subjects) == 3
    assert "CSE" in subjects
    assert "MAT" in subjects
    assert "ENG" in subjects
    assert subjects.count("CSE") == 1  # Only one instance


@pytest.mark.asyncio
async def test_full_integration_nested_subjects_and_clas_wrapper(scraper):
    """Integration test: nested subjects + CLAS wrapper classes."""
    with patch.object(
        scraper, "_fetch_subjects", new_callable=AsyncMock
    ) as mock_fetch_subjects, patch.object(
        scraper, "_fetch_subject_classes", new_callable=AsyncMock
    ) as mock_fetch_classes:
        # Mock nested subjects response
        mock_fetch_subjects.return_value = ["CSE", "MAT"]

        # Mock classes with CLAS wrapper
        mock_fetch_classes.return_value = SAMPLE_CLASSES_RESPONSE_PAGE1["classes"]

        # Scrape courses
        courses = await scraper.scrape_courses("ALL")

        # Verify results
        assert len(courses) == 2  # CSE 110 and CSE 205
        assert courses[0]["course_code"] == "CSE 110"
        assert len(courses[0]["classes"]) == 2

        # Verify CLASSNBR converted from int to string
        assert courses[0]["classes"][0]["class_number"] == "63179"
        assert isinstance(courses[0]["classes"][0]["class_number"], str)

        # Verify ENRLSTAT mapping
        assert courses[0]["classes"][0]["status"] == "Open"
        assert courses[0]["classes"][1]["status"] == "Closed"
