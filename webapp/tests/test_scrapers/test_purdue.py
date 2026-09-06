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

# Sample Banner HTML response for course search (CRN list) - realistic with hrefs
SAMPLE_COURSE_LIST_HTML = """
<html>
<body>
<table class="datadisplaytable">
    <tr>
        <td>
            <a href="/prod/bwckschd.p_disp_detail_sched?term_in=202710&crn_in=12345">
                Intro to Programming - 12345 - CS 18000 - 001
            </a>
        </td>
    </tr>
    <tr>
        <td>
            <a href="/prod/bwckschd.p_disp_detail_sched?term_in=202710&crn_in=12346">
                Intro to Programming - 12346 - CS 18000 - 002
            </a>
        </td>
    </tr>
    <tr>
        <td>
            <a href="/prod/bwckschd.p_disp_detail_sched?term_in=202710&crn_in=67890">
                Data Structures - 67890 - CS 25100 - 001
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
        <th class="ddlabel">Seats</th>
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
        <th class="ddlabel">Seats</th>
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

# Sample Banner HTML for CRN detail with waitlist (zero waitlist seats)
SAMPLE_DETAIL_WITH_WAITLIST_HTML = """
<html>
<body>
<table class="datadisplaytable">
    <caption class="captiontext">Registration Availability</caption>
    <tr>
        <th class="ddlabel">Seats</th>
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

# Sample Banner HTML with malformed Remaining cell
SAMPLE_DETAIL_MALFORMED_REMAINING_HTML = """
<html>
<body>
<table class="datadisplaytable">
    <caption class="captiontext">Registration Availability</caption>
    <tr>
        <th class="ddlabel">Seats</th>
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
async def test_fetch_subjects(scraper):
    """Test fetching subject list from Banner."""
    await scraper._ensure_client()

    with patch.object(
        scraper, "_make_request_with_retry", new_callable=AsyncMock
    ) as mock_request:
        mock_response = MagicMock()
        mock_response.content = SAMPLE_SUBJECTS_HTML.encode("utf-8")
        mock_request.return_value = mock_response

        subjects = await scraper._fetch_subjects()

        assert len(subjects) == 3
        assert "CS" in subjects
        assert "MA" in subjects
        assert "ECE" in subjects
        assert "%" not in subjects  # Should exclude dummy/all option


@pytest.mark.asyncio
async def test_fetch_subject_crns_with_href_parsing(scraper):
    """Test fetching CRN list using href parsing (not just onclick)."""
    await scraper._ensure_client()

    with patch.object(
        scraper, "_make_request_with_retry", new_callable=AsyncMock
    ) as mock_request:
        mock_response = MagicMock()
        mock_response.content = SAMPLE_COURSE_LIST_HTML.encode("utf-8")
        mock_request.return_value = mock_response

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
async def test_fetch_subject_crns_includes_banner_dummy_seeds(scraper):
    """Test that POST body includes Banner multi-select dummy seeds."""
    await scraper._ensure_client()

    with patch.object(
        scraper, "_make_request_with_retry", new_callable=AsyncMock
    ) as mock_request:
        mock_response = MagicMock()
        mock_response.content = SAMPLE_COURSE_LIST_HTML.encode("utf-8")
        mock_request.return_value = mock_response

        await scraper._fetch_subject_crns("CS")

        # Verify the request was made with proper Banner dummy seeds
        call_kwargs = mock_request.call_args[1]
        form_data = call_kwargs.get("data", {})

        # Check that sel_subj includes dummy seed
        assert "sel_subj" in form_data
        assert form_data["sel_subj"] == ["dummy", "CS"]

        # Check other dummy fields
        assert form_data.get("sel_day") == "dummy"
        assert form_data.get("sel_schd") == "dummy"


@pytest.mark.asyncio
async def test_deduplicate_crns(scraper):
    """Test CRN deduplication (keep first occurrence)."""
    crn_entries = [
        {
            "crn": "12345",
            "course_code": "CS 18000",
            "title": "Intro",
            "section": "001",
        },
        {
            "crn": "12346",
            "course_code": "CS 18000",
            "title": "Intro",
            "section": "002",
        },
        {
            "crn": "12345",
            "course_code": "CS 18000",
            "title": "Intro",
            "section": "003",
        },  # Duplicate
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
async def test_parse_seat_availability_separate_cells_open(scraper):
    """Test parsing seat availability with SEPARATE Capacity/Actual/Remaining cells (Open)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(SAMPLE_DETAIL_OPEN_HTML, "lxml")
    status = scraper._parse_seat_availability(soup, "12345")

    assert status == "Open"  # 15 remaining seats


