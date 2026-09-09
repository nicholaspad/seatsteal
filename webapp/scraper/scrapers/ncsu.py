from typing import List, Dict, Any, Optional
import asyncio
import httpx
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
    parse JSON response → deduplicate by Class # → return courses with classes.

    Term codes: STRM format (e.g., "2268" = Fall 2026)
    - YYY = year since 1900 (226 = 2026)
    - S = session digit:
      - 8 = Fall
      - 1 = Spring
      - 5 = Summer I
      - 6 = Summer II

    CRITICAL:
    - At NC State, CS = Crop Science, CSC = Computer Science
    - ONLY allowlist CSC (never CS as CompSci)
    - Use Class # (class_nbr) as identity, not section alone
    - Map Open→Open; Closed/Reserved/Waitlist/unknown→Closed (Reserved→Closed enables reserve-release alerts)
    - Department ALL → expand only to ALLOWED_DEPARTMENTS=["CSC"] (never ~199 subjects)
    - Content-Type may say text/html but body is JSON {"html":..., "json":...}
    - User-Agent: SeatSteal/1.0
    - Fail loud on budget exceeded, empty response, or unparseable data
    """

    BASE_URL = "https://webappprd.acs.ncsu.edu/php/coursecat"
    MAX_TOTAL_REQUESTS = 50
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

            # Parse response - may be JSON or HTML containing JSON
            subjects_data = self._parse_json_response(response)

            # Extract subject codes from response
            subjects = []
            if isinstance(subjects_data, list):
                # Response is array of subjects
                for subj in subjects_data:
                    if isinstance(subj, dict) and "subject" in subj:
                        subjects.append(subj["subject"])
                    elif isinstance(subj, str):
                        subjects.append(subj)
            elif isinstance(subjects_data, dict):
                # Response might have subjects nested
                if "subjects" in subjects_data:
                    subjects = subjects_data["subjects"]
                elif "data" in subjects_data:
                    subjects = subjects_data["data"]

            if not subjects:
                raise Exception("No subjects found in response")

            logger.info(f"Fetched {len(subjects)} subjects from NC State")
            return subjects

        except Exception as e:
            logger.error(f"Error fetching NC State subjects: {e}")
            raise

    async def _fetch_department_courses(self, department: str) -> List[Dict[str, Any]]:
        """
        Fetch courses for a specific department.

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

            # Parse JSON response
            search_data = self._parse_json_response(response)

            if not search_data:
                raise Exception("Empty response from search")

            # Extract courses from response
            courses_data = self._parse_courses_from_search(search_data, department)

            logger.info(
                f"Fetched {len(courses_data)} courses for department {department}"
            )
            return courses_data

        except Exception as e:
            logger.error(f"Error fetching courses for {department}: {e}")
            raise

    def _parse_json_response(self, response: httpx.Response) -> Any:
        """
        Parse JSON response that may have text/html Content-Type but JSON body.

        The ACS API returns {"html":..., "json":...} even with Content-Type: text/html.
        Parse as JSON and extract the json field if present.

        Args:
            response: httpx Response object

        Returns:
            Parsed data (dict or list)
        """
        try:
            # Try to parse as JSON first
            data = response.json()

            # If response has {"json": ...} structure, extract it
            if isinstance(data, dict) and "json" in data:
                return data["json"]

            return data

        except Exception as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response content: {response.text[:500]}")
            raise Exception(f"Could not parse response as JSON: {e}")

    def _parse_courses_from_search(
        self, search_data: Any, department: str
    ) -> List[Dict[str, Any]]:
        """
        Parse courses from search response data.

        Args:
            search_data: Parsed JSON data from search
            department: Department code for validation

        Returns:
            List of course dictionaries with classes
        """
        courses_dict: Dict[str, Dict[str, Any]] = {}

        # Handle different response formats
        sections = []
        if isinstance(search_data, list):
            sections = search_data
        elif isinstance(search_data, dict):
            if "sections" in search_data:
                sections = search_data["sections"]
            elif "courses" in search_data:
                sections = search_data["courses"]
            elif "data" in search_data:
                sections = search_data["data"]

        if not sections:
            logger.warning("No sections found in search response")
            # Fail loud if no sections found (may indicate breaking API change)
            raise Exception(
                f"No sections found in search response for {department}. "
                f"This may indicate a breaking change in the API or empty term data."
            )

        # Track seen class numbers for global deduplication
        seen_class_numbers = set()

        for section in sections:
            if not isinstance(section, dict):
                continue

            # Extract section data with various field name possibilities
            class_number = self._extract_field(
                section, ["class_nbr", "classNbr", "class_number", "classNumber"]
            )
            course_id = self._extract_field(
                section, ["course", "courseId", "course_id", "catalog"]
            )
            section_code = self._extract_field(
                section, ["section", "section_code", "sectionCode"]
            )
            title = self._extract_field(section, ["title", "courseTitle", "descr"])
            status = self._extract_field(
                section, ["status", "enrollStatus", "enrl_stat"]
            )

            if not class_number:
                logger.warning(f"Section missing class_nbr: {section}")
                continue

            # Deduplicate by class_number (CRITICAL: Class # is the identity)
            if class_number in seen_class_numbers:
                logger.debug(f"Skipping duplicate class_number: {class_number}")
                continue
            seen_class_numbers.add(class_number)

            # Parse course_code from course_id (e.g., "CSC-111" → "CSC 111")
            if course_id:
                if "-" in course_id:
                    parts = course_id.split("-", 1)
                    course_code = f"{parts[0]} {parts[1]}"
                else:
                    course_code = course_id.replace("_", " ")
            else:
                # Fallback: construct from section data
                course_code = f"{department} ???"
                logger.warning(
                    f"Could not determine course_code for class {class_number}"
                )

            # Normalize status: Open→Open, everything else→Closed
            normalized_status = self._normalize_ncsu_status(status)

            # Group by course_code
            if course_code not in courses_dict:
                courses_dict[course_code] = {
                    "course_code": course_code,
                    "title": title or "Unknown Title",
                    "classes": [],
                }

            courses_dict[course_code]["classes"].append(
                {
                    "class_number": str(class_number),
                    "section": section_code or "001",
                    "status": normalized_status,
                }
            )

        courses_data = list(courses_dict.values())

        # Fail loud if no courses parsed
        if not courses_data:
            raise Exception(
                f"Failed to parse any courses from search response for {department}. "
                f"This may indicate a breaking change in the API."
            )

        return courses_data

    def _extract_field(self, data: dict, field_names: List[str]) -> Optional[str]:
        """
        Extract field from dict trying multiple possible field names.

        Args:
            data: Dictionary to search
            field_names: List of possible field names to try

        Returns:
            Field value as string, or None if not found
        """
        for name in field_names:
            if name in data and data[name]:
                return str(data[name])
        return None

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
