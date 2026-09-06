"""Tests for Purdue University course scraper."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import sys
from pathlib import Path

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from scraper.scrapers.purdue import PurdueScraper, PurdueBudgetExceededError
from models.college import College
import httpx

# Sample Banner HTML response for term picker (realistic structure)
SAMPLE_TERM_PICKER_HTML = """
<html>
<body>
<form>
<select name="p_term" size="1" ID="term_input_id">
    <OPTION VALUE="">None</OPTION>
    <OPTION VALUE="202713">Winter 2026 (View only)</OPTION>
    <OPTION VALUE="202710">Fall 2026</OPTION>
    <OPTION VALUE="202630">Summer 2026 (View only)</OPTION>
    <OPTION VALUE="202620">Spring 2026 (View only)</OPTION>
    <OPTION VALUE="202613">Winter 2025 (View only)</OPTION>
    <OPTION VALUE="202610">Fall 2025 (View only)</OPTION>
</select>
</form>
</body>
</html>
"""

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

# Sample Banner HTML for course list with hyphenated title, hrefs, and meeting times
SAMPLE_COURSE_LIST_WITH_MEETING_TIMES_HTML = """
<html>
<body>
<table class="datadisplaytable">
    <tr>
        <td>
            <a href="/prod/bwckschd.p_disp_detail_sched?term_in=202710&crn_in=12345">
                Object-Oriented Programming - 12345 - CS 18000 - 001
            </a>
        </td>
    </tr>
    <tr>
        <td>
            <table class="datadisplaytable" summary="This table lists the scheduled meeting times and assigned instructors for this class..">
                <caption class="captiontext">Scheduled Meeting Times</caption>
                <tr>
                    <th class="ddheader">Type</th>
                    <th class="ddheader">Time</th>
                    <th class="ddheader">Days</th>
                    <th class="ddheader">Where</th>
                    <th class="ddheader">Date Range</th>
                    <th class="ddheader">Schedule Type</th>
                    <th class="ddheader">Instructors</th>
                </tr>
                <tr>
                    <td class="dddefault">Lecture</td>
                    <td class="dddefault">10:30 am - 11:20 am</td>
                    <td class="dddefault">MWF</td>
                    <td class="dddefault">WTHR 200</td>
                    <td class="dddefault">08/19/2026 - 12/13/2026</td>
                    <td class="dddefault">Lecture</td>
                    <td class="dddefault">John Smith (P)</td>
                </tr>
            </table>
        </td>
    </tr>
    <tr>
        <td>
            <a href="/prod/bwckschd.p_disp_detail_sched?term_in=202710&crn_in=12346">
                Data Structures - 12346 - CS 25100 - 002
            </a>
        </td>
    </tr>
    <tr>
        <td>
            <table class="datadisplaytable" summary="This table lists the scheduled meeting times and assigned instructors for this class..">
                <caption class="captiontext">Scheduled Meeting Times</caption>
                <tr>
                    <th class="ddheader">Type</th>
                    <th class="ddheader">Time</th>
                    <th class="ddheader">Days</th>
                    <th class="ddheader">Where</th>
                    <th class="ddheader">Date Range</th>
                    <th class="ddheader">Schedule Type</th>
                    <th class="ddheader">Instructors</th>
                </tr>
                <tr>
                    <td class="dddefault">Lecture</td>
                    <td class="dddefault">1:30 pm - 2:20 pm</td>
                    <td class="dddefault">TR</td>
                    <td class="dddefault">MATH 175</td>
                    <td class="dddefault">08/19/2026 - 12/13/2026</td>
                    <td class="dddefault">Lecture</td>
                    <td class="dddefault">Jane Doe (P)</td>
                </tr>
                <tr>
                    <td class="dddefault">Laboratory</td>
                    <td class="dddefault">3:30 pm - 4:20 pm</td>
                    <td class="dddefault">W</td>
                    <td class="dddefault">HAAS G056</td>
                    <td class="dddefault">08/19/2026 - 12/13/2026</td>
                    <td class="dddefault">Laboratory</td>
                    <td class="dddefault">Lab Assistant (P)</td>
                </tr>
            </table>
        </td>
    </tr>
</table>
</body>
</html>
"""

# Sample Banner HTML for course list with hyphenated title and hrefs (simpler version)
SAMPLE_COURSE_LIST_WITH_HYPHENATED_TITLE_HTML = """
<html>
<body>
<table class="datadisplaytable">
    <tr>
        <td>
            <a href="/prod/bwckschd.p_disp_detail_sched?term_in=202710&crn_in=12345">
                Object-Oriented Programming - 12345 - CS 18000 - 001
            </a>
        </td>
    </tr>
    <tr>
        <td>
            <a href="/prod/bwckschd.p_disp_detail_sched?term_in=202710&crn_in=12346">
                Data Structures - Analysis and Implementation - 12346 - CS 25100 - 002
            </a>
        </td>
    </tr>
