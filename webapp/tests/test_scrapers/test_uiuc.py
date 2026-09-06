"""Tests for University of Illinois Urbana-Champaign course scraper."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import sys
from pathlib import Path

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from scraper.scrapers.uiuc import UiucScraper
from models.college import College

# Sample XML response for subjects index (/cisapp/explorer/schedule/{year}/{season}.xml)
SAMPLE_SUBJECTS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<subjects>
    <subject id="CS" name="Computer Science"/>
    <subject id="MATH" name="Mathematics"/>
    <subject id="ENG" name="Engineering"/>
</subjects>
"""

# Sample XML response for subject courses (/cisapp/explorer/schedule/{year}/{season}/{subject}.xml)
SAMPLE_SUBJECT_COURSES_XML = """<?xml version="1.0" encoding="UTF-8"?>
<courses>
    <course id="100" name="Introduction to CS">
        <section id="A">
            <statusCode>A</statusCode>
        </section>
    </course>
    <course id="101" name="Data Structures">
        <section id="B">
            <statusCode>A</statusCode>
        </section>
    </course>
</courses>
"""

# Sample HTML response for course page (/schedule/{year}/{season}/{subject}/{course})
# Status: Open
SAMPLE_COURSE_HTML_OPEN = """
<!DOCTYPE html>
<html>
<head><title>CS 100</title></head>
<body>
    <h1 class="page-title">CS 100 - Introduction to Computer Science</h1>
    <table id="schedule-course-table">
        <tbody>
            <tr>
                <td>12345</td>
                <td>LEC</td>
                <td>Prof. Smith</td>
                <td>
                    <dl>
                        <dt>Availability</dt>
                        <dd>Open</dd>
                    </dl>
                </td>
            </tr>
            <tr>
                <td>12346</td>
                <td>DIS</td>
                <td>TA Jones</td>
                <td>
                    <dl>
                        <dt>Availability</dt>
                        <dd>Open (Restricted)</dd>
                    </dl>
                </td>
            </tr>
        </tbody>
    </table>
</body>
</html>
"""

# Status: Closed
SAMPLE_COURSE_HTML_CLOSED = """
<!DOCTYPE html>
<html>
<head><title>CS 101</title></head>
<body>
    <h1 class="page-title">CS 101 - Data Structures</h1>
    <table id="schedule-course-table">
        <tbody>
            <tr>
                <td>12347</td>
                <td>LEC</td>
                <td>Prof. Johnson</td>
                <td>
                    <dl>
                        <dt>Availability</dt>
                        <dd>Closed</dd>
                    </dl>
                </td>
            </tr>
        </tbody>
    </table>
</body>
</html>
"""

# Status: CrossListOpen
SAMPLE_COURSE_HTML_CROSSLIST = """
<!DOCTYPE html>
<html>
<head><title>CS 225</title></head>
<body>
    <h1 class="page-title">CS 225 - Algorithms</h1>
    <table id="schedule-course-table">
        <tbody>
            <tr>
                <td>55555</td>
                <td>LEC</td>
                <td>Prof. Lee</td>
                <td>
                    <dl>
                        <dt>Availability</dt>
                        <dd>CrossListOpen</dd>
                    </dl>
                </td>
            </tr>
            <tr>
                <td>55556</td>
                <td>DIS</td>
                <td>TA Park</td>
                <td>
                    <dl>
                        <dt>Availability</dt>
                        <dd>CrossListOpen (Restricted)</dd>
                    </dl>
                </td>
            </tr>
        </tbody>
    </table>
</body>
</html>
"""

# Status: Using aria-label fallback (no Availability dd)
SAMPLE_COURSE_HTML_ARIALABEL = """
<!DOCTYPE html>
<html>
<head><title>MATH 100</title></head>
<body>
    <h1 class="page-title">MATH 100 - Calculus I</h1>
    <table id="schedule-course-table">
        <tbody>
            <tr>
                <td>88888</td>
                <td>LEC</td>
                <td>Prof. Taylor</td>
                <td>
                    <i class="status-icon" aria-label="Open"></i>
                </td>
            </tr>
        </tbody>
    </table>
</body>
</html>
"""

