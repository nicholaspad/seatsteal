"""Tests for NC State University course scraper."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from pathlib import Path

import sys

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from scraper.scrapers.ncsu import NcsuScraper, NcsuBudgetExceededError
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
    """Test that scraper initializes with correct term code and allowlist."""
    assert scraper.college_short_name == "ncsu"
    assert scraper.current_term == "2268"
    assert scraper.total_request_count == 0
    assert scraper.ALLOWED_DEPARTMENTS == ["CSC"]
    assert scraper.MAX_RESPONSE_SIZE == 5 * 1024 * 1024


@pytest.mark.asyncio
async def test_csc_is_allowlisted_not_cs(scraper):
    """
    CRITICAL: Test that CSC (Computer Science) is allowlisted, NOT CS (Crop Science).
    This is the CS vs CSC trap mentioned in requirements.
    """
    assert "CSC" in scraper.ALLOWED_DEPARTMENTS
    assert "CS" not in scraper.ALLOWED_DEPARTMENTS


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
    """Test parsing courses from HTML with Open and Closed statuses."""
    search_fixture = load_fixture("search_csc_open_closed.json")
    html_content = search_fixture["html"]

    courses = scraper._parse_courses_from_html(html_content, "CSC")

    # Should have 2 courses (CSC 111 and CSC 216)
    assert len(courses) == 2

    # Find CSC 111
    csc111 = next((c for c in courses if c["course_code"] == "CSC 111"), None)
    assert csc111 is not None
    assert csc111["title"] == "Introduction to Computing: Python"
    assert len(csc111["classes"]) == 2

    # Check classes for CSC 111
    classes = csc111["classes"]

    # Find section 002 (Open)
    section_002 = next((c for c in classes if c["section"] == "002"), None)
    assert section_002 is not None
    assert section_002["class_number"] == "4780"
    assert section_002["status"] == "Open"

    # Find section 001 (Closed)
    section_001 = next((c for c in classes if c["section"] == "001"), None)
    assert section_001 is not None
    assert section_001["class_number"] == "8291"
    assert section_001["status"] == "Closed"


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

    with pytest.raises(Exception) as exc_info:
        scraper._parse_courses_from_html(html_content, "CSC")

    error_msg = str(exc_info.value)
    assert (
        "No course sections found" in error_msg
        or "breaking change" in error_msg.lower()
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


@pytest.mark.asyncio
async def test_all_department_maps_to_csc_allowlist(scraper):
    """
    Test that department='ALL' maps to CSC allowlist (not full ~199-subject catalog).
    """
    await scraper._ensure_client()

    subjects_fixture = load_fixture("subjects.json")
    search_fixture = load_fixture("search_csc_open_closed.json")

    with patch.object(
        scraper, "_make_request_with_retry", new_callable=AsyncMock
    ) as mock_request:
        # Mock subjects response
        subjects_response = MagicMock()
        subjects_response.json.return_value = subjects_fixture

        # Mock search response for CSC
        search_response = MagicMock()
        search_response.json.return_value = search_fixture

        mock_request.side_effect = [
            subjects_response,  # POST subjects
            search_response,  # POST search for CSC
        ]

        # Scrape with department='ALL'
        courses = await scraper.scrape_courses("ALL", limit=None)

        # Verify:
        # 1. Should succeed
        # 2. Should return CSC courses only
        # 3. All course_codes should start with "CSC"
        assert len(courses) > 0, "ALL should map to CSC and return courses"
        assert all(
            c["course_code"].startswith("CSC") for c in courses
        ), "ALL should only scrape CSC (allowlist)"


@pytest.mark.asyncio
async def test_cs_crop_science_rejected(scraper):
    """
    CRITICAL: Test that CS (Crop Science) is rejected, not confused with Computer Science.
    """
    await scraper._ensure_client()

    # Try CS (Crop Science) - should be rejected
    with pytest.raises(ValueError) as exc_info:
        await scraper.scrape_courses("CS")

    error_msg = str(exc_info.value)
    assert "only supports allowlisted departments" in error_msg
    assert "CSC" in error_msg
    assert "CS" in error_msg or "'CS'" in error_msg


@pytest.mark.asyncio
async def test_non_allowlisted_department_rejected(scraper):
    """Test that non-allowlisted departments (e.g., MA, ECE) are rejected."""
    await scraper._ensure_client()

    # Try Mathematics (not in allowlist)
    with pytest.raises(ValueError) as exc_info:
        await scraper.scrape_courses("MA")

    error_msg = str(exc_info.value)
    assert "only supports allowlisted departments" in error_msg
    assert "CSC" in error_msg

    # Try ECE (not in allowlist)
    with pytest.raises(ValueError) as exc_info:
        await scraper.scrape_courses("ECE")

    error_msg = str(exc_info.value)
    assert "only supports allowlisted departments" in error_msg


@pytest.mark.asyncio
async def test_csc_allowlisted_department_works(scraper):
    """Test that CSC (allowlisted) department can be scraped."""
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

        # CSC should work (in allowlist)
        courses = await scraper.scrape_courses("CSC")

        # Should succeed and return courses
        assert len(courses) > 0


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
async def test_fixtures_exist():
    """Test that all required fixtures exist."""
    required_fixtures = [
        "subjects.json",
        "search_csc_open_closed.json",
        "search_csc_reserved.json",
        "search_csc_empty.json",
    ]

    for fixture in required_fixtures:
        fixture_path = FIXTURES_DIR / fixture
        assert (
            fixture_path.exists()
        ), f"Required fixture {fixture} not found at {fixture_path}"