</table>
</body>
</html>
"""

# Sample Banner HTML for CRN detail with SEPARATE cells (realistic Banner structure)
SAMPLE_DETAIL_OPEN_HTML = """
<html>
<body>
<table class="datadisplaytable">
    <caption class="captiontext">Registration Availability</caption>
    <tr>
        <th class="ddlabel"></th>
        <th class="ddheader">Capacity</th>
        <th class="ddheader">Actual</th>
        <th class="ddheader">Remaining</th>
    </tr>
    <tr>
        <td class="dddefault">Seats</td>
        <td class="dddefault">50</td>
        <td class="dddefault">35</td>
        <td class="dddefault">15</td>
    </tr>
</table>
</body>
</html>
"""

# Sample Banner HTML for CRN detail with no seats (closed)
SAMPLE_DETAIL_CLOSED_HTML = """
<html>
<body>
<table class="datadisplaytable">
    <caption class="captiontext">Registration Availability</caption>
    <tr>
        <th class="ddlabel"></th>
        <th class="ddheader">Capacity</th>
        <th class="ddheader">Actual</th>
        <th class="ddheader">Remaining</th>
    </tr>
    <tr>
        <td class="dddefault">Seats</td>
        <td class="dddefault">50</td>
        <td class="dddefault">50</td>
        <td class="dddefault">0</td>
    </tr>
</table>
</body>
</html>
"""

# Sample Banner HTML with non-zero waitlist (waitlist-enabled)
SAMPLE_DETAIL_WITH_NON_ZERO_WAITLIST_HTML = """
<html>
<body>
<table class="datadisplaytable">
    <caption class="captiontext">Registration Availability</caption>
    <tr>
        <th class="ddlabel"></th>
        <th class="ddheader">Capacity</th>
        <th class="ddheader">Actual</th>
        <th class="ddheader">Remaining</th>
    </tr>
    <tr>
        <td class="dddefault">Seats</td>
        <td class="dddefault">50</td>
        <td class="dddefault">50</td>
        <td class="dddefault">0</td>
    </tr>
    <tr>
        <td class="dddefault">Waitlist Seats</td>
        <td class="dddefault">10</td>
        <td class="dddefault">5</td>
        <td class="dddefault">5</td>
    </tr>
</table>
</body>
</html>
"""

# Sample Banner HTML with zero-waitlist capacity (NOT an error)
SAMPLE_DETAIL_WITH_ZERO_WAITLIST_HTML = """
<html>
<body>
<table class="datadisplaytable">
    <caption class="captiontext">Registration Availability</caption>
    <tr>
        <th class="ddlabel"></th>
        <th class="ddheader">Capacity</th>
        <th class="ddheader">Actual</th>
        <th class="ddheader">Remaining</th>
    </tr>
    <tr>
        <td class="dddefault">Seats</td>
        <td class="dddefault">50</td>
        <td class="dddefault">35</td>
        <td class="dddefault">15</td>
    </tr>
    <tr>
        <td class="dddefault">Waitlist Seats</td>
        <td class="dddefault">0</td>
        <td class="dddefault">0</td>
        <td class="dddefault">0</td>
    </tr>
</table>
</body>
</html>
"""

# Sample Banner HTML with malformed Remaining cell
SAMPLE_DETAIL_MALFORMED_REMAINING_HTML = """
<html>
<body>
<table class="datadisplaytable">
    <caption class="captiontext">Registration Availability</caption>
    <tr>
        <th class="ddlabel"></th>
        <th class="ddheader">Capacity</th>
        <th class="ddheader">Actual</th>
        <th class="ddheader">Remaining</th>
    </tr>
    <tr>
        <td class="dddefault">Seats</td>
        <td class="dddefault">50</td>
        <td class="dddefault">35</td>
        <td class="dddefault">N/A</td>
    </tr>