# Status: Missing availability (conservative: Closed)
SAMPLE_COURSE_HTML_MISSING = """
<!DOCTYPE html>
<html>
<head><title>ENG 100</title></head>
<body>
    <h1 class="page-title">ENG 100 - Engineering Fundamentals</h1>
    <table id="schedule-course-table">
        <tbody>
            <tr>
                <td>99999</td>
                <td>LEC</td>
                <td>Prof. Wilson</td>
                <td></td>
            </tr>
        </tbody>
    </table>
</body>
</html>
"""

# HTML with XML statusCode="A" but Closed availability (regression test)
SAMPLE_COURSE_HTML_STATUSCODE_NOT_AVAILABILITY = """
<!DOCTYPE html>
<html>
<head><title>CS 400</title></head>
<body>
    <h1 class="page-title">CS 400 - Advanced Course</h1>
    <div class="xml-status">
        <statusCode>A</statusCode>
        <sectionStatusCode>A</sectionStatusCode>
    </div>
    <table id="schedule-course-table">
        <tbody>
            <tr>
                <td>44444</td>
                <td>LEC</td>
                <td>Prof. Brown</td>
                <td>
                    <dl>
                        <dt>Availability</dt>
                        <dd>Closed</dd>
                    </dl>
                </td>
            </tr>
        </tbody>
    </table>
</body>
</html>
"""