@pytest.mark.asyncio
async def test_parse_seat_availability_separate_cells_closed(scraper):
    """Test parsing seat availability with SEPARATE cells (Closed)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(SAMPLE_DETAIL_CLOSED_HTML, "lxml")
    status = scraper._parse_seat_availability(soup, "67890")

    assert status == "Closed"  # 0 remaining seats


@pytest.mark.asyncio
async def test_parse_seat_availability_with_waitlist(scraper):
    """Test parsing seat table that includes waitlist rows (focus on main Seats row)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(SAMPLE_DETAIL_WITH_WAITLIST_HTML, "lxml")
    status = scraper._parse_seat_availability(soup, "99999")

    # Main seats are 0 remaining, so should be Closed
    # (Waitlist parsing is out of scope for now)
    assert status == "Closed"


@pytest.mark.asyncio
async def test_parse_seat_availability_malformed_remaining_defaults_closed(scraper):
    """Test that malformed Remaining cell defaults to Closed (never invent Open)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(SAMPLE_DETAIL_MALFORMED_REMAINING_HTML, "lxml")
    status = scraper._parse_seat_availability(soup, "88888")

    # CRITICAL: Should default to Closed when Remaining is unparsable
    assert status == "Closed"


@pytest.mark.asyncio
async def test_parse_seat_availability_missing_seats_defaults_closed(scraper):
    """Test that missing seat data defaults to Closed (never invent Open)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(SAMPLE_DETAIL_MISSING_SEATS_HTML, "lxml")
    status = scraper._parse_seat_availability(soup, "77777")

    # CRITICAL: Should default to Closed when seat data is missing
    assert status == "Closed"


@pytest.mark.asyncio
async def test_fetch_crn_detail_open(scraper):
    """Test fetching detail page with open seats."""
    await scraper._ensure_client()

    with patch.object(
        scraper, "_make_request_with_retry", new_callable=AsyncMock
    ) as mock_request:
        mock_response = MagicMock()
        mock_response.content = SAMPLE_DETAIL_OPEN_HTML.encode("utf-8")
        mock_request.return_value = mock_response

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
async def test_retry_logic_on_transport_error(scraper):
    """Test that scraper retries on transient transport errors."""
    await scraper._ensure_client()

    call_count = 0

    async def mock_request_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1

        if call_count < 2:
            # First attempt: transport error
            raise httpx.TransportError("Connection reset")
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
async def test_retry_exhaustion_raises_exception(scraper):
    """Test that scraper raises exception after exhausting retries."""
    await scraper._ensure_client()

    async def mock_request_side_effect(*args, **kwargs):
        response = MagicMock()
        response.status_code = 503
        raise httpx.HTTPStatusError(
            "Service unavailable", request=MagicMock(), response=response
        )

    with patch.object(scraper.client, "get", side_effect=mock_request_side_effect):
        with pytest.raises(httpx.HTTPStatusError):
            await scraper._make_request_with_retry("GET", "http://test.com")


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
async def test_request_budget_covers_all_requests_including_retries(scraper):
    """Test that request budget accounts for listings + retries + details."""
    await scraper._ensure_client()

    # Set a very low budget
    scraper.MAX_TOTAL_REQUESTS = 5

    call_count = 0

    async def mock_request_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1

        # Always succeed to test budget enforcement
        response = MagicMock()
        response.content = SAMPLE_SUBJECTS_HTML.encode("utf-8")
        response.raise_for_status = MagicMock()
        return response

    with patch.object(scraper.client, "post", side_effect=mock_request_side_effect):
        with patch.object(scraper.client, "get", side_effect=mock_request_side_effect):
            with pytest.raises(Exception) as exc_info:
                # Try to make more requests than budget allows
                for i in range(10):
                    await scraper._make_request_with_retry("POST", "http://test.com")

            assert "Request budget exceeded" in str(exc_info.value)


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
async def test_crn_is_used_as_class_number(scraper):
    """Test that CRN is used as class_number (identity mapping)."""
    await scraper._ensure_client()

    with patch.object(
        scraper, "_make_request_with_retry", new_callable=AsyncMock
    ) as mock_request:
        mock_response = MagicMock()
        mock_response.content = SAMPLE_DETAIL_OPEN_HTML.encode("utf-8")
        mock_request.return_value = mock_response

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
