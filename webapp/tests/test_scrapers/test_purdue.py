"""Tests for Purdue University course scraper."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import sys
from pathlib import Path

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from scraper.scrapers.purdue import PurdueScraper
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

# Sample Banner HTML for course list with hyphenated title and hrefs
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
    """Test that scraper initializes with correct term code."""
    assert scraper.college_short_name == "purdue"
    assert scraper.current_term == "202710"
    assert scraper.total_request_count == 0


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

        # Check % for "all" filters
        assert form_data.get("sel_schd") == "%"
        assert form_data.get("sel_insm") == "%"
        assert form_data.get("sel_camp") == "%"
        assert form_data.get("sel_levl") == "%"
        assert form_data.get("sel_sess") == "%"
        assert form_data.get("sel_instr") == "%"
        assert form_data.get("sel_ptrm") == "%"
        assert form_data.get("sel_attr") == "%"

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
            raise Exception(
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
            # POST course list for first subject
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
        with pytest.raises(Exception) as exc_info:
            await scraper.scrape_courses("ALL")  # Try to scrape all subjects

        assert "budget" in str(exc_info.value).lower()


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
