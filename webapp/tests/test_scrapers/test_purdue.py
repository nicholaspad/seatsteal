"""Tests for Purdue University course scraper."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import sys
from pathlib import Path

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from scraper.scrapers.purdue import PurdueScraper
from models.college import College

# Sample Banner HTML response for subject list
SAMPLE_SUBJECTS_HTML = """
<html>
<body>
<select name="sel_subj" id="subj_id">
    <option value="%">All</option>
    <option value="CS">Computer Science</option>
    <option value="MA">Mathematics</option>
    <option value="ECE">Electrical and Computer Engineering</option>
</select>
</body>
</html>
"""

# Sample Banner HTML response for course search (CRN list)
SAMPLE_COURSE_LIST_HTML = """
<html>
<body>
<table class="datadisplaytable">
    <tr>
        <td>
            <a href="#" onclick="window.open('/prod/bwckschd.p_disp_detail_sched?term_in=202710&crn_in=12345')">
                Intro to Programming - 12345 - CS 18000 - 001
            </a>
        </td>
    </tr>
    <tr>
        <td>
            <a href="#" onclick="window.open('/prod/bwckschd.p_disp_detail_sched?term_in=202710&crn_in=12346')">
                Intro to Programming - 12346 - CS 18000 - 002
            </a>
        </td>
    </tr>
    <tr>
        <td>
            <a href="#" onclick="window.open('/prod/bwckschd.p_disp_detail_sched?term_in=202710&crn_in=67890')">
                Data Structures - 67890 - CS 25100 - 001
            </a>
        </td>
    </tr>
</table>
</body>
</html>
"""

# Sample Banner HTML response for CRN detail with seats available
SAMPLE_DETAIL_OPEN_HTML = """
<html>
<body>
<table class="datadisplaytable">
    <caption class="captiontext">Registration Availability</caption>
    <tr>
        <th class="ddlabel">Seats</th>
        <td class="dddefault">Capacity: 50, Actual: 35, Remaining: 15</td>
    </tr>
</table>
</body>
</html>
"""

# Sample Banner HTML response for CRN detail with no seats
SAMPLE_DETAIL_CLOSED_HTML = """
<html>
<body>
<table class="datadisplaytable">
    <caption class="captiontext">Registration Availability</caption>
    <tr>
        <th class="ddlabel">Seats</th>
        <td class="dddefault">Capacity: 50, Actual: 50, Remaining: 0</td>
    </tr>
</table>
</body>
</html>
"""

# Sample Banner HTML response with missing seat info (should default to Closed)
SAMPLE_DETAIL_MISSING_SEATS_HTML = """
<html>
<body>
<table class="datadisplaytable">
    <caption class="captiontext">Registration Availability</caption>
    <tr>
        <th>Status</th>
        <td>Active</td>
    </tr>
