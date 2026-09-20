"""Tests for NC State University course scraper."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from pathlib import Path

import sys

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from scraper.scrapers.ncsu import (
    NcsuScraper,
    NcsuBudgetExceededError,
    NcsuEmptySubjectError,
)
from models.college import College
import httpx

# Fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "ncsu"


def load_fixture(filename: str) -> dict:
    """Load a JSON fixture file. Tests fail if fixture is missing."""
    fixture_path = FIXTURES_DIR / filename
    if not fixture_path.exists():
        raise FileNotFoundError(
            f"Fixture {filename} not found at {fixture_path}. "
            f"Tests require real-shaped fixtures."
        )
    with open(fixture_path, "r") as f:
        return json.load(f)


@pytest.fixture
def mock_db_session():
    """Create a mock database session for NC State scraper."""
    mock_session = MagicMock()
    mock_college = College(
        id=1,
        name="North Carolina State University",
        short_name="ncsu",
        term_code="2268",  # Fall 2026
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
    """Create an NC State scraper instance."""
    return NcsuScraper(db_session=mock_db_session)


@pytest.mark.asyncio
async def test_scraper_initialization(scraper):
    """Test that scraper initializes with correct term code and full-catalog budget."""
    assert scraper.college_short_name == "ncsu"
    assert scraper.current_term == "2268"
    assert scraper.total_request_count == 0
    assert not hasattr(scraper, "ALLOWED_DEPARTMENTS")
    assert scraper.MAX_RESPONSE_SIZE == 5 * 1024 * 1024
    # 1 subjects.php + 199 Fall search.php = 200; 350 leaves retry/growth headroom
    assert scraper.MAX_TOTAL_REQUESTS == 350


@pytest.mark.asyncio
async def test_cs_is_crop_science_not_compsci(scraper):
    """
    CRITICAL: CS = Crop Science, CSC = Computer Science.
    Full catalog scrapes both ACS codes; CS must never be treated as CompSci.
    """
    subjects_fixture = load_fixture("subjects.json")
    subjects_list = json.loads(subjects_fixture["subj_js"])

    cs_entry = next(s for s in subjects_list if s.startswith("CS "))
    csc_entry = next(s for s in subjects_list if s.startswith("CSC "))

    assert "Crop Science" in cs_entry
    assert "Computer Science" in csc_entry
    assert "Computer Science" not in cs_entry


@pytest.mark.asyncio
async def test_full_catalog_budget_covers_verified_fall_cardinality(scraper):
    """
    Live Fall 2026 (strm=2268, verified 2026-09-20): 199 subjects.
    Baseline = 1 subjects.php + 199 search.php = 200.
    Budget 350 covers that plus retry/growth headroom without fail-loud abort.
    """
    verified_fall_subjects = 199
    baseline_requests = 1 + verified_fall_subjects
    assert scraper.MAX_TOTAL_REQUESTS == 350
    assert baseline_requests < scraper.MAX_TOTAL_REQUESTS
    assert scraper.MAX_TOTAL_REQUESTS - baseline_requests >= 100


@pytest.mark.asyncio
async def test_fetch_subjects_parses_nested_json(scraper):
    """Test parsing subjects from nested subj_js JSON string."""
    await scraper._ensure_client()

    subjects_fixture = load_fixture("subjects.json")

    with patch.object(
        scraper, "_make_request_with_retry", new_callable=AsyncMock
    ) as mock_request:
        response = MagicMock()
        response.json.return_value = subjects_fixture
        mock_request.return_value = response

        subjects = await scraper._fetch_subjects()

        # Should have parsed subject codes from nested JSON
        assert "CSC" in subjects
        assert "CS" in subjects  # Crop Science
        assert "MA" in subjects
        assert "ECE" in subjects


@pytest.mark.asyncio
async def test_parse_courses_from_html_with_open_closed(scraper):
    """Test parsing courses from real-shaped HTML with Open and Closed statuses."""
    search_fixture = load_fixture("search_csc_open_closed.json")
    html_content = search_fixture["html"]

    courses = scraper._parse_courses_from_html(html_content, "CSC")

    # Should have 3 courses
    assert len(courses) == 3

    # Find CSC 110
    csc110 = next((c for c in courses if c["course_code"] == "CSC 110"), None)
    assert csc110 is not None
    assert "Computer Science Principles" in csc110["title"]
    assert len(csc110["classes"]) == 2

    # Check Open status
    open_classes = [c for c in csc110["classes"] if c["status"] == "Open"]
    assert len(open_classes) == 2

    # Find CSC 111
    csc111 = next((c for c in courses if c["course_code"] == "CSC 111"), None)
    assert csc111 is not None
    assert "Data Science" in csc111["title"] or "Python" in csc111["title"]

    # Should have both Reserved and Closed
    reserved_class = next(
        (c for c in csc111["classes"] if c["class_number"] == "8291"), None
    )
    assert reserved_class is not None
    assert reserved_class["status"] == "Closed"  # Reserved maps to Closed

    closed_class = next(
        (c for c in csc111["classes"] if c["class_number"] == "4780"), None
    )
    assert closed_class is not None
    assert closed_class["status"] == "Closed"


@pytest.mark.asyncio
async def test_status_mapping_reserved_waitlist_to_closed(scraper):
    """
    Test that Reserved and Waitlist statuses map to Closed.
    Reserved→Closed enables reserve-release alerts.
    """
    search_fixture = load_fixture("search_csc_reserved.json")
    html_content = search_fixture["html"]

    courses = scraper._parse_courses_from_html(html_content, "CSC")

    assert len(courses) == 1
    csc316 = courses[0]
    assert csc316["course_code"] == "CSC 316"

    # Both sections should be Closed (Reserved and Waitlist map to Closed)
    for class_data in csc316["classes"]:
        assert class_data["status"] == "Closed"


@pytest.mark.asyncio
async def test_class_number_identity(scraper):
    """
    CRITICAL: Test that class_number (from td.class-num) is present as the identity field.
    NC State uses Class # as the unique identifier, not section alone.
    """
    search_fixture = load_fixture("search_csc_open_closed.json")
    html_content = search_fixture["html"]

    courses = scraper._parse_courses_from_html(html_content, "CSC")

    # Every class should have a class_number
    for course in courses:
        for class_data in course["classes"]:
            assert "class_number" in class_data
            assert class_data["class_number"] is not None
            assert len(class_data["class_number"]) > 0


@pytest.mark.asyncio
async def test_empty_html_fails_loud(scraper):
    """Test that empty HTML content fails loud (no silent partial success)."""
    search_fixture = load_fixture("search_csc_empty.json")
    html_content = search_fixture["html"]

    with pytest.raises(NcsuEmptySubjectError) as exc_info:
        scraper._parse_courses_from_html(html_content, "CSC")

    error_msg = str(exc_info.value)
    assert (
        "No course sections found" in error_msg
        or "breaking change" in error_msg.lower()
    )


@pytest.mark.asyncio
async def test_all_continues_past_empty_subject(scraper):
    """
    ALL fan-out must skip subjects with empty HTML or zero course sections
    (live CNR shape: no-result-alert, no <section class="course">) and still
    return courses from non-empty subjects.
    """
    await scraper._ensure_client()

    subjects_payload = {
        "subj_js": json.dumps(
            [
                "CNR - College of Natural Resources",
                "AA - Advanced Analytics",
                "CSC - Computer Science",
            ]
        )
    }
    search_cnr = load_fixture("search_cnr_empty.json")
    search_empty_html = load_fixture("search_csc_empty.json")
    search_csc = load_fixture("search_csc_open_closed.json")
    requested_subjects = []

    async def mock_request(method, url, **kwargs):
        response = MagicMock()
        if "subjects.php" in url:
            response.json.return_value = subjects_payload
            return response
        subject = kwargs.get("data", {}).get("subject")
        requested_subjects.append(subject)
        if subject == "CNR":
            response.json.return_value = search_cnr
        elif subject == "AA":
            response.json.return_value = search_empty_html
        elif subject == "CSC":
            response.json.return_value = search_csc
        else:
            raise AssertionError(f"Unexpected subject {subject}")
        return response

    with patch.object(scraper, "_make_request_with_retry", side_effect=mock_request):
        courses = await scraper.scrape_courses("ALL")

    assert requested_subjects == ["CNR", "AA", "CSC"]
    assert len(courses) > 0
    assert all(_subject_code(c["course_code"]) == "CSC" for c in courses)
    assert not any(_subject_code(c["course_code"]) in {"CNR", "AA"} for c in courses)


@pytest.mark.asyncio
async def test_named_empty_department_fails_loud(scraper):
    """Named department scrape still fails loud on empty / no-section HTML."""
    await scraper._ensure_client()

    subjects_fixture = load_fixture("subjects.json")
    empty_searches = [
        load_fixture("search_cnr_empty.json"),
        load_fixture("search_csc_empty.json"),
    ]

    for empty_search in empty_searches:

        async def mock_request(method, url, **kwargs):
            response = MagicMock()
            if "subjects.php" in url:
                response.json.return_value = subjects_fixture
                return response
            response.json.return_value = empty_search
            return response

        with patch.object(
            scraper, "_make_request_with_retry", side_effect=mock_request
        ):
            with pytest.raises(NcsuEmptySubjectError) as exc_info:
                await scraper.scrape_courses("CSC")

        error_msg = str(exc_info.value)
        assert (
            "No course sections found" in error_msg or "Empty HTML content" in error_msg
        )


@pytest.mark.asyncio
async def test_all_empty_catalog_fails_loud(scraper):
    """ALL that finds zero courses across all subjects still fails loud."""
    await scraper._ensure_client()

    subjects_payload = {
        "subj_js": json.dumps(
            [
                "CNR - College of Natural Resources",
                "AA - Advanced Analytics",
            ]
        )
    }
    search_cnr = load_fixture("search_cnr_empty.json")
    search_empty_html = load_fixture("search_csc_empty.json")

    async def mock_request(method, url, **kwargs):
        response = MagicMock()
        if "subjects.php" in url:
            response.json.return_value = subjects_payload
            return response
        subject = kwargs.get("data", {}).get("subject")
        if subject == "CNR":
            response.json.return_value = search_cnr
        else:
            response.json.return_value = search_empty_html
        return response

    with patch.object(scraper, "_make_request_with_retry", side_effect=mock_request):
        with pytest.raises(Exception) as exc_info:
            await scraper.scrape_courses("ALL")

    error_msg = str(exc_info.value)
    assert "No courses found across" in error_msg
    assert (
        "empty term data" in error_msg.lower() or "breaking change" in error_msg.lower()
    )


@pytest.mark.asyncio
async def test_normalize_ncsu_status(scraper):
    """Test status normalization for NC State statuses."""
    # Open → Open
    assert scraper._normalize_ncsu_status("Open") == "Open"
    assert scraper._normalize_ncsu_status("open") == "Open"
    assert scraper._normalize_ncsu_status("OPEN") == "Open"

    # Closed → Closed
    assert scraper._normalize_ncsu_status("Closed") == "Closed"
    assert scraper._normalize_ncsu_status("closed") == "Closed"

    # Reserved → Closed
    assert scraper._normalize_ncsu_status("Reserved") == "Closed"
    assert scraper._normalize_ncsu_status("reserved") == "Closed"

    # Waitlist → Closed
    assert scraper._normalize_ncsu_status("Waitlist") == "Closed"
    assert scraper._normalize_ncsu_status("waitlist") == "Closed"

    # Unknown → Closed (conservative default)
    assert scraper._normalize_ncsu_status("Unknown") == "Closed"
    assert scraper._normalize_ncsu_status("Pending") == "Closed"
    assert scraper._normalize_ncsu_status("") == "Closed"
    assert scraper._normalize_ncsu_status(None) == "Closed"


def _subject_code(course_code: str) -> str:
    """Extract ACS subject code; do not use startswith('CS') (matches CSC)."""
    return course_code.split(" ", 1)[0]


@pytest.mark.asyncio
async def test_all_department_fans_out_to_all_subjects(scraper):
    """
    Test that department='ALL' fans out to every subject from subjects.php,
    including both CS (Crop Science) and CSC (Computer Science).
    """
    await scraper._ensure_client()

    subjects_fixture = load_fixture("subjects.json")
    expected_subjects = [
        entry.split(" - ", 1)[0].strip()
        for entry in json.loads(subjects_fixture["subj_js"])
    ]
    assert "CS" in expected_subjects
    assert "CSC" in expected_subjects

    fetched_departments = []

    async def fake_fetch_department_courses(department: str):
        fetched_departments.append(department)
        return [
            {
                "course_code": f"{department} 101",
                "title": f"{department} Course",
                "classes": [
                    {
                        "class_number": "1",
                        "section": "001",
                        "status": "Open",
                    }
                ],
            }
        ]

    with patch.object(
        scraper, "_make_request_with_retry", new_callable=AsyncMock
    ) as mock_request:
        subjects_response = MagicMock()
        subjects_response.json.return_value = subjects_fixture
        mock_request.return_value = subjects_response

        with patch.object(
            scraper,
            "_fetch_department_courses",
            side_effect=fake_fetch_department_courses,
        ):
            courses = await scraper.scrape_courses("ALL", limit=None)

    assert fetched_departments == expected_subjects
    assert [_subject_code(c["course_code"]) for c in courses] == expected_subjects
    assert mock_request.call_count == 1
    assert "subjects.php" in mock_request.call_args.args[1]


@pytest.mark.asyncio
async def test_cs_crop_science_scrapes_as_own_subject(scraper):
    """
    CRITICAL: CS is Crop Science. Scrape CS as that ACS code; do not remap to CSC.
    """
    await scraper._ensure_client()

    subjects_fixture = load_fixture("subjects.json")
    search_fixture = load_fixture("search_csc_open_closed.json")
    requested_subjects = []

    async def mock_request(method, url, **kwargs):
        response = MagicMock()
        if "subjects.php" in url:
            response.json.return_value = subjects_fixture
            return response
        requested_subjects.append(kwargs.get("data", {}).get("subject"))
        response.json.return_value = search_fixture
        return response

    with patch.object(scraper, "_make_request_with_retry", side_effect=mock_request):
        courses = await scraper.scrape_courses("CS")

    assert requested_subjects == ["CS"]
    assert "CSC" not in requested_subjects
    assert len(courses) > 0


@pytest.mark.asyncio
async def test_named_departments_other_than_csc_work(scraper):
    """Explicit single-department scrapes (MA, ECE) work for debugging."""
    await scraper._ensure_client()

    subjects_fixture = load_fixture("subjects.json")
    search_fixture = load_fixture("search_csc_open_closed.json")

    for dept in ("MA", "ECE"):
        requested_subjects = []

        async def mock_request(method, url, **kwargs):
            response = MagicMock()
            if "subjects.php" in url:
                response.json.return_value = subjects_fixture
                return response
            requested_subjects.append(kwargs.get("data", {}).get("subject"))
            response.json.return_value = search_fixture
            return response

        with patch.object(
            scraper, "_make_request_with_retry", side_effect=mock_request
        ):
            courses = await scraper.scrape_courses(dept)

        assert requested_subjects == [dept]
        assert len(courses) > 0


@pytest.mark.asyncio
async def test_unknown_department_returns_empty(scraper):
    """Unknown subject codes are a no-op, not an allowlist rejection."""
    await scraper._ensure_client()

    subjects_fixture = load_fixture("subjects.json")

    with patch.object(
        scraper, "_make_request_with_retry", new_callable=AsyncMock
    ) as mock_request:
        subjects_response = MagicMock()
        subjects_response.json.return_value = subjects_fixture
        mock_request.return_value = subjects_response

        courses = await scraper.scrape_courses("NOTASUBJ")

    assert courses == []
    assert mock_request.call_count == 1


@pytest.mark.asyncio
async def test_explicit_csc_department_works(scraper):
    """Test that an explicit CSC (Computer Science) scrape still works."""
    await scraper._ensure_client()

    subjects_fixture = load_fixture("subjects.json")
    search_fixture = load_fixture("search_csc_open_closed.json")

    with patch.object(
        scraper, "_make_request_with_retry", new_callable=AsyncMock
    ) as mock_request:
        # Mock subjects response
        subjects_response = MagicMock()
        subjects_response.json.return_value = subjects_fixture

        # Mock search response
        search_response = MagicMock()
        search_response.json.return_value = search_fixture

        mock_request.side_effect = [
            subjects_response,
            search_response,
        ]

        courses = await scraper.scrape_courses("CSC")

        # Should succeed and return courses
        assert len(courses) > 0
        search_call = mock_request.call_args_list[1]
        assert search_call.kwargs["data"]["subject"] == "CSC"


@pytest.mark.asyncio
async def test_x_requested_with_header_present(scraper):
    """Test that X-Requested-With: XMLHttpRequest header is set."""
    await scraper._ensure_client()

    headers = scraper.client.headers
    assert headers.get("X-Requested-With") == "XMLHttpRequest"


@pytest.mark.asyncio
async def test_user_agent_is_seatsteal(scraper):
    """Test that User-Agent is set to SeatSteal/1.0."""
    await scraper._ensure_client()

    headers = scraper.client.headers
    assert headers.get("User-Agent") == "SeatSteal/1.0"


@pytest.mark.asyncio
async def test_max_response_size_enforced(scraper):
    """Test that MAX_RESPONSE_SIZE is enforced."""
    await scraper._ensure_client()

    # Create a response that exceeds MAX_RESPONSE_SIZE
    large_content = b"x" * (scraper.MAX_RESPONSE_SIZE + 1)

    async def mock_request_side_effect(*args, **kwargs):
        response = MagicMock()
        response.content = large_content
        response.raise_for_status = MagicMock()
        return response

    with patch.object(scraper.client, "post", side_effect=mock_request_side_effect):
        with pytest.raises(Exception) as exc_info:
            await scraper._make_request_with_retry("POST", "http://test.com")

        error_msg = str(exc_info.value)
        assert "Response size" in error_msg and "exceeds MAX_RESPONSE_SIZE" in error_msg


@pytest.mark.asyncio
async def test_budget_error_is_non_retryable(scraper):
    """Test that budget errors raise NcsuBudgetExceededError (non-retryable)."""
    await scraper._ensure_client()

    # Set a very low budget (will exceed on second request)
    scraper.MAX_TOTAL_REQUESTS = 1

    subjects_fixture = load_fixture("subjects.json")
    search_fixture = load_fixture("search_csc_open_closed.json")

    call_count = 0

    async def mock_request_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1

        # Simulate budget check (same logic as in _make_request_with_retry)
        scraper.total_request_count += 1
        if scraper.total_request_count > scraper.MAX_TOTAL_REQUESTS:
            raise NcsuBudgetExceededError(
                f"Request budget exceeded: {scraper.total_request_count} > "
                f"{scraper.MAX_TOTAL_REQUESTS}"
            )

        # Return mock responses
        if call_count == 1:
            response = MagicMock()
            response.json.return_value = subjects_fixture
            response.content = b"{}"
            response.raise_for_status = MagicMock()
            return response
        elif call_count == 2:
            response = MagicMock()
            response.json.return_value = search_fixture
            response.content = b"{}"
            response.raise_for_status = MagicMock()
            return response

    with patch.object(
        scraper, "_make_request_with_retry", side_effect=mock_request_side_effect
    ):
        with pytest.raises(NcsuBudgetExceededError) as exc_info:
            await scraper.scrape_courses("CSC")

        error_msg = str(exc_info.value)
        assert "budget" in error_msg.lower() and "exceed" in error_msg.lower()


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
            response.content = b'{"subj_js": "[]"}'
            response.raise_for_status = MagicMock()
            return response

    with patch.object(scraper.client, "post", side_effect=mock_request_side_effect):
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
            response.content = b'{"subj_js": "[]"}'
            response.raise_for_status = MagicMock()
            return response

    with patch.object(scraper.client, "get", side_effect=mock_request_side_effect):
        result = await scraper._make_request_with_retry("GET", "http://test.com")

        # Should have retried 1 time + 1 success = 2 total attempts
        assert call_count == 2


@pytest.mark.asyncio
async def test_term_code_from_db(mock_db_session):
    """Test that term code is fetched from database, not hardcoded."""
    scraper = NcsuScraper(db_session=mock_db_session)

    # Should get term from mock_db_session
    assert scraper.current_term == "2268"


@pytest.mark.asyncio
async def test_course_code_parsing_from_section_id(scraper):
    """Test that course_code is correctly parsed from section id (e.g., CSC-111 → CSC 111)."""
    search_fixture = load_fixture("search_csc_open_closed.json")
    html_content = search_fixture["html"]

    courses = scraper._parse_courses_from_html(html_content, "CSC")

    # Check that course IDs like "CSC-111" are parsed to "CSC 111"
    for course in courses:
        course_code = course["course_code"]
        # Should have space, not hyphen
        assert " " in course_code
        assert "-" not in course_code


@pytest.mark.asyncio
async def test_regression_live_shaped_fixture_has_open_statuses(scraper):
    """
    Regression test: Real-shaped fixture should have Open statuses (not all Closed).

    Live baseline (2026-09-09): CSC ~86 courses / 204 Class #s
    - Open: ~172
    - Closed: ~21
    - Reserved: ~11

    Parser was returning 204 Closed + Unknown Title - this test ensures we now parse correctly.
    """
    search_fixture = load_fixture("search_csc_open_closed.json")
    html_content = search_fixture["html"]

    courses = scraper._parse_courses_from_html(html_content, "CSC")

    # Count Open vs Closed statuses
    all_classes = []
    for course in courses:
        all_classes.extend(course["classes"])

    open_count = sum(1 for c in all_classes if c["status"] == "Open")
    closed_count = sum(1 for c in all_classes if c["status"] == "Closed")

    # Assert we have Open statuses (not all Closed)
    assert open_count > 0, "Should have at least one Open class"
    assert (
        open_count >= closed_count
    ), "Should have more Open than Closed in this fixture"

    # Assert titles are real (not "Unknown Title")
    for course in courses:
        assert (
            course["title"] != "Unknown Title"
        ), f"Course {course['course_code']} has Unknown Title"
        assert (
            len(course["title"]) > 10
        ), f"Course {course['course_code']} title too short: {course['title']}"


@pytest.mark.asyncio
async def test_real_html_structure_h1_with_small(scraper):
    """Test that parser handles real h1 with small tag structure."""
    search_fixture = load_fixture("search_csc_open_closed.json")
    html_content = search_fixture["html"]

    courses = scraper._parse_courses_from_html(html_content, "CSC")

    # Verify titles are extracted correctly from h1/small
    for course in courses:
        # Titles should be meaningful (from real h1/small structure)
        assert course["title"] != "Unknown Title"
        # Should not have "Units: X" in title (should be stripped)
        assert "Units:" not in course["title"]


@pytest.mark.asyncio
async def test_real_html_structure_span_text_success_danger(scraper):
    """Test that parser extracts status from span.text-success/text-danger."""
    search_fixture = load_fixture("search_csc_open_closed.json")
    html_content = search_fixture["html"]

    # Parse directly to see the spans
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_content, "lxml")

    # Find a span with text-success (Open or Reserved)
    success_spans = soup.find_all("span", class_="text-success")
    assert len(success_spans) > 0, "Should have text-success spans"

    # Find a span with text-danger (Closed)
    danger_spans = soup.find_all("span", class_="text-danger")
    assert len(danger_spans) > 0, "Should have text-danger spans"

    # Now test parsing
    courses = scraper._parse_courses_from_html(html_content, "CSC")

    # Verify we parsed both Open and Closed statuses
    all_statuses = set()
    for course in courses:
        for class_data in course["classes"]:
            all_statuses.add(class_data["status"])

    assert (
        "Open" in all_statuses or "Closed" in all_statuses
    ), "Should have parsed status from spans"


@pytest.mark.asyncio
async def test_fixtures_exist():
    """Test that all required fixtures exist."""
    required_fixtures = [
        "subjects.json",
        "search_csc_open_closed.json",
        "search_csc_reserved.json",
        "search_csc_empty.json",
        "search_cnr_empty.json",
    ]

    for fixture in required_fixtures:
        fixture_path = FIXTURES_DIR / fixture
        assert (
            fixture_path.exists()
        ), f"Required fixture {fixture} not found at {fixture_path}"