</table>
</body>
</html>
"""

# Sample Banner HTML with missing seat info
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
    """Test that scraper initializes with correct term code and allowlist."""
    assert scraper.college_short_name == "purdue"
    assert scraper.current_term == "202710"
    assert scraper.total_request_count == 0
    assert scraper.ALLOWED_DEPARTMENTS == ["CS"]


@pytest.mark.asyncio
async def test_all_department_rejected(scraper):
    """Test that department='ALL' is rejected with clear error (full catalog exceeds budget)."""
    await scraper._ensure_client()

    with pytest.raises(ValueError) as exc_info:
        await scraper.scrape_courses("ALL")
    
    error_msg = str(exc_info.value)
    assert "does not support department='ALL'" in error_msg
    assert "21k CRNs" in error_msg
    assert "exceeds budget" in error_msg
    assert "3000 requests" in error_msg
    assert "CS" in error_msg  # Should mention allowed departments


@pytest.mark.asyncio
async def test_non_allowlisted_department_rejected(scraper):
    """Test that non-allowlisted departments (e.g., MA, ECE) are rejected."""
    await scraper._ensure_client()

    # Try Mathematics (not in allowlist)
    with pytest.raises(ValueError) as exc_info:
        await scraper.scrape_courses("MA")
    
    error_msg = str(exc_info.value)
    assert "only supports allowlisted departments" in error_msg
    assert "CS" in error_msg
    assert "MA" in error_msg or "'MA'" in error_msg

    # Try ECE (not in allowlist)
    with pytest.raises(ValueError) as exc_info:
        await scraper.scrape_courses("ECE")
    
    error_msg = str(exc_info.value)
    assert "only supports allowlisted departments" in error_msg
    assert "ECE" in error_msg or "'ECE'" in error_msg


@pytest.mark.asyncio
async def test_cs_allowlisted_department_works(scraper):
    """Test that CS (allowlisted) department can be scraped."""
    await scraper._ensure_client()

    with patch.object(
        scraper, "_make_request_with_retry", new_callable=AsyncMock
    ) as mock_request:
        # Mock picker response
        picker_response = MagicMock()
        picker_response.text = SAMPLE_TERM_PICKER_HTML
        picker_response.content = SAMPLE_TERM_PICKER_HTML.encode("utf-8")

        # Mock subjects response
        subjects_response = MagicMock()
        subjects_response.content = SAMPLE_SUBJECTS_HTML.encode("utf-8")

        # Mock course list response
        course_list_response = MagicMock()
        course_list_response.content = (
            SAMPLE_COURSE_LIST_WITH_HYPHENATED_TITLE_HTML.encode("utf-8")
        )

        # Mock detail responses
        detail_response = MagicMock()
        detail_response.content = SAMPLE_DETAIL_OPEN_HTML.encode("utf-8")

        # Set up side effect to return appropriate responses
        mock_request.side_effect = [
            picker_response,  # GET term picker
            subjects_response,  # POST subjects
            course_list_response,  # POST course list for CS
            detail_response,  # GET detail for CRN 12345
            detail_response,  # GET detail for CRN 12346
        ]

        # CS should work (in allowlist)
        courses = await scraper.scrape_courses("CS")

        # Should succeed and return courses
        assert len(courses) > 0


def test_parse_term_picker(scraper):
    """Test parsing term picker to distinguish registerable vs view-only terms."""
    terms = scraper.parse_term_picker(SAMPLE_TERM_PICKER_HTML)

    assert len(terms) == 6  # Excludes "None" option

    # Check registerable term (no "View only")
    fall_2026 = [t for t in terms if t["code"] == "202710"][0]
    assert fall_2026["name"] == "Fall 2026"
    assert fall_2026["registerable"] is True

    # Check view-only term
    winter_2026 = [t for t in terms if t["code"] == "202713"][0]
    assert winter_2026["name"] == "Winter 2026"
    assert winter_2026["registerable"] is False

    # Check another view-only
    spring_2026 = [t for t in terms if t["code"] == "202620"][0]
    assert spring_2026["registerable"] is False


@pytest.mark.asyncio
async def test_term_validation_via_picker(scraper):
    """Test that scrape_courses validates term via picker."""
    await scraper._ensure_client()

    with patch.object(
        scraper, "_make_request_with_retry", new_callable=AsyncMock
    ) as mock_request:
        # Mock picker response
        picker_response = MagicMock()
        picker_response.text = SAMPLE_TERM_PICKER_HTML
        picker_response.content = SAMPLE_TERM_PICKER_HTML.encode("utf-8")

        # Mock subjects response
        subjects_response = MagicMock()
        subjects_response.content = SAMPLE_SUBJECTS_HTML.encode("utf-8")

        # Mock course list response
        course_list_response = MagicMock()
        course_list_response.content = (
            SAMPLE_COURSE_LIST_WITH_HYPHENATED_TITLE_HTML.encode("utf-8")
        )

        # Mock detail responses
        detail_response = MagicMock()
        detail_response.content = SAMPLE_DETAIL_OPEN_HTML.encode("utf-8")

        # Set up side effect to return appropriate responses
        mock_request.side_effect = [
            picker_response,  # GET term picker
            subjects_response,  # POST subjects
            course_list_response,  # POST course list for CS
            detail_response,  # GET detail for CRN 12345
            detail_response,  # GET detail for CRN 12346
        ]

        courses = await scraper.scrape_courses("CS")

        # Verify picker was called (first call)
        assert mock_request.call_count >= 1
        first_call = mock_request.call_args_list[0]
        assert first_call[0][0] == "GET"
        assert "bwckschd.p_disp_dyn_sched" in first_call[0][1]


@pytest.mark.asyncio
async def test_term_validation_fails_if_term_not_in_picker(scraper):
    """Test that scraper fails loud if DB term not found in picker."""
    await scraper._ensure_client()

    # Use a term that's NOT in the picker
    scraper.current_term = "999999"

    with patch.object(
        scraper, "_make_request_with_retry", new_callable=AsyncMock
    ) as mock_request:
        picker_response = MagicMock()
        picker_response.text = SAMPLE_TERM_PICKER_HTML
        picker_response.content = SAMPLE_TERM_PICKER_HTML.encode("utf-8")
        mock_request.return_value = picker_response

        with pytest.raises(Exception) as exc_info:
            await scraper.scrape_courses("CS")

        assert "999999" in str(exc_info.value)
        assert "not found in picker" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fetch_subject_crns_includes_complete_banner_post_fields(scraper):
    """Test that POST body includes complete Banner multi-select fields with % for all."""
    await scraper._ensure_client()

    with patch.object(
        scraper, "_make_request_with_retry", new_callable=AsyncMock
    ) as mock_request:
        mock_response = MagicMock()
        mock_response.content = SAMPLE_COURSE_LIST_WITH_HYPHENATED_TITLE_HTML.encode(
            "utf-8"
        )
        mock_request.return_value = mock_response

        await scraper._fetch_subject_crns("CS")

        # Verify the request was made with complete Banner POST fields
        call_kwargs = mock_request.call_args[1]
        form_data = call_kwargs.get("data", {})

        # Check required fields
        assert form_data.get("term_in") == "202710"
        assert form_data.get("sel_subj") == ["dummy", "CS"]  # dummy seed + value

        # Check dummy seeds + % for "all" filters (Banner multi-select requirement)
        assert form_data.get("sel_schd") == ["dummy", "%"]
        assert form_data.get("sel_insm") == ["dummy", "%"]
        assert form_data.get("sel_camp") == ["dummy", "%"]
        assert form_data.get("sel_levl") == ["dummy", "%"]
        assert form_data.get("sel_sess") == ["dummy", "%"]
        assert form_data.get("sel_instr") == ["dummy", "%"]
        assert form_data.get("sel_ptrm") == ["dummy", "%"]
        assert form_data.get("sel_attr") == ["dummy", "%"]

        # Check other required fields
        assert form_data.get("sel_day") == "dummy"
        assert form_data.get("sel_crse") == ""
        assert form_data.get("sel_title") == ""
        assert form_data.get("sel_from_cred") == ""
        assert form_data.get("sel_to_cred") == ""
        assert "begin_hh" in form_data
        assert "begin_mi" in form_data
        assert "begin_ap" in form_data
        assert "end_hh" in form_data
        assert "end_mi" in form_data
        assert "end_ap" in form_data


@pytest.mark.asyncio
async def test_extract_crn_from_href_robust(scraper):
    """Test CRN extraction from href query parameter (not text splitting)."""
    href1 = "/prod/bwckschd.p_disp_detail_sched?term_in=202710&crn_in=12345"
    crn1 = scraper._extract_crn_from_href(href1)
    assert crn1 == "12345"

    href2 = "?crn_in=67890&term_in=202710"
    crn2 = scraper._extract_crn_from_href(href2)
    assert crn2 == "67890"


@pytest.mark.asyncio
async def test_parse_hyphenated_title_robust(scraper):
    """Test parsing section text with hyphenated title (robust against naive split)."""
    # Title with hyphen
    text1 = "Object-Oriented Programming - 12345 - CS 18000 - 001"
    parsed1 = scraper._parse_section_text_robust(text1, "12345")

    assert parsed1 is not None
    assert parsed1["crn"] == "12345"
    assert parsed1["title"] == "Object-Oriented Programming"
    assert parsed1["course_code"] == "CS 18000"
    assert parsed1["section"] == "001"

    # Title with multiple hyphens
    text2 = "Data Structures - Analysis and Implementation - 12346 - CS 25100 - 002"
    parsed2 = scraper._parse_section_text_robust(text2, "12346")

    assert parsed2 is not None
    assert parsed2["crn"] == "12346"
    assert parsed2["title"] == "Data Structures - Analysis and Implementation"
    assert parsed2["course_code"] == "CS 25100"
    assert parsed2["section"] == "002"


@pytest.mark.asyncio
async def test_parse_scheduled_meeting_times(scraper):
    """Test parsing Scheduled Meeting Times from listing HTML."""
    await scraper._ensure_client()

    with patch.object(
        scraper, "_make_request_with_retry", new_callable=AsyncMock
    ) as mock_request:
        mock_response = MagicMock()
        mock_response.content = SAMPLE_COURSE_LIST_WITH_MEETING_TIMES_HTML.encode(
            "utf-8"
        )
        mock_request.return_value = mock_response

        crn_entries = await scraper._fetch_subject_crns("CS")

        assert len(crn_entries) == 2

        # Check first CRN has meeting times
        first_entry = crn_entries[0]
        assert first_entry["crn"] == "12345"
        assert "meeting_times" in first_entry
        assert len(first_entry["meeting_times"]) == 1

        # Verify meeting time fields
        meeting = first_entry["meeting_times"][0]
        assert meeting["type"] == "Lecture"
        assert meeting["time"] == "10:30 am - 11:20 am"
        assert meeting["days"] == "MWF"
        assert meeting["where"] == "WTHR 200"
        assert meeting["date_range"] == "08/19/2026 - 12/13/2026"
        assert meeting["schedule_type"] == "Lecture"
        assert meeting["instructors"] == "John Smith (P)"

        # Check second CRN has multiple meeting times (lecture + lab)
        second_entry = crn_entries[1]
        assert second_entry["crn"] == "12346"
        assert "meeting_times" in second_entry
        assert len(second_entry["meeting_times"]) == 2

        # Verify lecture meeting
        lecture = second_entry["meeting_times"][0]
        assert lecture["type"] == "Lecture"
        assert lecture["time"] == "1:30 pm - 2:20 pm"
        assert lecture["days"] == "TR"

        # Verify lab meeting
        lab = second_entry["meeting_times"][1]
        assert lab["type"] == "Laboratory"
        assert lab["time"] == "3:30 pm - 4:20 pm"
        assert lab["days"] == "W"
        assert lab["where"] == "HAAS G056"


@pytest.mark.asyncio
async def test_parse_seat_availability_with_non_zero_waitlist(scraper):
    """Test parsing seat table with non-zero waitlist (waitlist-enabled fixture)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(SAMPLE_DETAIL_WITH_NON_ZERO_WAITLIST_HTML, "lxml")
    seat_info = scraper._parse_seat_availability(soup, "12345")

    # Main seats are 0 remaining, so should be Closed
    # Status is driven by main Seats, not waitlist
    assert seat_info["status"] == "Closed"