</table>
</body>
</html>
"""


@pytest.fixture
def mock_db_session():
    """Create a mock database session for Purdue scraper."""
    mock_session = MagicMock()
    mock_college = College(
        id=1,
        name="Purdue University",
        short_name="purdue",
        term_code="202710",  # Fall 2026
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
    """Create a Purdue scraper instance."""
    return PurdueScraper(db_session=mock_db_session)


@pytest.mark.asyncio
async def test_scraper_initialization(scraper):
    """Test that scraper initializes with correct term code."""
    assert scraper.college_short_name == "purdue"
    assert scraper.current_term == "202710"
    assert scraper.detail_request_count == 0


@pytest.mark.asyncio
async def test_fetch_subjects(scraper):
    """Test fetching subject list from Banner."""
    await scraper._ensure_client()

    with patch.object(scraper.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.content = SAMPLE_SUBJECTS_HTML.encode("utf-8")
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        subjects = await scraper._fetch_subjects()

        assert len(subjects) == 3
        assert "CS" in subjects
        assert "MA" in subjects
        assert "ECE" in subjects
        assert "%" not in subjects  # Should exclude dummy/all option


@pytest.mark.asyncio
async def test_fetch_subject_crns(scraper):
    """Test fetching CRN list for a subject."""
    await scraper._ensure_client()

    with patch.object(scraper.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.content = SAMPLE_COURSE_LIST_HTML.encode("utf-8")
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        crn_entries = await scraper._fetch_subject_crns("CS")

        assert len(crn_entries) == 3
        
        # Check first entry
        assert crn_entries[0]["crn"] == "12345"
        assert crn_entries[0]["course_code"] == "CS 18000"
        assert crn_entries[0]["title"] == "Intro to Programming"
        assert crn_entries[0]["section"] == "001"
        
        # Check third entry
        assert crn_entries[2]["crn"] == "67890"
        assert crn_entries[2]["course_code"] == "CS 25100"


@pytest.mark.asyncio
async def test_deduplicate_crns(scraper):
    """Test CRN deduplication (keep first occurrence)."""
    crn_entries = [
        {"crn": "12345", "course_code": "CS 18000", "title": "Intro", "section": "001"},
        {"crn": "12346", "course_code": "CS 18000", "title": "Intro", "section": "002"},
        {"crn": "12345", "course_code": "CS 18000", "title": "Intro", "section": "003"},  # Duplicate
        {"crn": "67890", "course_code": "CS 25100", "title": "Data", "section": "001"},
    ]

    unique_entries = scraper._deduplicate_crns(crn_entries)

    assert len(unique_entries) == 3
    assert unique_entries[0]["crn"] == "12345"
    assert unique_entries[1]["crn"] == "12346"
    assert unique_entries[2]["crn"] == "67890"
    
    # Verify first occurrence is kept (section 001, not 003)
    assert unique_entries[0]["section"] == "001"


@pytest.mark.asyncio
async def test_fetch_crn_detail_open(scraper):
    """Test fetching detail page with open seats."""
    await scraper._ensure_client()

    with patch.object(scraper.client, "get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.content = SAMPLE_DETAIL_OPEN_HTML.encode("utf-8")
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        crn_entry = {
            "crn": "12345",
            "course_code": "CS 18000",
            "title": "Intro to Programming",
            "section": "001",
        }

        class_data = await scraper._fetch_crn_detail(crn_entry)

        assert class_data is not None
        assert class_data["class_number"] == "12345"  # CRN is class_number
        assert class_data["course_code"] == "CS 18000"
        assert class_data["status"] == "Open"  # 15 remaining seats
        assert class_data["section"] == "001"


@pytest.mark.asyncio
async def test_fetch_crn_detail_closed(scraper):
    """Test fetching detail page with no seats (closed)."""
    await scraper._ensure_client()

    with patch.object(scraper.client, "get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.content = SAMPLE_DETAIL_CLOSED_HTML.encode("utf-8")
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        crn_entry = {
            "crn": "67890",
            "course_code": "CS 25100",
            "title": "Data Structures",
            "section": "001",
        }

        class_data = await scraper._fetch_crn_detail(crn_entry)

        assert class_data is not None
        assert class_data["class_number"] == "67890"
        assert class_data["status"] == "Closed"  # 0 remaining seats


@pytest.mark.asyncio
async def test_fetch_crn_detail_missing_seats_defaults_closed(scraper):
    """Test that missing/unparsable seat data defaults to Closed (never invent Open)."""
    await scraper._ensure_client()

    with patch.object(scraper.client, "get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.content = SAMPLE_DETAIL_MISSING_SEATS_HTML.encode("utf-8")
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        crn_entry = {
            "crn": "99999",
            "course_code": "CS 99999",
            "title": "Unknown Course",
            "section": "001",
        }

        class_data = await scraper._fetch_crn_detail(crn_entry)

        assert class_data is not None
        # CRITICAL: Should default to Closed when seat data is missing
        assert class_data["status"] == "Closed"


@pytest.mark.asyncio
async def test_scrape_courses_all(scraper):
    """Test scraping all courses (mocked)."""
    await scraper._ensure_client()

    # Mock the internal methods
    with patch.object(scraper, "_fetch_subjects", new_callable=AsyncMock) as mock_subjects, \
         patch.object(scraper, "_fetch_subject_crns", new_callable=AsyncMock) as mock_crns, \
         patch.object(scraper, "_fetch_details_and_group", new_callable=AsyncMock) as mock_details:

        mock_subjects.return_value = ["CS", "MA"]
        mock_crns.side_effect = [
            [
                {"crn": "12345", "course_code": "CS 18000", "title": "Intro", "section": "001"},
            ],
            [
                {"crn": "67890", "course_code": "MA 16100", "title": "Calculus", "section": "001"},
            ],
        ]
        mock_details.return_value = [
            {
                "course_code": "CS 18000",
                "title": "Intro",
                "classes": [{"class_number": "12345", "section": "001", "status": "Open"}],
            },
            {
                "course_code": "MA 16100",
                "title": "Calculus",
                "classes": [{"class_number": "67890", "section": "001", "status": "Closed"}],
            },
        ]

        courses = await scraper.scrape_courses("ALL")

        assert len(courses) == 2
        assert courses[0]["course_code"] == "CS 18000"
        assert courses[1]["course_code"] == "MA 16100"


@pytest.mark.asyncio
async def test_scrape_courses_single_department(scraper):
    """Test scraping courses for a single department."""
    await scraper._ensure_client()

    with patch.object(scraper, "_fetch_subjects", new_callable=AsyncMock) as mock_subjects, \
         patch.object(scraper, "_fetch_subject_crns", new_callable=AsyncMock) as mock_crns, \
         patch.object(scraper, "_fetch_details_and_group", new_callable=AsyncMock) as mock_details:

        mock_subjects.return_value = ["CS", "MA", "ECE"]
        mock_crns.return_value = [
            {"crn": "12345", "course_code": "CS 18000", "title": "Intro", "section": "001"},
        ]
        mock_details.return_value = [
            {
                "course_code": "CS 18000",
                "title": "Intro",
                "classes": [{"class_number": "12345", "section": "001", "status": "Open"}],
            },
        ]

        courses = await scraper.scrape_courses("CS")

        # Should only fetch CS subject
        mock_crns.assert_called_once_with("CS")
        assert len(courses) == 1
        assert courses[0]["course_code"] == "CS 18000"


@pytest.mark.asyncio
async def test_request_budget_exceeded_fails_loud(scraper):
    """Test that exceeding request budget raises exception (no fake-success partial)."""
    await scraper._ensure_client()

    with patch.object(scraper, "_fetch_subjects", new_callable=AsyncMock) as mock_subjects, \
         patch.object(scraper, "_fetch_subject_crns", new_callable=AsyncMock) as mock_crns:

        mock_subjects.return_value = ["CS"]
        
        # Create more CRNs than MAX_DETAIL_REQUESTS (2000)
        excessive_crns = [
            {"crn": str(i), "course_code": f"CS {i}", "title": "Test", "section": "001"}
            for i in range(2001)
        ]
        mock_crns.return_value = excessive_crns

        with pytest.raises(Exception) as exc_info:
            await scraper.scrape_courses("CS")

        assert "Request budget exceeded" in str(exc_info.value)
        assert "failing loud" in str(exc_info.value)


@pytest.mark.asyncio
async def test_detail_request_counter_increments(scraper):
    """Test that detail request counter increments correctly."""
    await scraper._ensure_client()

    with patch.object(scraper.client, "get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.content = SAMPLE_DETAIL_OPEN_HTML.encode("utf-8")
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        crn_entry = {"crn": "12345", "course_code": "CS 18000", "title": "Intro", "section": "001"}

        assert scraper.detail_request_count == 0
        
        await scraper._fetch_crn_detail(crn_entry)
        assert scraper.detail_request_count == 1
        
        await scraper._fetch_crn_detail(crn_entry)
        assert scraper.detail_request_count == 2


@pytest.mark.asyncio
async def test_crn_is_used_as_class_number(scraper):
    """Test that CRN is used as class_number (identity mapping)."""
    await scraper._ensure_client()

    with patch.object(scraper.client, "get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.content = SAMPLE_DETAIL_OPEN_HTML.encode("utf-8")
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        crn_entry = {
            "crn": "98765",  # This should become class_number
            "course_code": "CS 18000",
            "title": "Test Course",
            "section": "999",
        }

        class_data = await scraper._fetch_crn_detail(crn_entry)

        # CRITICAL: Verify CRN is used as class_number
        assert class_data["class_number"] == "98765"
        assert class_data["section"] == "999"  # Section is separate


@pytest.mark.asyncio
async def test_term_code_from_db(mock_db_session):
    """Test that term code is fetched from database, not hardcoded."""
    scraper = PurdueScraper(db_session=mock_db_session)
    
    # Should get term from mock_db_session
    assert scraper.current_term == "202710"
    
    # Verify no hardcoded term in production code path
    # (This is validated by the scraper using get_term_code_from_db in __init__)
