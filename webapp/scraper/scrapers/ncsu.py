from typing import List, Dict, Any, Optional
import asyncio
import json
import re
import httpx
from bs4 import BeautifulSoup
from scraper.base import BaseScraper
from scraper.utils.logger import scraper_logger as logger
from scraper.utils.term_code_db import get_term_code_from_db


class NcsuBudgetExceededError(Exception):
    """
    Non-retryable budget error for NC State scraper.
    Signals that request budget was exceeded and retry will not help.
    """

    pass


class NcsuScraper(BaseScraper):
    """
    NC State University course scraper.

    Scrapes course data from NC State's PeopleSoft ACS Class Search system.
    Strategy: POST subjects.php for subject list → POST search.php per subject →
    parse HTML response → deduplicate by Class # → return courses with classes.

    Term codes: STRM format (e.g., "2268" = Fall 2026)
    - YYY = year since 1900 (226 = 2026)
    - S = session digit:
      - 1 = Spring
      - 6 = Summer I
      - 7 = Summer II
      - 8 = Fall

    CRITICAL:
    - At NC State, CS = Crop Science, CSC = Computer Science
    - ONLY allowlist CSC (never CS as CompSci)
    - Use Class # (from td.class-num) as identity, not section alone
    - Map Open→Open; Closed/Reserved/Waitlist/unknown→Closed (Reserved→Closed enables reserve-release alerts)
    - Department ALL → expand only to ALLOWED_DEPARTMENTS=["CSC"] (never ~199 subjects)
    - Response is JSON {"html":"<section class=course...>", "json":{...}}
    - Parse the HTML field with BeautifulSoup, NOT the json field
    - User-Agent: SeatSteal/1.0, X-Requested-With: XMLHttpRequest
    - Fail loud on budget exceeded, empty response, or unparseable data
    """

    BASE_URL = "https://webappprd.acs.ncsu.edu/php/coursecat"
    MAX_TOTAL_REQUESTS = 50
    MAX_RESPONSE_SIZE = 5 * 1024 * 1024  # 5MB
    MAX_RETRIES = 3
    ALLOWED_DEPARTMENTS = ["CSC"]

    def __init__(self, db_session=None):
        super().__init__("ncsu")
        self.client: Optional[httpx.AsyncClient] = None
        self.current_term = get_term_code_from_db(db_session, "ncsu")
        self.total_request_count = 0
        logger.info(f"Initialized NC State scraper with term: {self.current_term}")

    async def _ensure_client(self):
        """Ensure HTTP client is initialized"""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "SeatSteal/1.0",
                    "Accept": "application/json, text/html, */*",
                    "Accept-Language": "en-US,en;q=0.5",
                    "X-Requested-With": "XMLHttpRequest",
                },
            )

    async def scrape_courses(
        self, department: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape NC State courses for a specific department or all courses.

        Args:
            department: Department/subject code (e.g., 'CSC') or 'ALL' for all courses
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries with class information
        """
        logger.info(
            f"Scraping NC State {department} courses (limit: {limit}, term: {self.current_term})"
        )

        # Map ALL to allowlist expansion (production compatibility)
        if department.upper() == "ALL":
            logger.info(
                f"ALL mapped to allowlist {self.ALLOWED_DEPARTMENTS} "
                f"(never fans out to full ~199-subject catalog)"
            )
            all_courses = []
            for allowed_dept in self.ALLOWED_DEPARTMENTS:
                logger.info(f"Scraping allowlisted department: {allowed_dept}")
                dept_courses = await self.scrape_courses(allowed_dept, limit)
                all_courses.extend(dept_courses)
            return all_courses

        # ENFORCE ALLOWLIST: Only allowlisted departments
        if department.upper() not in [d.upper() for d in self.ALLOWED_DEPARTMENTS]:
            raise ValueError(
                f"NC State scraper only supports allowlisted departments: {', '.join(self.ALLOWED_DEPARTMENTS)}. "
                f"Requested department '{department}' is not allowed. "
                f"Full catalog scraping exceeds budget ({self.MAX_TOTAL_REQUESTS} requests)."
            )

        await self._ensure_client()

        try:
            # Fetch subjects to validate department exists
            subjects = await self._fetch_subjects()
            logger.info(
                f"CARDINALITY: Discovered {len(subjects)} total subjects for term {self.current_term}"
            )

            # Filter by department
            if department.upper() not in [s.upper() for s in subjects]:
                logger.warning(f"No subject found matching department: {department}")
                return []

            # Fetch courses for the department
            courses_data = await self._fetch_department_courses(department)

            logger.info(
                f"Successfully scraped {len(courses_data)} courses from NC State {department}. "
                f"Total requests: {self.total_request_count}"
            )
            return courses_data

        except Exception as e:
            logger.error(f"Failed to scrape NC State {department}: {e}")
            raise
        finally:
            if self.client:
                await self.client.aclose()
                self.client = None

    async def _fetch_subjects(self) -> List[str]:
        """
        Fetch available subjects for the current term.

        Response format: {"subj_js": "[\"AA - Art and Architecture\", \"CSC - Computer Science\", ...]"}
        Parse the nested JSON string and extract subject codes.

        Returns:
            List of subject codes (e.g., ['CSC', 'MA', 'ECE'])
        """
        try:
            url = f"{self.BASE_URL}/subjects.php"
            data = {"strm": self.current_term}

            response = await self._make_request_with_retry(
                "POST",
                url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            # Parse outer JSON
            response_data = response.json()

            # Extract nested subj_js JSON string
            if "subj_js" not in response_data:
                raise Exception("No subj_js field in subjects response")

            subj_js = response_data["subj_js"]

            # Parse nested JSON string
            subjects_list = json.loads(subj_js)

            # Extract subject codes from "CODE - Description" format
            subjects = []
            for subj_entry in subjects_list:
                if " - " in subj_entry:
                    # Split on first " - " to get code
                    code = subj_entry.split(" - ", 1)[0].strip()
                    subjects.append(code)

            if not subjects:
                raise Exception("No subjects parsed from subj_js")

            logger.info(f"Fetched {len(subjects)} subjects from NC State")
            return subjects

        except Exception as e:
            logger.error(f"Error fetching NC State subjects: {e}")
            raise

    async def _fetch_department_courses(self, department: str) -> List[Dict[str, Any]]:
        """
        Fetch courses for a specific department.

        Response format: {"html": "<section class=course...>", "json": {...}}
        Parse the HTML field with BeautifulSoup.

        Args:
            department: Department/subject code (e.g., 'CSC')

        Returns:
            List of course dictionaries with classes
        """
        try:
            url = f"{self.BASE_URL}/search.php"

            # Build form data - DO NOT send open-classes=1 (would drop Closed sections)
            form_data = {
                "term": self.current_term,
                "subject": department,
                "course-inequality": "=",
                "course-number": "",
                "course-career": "",
                "session": "",
                "start-time-inequality": "",
                "start-time": "",
                "end-time-inequality": "",
                "end-time": "",
                "instructor-name": "",
                "current_strm": self.current_term,
            }

            response = await self._make_request_with_retry(
                "POST",
                url,
                data=form_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            # Parse JSON response to get HTML
            response_data = response.json()

            if "html" not in response_data:
                raise Exception("No html field in search response")

            html_content = response_data["html"]

            if not html_content or html_content.strip() == "":
                raise Exception(
                    f"Empty HTML content in search response for {department}. "
                    f"This may indicate no courses or a breaking API change."
                )

            # Parse HTML with BeautifulSoup
            courses_data = self._parse_courses_from_html(html_content, department)

            logger.info(
                f"Fetched {len(courses_data)} courses for department {department}"
            )
            return courses_data

        except Exception as e:
            logger.error(f"Error fetching courses for {department}: {e}")
            raise

    def _parse_courses_from_html(
        self, html_content: str, department: str
    ) -> List[Dict[str, Any]]:
        """
        Parse courses from HTML content.

        Real HTML structure:
        <section class="course" id="CSC-111">
            <h1>CSC 111 <small>Title</small> ...</h1>
            <table class="table section-table...">
                <tr>
                    <td>001</td>
                    <td>Lec</td>
                    <td class="class-num hidden-xs">12345</td>
                    <td><span class="text-success">Open</span><br/>4/60</td>
                    ...
                </tr>
            </table>
        </section>

        Args:
            html_content: HTML string from search response
            department: Department code for validation

        Returns:
            List of course dictionaries with classes
        """
        soup = BeautifulSoup(html_content, "lxml")

        courses_dict: Dict[str, Dict[str, Any]] = {}
        seen_class_numbers = set()

        # Find all course sections
        course_sections = soup.find_all("section", class_="course")

        if not course_sections:
            # Fail loud if no courses found (may indicate breaking API change)
            raise Exception(
                f"No course sections found in HTML for {department}. "
                f"This may indicate a breaking change in the API or empty term data."
            )

        for course_section in course_sections:
            # Extract course ID from section id attribute (e.g., "CSC-111")
            course_id = course_section.get("id", "")
            if not course_id:
                logger.warning("Course section missing id attribute")
                continue

            # Parse course_code from course_id (e.g., "CSC-111" → "CSC 111")
            if "-" in course_id:
                parts = course_id.split("-", 1)
                course_code = f"{parts[0]} {parts[1]}"
            else:
                course_code = course_id.replace("_", " ")

            # Extract course title from h1 with small tag
            h1_elem = course_section.find("h1")
            if h1_elem:
                # Title is in the h1, with main title before small and detail in small
                h1_text = h1_elem.get_text(" ", strip=True)
                # Remove "Units: X" suffix if present
                h1_text = re.sub(r"\s+Units:\s+\d+", "", h1_text)
                title = h1_text
            else:
                title = "Unknown Title"

            # Find table with class data
            table = course_section.find("table", class_="section-table")
            if not table:
                logger.debug(f"No section-table found for {course_id}")
                continue

            # Find all data rows (skip header)
            rows = table.find_all("tr")
            for row in rows[1:]:  # Skip header row
                cells = row.find_all("td")
                if len(cells) < 4:
                    continue

                # Extract section code (first cell)
                section_code = cells[0].get_text(strip=True) or "001"

                # Extract class number (cell with class="class-num hidden-xs")
                class_num_cell = None
                for cell in cells:
                    if "class-num" in cell.get("class", []):
                        class_num_cell = cell
                        break

                if not class_num_cell:
                    logger.warning(f"No class-num cell found in row for {course_id}")
                    continue

                class_number = class_num_cell.get_text(strip=True)
                if not class_number:
                    continue

                # Deduplicate by class_number (CRITICAL: Class # is the identity)
                if class_number in seen_class_numbers:
                    logger.debug(f"Skipping duplicate class_number: {class_number}")
                    continue
                seen_class_numbers.add(class_number)

                # Find availability cell (next cell after class-num)
                # The avail cell contains: <span class="text-success">Open</span><br/>4/60
                # or: <em><span class="text-danger">Closed</span></em><br/>0/35
                class_num_idx = cells.index(class_num_cell)
                if class_num_idx + 1 < len(cells):
                    avail_cell = cells[class_num_idx + 1]
                else:
                    logger.warning(f"No avail cell after class-num for {class_number}")
                    avail_cell = None

                # Extract status from span within avail cell
                status_text = "Unknown"
                if avail_cell:
                    # Look for span with text-success or text-danger class
                    status_span = avail_cell.find("span")
                    if status_span:
                        status_text = status_span.get_text(strip=True)

                # Normalize status: Open→Open, everything else→Closed
                normalized_status = self._normalize_ncsu_status(status_text)

                # Group by course_code
                if course_code not in courses_dict:
                    courses_dict[course_code] = {
                        "course_code": course_code,
                        "title": title,
                        "classes": [],
                    }

                courses_dict[course_code]["classes"].append(
                    {
                        "class_number": str(class_number),
                        "section": section_code,
                        "status": normalized_status,
                    }
                )

        courses_data = list(courses_dict.values())

        # Fail loud if no courses parsed
        if not courses_data:
            raise Exception(
                f"Failed to parse any courses from HTML for {department}. "
                f"This may indicate a breaking change in the API."
            )

        return courses_data

    def _normalize_ncsu_status(self, status: Optional[str]) -> str:
        """
        Normalize NC State status to Open or Closed.

        NC State statuses:
        - Open → Open
        - Closed, Reserved, Waitlist, unknown → Closed

        Reserved→Closed enables reserve-release alerts.

        Args:
            status: Raw status string

        Returns:
            'Open' or 'Closed'
        """
        if not status:
            return "Closed"

        status_lower = status.lower().strip()

        if status_lower == "open":
            return "Open"
        elif status_lower in ["closed", "reserved", "waitlist"]:
            return "Closed"
        else:
            # Unknown status defaults to Closed (conservative)
            logger.debug(f"Unknown status '{status}' mapped to Closed")
            return "Closed"

    async def _make_request_with_retry(
        self, method: str, url: str, max_retries: int = None, **kwargs
    ) -> httpx.Response:
        """
        Make HTTP request with retry logic for transient errors.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL to request
            max_retries: Maximum retry attempts (default: self.MAX_RETRIES)
            **kwargs: Additional arguments to pass to httpx request

        Returns:
            httpx.Response object

        Raises:
            Exception: If all retries exhausted or non-retryable error
        """
        if max_retries is None:
            max_retries = self.MAX_RETRIES

        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                # Check request budget
                self.total_request_count += 1
                if self.total_request_count > self.MAX_TOTAL_REQUESTS:
                    raise NcsuBudgetExceededError(
                        f"Request budget exceeded: {self.total_request_count} > "
                        f"{self.MAX_TOTAL_REQUESTS}. Failing loud, no partial success. "
                        f"This is a non-retryable error - reduce scope or increase budget."
                    )

                # Make request
                if method.upper() == "GET":
                    response = await self.client.get(url, **kwargs)
                elif method.upper() == "POST":
                    response = await self.client.post(url, **kwargs)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()

                # Check response size
                content_length = len(response.content)
                if content_length > self.MAX_RESPONSE_SIZE:
                    raise Exception(
                        f"Response size {content_length} exceeds MAX_RESPONSE_SIZE "
                        f"{self.MAX_RESPONSE_SIZE}. Potential runaway response."
                    )

                self.request_count += 1
                return response

            except (
                httpx.HTTPStatusError,
                httpx.TransportError,
                httpx.TimeoutException,
            ) as e:
                last_exception = e

                # Check if error is retryable
                retryable = False
                if isinstance(e, httpx.HTTPStatusError):
                    # Retry on 429 (rate limit) and 5xx (server errors)
                    retryable = (
                        e.response.status_code == 429 or e.response.status_code >= 500
                    )
                elif isinstance(e, (httpx.TransportError, httpx.TimeoutException)):
                    # Retry on transport/timeout errors
                    retryable = True

                if not retryable or attempt >= max_retries:
                    logger.error(
                        f"Request failed (attempt {attempt + 1}/{max_retries + 1}): {e}"
                    )
                    raise

                # Exponential backoff: 1s, 2s, 4s
                wait_time = 2**attempt
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{max_retries + 1}), "
                    f"retrying in {wait_time}s: {e}"
                )
                await asyncio.sleep(wait_time)

        # Should never reach here, but just in case
        raise last_exception or Exception("Request failed after retries")