@pytest.mark.asyncio
async def test_parse_seat_availability_with_zero_waitlist_not_error(scraper):
    """Test that zero-waitlist capacity is NOT treated as an error."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(SAMPLE_DETAIL_WITH_ZERO_WAITLIST_HTML, "lxml")
    seat_info = scraper._parse_seat_availability(soup, "99999")

    # Main seats have 15 remaining, so should be Open
    # Zero waitlist capacity should NOT cause an error
    assert seat_info["status"] == "Open"


@pytest.mark.asyncio
async def test_parse_seat_availability_separate_cells_open(scraper):
    """Test parsing seat availability with SEPARATE Capacity/Actual/Remaining cells (Open)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(SAMPLE_DETAIL_OPEN_HTML, "lxml")
    seat_info = scraper._parse_seat_availability(soup, "12345")

    assert seat_info["status"] == "Open"  # 15 remaining seats


@pytest.mark.asyncio
async def test_parse_seat_availability_separate_cells_closed(scraper):
    """Test parsing seat availability with SEPARATE cells (Closed)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(SAMPLE_DETAIL_CLOSED_HTML, "lxml")
    seat_info = scraper._parse_seat_availability(soup, "67890")

    assert seat_info["status"] == "Closed"  # 0 remaining seats


@pytest.mark.asyncio
async def test_parse_seat_availability_malformed_remaining_defaults_closed(scraper):
    """Test that malformed Remaining cell defaults to Closed (never invent Open)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(SAMPLE_DETAIL_MALFORMED_REMAINING_HTML, "lxml")
    seat_info = scraper._parse_seat_availability(soup, "88888")

    # CRITICAL: Should default to Closed when Remaining is unparsable
    assert seat_info["status"] == "Closed"