@pytest.fixture
def mock_db_session():
    """Create a mock database session for UIUC scraper."""
    mock_session = MagicMock()
    mock_college = College(
        id=1,
        name="University of Illinois Urbana-Champaign",
        short_name="uiuc",
        term_code="120268",  # Fall 2026
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
    """Create a UIUC scraper instance."""
    return UiucScraper(db_session=mock_db_session)


def test_parse_term_code_fall_2026(scraper):
    """Test parsing Fall 2026 term code."""
    year, season = scraper._parse_term_code("120268")
    assert year == "2026"
    assert season == "fall"


def test_parse_term_code_spring_2026(scraper):
    """Test parsing Spring 2026 term code."""
    year, season = scraper._parse_term_code("120261")
    assert year == "2026"
    assert season == "spring"


def test_parse_term_code_summer_2026(scraper):
    """Test parsing Summer 2026 term code."""
    year, season = scraper._parse_term_code("120265")
    assert year == "2026"
    assert season == "summer"


def test_parse_term_code_winter_2026(scraper):
    """Test parsing Winter 2026 term code."""
    year, season = scraper._parse_term_code("120260")
    assert year == "2026"
    assert season == "winter"


def test_parse_term_code_invalid(scraper):
    """Test parsing invalid term codes."""
    with pytest.raises(ValueError):
        scraper._parse_term_code("12026")  # Too short

    with pytest.raises(ValueError):
        scraper._parse_term_code("1202689")  # Too long

    with pytest.raises(ValueError):
        scraper._parse_term_code("120269")  # Invalid semester code


def test_map_availability_status_open(scraper):
    """Test mapping Open status variants."""
    assert scraper._map_availability_status("Open") == "Open"
    assert scraper._map_availability_status("open") == "Open"
    assert scraper._map_availability_status("OPEN") == "Open"


def test_map_availability_status_open_restricted(scraper):
    """Test mapping Open (Restricted) status."""
    assert scraper._map_availability_status("Open (Restricted)") == "Open"
    assert scraper._map_availability_status("open (restricted)") == "Open"


def test_map_availability_status_crosslistopen(scraper):
    """Test mapping CrossListOpen status variants."""
    assert scraper._map_availability_status("CrossListOpen") == "Open"
    assert scraper._map_availability_status("crosslistopen") == "Open"
    assert scraper._map_availability_status("CrossListOpen (Restricted)") == "Open"
    assert scraper._map_availability_status("crosslistopen (restricted)") == "Open"


def test_map_availability_status_closed_variants(scraper):
    """Test mapping Closed status variants."""
    assert scraper._map_availability_status("Closed") == "Closed"
    assert scraper._map_availability_status("closed") == "Closed"
    assert scraper._map_availability_status("Pending") == "Closed"
    assert scraper._map_availability_status("Unknown") == "Closed"
    assert scraper._map_availability_status("") == "Closed"
    assert scraper._map_availability_status("Invalid") == "Closed"


@pytest.mark.asyncio
async def test_fetch_subjects(scraper):
    """Test fetching subjects from XML."""
    await scraper._ensure_client()

    with patch.object(
        scraper, "_fetch_with_retry", new_callable=AsyncMock
    ) as mock_fetch:
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.content = SAMPLE_SUBJECTS_XML.encode()
        mock_fetch.return_value = mock_response

        # Fetch subjects
        subjects = await scraper._fetch_subjects("2026", "fall")

        # Verify results
        assert len(subjects) == 3
        assert "CS" in subjects
        assert "MATH" in subjects
        assert "ENG" in subjects

    await scraper.client.aclose()


@pytest.mark.asyncio
async def test_fetch_subject_courses(scraper):
    """Test fetching course IDs for a subject from XML."""
    await scraper._ensure_client()

    with patch.object(
        scraper, "_fetch_with_retry", new_callable=AsyncMock
    ) as mock_fetch:
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.content = SAMPLE_SUBJECT_COURSES_XML.encode()
        mock_fetch.return_value = mock_response

        # Fetch course IDs
        course_ids = await scraper._fetch_subject_courses("2026", "fall", "CS")

        # Verify results
        assert len(course_ids) == 2
        assert "100" in course_ids
        assert "101" in course_ids

    await scraper.client.aclose()


@pytest.mark.asyncio
async def test_fetch_course_html_open(scraper):
    """Test fetching course HTML with Open status."""
    await scraper._ensure_client()

    with patch.object(
        scraper, "_fetch_with_retry", new_callable=AsyncMock
    ) as mock_fetch:
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.content = SAMPLE_COURSE_HTML_OPEN.encode()
        mock_fetch.return_value = mock_response

        # Fetch course HTML
        classes = await scraper._fetch_course_html("2026", "fall", "CS", "100")

        # Verify results
        assert len(classes) == 2
        assert classes[0]["course_code"] == "CS 100"
        assert classes[0]["title"] == "Introduction to Computer Science"
        assert classes[0]["class_number"] == "12345"
        assert classes[0]["status"] == "Open"
        assert classes[1]["class_number"] == "12346"
        assert classes[1]["status"] == "Open"  # Open (Restricted) → Open

    await scraper.client.aclose()


@pytest.mark.asyncio
async def test_fetch_course_html_closed(scraper):
    """Test fetching course HTML with Closed status."""
    await scraper._ensure_client()

    with patch.object(
        scraper, "_fetch_with_retry", new_callable=AsyncMock
    ) as mock_fetch:
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.content = SAMPLE_COURSE_HTML_CLOSED.encode()
        mock_fetch.return_value = mock_response

        # Fetch course HTML
        classes = await scraper._fetch_course_html("2026", "fall", "CS", "101")

        # Verify results
        assert len(classes) == 1
        assert classes[0]["course_code"] == "CS 101"
        assert classes[0]["title"] == "Data Structures"
        assert classes[0]["class_number"] == "12347"
        assert classes[0]["status"] == "Closed"

    await scraper.client.aclose()


@pytest.mark.asyncio
async def test_fetch_course_html_crosslistopen(scraper):
    """Test fetching course HTML with CrossListOpen status."""
    await scraper._ensure_client()

    with patch.object(
        scraper, "_fetch_with_retry", new_callable=AsyncMock
    ) as mock_fetch:
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.content = SAMPLE_COURSE_HTML_CROSSLIST.encode()
        mock_fetch.return_value = mock_response

        # Fetch course HTML
        classes = await scraper._fetch_course_html("2026", "fall", "CS", "225")

        # Verify results
        assert len(classes) == 2
        assert classes[0]["class_number"] == "55555"
        assert classes[0]["status"] == "Open"  # CrossListOpen → Open
        assert classes[1]["class_number"] == "55556"
        assert classes[1]["status"] == "Open"  # CrossListOpen (Restricted) → Open

    await scraper.client.aclose()


@pytest.mark.asyncio
async def test_fetch_course_html_arialabel_fallback(scraper):
    """Test fetching course HTML with aria-label status fallback."""
    await scraper._ensure_client()

    with patch.object(
        scraper, "_fetch_with_retry", new_callable=AsyncMock
    ) as mock_fetch:
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.content = SAMPLE_COURSE_HTML_ARIALABEL.encode()
        mock_fetch.return_value = mock_response

        # Fetch course HTML
        classes = await scraper._fetch_course_html("2026", "fall", "MATH", "100")

        # Verify results
        assert len(classes) == 1
        assert classes[0]["class_number"] == "88888"
        assert classes[0]["status"] == "Open"  # From aria-label

    await scraper.client.aclose()


@pytest.mark.asyncio
async def test_fetch_course_html_missing_availability(scraper):
    """Test fetching course HTML with missing availability (conservative: Closed)."""
    await scraper._ensure_client()

    with patch.object(
        scraper, "_fetch_with_retry", new_callable=AsyncMock
    ) as mock_fetch:
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.content = SAMPLE_COURSE_HTML_MISSING.encode()
        mock_fetch.return_value = mock_response

        # Fetch course HTML
        classes = await scraper._fetch_course_html("2026", "fall", "ENG", "100")

        # Verify results
        assert len(classes) == 1
        assert classes[0]["class_number"] == "99999"
        assert classes[0]["status"] == "Closed"  # Conservative default

    await scraper.client.aclose()


@pytest.mark.asyncio
async def test_statuscode_not_used_for_availability(scraper):
    """Test that XML statusCode is NOT used for availability (regression test)."""
    await scraper._ensure_client()

    with patch.object(
        scraper, "_fetch_with_retry", new_callable=AsyncMock
    ) as mock_fetch:
        # Mock HTTP response with statusCode="A" but Closed availability
        mock_response = MagicMock()
        mock_response.content = SAMPLE_COURSE_HTML_STATUSCODE_NOT_AVAILABILITY.encode()
        mock_fetch.return_value = mock_response

        # Fetch course HTML
        classes = await scraper._fetch_course_html("2026", "fall", "CS", "400")

        # Verify: Uses HTML Availability, NOT XML statusCode
        assert len(classes) == 1
        assert classes[0]["class_number"] == "44444"
        assert classes[0]["status"] == "Closed"  # From HTML, not statusCode

    await scraper.client.aclose()


@pytest.mark.asyncio
async def test_fetch_with_retry_success(scraper):
    """Test successful fetch without retries."""
    await scraper._ensure_client()

    with patch.object(scraper.client, "get", new_callable=AsyncMock) as mock_get:
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Fetch with retry
        result = await scraper._fetch_with_retry("https://example.com")

        # Verify single attempt
        assert mock_get.call_count == 1
        assert result == mock_response

    await scraper.client.aclose()


@pytest.mark.asyncio
async def test_fetch_with_retry_429(scraper):
    """Test retry logic for 429 rate limiting."""
    await scraper._ensure_client()

    with patch.object(scraper.client, "get", new_callable=AsyncMock) as mock_get:
        # Mock 429 responses then success
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "1"}

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.raise_for_status = MagicMock()

        mock_get.side_effect = [mock_response_429, mock_response_200]

        # Fetch with retry
        result = await scraper._fetch_with_retry("https://example.com")

        # Verify retried
        assert mock_get.call_count == 2
        assert result == mock_response_200

    await scraper.client.aclose()


