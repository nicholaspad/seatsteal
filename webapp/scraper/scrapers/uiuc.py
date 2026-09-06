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
    MAX_REQUESTS = 10000  # Request budget to prevent runaway scraping
    RETRY_BACKOFF_DELAYS = [2, 4, 8]  # Exponential backoff for retries (seconds)

    def __init__(self, db_session=None):
        super().__init__("uiuc")
        self.client: Optional[httpx.AsyncClient] = None
        self.current_term = get_term_code_from_db(db_session, "uiuc")
        self.request_count = 0
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

        Term format: 1202YYS
        - 1202 = prefix
        - YY = 2-digit year (26 = 2026, 68 would be wrong interpretation)
        - S = semester (8=Fall, 1=Spring, 5=Summer, 0=Winter)

        Args:
            term_code: 6-digit term code (e.g., "120268")

        Returns:
            Tuple of (year, season) for URL (e.g., ("2026", "fall"))

        Raises:
            ValueError: If term code is invalid
        """
        if not term_code or len(term_code) != 6:
            raise ValueError(f"Invalid UIUC term code: {term_code}")

        # Extract YY and S from 1202YYS
        # Position 4 is the first digit of YY, position 5 is the semester code
        yy = term_code[4]  # Single digit for year
        semester_code = term_code[5]

        # For UIUC pattern 1202YYS where Y is decade and S is both year+semester
        # Actually looking at 120268: 1202 + 6 + 8
        # It appears YY is at position 4 only, and S at position 5
        # But 68 would mean 2068, not 2026

        # Correction: The pattern seems to be 12026 + 8, where:
        # - 1202 = prefix
        # - 6 = year within decade (2026)
        # - 8 = semester

        # So we need to extract position 4 as year offset, position 5 as semester
        year_offset = term_code[4]
        semester_code = term_code[5]

        # Construct full year (assume 202X decade)
        year = f"202{year_offset}"

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
                f"Invalid semester code '{semester_code}' in term {term_code}"
            )

        return year, season

    async def _fetch_subjects(self, year: str, season: str) -> List[str]:
        """
        Fetch available subjects from UIUC XML index.

        URL: /cisapp/explorer/schedule/{year}/{season}.xml

        Args:
            year: Year string (e.g., "2026")
            season: Season string (e.g., "fall")

        Returns:
            List of subject codes (e.g., ['CS', 'MATH', 'ENG'])
        """
        url = f"{self.BASE_URL}/cisapp/explorer/schedule/{year}/{season}.xml"

        try:
            response = await self._fetch_with_retry(url)
            self.request_count += 1

            # Parse XML
            root = ET.fromstring(response.content)

            # Extract subject codes from XML
            subjects = []
            for subject_elem in root.findall(".//subject"):
                subject_id = subject_elem.get("id")
                if subject_id:
                    subjects.append(subject_id)

            logger.info(f"Fetched {len(subjects)} subjects from XML index")
            return subjects

        except Exception as e:
            logger.error(f"Error fetching UIUC subjects: {e}")
            raise

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
            List of course IDs (e.g., ['100', '101', '225'])
        """
        url = f"{self.BASE_URL}/cisapp/explorer/schedule/{year}/{season}/{subject}.xml"

        try:
            response = await self._fetch_with_retry(url)
            self.request_count += 1

            # Parse XML
            root = ET.fromstring(response.content)

            # Extract course IDs from XML
            course_ids = []
            for course_elem in root.findall(".//course"):
                course_id = course_elem.get("id")
                if course_id:
                    course_ids.append(course_id)

            logger.debug(f"Subject {subject}: {len(course_ids)} courses in XML")
            return course_ids

        except Exception as e:
            logger.error(f"Error fetching UIUC courses for subject {subject}: {e}")
            raise

    async def _fetch_courses_concurrent(
        self, year: str, season: str, course_ids: List[Tuple[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Fetch course details from HTML with bounded concurrency.

        Args:
            year: Year string
            season: Season string
            course_ids: List of (subject, course_id) tuples

        Returns:
            List of raw class data dictionaries
        """
        all_classes = []
        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_COURSES)

        async def fetch_one(subject: str, course_id: str):
            async with semaphore:
                return await self._fetch_course_html(year, season, subject, course_id)

        # Process in batches to respect rate limits
        batch_size = 20
        for i in range(0, len(course_ids), batch_size):
            batch = course_ids[i : i + batch_size]

            # Fetch batch concurrently
            tasks = [fetch_one(subject, course_id) for subject, course_id in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Collect successful results
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.warning(f"Course fetch failed: {result}")
                    continue
                if result:
                    all_classes.extend(result)

            logger.debug(
                f"Processed batch {i // batch_size + 1}: "
                f"{len(batch)} courses (total classes: {len(all_classes)})"
            )

            # Rate limiting between batches
            await asyncio.sleep(0.2)

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
        """
        url = f"{self.BASE_URL}/schedule/{year}/{season}/{subject}/{course_id}"

        try:
            # Check request budget
            if self.request_count >= self.MAX_REQUESTS:
                logger.error(f"Request budget exhausted ({self.MAX_REQUESTS})")
                raise RuntimeError("Request budget exhausted")

            response = await self._fetch_with_retry(url)
            self.request_count += 1

            # Parse HTML
            soup = BeautifulSoup(response.content, "lxml")

            # Find course title
            title_elem = soup.find("h1", class_="page-title")
            if not title_elem:
                logger.warning(f"No title found for {subject} {course_id}")
                return []

            title_text = title_elem.get_text(strip=True)
            # Title format: "SUBJECT COURSE - Title" (e.g., "CS 100 - Intro to CS")
            course_code = f"{subject} {course_id}"
            if "-" in title_text:
                title = title_text.split("-", 1)[1].strip()
            else:
                title = title_text

            # Parse schedule table
            classes = []
            schedule_table = soup.find("table", id="schedule-course-table")
            if not schedule_table:
                logger.warning(f"No schedule table found for {subject} {course_id}")
                return []

            tbody = schedule_table.find("tbody")
            if not tbody:
                return []

            for row in tbody.find_all("tr"):
                try:
                    class_data = self._parse_class_row(row, course_code, title)
                    if class_data:
                        classes.append(class_data)
                except Exception as e:
                    logger.warning(f"Error parsing class row for {course_code}: {e}")
                    continue

            logger.debug(
                f"Parsed {len(classes)} classes from {subject} {course_id} HTML"
            )
            return classes

        except httpx.HTTPStatusError as e:
            if e.response.status_code in [401, 403]:
                # Fail loud on auth errors
                logger.error(f"Auth error {e.response.status_code} for {url}")
                raise
            logger.warning(f"HTTP error {e.response.status_code} for {url}")
            return []
        except Exception as e:
            logger.warning(f"Error fetching course HTML for {subject} {course_id}: {e}")
            return []

    def _parse_class_row(
        self, row, course_code: str, title: str
    ) -> Optional[Dict[str, Any]]:
        """
        Parse a single class row from the schedule table.

        Args:
            row: BeautifulSoup tr element
            course_code: Course code (e.g., "CS 100")
            title: Course title

        Returns:
            Dictionary with class data or None if invalid
        """
        cells = row.find_all("td")
        if len(cells) < 2:
            return None

        # Extract CRN (first cell)
        crn_cell = cells[0]
        crn = crn_cell.get_text(strip=True)
        if not crn:
            return None

        # Extract section/type from first cell or second cell
        # Look for section info in the same cell or nearby
        section = ""
        section_elem = crn_cell.find("span", class_="section-code")
        if section_elem:
            section = section_elem.get_text(strip=True)
        elif len(cells) > 1:
            # Try second cell for section
            section = cells[1].get_text(strip=True)

        # Extract availability status
        # Look for "Availability" dd element or status icon aria-label
        status = "Closed"  # Conservative default

        # Find the availability dd element
        for dd in row.find_all("dd"):
            dt = dd.find_previous_sibling("dt")
            if dt and "availability" in dt.get_text(strip=True).lower():
                availability_text = dd.get_text(strip=True)
                status = self._map_availability_status(availability_text)
                break

        # Fallback: look for status icon aria-label
        if status == "Closed":
            status_icon = row.find("i", attrs={"aria-label": True})
            if status_icon:
                aria_label = status_icon.get("aria-label", "")
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