@pytest.mark.asyncio
async def test_parse_seat_availability_missing_seats_defaults_closed(scraper):
    """Test that missing seat data defaults to Closed (never invent Open)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(SAMPLE_DETAIL_MISSING_SEATS_HTML, "lxml")
    seat_info = scraper._parse_seat_availability(soup, "77777")

    # CRITICAL: Should default to Closed when seat data is missing
    assert seat_info["status"] == "Closed"


@pytest.mark.asyncio
async def test_budget_error_is_non_retryable(scraper):
    """Test that budget errors raise PurdueBudgetExceededError (non-retryable)."""
    await scraper._ensure_client()

    # Set a very low budget to trigger error
    scraper.MAX_TOTAL_REQUESTS = 3

    call_count = 0

    async def mock_request_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1

        # Simulate budget check
        scraper.total_request_count += 1
        if scraper.total_request_count > scraper.MAX_TOTAL_REQUESTS:
            raise PurdueBudgetExceededError(
                f"Request budget exceeded: {scraper.total_request_count} > "
                f"{scraper.MAX_TOTAL_REQUESTS}"
            )

        # Return appropriate mock responses
        if call_count == 1:
            # GET term picker
            response = MagicMock()
            response.text = SAMPLE_TERM_PICKER_HTML
            response.content = SAMPLE_TERM_PICKER_HTML.encode("utf-8")
            response.raise_for_status = MagicMock()
            return response
        elif call_count == 2:
            # POST subjects
            response = MagicMock()
            response.content = SAMPLE_SUBJECTS_HTML.encode("utf-8")
            response.raise_for_status = MagicMock()
            return response
        elif call_count == 3:
            # POST course list for CS
            response = MagicMock()
            response.content = SAMPLE_COURSE_LIST_WITH_HYPHENATED_TITLE_HTML.encode(
                "utf-8"
            )
            response.raise_for_status = MagicMock()
            return response
        else:
            # This should trigger budget exceeded
            response = MagicMock()
            response.content = SAMPLE_COURSE_LIST_WITH_HYPHENATED_TITLE_HTML.encode(
                "utf-8"
            )
            response.raise_for_status = MagicMock()
            return response

    with patch.object(
        scraper, "_make_request_with_retry", side_effect=mock_request_side_effect
    ):
        # Should raise PurdueBudgetExceededError, not generic Exception
        with pytest.raises(PurdueBudgetExceededError) as exc_info:
            await scraper.scrape_courses("CS")

        error_msg = str(exc_info.value)
        assert "budget exceeded" in error_msg.lower()
        assert "non-retryable" in error_msg.lower()


@pytest.mark.asyncio
async def test_budget_preflight_uses_worst_case_estimate(scraper):
    """Test that preflight budget check uses worst-case (1+MAX_RETRIES) multiplier."""
    await scraper._ensure_client()

    # Set up scenario: 161 listing + 750 CRNs
    # Preflight: 161 + (750 * 4) = 3161 > 3000 -> should FAIL
    scraper.total_request_count = 161
    scraper.MAX_TOTAL_REQUESTS = 3000

    # Create 750 CRNs (will exceed with 4x multiplier)
    all_crn_entries = [
        {"crn": str(i), "course_code": f"CS {i}", "title": "Test", "section": "001"}
        for i in range(750)
    ]

    with patch.object(scraper, "_validate_term_via_picker", new_callable=AsyncMock):
        with patch.object(scraper, "_fetch_subjects", new_callable=AsyncMock) as mock_subjects:
            mock_subjects.return_value = ["CS"]
            with patch.object(scraper, "_fetch_subject_crns", new_callable=AsyncMock) as mock_crns:
                mock_crns.return_value = all_crn_entries

                # Should raise PurdueBudgetExceededError due to preflight
                with pytest.raises(PurdueBudgetExceededError) as exc_info:
                    await scraper.scrape_courses("CS")
                
                error_msg = str(exc_info.value).lower()
                assert "budget" in error_msg
                assert "would be exceeded" in error_msg
                assert "no partial success" in error_msg


@pytest.mark.asyncio
async def test_limit_truncation_fails_loud(scraper):
    """Test that limit truncation fails loud to prevent silent partial success."""
    await scraper._ensure_client()

    # Set up scenario: 2000 CRNs but limit=100
    # Should FAIL with truncation error (not silently truncate)
    scraper.total_request_count = 161
    scraper.MAX_TOTAL_REQUESTS = 3000

    # Create 2000 CRN entries
    all_crn_entries = [
        {"crn": str(i), "course_code": f"CS {i}", "title": "Test", "section": "001"}
        for i in range(2000)
    ]

    with patch.object(scraper, "_validate_term_via_picker", new_callable=AsyncMock):
        with patch.object(scraper, "_fetch_subjects", new_callable=AsyncMock) as mock_subjects:
            mock_subjects.return_value = ["CS"]
            with patch.object(scraper, "_fetch_subject_crns", new_callable=AsyncMock) as mock_crns:
                mock_crns.return_value = all_crn_entries

                # Should raise PurdueBudgetExceededError for truncation
                with pytest.raises(PurdueBudgetExceededError) as exc_info:
                    await scraper.scrape_courses("CS", limit=100)
                
                error_msg = str(exc_info.value)
                assert "LIMIT TRUNCATION" in error_msg or "truncat" in error_msg.lower()
                assert "2000" in error_msg  # Total CRNs
                assert "100" in error_msg  # Limit
                assert "silent partial success" in error_msg.lower()


@pytest.mark.asyncio
async def test_request_budget_failure_through_scrape_courses_path(scraper):
    """Test request budget failure through the scrape_courses path (not just helper)."""
    await scraper._ensure_client()

    # Set a very low budget
    scraper.MAX_TOTAL_REQUESTS = 3

    call_count = 0

    async def mock_request_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1

        # Simulate budget check
        scraper.total_request_count += 1
        if scraper.total_request_count > scraper.MAX_TOTAL_REQUESTS:
            raise PurdueBudgetExceededError(
                f"Request budget exceeded: {scraper.total_request_count} > "
                f"{scraper.MAX_TOTAL_REQUESTS}"
            )

        # Return appropriate mock responses
        if call_count == 1:
            # GET term picker
            response = MagicMock()
            response.text = SAMPLE_TERM_PICKER_HTML
            response.content = SAMPLE_TERM_PICKER_HTML.encode("utf-8")
            response.raise_for_status = MagicMock()
            return response
        elif call_count == 2:
            # POST subjects
            response = MagicMock()
            response.content = SAMPLE_SUBJECTS_HTML.encode("utf-8")
            response.raise_for_status = MagicMock()
            return response
        elif call_count == 3:
            # POST course list for CS
            response = MagicMock()
            response.content = SAMPLE_COURSE_LIST_WITH_HYPHENATED_TITLE_HTML.encode(
                "utf-8"
            )
            response.raise_for_status = MagicMock()
            return response
        else:
            # This should trigger budget exceeded
            response = MagicMock()
            response.content = SAMPLE_COURSE_LIST_WITH_HYPHENATED_TITLE_HTML.encode(
                "utf-8"
            )
            response.raise_for_status = MagicMock()
            return response

    with patch.object(
        scraper, "_make_request_with_retry", side_effect=mock_request_side_effect
    ):
        with pytest.raises(PurdueBudgetExceededError):
            await scraper.scrape_courses("CS")


@pytest.mark.asyncio
async def test_retry_logic_on_429_rate_limit(scraper):
    """Test that scraper retries on 429 rate limit with backoff."""
    await scraper._ensure_client()

    call_count = 0

    async def mock_request_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1

        if call_count < 3:
            # First 2 attempts: return 429
            response = MagicMock()
            response.status_code = 429
            raise httpx.HTTPStatusError(
                "Rate limited",
                request=MagicMock(),
                response=response,
            )
        else:
            # Third attempt: success
            response = MagicMock()
            response.content = SAMPLE_SUBJECTS_HTML.encode("utf-8")
            response.raise_for_status = MagicMock()
            return response

    with patch.object(scraper.client, "post", side_effect=mock_request_side_effect):
        # This should succeed after retries
        result = await scraper._make_request_with_retry("POST", "http://test.com")

        # Should have retried 2 times + 1 success = 3 total attempts
        assert call_count == 3


@pytest.mark.asyncio
async def test_retry_logic_on_5xx_server_error(scraper):
    """Test that scraper retries on 5xx server errors with backoff."""
    await scraper._ensure_client()

    call_count = 0

    async def mock_request_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1

        if call_count < 2:
            # First attempt: return 503
            response = MagicMock()
            response.status_code = 503
            raise httpx.HTTPStatusError(
                "Service unavailable",
                request=MagicMock(),
                response=response,
            )
        else:
            # Second attempt: success
            response = MagicMock()
            response.content = SAMPLE_SUBJECTS_HTML.encode("utf-8")
            response.raise_for_status = MagicMock()
            return response

    with patch.object(scraper.client, "get", side_effect=mock_request_side_effect):
        # This should succeed after retries
        result = await scraper._make_request_with_retry("GET", "http://test.com")

        # Should have retried 1 time + 1 success = 2 total attempts
        assert call_count == 2


@pytest.mark.asyncio
async def test_partial_detail_failure_aborts_scrape(scraper):
    """Test that any detail fetch returning None aborts the entire scrape (fail-loud)."""
    await scraper._ensure_client()

    # Mock one success and one failure (None)
    crn_entries = [
        {"crn": "12345", "course_code": "CS 180", "title": "Test1", "section": "001"},
        {"crn": "67890", "course_code": "CS 240", "title": "Test2", "section": "001"},
    ]

    call_count = 0

    async def mock_fetch_detail(entry):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call succeeds
            return {
                "class_number": entry["crn"],
                "course_code": entry["course_code"],
                "title": entry["title"],
                "section": entry["section"],
                "status": "Open",
            }
        else:
            # Second call returns None (failure)
            return None

    with patch.object(scraper, "_fetch_crn_detail", side_effect=mock_fetch_detail):
        with pytest.raises(Exception) as exc_info:
            await scraper._fetch_details_and_group(crn_entries)

        # Should mention "no partial success"
        assert "no partial success" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_bounded_concurrency_enforced(scraper):
    """Test that detail fetches use bounded concurrency (semaphore = 4)."""
    await scraper._ensure_client()

    max_concurrent = 0
    current_concurrent = 0

    async def mock_fetch_detail(entry):
        nonlocal max_concurrent, current_concurrent
        current_concurrent += 1
        max_concurrent = max(max_concurrent, current_concurrent)

        # Simulate work
        await asyncio.sleep(0.01)

        current_concurrent -= 1
        return {
            "class_number": entry["crn"],
            "course_code": entry["course_code"],
            "title": entry["title"],
            "section": entry["section"],
            "status": "Open",
        }

    # Create 20 CRN entries
    crn_entries = [
        {"crn": str(i), "course_code": f"CS {i}", "title": "Test", "section": "001"}
        for i in range(20)
    ]

    with patch.object(scraper, "_fetch_crn_detail", side_effect=mock_fetch_detail):
        await scraper._fetch_details_and_group(crn_entries)

    # Max concurrent should be 4 (semaphore limit)
    assert max_concurrent == 4


@pytest.mark.asyncio
async def test_term_code_from_db(mock_db_session):
    """Test that term code is fetched from database, not hardcoded."""
    scraper = PurdueScraper(db_session=mock_db_session)

    # Should get term from mock_db_session
    assert scraper.current_term == "202710"

    # Verify no hardcoded term in production code path
    # (This is validated by the scraper using get_term_code_from_db in __init__)


@pytest.mark.asyncio
async def test_budget_exceeded_consumes_one_attempt_not_three():
    """
    Test service/job boundary: budget_exceeded outcome consumes ONE attempt, not three.
    Regression test proving non-retryable wiring works end-to-end.
    """
    from scraper.scraper_job import ScraperJob, JobConfig
    from scraper.services.scraper_service import ScraperService
    from unittest.mock import AsyncMock, MagicMock, patch
    
    # Create mock college and db session
    mock_college = MagicMock()
    mock_college.id = 20
    mock_college.name = "Purdue University"
    mock_college.short_name = "purdue"
    mock_college.is_active = True
    
    mock_db = MagicMock()
    
    # Track how many times scrape_college is called
    attempt_count = 0
    
    async def mock_scrape_college(*args, **kwargs):
        nonlocal attempt_count
        attempt_count += 1
        # Simulate budget exceeded error
        return {
            "college": "purdue",
            "department": "ALL",
            "courses_saved": 0,
            "classes_saved": 0,
            "enrollments_saved": 0,
            "duration_seconds": 0.1,
            "success": False,
            "outcome": "budget_exceeded",  # Non-retryable outcome
            "error": "Request budget would be exceeded by details: 161 + 85548 > 3000",
        }
    
    # Create job with 3 retry attempts (default)
    config = JobConfig(subject="ALL", limit=None, retry_attempts=3)
    job = ScraperJob(mock_college, mock_db, config)
    
    # Mock the lock and log service
    with patch.object(job.lock, 'acquire', return_value=MagicMock(success=True)):
        with patch.object(job.lock, 'release'):
            with patch.object(job.lock, 'get_scraper_id', return_value=1):
                with patch('scraper.scraper_job.ScraperLogService') as mock_log_service:
                    mock_log_service_instance = AsyncMock()
                    mock_log_service_instance.start_log = AsyncMock(return_value=1)
                    mock_log_service_instance.complete_log = AsyncMock()
                    mock_log_service.return_value = mock_log_service_instance
                    
                    # Patch ScraperService.scrape_college to return budget_exceeded
                    with patch.object(ScraperService, 'scrape_college', side_effect=mock_scrape_college):
                        result = await job.execute()
    
    # CRITICAL: Should have called scrape_college ONCE, not three times
    # budget_exceeded outcome should prevent retry
    assert attempt_count == 1, f"Expected 1 attempt, got {attempt_count}. budget_exceeded should not retry!"
    assert result.success is False
    assert "budget" in result.error.lower()