@pytest.mark.asyncio
async def test_fetch_with_retry_5xx(scraper):
    """Test retry logic for 5xx server errors."""
    await scraper._ensure_client()

    with patch.object(scraper.client, "get", new_callable=AsyncMock) as mock_get:
        # Mock 503 responses then success
        mock_response_503 = MagicMock()
        mock_response_503.status_code = 503
        mock_response_503.raise_for_status = MagicMock(
            side_effect=Exception("503 error")
        )

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.raise_for_status = MagicMock()

        mock_get.side_effect = [mock_response_503, mock_response_200]

        # Fetch with retry
        result = await scraper._fetch_with_retry("https://example.com")

        # Verify retried
        assert mock_get.call_count == 2
        assert result == mock_response_200

    await scraper.client.aclose()


@pytest.mark.asyncio
async def test_fetch_with_retry_exhausted(scraper):
    """Test that retries are exhausted after max attempts."""
    await scraper._ensure_client()

    with patch.object(scraper.client, "get", new_callable=AsyncMock) as mock_get:
        # Mock persistent 503 errors
        mock_response_503 = MagicMock()
        mock_response_503.status_code = 503
        mock_response_503.raise_for_status = MagicMock(
            side_effect=Exception("503 error")
        )

        mock_get.return_value = mock_response_503

        # Fetch with retry (should exhaust retries)
        with pytest.raises(Exception):
            await scraper._fetch_with_retry("https://example.com")

        # Verify retries: 1 initial + 3 retries = 4 total
        assert mock_get.call_count == 4

    await scraper.client.aclose()


