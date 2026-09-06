from typing import List, Dict, Any, Optional, Tuple
import asyncio
import httpx
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from scraper.base import BaseScraper
from scraper.utils.logger import scraper_logger as logger
from scraper.utils.term_code_db import get_term_code_from_db


class UiucScraper(BaseScraper):
    """
    University of Illinois Urbana-Champaign course scraper.

    Scrapes course data from UIUC's courses.illinois.edu system.
    Strategy: Fetch subjects XML → per subject fetch summary XML → per course fetch HTML.

    Term codes: 1202YYS format (e.g., "120268" = Fall 2026)
    - 1202 = prefix
    - YY = 2-digit year (68 = 2026)
    - S = semester indicator (8 = Fall, 1 = Spring, 5 = Summer, 0 = Winter)

    Status mapping:
    - Open, Open (Restricted), CrossListOpen, CrossListOpen (Restricted) → Open
    - Closed, Pending, Unknown, missing/malformed → Closed

    CRITICAL: Do NOT use XML statusCode/sectionStatusCode fields as Open/Closed.
    These are observed to return "A" on Closed sections. Always parse HTML availability.
    """

    BASE_URL = "https://courses.illinois.edu"
    MAX_CONCURRENT_COURSES = 4  # Bounded concurrency for course page fetches
    RETRY_BACKOFF_DELAYS = [2, 4, 8]  # Exponential backoff for retries (seconds)

    # Budget multipliers for calculating dynamic request budget
    BUDGET_PER_SUBJECT_XML = 1  # 1 request per subject XML fetch
    BUDGET_PER_COURSE_HTML = 1  # 1 request per course HTML page
    BUDGET_RETRY_MULTIPLIER = 1.3  # 30% allowance for retries
    BUDGET_BASE_OVERHEAD = 2  # Base: subjects index XML + margin

    def __init__(self, db_session=None):
        super().__init__("uiuc")
        self.client: Optional[httpx.AsyncClient] = None
        self.current_term = get_term_code_from_db(db_session, "uiuc")
        self.request_count = 0
        self.request_budget = 0  # Will be calculated dynamically
        self.budget_lock = asyncio.Lock()  # Synchronize budget checks
        self.failed_courses = 0  # Track failures for material partial detection
        logger.info(f"Initialized UIUC scraper with term: {self.current_term}")

    async def _ensure_client(self):
        """Ensure HTTP client is initialized"""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "SeatSteal/1.0",
                    "Accept": "text/html,application/xml",
                },
            )

    async def scrape_courses(
        self, department: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape UIUC courses for a specific department or all courses.

        Args:
            department: Department code (e.g., 'CS', 'MATH') or 'ALL' for all courses
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries with class information
        """
        logger.info(
            f"Scraping UIUC {department} courses (limit: {limit}, term: {self.current_term})"
        )

        await self._ensure_client()

        try:
            # Parse term code into year/season for URL construction
            year, season = self._parse_term_code(self.current_term)
            logger.info(f"Parsed term {self.current_term} → {year}/{season}")

            # Fetch subjects from XML
            subjects = await self._fetch_subjects(year, season)
            logger.info(f"Found {len(subjects)} subjects for term {year}/{season}")

            # Filter by department if not ALL
            if department.upper() != "ALL":
                subjects = [s for s in subjects if s.upper() == department.upper()]
                if not subjects:
                    logger.warning(
                        f"No subject found matching department: {department}"
                    )
                    return []
                logger.info(f"Filtered to subject: {subjects[0]}")

            # Fetch course IDs for each subject from summary XML
            all_course_ids = []
            for subject in subjects:
                logger.info(f"Fetching course IDs for subject: {subject}")
                course_ids = await self._fetch_subject_courses(year, season, subject)
                all_course_ids.extend(
                    [(subject, course_id) for course_id in course_ids]
                )
                logger.info(
                    f"Subject {subject}: {len(course_ids)} courses "
                    f"(total: {len(all_course_ids)})"
                )

                # Check limit
                if limit and len(all_course_ids) >= limit:
                    logger.info(f"Reached limit of {limit} courses")
                    all_course_ids = all_course_ids[:limit]
                    break

            # Calculate dynamic request budget based on discovered work
            planned_courses = len(all_course_ids)
            self._calculate_request_budget(len(subjects), planned_courses)
            logger.info(
                f"Request budget: {self.request_budget} "
                f"(planned: {len(subjects)} subjects + {planned_courses} courses, "
                f"current: {self.request_count})"
            )

            # Fetch course details from HTML with bounded concurrency
            logger.info(
                f"Fetching {len(all_course_ids)} course pages with concurrency {self.MAX_CONCURRENT_COURSES}"
            )
            all_raw_classes = await self._fetch_courses_concurrent(
                year, season, all_course_ids
            )

            # Transform to standard format with global CRN deduplication
            courses_data = self._transform_classes(all_raw_classes)
            logger.info(
                f"Successfully scraped {len(courses_data)} courses from UIUC "
                f"({len(all_raw_classes)} total classes)"
            )
            return courses_data

        except Exception as e:
            logger.error(f"Failed to scrape UIUC {department}: {e}")
            raise
        finally:
            if self.client:
                await self.client.aclose()
                self.client = None

    def _parse_term_code(self, term_code: str) -> Tuple[str, str]:
        """
        Parse UIUC term code into year and season.

        Term format: 1202YS where Y is year digit, S is semester
        - 1202 = required prefix
        - Y = year digit (6 = 2026, 7 = 2027, etc. in 202X decade)
        - S = semester (8=Fall, 1=Spring, 5=Summer, 0=Winter)

        Examples:
        - 120268 → 2026/fall
        - 120261 → 2026/spring

        Args:
            term_code: 6-digit term code (e.g., "120268")

        Returns:
            Tuple of (year, season) for URL (e.g., ("2026", "fall"))

        Raises:
            ValueError: If term code is invalid
        """
        if not term_code:
            raise ValueError("Term code cannot be empty")

        if not isinstance(term_code, str):
            raise ValueError(f"Term code must be string, got {type(term_code)}")

        if not term_code.isdigit():
            raise ValueError(f"Term code must be numeric: {term_code}")

        if len(term_code) != 6:
            raise ValueError(
                f"Term code must be 6 digits, got {len(term_code)}: {term_code}"
            )

        # Validate prefix
        if not term_code.startswith("1202"):
            raise ValueError(f"Term code must start with '1202', got: {term_code}")

        # Extract year digit and semester code from 1202YS
        year_digit = term_code[4]  # Position 4 is year digit
        semester_code = term_code[5]  # Position 5 is semester code

        # Construct full year (assume 202X decade)
        year = f"202{year_digit}"

        # Map semester code to season string
        season_map = {
            "8": "fall",
            "1": "spring",
            "5": "summer",
            "0": "winter",
        }

        season = season_map.get(semester_code)
        if not season:
            raise ValueError(
                f"Invalid semester code '{semester_code}' in term {term_code}. "
                f"Valid codes: {list(season_map.keys())}"
            )

        return year, season

    def _calculate_request_budget(self, num_subjects: int, num_courses: int):
        """
        Calculate dynamic request budget based on discovered work.

        Budget formula:
        - Base overhead (subjects index XML + margin)
        - Subject XMLs (one per subject)
        - Course HTMLs (one per course)
        - Retry allowance (30% multiplier for retries/failures)

        Args:
            num_subjects: Number of subjects to fetch
            num_courses: Number of courses to fetch

        Sets:
            self.request_budget: Total allowed requests
        """
        base_budget = (
            self.BUDGET_BASE_OVERHEAD
            + (num_subjects * self.BUDGET_PER_SUBJECT_XML)
            + (num_courses * self.BUDGET_PER_COURSE_HTML)
        )

        # Apply retry multiplier
        self.request_budget = int(base_budget * self.BUDGET_RETRY_MULTIPLIER)

        logger.info(
            f"Calculated request budget: {self.request_budget} "
            f"(base: {base_budget}, subjects: {num_subjects}, courses: {num_courses})"
        )

    async def _check_and_increment_budget(self):
        """
        Check request budget and increment counter atomically.

        Uses lock to synchronize budget checks across concurrent tasks.

        Raises:
            RuntimeError: If budget would be exceeded
        """
        async with self.budget_lock:
            if self.request_count >= self.request_budget:
                logger.error(
                    f"Request budget exhausted: {self.request_count}/{self.request_budget}"
                )
                raise RuntimeError(
                    f"Request budget exhausted ({self.request_count}/{self.request_budget})"
                )
            self.request_count += 1

    async def _fetch_subjects(self, year: str, season: str) -> List[str]:
        """
        Fetch available subjects from UIUC XML index.

        URL: /cisapp/explorer/schedule/{year}/{season}.xml

        Args:
            year: Year string (e.g., "2026")
            season: Season string (e.g., "fall")

        Returns:
            List of unique subject codes (e.g., ['CS', 'MATH', 'ENG'])
        """
        url = f"{self.BASE_URL}/cisapp/explorer/schedule/{year}/{season}.xml"

        await self._check_and_increment_budget()
        response = await self._fetch_with_retry(url)

        # Parse XML with namespace safety
        root = ET.fromstring(response.content)

        # Extract subject codes from XML (namespace-independent)
        # Use local-name() via iteration to handle namespaced elements
        subjects = []
        seen = set()  # Deduplicate subject IDs

        for elem in root.iter():
            # Check local tag name (ignoring namespace)
            local_tag = elem.tag.split("}")[1] if "}" in elem.tag else elem.tag
            if local_tag == "subject":
                subject_id = elem.get("id")
                if subject_id and subject_id not in seen:
                    seen.add(subject_id)
                    subjects.append(subject_id)

        logger.info(f"Fetched {len(subjects)} unique subjects from XML index")
        return subjects

    async def _fetch_subject_courses(
        self, year: str, season: str, subject: str
    ) -> List[str]:
        """
        Fetch course IDs for a subject from UIUC XML summary.

        URL: /cisapp/explorer/schedule/{year}/{season}/{subject}.xml

        Args:
            year: Year string (e.g., "2026")
            season: Season string (e.g., "fall")
            subject: Subject code (e.g., "CS")

        Returns:
            List of unique course IDs (e.g., ['100', '101', '225'])
        """
        url = f"{self.BASE_URL}/cisapp/explorer/schedule/{year}/{season}/{subject}.xml"

        await self._check_and_increment_budget()
        response = await self._fetch_with_retry(url)

        # Parse XML with namespace safety
        root = ET.fromstring(response.content)

        # Extract course IDs from XML (namespace-independent)
        course_ids = []
        seen = set()  # Deduplicate course IDs

        for elem in root.iter():
            # Check local tag name (ignoring namespace)
            local_tag = elem.tag.split("}")[1] if "}" in elem.tag else elem.tag
            if local_tag == "course":
                course_id = elem.get("id")
                if course_id and course_id not in seen:
                    seen.add(course_id)
                    course_ids.append(course_id)

        logger.debug(f"Subject {subject}: {len(course_ids)} unique courses in XML")
        return course_ids

    async def _fetch_courses_concurrent(
        self, year: str, season: str, course_ids: List[Tuple[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Fetch course details from HTML with bounded concurrency.

        Fail-loud strategy: Track failures (exceptions AND empty-success) and abort
        on material partial failure, 401/403, or budget exhaustion.

        Args:
            year: Year string
            season: Season string
            course_ids: List of (subject, course_id) tuples

        Returns:
            List of raw class data dictionaries

        Raises:
            RuntimeError: On material partial failure (>20% fail rate or empty-success rate)
            httpx.HTTPStatusError: On 401/403 auth errors
            RuntimeError: On request budget exhaustion
        """
        all_classes = []
        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_COURSES)
        total_courses = len(course_ids)
        courses_with_classes = 0
        courses_empty_success = 0  # Track courses that return [] (malformed/no rows)

        async def fetch_one(subject: str, course_id: str):
            async with semaphore:
                return await self._fetch_course_html(year, season, subject, course_id)

        # Process in batches to respect rate limits
        batch_size = 20
        for i in range(0, len(course_ids), batch_size):
            batch = course_ids[i : i + batch_size]

            # Fetch batch concurrently WITHOUT return_exceptions
            # Auth errors (401/403) and budget exhaustion will propagate immediately
            tasks = [fetch_one(subject, course_id) for subject, course_id in batch]

            try:
                batch_results = await asyncio.gather(*tasks)
            except (httpx.HTTPStatusError, RuntimeError) as e:
                # Auth errors or budget exhaustion - fail immediately
                logger.error(f"Critical error during batch fetch: {e}")
                raise

            # Collect results and track empty-success (malformed/no classes)
            for idx, result in enumerate(batch_results):
                if isinstance(result, list):
                    if len(result) > 0:
                        # Success with classes
                        all_classes.extend(result)
                        courses_with_classes += 1
                    else:
                        # Empty success - malformed HTML or no sections offered
                        courses_empty_success += 1
                        subject, course_id = batch[idx]
                        logger.warning(
                            f"Empty-success course: {subject} {course_id} (no classes parsed)"
                        )
                else:
                    # Should never happen - indicates bug in implementation
                    courses_empty_success += 1
                    logger.error(f"Unexpected non-list result: {result}")

            logger.debug(
                f"Processed batch {i // batch_size + 1}: "
                f"{len(batch)} courses "
                f"(classes: {len(all_classes)}, with_data: {courses_with_classes}, empty: {courses_empty_success})"
            )

            # Check material failure threshold (>20% empty-success rate)
            if total_courses > 10:  # Only enforce for meaningful sample size
                empty_rate = courses_empty_success / total_courses
                if empty_rate > 0.2:
                    error_msg = (
                        f"Material partial failure: {courses_empty_success}/{total_courses} "
                        f"courses empty-success ({empty_rate:.1%})"
                    )
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

            # Rate limiting between batches
            await asyncio.sleep(0.2)

        # Final summary
        logger.info(
            f"Completed course fetch: {courses_with_classes} courses with classes, "
            f"{courses_empty_success} empty-success, "
            f"{len(all_classes)} total class rows"
        )

        if courses_empty_success > 0 and total_courses > 10:
            empty_rate = courses_empty_success / total_courses
            if empty_rate > 0.2:
                logger.warning(
                    f"High empty-success rate: {empty_rate:.1%} "
                    f"({courses_empty_success}/{total_courses})"
                )

        return all_classes

    async def _fetch_course_html(
        self, year: str, season: str, subject: str, course_id: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch course details from HTML page.

        URL: /schedule/{year}/{season}/{subject}/{course}

        Args:
            year: Year string
            season: Season string
            subject: Subject code
            course_id: Course ID

        Returns:
            List of class data dictionaries

        Raises:
            httpx.HTTPStatusError: On 401/403 auth errors
            RuntimeError: On request budget exhaustion
        """
        url = f"{self.BASE_URL}/schedule/{year}/{season}/{subject}/{course_id}"

        # Check request budget atomically BEFORE making request
        await self._check_and_increment_budget()

        response = await self._fetch_with_retry(url)

        # Parse HTML
        soup = BeautifulSoup(response.content, "lxml")

        # Find course heading and title
        # Official DOM: <h1 class="fw-bold">CS 124</h1> with title in .app-label
        title_elem = soup.find("h1", class_="fw-bold")
        if not title_elem:
            raise ValueError(f"No course heading found for {subject} {course_id}")

        # Get course code from h1 (e.g., "CS 124")
        heading_text = title_elem.get_text(strip=True)
        course_code = heading_text  # Use the official heading as course code

        # Get title from .app-label
        title = ""
        app_label = soup.find(class_="app-label")
        if app_label:
            title = app_label.get_text(strip=True)

        # Parse schedule table
        classes = []
        schedule_table = soup.find("table", id="schedule-course-table")
        if not schedule_table:
            raise ValueError(f"No schedule table found for {subject} {course_id}")

        tbody = schedule_table.find("tbody")
        if not tbody:
            # Empty tbody is valid (no sections offered)
            logger.debug(f"Empty tbody for {subject} {course_id}")
            return []

        for row in tbody.find_all("tr"):
            try:
                class_data = self._parse_class_row(row, course_code, title)
                if class_data:
                    classes.append(class_data)
            except Exception as e:
                logger.warning(f"Error parsing class row for {course_code}: {e}")
                continue

        logger.debug(f"Parsed {len(classes)} classes from {subject} {course_id} HTML")
        return classes

    def _parse_class_row(
        self, row, course_code: str, title: str
    ) -> Optional[Dict[str, Any]]:
        """
        Parse a single class row from the schedule table.

        Official DOM structure (per CS 124 live page):
        - td[0]: empty details-control
        - td[1]: status icon
        - td[2]: favorites
        - td[3]: CRN (4th column)
        - td[4]: Section (5th column)
        - ... other columns

        Args:
            row: BeautifulSoup tr element
            course_code: Course code (e.g., "CS 124")
            title: Course title

        Returns:
            Dictionary with class data or None if invalid
        """
        cells = row.find_all("td")
        if len(cells) < 5:
            # Need at least 5 columns to get CRN and Section
            return None

        # Extract CRN (4th column, index 3)
        crn = cells[3].get_text(strip=True)
        if not crn:
            return None

        # Extract section (5th column, index 4)
        section = cells[4].get_text(strip=True)

        # Extract availability status
        # Prefer Availability dd element, fallback to icon aria-label
        status = "Closed"  # Conservative default

        # Look for Availability dd element
        for dd in row.find_all("dd"):
            dt = dd.find_previous_sibling("dt")
            if dt and "availability" in dt.get_text(strip=True).lower():
                availability_text = dd.get_text(strip=True)
                status = self._map_availability_status(availability_text)
                break

        # Fallback: look for status icon aria-label (in td[1], status column)
        if status == "Closed" and len(cells) > 1:
            status_icon = cells[1].find("i", attrs={"aria-label": True})
            if status_icon:
                aria_label = status_icon.get("aria-label", "")
                # Strip "Section " prefix from official labels like "Section CrossListOpen (Restricted)"
                if aria_label.startswith("Section "):
                    aria_label = aria_label[len("Section ") :]
                status = self._map_availability_status(aria_label)

        return {
            "course_code": course_code,
            "title": title,
            "class_number": crn,
            "section": section,
            "status": status,
        }

    def _map_availability_status(self, availability_text: str) -> str:
        """
        Map UIUC availability text to standard status.

        Open statuses:
        - "Open"
        - "Open (Restricted)"
        - "CrossListOpen"
        - "CrossListOpen (Restricted)"

        Closed statuses (conservative):
        - "Closed"
        - "Pending"
        - "Unknown"
        - Missing/malformed

        Args:
            availability_text: Raw availability text from HTML

        Returns:
            "Open" or "Closed"
        """
        availability_lower = availability_text.lower().strip()

        # Open variants (exact match required)
        open_variants = [
            "open",
            "open (restricted)",
            "crosslistopen",
            "crosslistopen (restricted)",
        ]

        if availability_lower in open_variants:
            return "Open"

        # Everything else is Closed (conservative)
        return "Closed"

    def _transform_classes(
        self, raw_classes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Transform raw classes to standard format with global CRN deduplication.

        Deduplicates by CRN (class_number) across all courses since cross-listed
        courses can share the same CRN.

        Args:
            raw_classes: List of raw class data

        Returns:
            List of course dictionaries grouped by course_code
        """
        # First, deduplicate by CRN globally
        seen_crns = set()
        deduplicated_classes = []

        for class_data in raw_classes:
            crn = class_data["class_number"]
            if crn not in seen_crns:
                seen_crns.add(crn)
                deduplicated_classes.append(class_data)

        if len(raw_classes) != len(deduplicated_classes):
            logger.info(
                f"Global CRN deduplication: {len(raw_classes)} → "
                f"{len(deduplicated_classes)} classes "
                f"(removed {len(raw_classes) - len(deduplicated_classes)} cross-listed duplicates)"
            )

        # Group by course_code
        courses_dict: Dict[str, Dict[str, Any]] = {}
        for class_data in deduplicated_classes:
            course_code = class_data["course_code"]

            if course_code not in courses_dict:
                courses_dict[course_code] = {
                    "course_code": course_code,
                    "title": class_data["title"],
                    "classes": [],
                }

            # Add class to course
            courses_dict[course_code]["classes"].append(
                {
                    "class_number": class_data["class_number"],
                    "section": class_data["section"],
                    "status": class_data["status"],
                }
            )

        courses_data = list(courses_dict.values())
        logger.info(
            f"Transformed {len(deduplicated_classes)} classes into "
            f"{len(courses_data)} courses"
        )
        return courses_data

    async def _fetch_with_retry(self, url: str) -> httpx.Response:
        """
        Fetch URL with retry logic for 429 and 5xx errors.

        Args:
            url: URL to fetch

        Returns:
            HTTP response

        Raises:
            httpx.HTTPError: If all retries fail or on auth errors (401/403)
        """
        last_exception = None

        for attempt, delay in enumerate([0] + self.RETRY_BACKOFF_DELAYS):
            try:
                if delay > 0:
                    logger.info(f"Retrying {url} after {delay}s delay")
                    await asyncio.sleep(delay)

                response = await self.client.get(url)

                # Handle auth errors immediately (no retry)
                if response.status_code in [401, 403]:
                    response.raise_for_status()

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        wait_time = int(retry_after)
                        logger.warning(f"Rate limited, Retry-After: {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    # No Retry-After header, use backoff
                    if attempt < len(self.RETRY_BACKOFF_DELAYS):
                        continue
                    response.raise_for_status()

                # Handle server errors (5xx)
                if response.status_code >= 500:
                    if attempt < len(self.RETRY_BACKOFF_DELAYS):
                        logger.warning(
                            f"Server error {response.status_code}, will retry"
                        )
                        continue
                    response.raise_for_status()

                # Success or client error (4xx other than 429/401/403)
                response.raise_for_status()
                return response

            except Exception as e:
                last_exception = e
                # Check if this is an auth error - fail immediately
                if hasattr(e, "response") and e.response.status_code in [401, 403]:
                    raise
                if attempt >= len(self.RETRY_BACKOFF_DELAYS):
                    break

        # All retries exhausted
        logger.error(f"All retries exhausted for {url}")
        raise last_exception