@pytest.mark.asyncio
async def test_fetch_with_retry_403_no_retry(scraper):
    """Test that 403 errors fail immediately without retry."""
    await scraper._ensure_client()

    with patch.object(scraper.client, "get", new_callable=AsyncMock) as mock_get:
        # Mock 403 response
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 403

        def raise_403():
            raise httpx.HTTPStatusError(
                "403", request=MagicMock(), response=mock_response
            )

        mock_response.raise_for_status = raise_403
        mock_get.return_value = mock_response

        # Fetch with retry (should fail immediately)
        with pytest.raises(httpx.HTTPStatusError):
            await scraper._fetch_with_retry("https://example.com")

        # Verify no retries
        assert mock_get.call_count == 1

    await scraper.client.aclose()


def test_transform_classes_crn_deduplication(scraper):
    """Test global CRN deduplication for cross-listed courses."""
    raw_classes = [
        {
            "course_code": "CS 225",
            "title": "Algorithms",
            "class_number": "55555",  # Duplicate CRN
            "section": "LEC",
            "status": "Open",
        },
        {
            "course_code": "CS 225",
            "title": "Algorithms",
            "class_number": "55556",
            "section": "DIS",
            "status": "Open",
        },
        {
            "course_code": "ECE 225",
            "title": "Algorithms (ECE)",
            "class_number": "55555",  # Duplicate CRN (cross-listed)
            "section": "LEC",
            "status": "Open",
        },
    ]

    courses = scraper._transform_classes(raw_classes)

    # Should deduplicate CRN 55555 (cross-listed)
    all_crns = []
    for course in courses:
        for cls in course["classes"]:
            all_crns.append(cls["class_number"])

    assert "55555" in all_crns
    assert all_crns.count("55555") == 1  # Only one instance
    assert "55556" in all_crns


def test_transform_classes_grouping(scraper):
    """Test that classes are grouped by course_code."""
    raw_classes = [
        {
            "course_code": "CS 100",
            "title": "Intro to CS",
            "class_number": "11111",
            "section": "LEC",
            "status": "Open",
        },
        {
            "course_code": "CS 100",
            "title": "Intro to CS",
            "class_number": "11112",
            "section": "DIS",
            "status": "Closed",
        },
        {
            "course_code": "CS 101",
            "title": "Data Structures",
            "class_number": "22222",
            "section": "LEC",
            "status": "Open",
        },
    ]

    courses = scraper._transform_classes(raw_classes)

    # Should have 2 courses
    assert len(courses) == 2

    # Find CS 100
    cs100 = next(c for c in courses if c["course_code"] == "CS 100")
    assert len(cs100["classes"]) == 2
    assert cs100["classes"][0]["class_number"] == "11111"
    assert cs100["classes"][1]["class_number"] == "11112"

    # Find CS 101
    cs101 = next(c for c in courses if c["course_code"] == "CS 101")
    assert len(cs101["classes"]) == 1
    assert cs101["classes"][0]["class_number"] == "22222"


@pytest.mark.asyncio
async def test_scrape_courses_department_filter(scraper):
    """Test scraping courses with department filter."""
    with patch.object(
        scraper, "_fetch_subjects", new_callable=AsyncMock
    ) as mock_fetch_subjects, patch.object(
        scraper, "_fetch_subject_courses", new_callable=AsyncMock
    ) as mock_fetch_courses, patch.object(
        scraper, "_fetch_courses_concurrent", new_callable=AsyncMock
    ) as mock_fetch_concurrent:
        # Mock subjects
        mock_fetch_subjects.return_value = ["CS", "MATH", "ENG"]

        # Mock course IDs
        mock_fetch_courses.return_value = ["100", "101"]

        # Mock course HTML results
        mock_fetch_concurrent.return_value = [
            {
                "course_code": "CS 100",
                "title": "Intro to CS",
                "class_number": "11111",
                "section": "LEC",
                "status": "Open",
            }
        ]

        # Scrape CS courses only
        courses = await scraper.scrape_courses("CS")

        # Verify department filter applied
        mock_fetch_subjects.assert_called_once()
        mock_fetch_courses.assert_called_once_with("2026", "fall", "CS")

        # Verify results
        assert len(courses) == 1
        assert courses[0]["course_code"] == "CS 100"


@pytest.mark.asyncio
async def test_scrape_courses_limit(scraper):
    """Test scraping courses with limit."""
    with patch.object(
        scraper, "_fetch_subjects", new_callable=AsyncMock
    ) as mock_fetch_subjects, patch.object(
        scraper, "_fetch_subject_courses", new_callable=AsyncMock
    ) as mock_fetch_courses, patch.object(
        scraper, "_fetch_courses_concurrent", new_callable=AsyncMock
    ) as mock_fetch_concurrent:
        # Mock subjects
        mock_fetch_subjects.return_value = ["CS"]

        # Mock many course IDs
        mock_fetch_courses.return_value = [str(i) for i in range(100, 200)]

        # Mock course HTML results
        mock_fetch_concurrent.return_value = []

        # Scrape with limit=5
        await scraper.scrape_courses("CS", limit=5)

        # Verify only 5 course IDs fetched
        assert mock_fetch_concurrent.call_count == 1
        course_ids_arg = mock_fetch_concurrent.call_args[0][2]
        assert len(course_ids_arg) == 5


@pytest.mark.asyncio
async def test_request_budget_exceeded(scraper):
    """Test that request budget is enforced."""
    await scraper._ensure_client()

    # Set request count to max
    scraper.request_count = scraper.MAX_REQUESTS

    # Try to fetch course HTML (should return empty list due to budget)
    result = await scraper._fetch_course_html("2026", "fall", "CS", "100")

    # Verify empty result due to budget exhaustion
    assert result == []

    await scraper.client.aclose()


def test_term_code_format(scraper):
    """Test that term code follows 1202YYS format."""
    # Term code should be 120268 (Fall 2026)
    assert scraper.current_term == "120268"

    # Verify it's a 6-digit string
    assert len(scraper.current_term) == 6
    assert scraper.current_term.startswith("1202")
