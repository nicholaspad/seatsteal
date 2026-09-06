from typing import List, Dict, Any, Optional, Set, Tuple
import asyncio
import httpx
from bs4 import BeautifulSoup
from scraper.base import BaseScraper
from scraper.utils.logger import scraper_logger as logger
from scraper.utils.term_code_db import get_term_code_from_db


class PurdueScraper(BaseScraper):
    """
    Purdue University course scraper.

    Scrapes course data from Purdue's Banner self-service system.
    Strategy: Fetch subjects for term → for each subject POST course search →
    parse CRN list → deduplicate → fetch detail pages for seat counts.

    Term codes: YYYYTT Banner format (e.g., "202710" = Fall 2026)
    - YYYY: 4-digit year
    - TT: Term code (10 = Fall, 13 = Winter, 20 = Spring, 30 = Summer)

    CRITICAL:
    - Deduplicate by CRN before detail fetches
    - Use bounded concurrency (4) for detail pages
    - Retry with backoff on 429/5xx and transient transport errors
    - Fail loud on any detail fetch failure (no partial success)
    - Never POST registration actions
    - Parse SEPARATE Capacity/Actual/Remaining cells in seat table
    """

    BASE_URL = "https://selfservice.mypurdue.purdue.edu/prod"
    MAX_TOTAL_REQUESTS = 3000  # Hard budget including listings + retries + details
    MAX_RETRIES = 3  # Retry count for transient errors

    def __init__(self, db_session=None):
        super().__init__("purdue")
        self.client: Optional[httpx.AsyncClient] = None
        self.current_term = get_term_code_from_db(db_session, "purdue")
        self.total_request_count = 0  # Track all requests including retries
        logger.info(f"Initialized Purdue scraper with term: {self.current_term}")

    async def _ensure_client(self):
        """Ensure HTTP client is initialized"""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "SeatSteal/1.0",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                },
            )

    async def scrape_courses(
        self, department: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape Purdue courses for a specific department or all courses.

        Args:
            department: Department/subject code (e.g., 'CS', 'MA') or 'ALL' for all courses
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries with class information
        """
        logger.info(
            f"Scraping Purdue {department} courses (limit: {limit}, term: {self.current_term})"
        )

        await self._ensure_client()

        try:
            # Fetch subjects for the term
            subjects = await self._fetch_subjects()
            logger.info(f"Found {len(subjects)} subjects for term {self.current_term}")

            # Filter by department if not ALL
            if department.upper() != "ALL":
                subjects = [s for s in subjects if s.upper() == department.upper()]
                if not subjects:
                    logger.warning(
                        f"No subject found matching department: {department}"
                    )
                    return []
                logger.info(f"Filtered to subject: {subjects[0]}")

            # Collect all CRN entries from subject searches
            all_crn_entries = []
            for subject in subjects:
                logger.info(f"Fetching course list for subject: {subject}")
                crn_entries = await self._fetch_subject_crns(subject)
                all_crn_entries.extend(crn_entries)
                logger.info(
                    f"Subject {subject}: {len(crn_entries)} sections "
                    f"(total: {len(all_crn_entries)})"
                )

                # Check request budget after each subject
                if self.total_request_count > self.MAX_TOTAL_REQUESTS:
                    raise Exception(
                        f"Request budget exceeded during listing: {self.total_request_count} > "
                        f"{self.MAX_TOTAL_REQUESTS} (failing loud, no partial success)"
                    )

                # Rate limiting between subjects
                await asyncio.sleep(0.2)

            # Deduplicate by CRN before detail fetches
            unique_crns = self._deduplicate_crns(all_crn_entries)
            logger.info(
                f"Deduplicated: {len(all_crn_entries)} sections → {len(unique_crns)} unique CRNs"
            )

            # Check if detail fetches would exceed budget
            estimated_detail_requests = len(unique_crns) * (1 + self.MAX_RETRIES)
            if (
                self.total_request_count + estimated_detail_requests
                > self.MAX_TOTAL_REQUESTS
            ):
                raise Exception(
                    f"Request budget would be exceeded by details: "
                    f"{self.total_request_count} + {estimated_detail_requests} (estimated) > "
                    f"{self.MAX_TOTAL_REQUESTS} (failing loud, no partial success)"
                )

            # Fetch detail pages with bounded concurrency and fail-loud on errors
            courses_data = await self._fetch_details_and_group(unique_crns, limit)

            logger.info(
                f"Successfully scraped {len(courses_data)} courses from Purdue "
                f"({len(unique_crns)} sections processed, {self.total_request_count} total requests)"
            )
            return courses_data

        except Exception as e:
            logger.error(f"Failed to scrape Purdue {department}: {e}")
            raise
        finally:
            if self.client:
                await self.client.aclose()
                self.client = None

    def parse_term_picker(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Parse term picker HTML to extract available terms.

        Args:
            html_content: HTML content from term picker page

        Returns:
            List of dicts with 'code', 'name', and 'registerable' keys
        """
        soup = BeautifulSoup(html_content, "lxml")
        terms = []

        term_select = soup.find("select", {"name": "p_term"})
        if not term_select:
            raise Exception("Term select element not found in picker page")

        for option in term_select.find_all("option"):
            code = option.get("value", "").strip()
            text = option.get_text(strip=True)

            if code and code.lower() != "none":
                # Check if term is registerable (no "View only" suffix)
                registerable = "(View only)" not in text
                # Strip "(View only)" from name
                name = text.replace("(View only)", "").strip()

                terms.append(
                    {
                        "code": code,
                        "name": name,
                        "registerable": registerable,
                    }
                )

        return terms

    async def _fetch_subjects(self) -> List[str]:
        """
        Fetch available subjects for the current term from the term picker page.

        Returns:
            List of subject codes (e.g., ['CS', 'MA', 'ECE'])
        """
        try:
            url = f"{self.BASE_URL}/bwckgens.p_proc_term_date"

            # POST to get subject list for term
            form_data = {
                "p_calling_proc": "bwckschd.p_disp_dyn_sched",
                "p_term": self.current_term,
            }

            response = await self._make_request_with_retry(
                "POST",
                url,
                data=form_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            soup = BeautifulSoup(response.content, "lxml")

            # Find subject select element
            subject_select = soup.find("select", {"name": "sel_subj", "id": "subj_id"})
            if not subject_select:
                raise Exception("Subject select element not found in response")

            # Extract subject codes from option values
            subjects = []
            for option in subject_select.find_all("option"):
                value = option.get("value", "").strip()
                if value and value != "%":  # Skip dummy/all options
                    subjects.append(value)

            logger.info(f"Fetched {len(subjects)} subjects from Purdue")
            return subjects

        except Exception as e:
            logger.error(f"Error fetching Purdue subjects: {e}")
            raise

    async def _fetch_subject_crns(self, subject: str) -> List[Dict[str, str]]:
        """
        Fetch CRN list for a subject using Banner course search POST.

        Args:
            subject: Subject code (e.g., 'CS')

        Returns:
            List of dicts with CRN, course_code, title, section info
        """
        try:
            url = f"{self.BASE_URL}/bwckschd.p_get_crse_unsec"

            # Banner multi-select requires dummy seeds before real values
            form_data = {
                "term_in": self.current_term,
                "sel_subj": ["dummy", subject],  # Banner pattern: dummy + value
                "sel_day": "dummy",
                "sel_schd": "dummy",
                "sel_insm": "dummy",
                "sel_camp": "dummy",
                "sel_levl": "dummy",
                "sel_sess": "dummy",
                "sel_instr": "dummy",
                "sel_ptrm": "dummy",
                "sel_attr": "dummy",
                "sel_crse": "",  # Empty for all courses
                "sel_title": "",
                "sel_from_cred": "",
                "sel_to_cred": "",
                "begin_hh": "0",
                "begin_mi": "0",
                "begin_ap": "a",
                "end_hh": "0",
                "end_mi": "0",
                "end_ap": "a",
            }

            response = await self._make_request_with_retry(
                "POST",
                url,
                data=form_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            soup = BeautifulSoup(response.content, "lxml")

            # Parse section links via href (more stable than onclick)
            crn_entries = []

            # Find all course detail links
            for anchor in soup.find_all("a", href=True):
                href = anchor.get("href", "")
                if "bwckschd.p_disp_detail_sched" in href:
                    # Extract link text: "Title - CRN - SUBJECT NUMBER - SECTION"
                    text = anchor.get_text(strip=True)
                    parts = [p.strip() for p in text.split("-")]

                    if len(parts) >= 4:
                        # Extract CRN (second part)
                        crn = parts[1].strip()

                        # Extract SUBJECT NUMBER (third part)
                        subject_number = parts[2].strip()

                        # Extract section (fourth part)
                        section = parts[3].strip()

                        # Title is first part
                        title = parts[0].strip()

                        crn_entries.append(
                            {
                                "crn": crn,
                                "course_code": subject_number,  # e.g., "CS 18000"
                                "title": title,
                                "section": section,
                            }
                        )

            logger.debug(f"Subject {subject}: parsed {len(crn_entries)} CRN entries")
            return crn_entries

        except Exception as e:
            logger.error(f"Error fetching subject CRNs for {subject}: {e}")
            raise

    def _deduplicate_crns(
        self, crn_entries: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """
        Deduplicate CRN entries by CRN (keep first occurrence).

        Args:
            crn_entries: List of CRN entry dicts

        Returns:
            List of unique CRN entries
        """
        seen_crns: Set[str] = set()
        unique_entries = []

        for entry in crn_entries:
            crn = entry.get("crn", "")
            if crn and crn not in seen_crns:
                seen_crns.add(crn)
                unique_entries.append(entry)

        if len(crn_entries) != len(unique_entries):
            logger.info(
                f"Deduplicated CRNs: {len(crn_entries)} → {len(unique_entries)} "
                f"(removed {len(crn_entries) - len(unique_entries)} duplicates)"
            )

        return unique_entries

    async def _fetch_details_and_group(
        self, crn_entries: List[Dict[str, str]], limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch detail pages for CRNs with bounded concurrency and group by course.
        FAIL LOUD on any detail fetch error - no partial success.

        Args:
            crn_entries: List of unique CRN entries
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries grouped by course_code
        """
        # Apply limit if specified (before detail fetches)
        if limit and len(crn_entries) > limit:
            crn_entries = crn_entries[:limit]
            logger.info(f"Limited to {limit} CRN entries before detail fetches")

        # Fetch detail pages with bounded concurrency (4 concurrent requests)
        semaphore = asyncio.Semaphore(4)

        async def fetch_with_semaphore(entry):
            async with semaphore:
                return await self._fetch_crn_detail(entry)

        logger.info(f"Fetching {len(crn_entries)} detail pages with concurrency=4...")

        # Process in batches for progress logging
        batch_size = 50
        all_classes = []
        failed_crns = []

        for i in range(0, len(crn_entries), batch_size):
            batch = crn_entries[i : i + batch_size]
            batch_tasks = [fetch_with_semaphore(entry) for entry in batch]
            # DO NOT use return_exceptions=True - let exceptions propagate
            # But we need to catch them to provide better error messages
            try:
                batch_results = await asyncio.gather(*batch_tasks)

                # Check for None results (fetch failures that were caught)
                for idx, result in enumerate(batch_results):
                    if result is None:
                        failed_crns.append(batch[idx].get("crn", "unknown"))
                    else:
                        all_classes.append(result)

            except Exception as e:
                # If any detail fetch raised an exception, fail the entire scrape
                logger.error(f"Detail fetch failed in batch {i // batch_size + 1}: {e}")
                raise Exception(
                    f"Detail fetch failed for batch starting at CRN {batch[0].get('crn')}: {e}. "
                    "Aborting scrape (no partial success)."
                )

            logger.info(
                f"Progress: {min(i + batch_size, len(crn_entries))}/{len(crn_entries)} "
                f"details fetched"
            )

            # Rate limiting between batches
            if i + batch_size < len(crn_entries):
                await asyncio.sleep(0.3)

        # FAIL LOUD if any detail fetches returned None
        if failed_crns:
            raise Exception(
                f"Detail fetch failed for {len(failed_crns)} CRNs: {failed_crns[:10]}... "
                "Aborting scrape (no partial success)."
            )

        logger.info(
            f"Fetched {len(all_classes)} class details (all required details succeeded)"
        )

        # Group by course_code
        courses_dict: Dict[str, Dict[str, Any]] = {}
        for class_data in all_classes:
            course_code = class_data["course_code"]

            if course_code not in courses_dict:
                courses_dict[course_code] = {
                    "course_code": course_code,
                    "title": class_data["title"],
                    "classes": [],
                }

            courses_dict[course_code]["classes"].append(
                {
                    "class_number": class_data["class_number"],
                    "section": class_data["section"],
                    "status": class_data["status"],
                }
            )

        courses_data = list(courses_dict.values())
        logger.info(
            f"Grouped {len(all_classes)} classes into {len(courses_data)} courses"
        )
        return courses_data

    async def _fetch_crn_detail(
        self, crn_entry: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch detail page for a CRN and parse seat availability.
        Uses retry logic with backoff for transient errors.

        Args:
            crn_entry: Dict with crn, course_code, title, section

        Returns:
            Dict with class data including status (Open/Closed), or None on error
        """
        crn = crn_entry.get("crn", "")
        if not crn:
            logger.error("CRN entry missing 'crn' field")
            return None

        try:
            url = f"{self.BASE_URL}/bwckschd.p_disp_detail_sched"
            params = {
                "term_in": self.current_term,
                "crn_in": crn,
            }

            response = await self._make_request_with_retry("GET", url, params=params)

            soup = BeautifulSoup(response.content, "lxml")

            # Parse "Registration Availability" section with SEPARATE cells
            status = self._parse_seat_availability(soup, crn)

            return {
                "class_number": crn,  # CRN is the class_number
                "course_code": crn_entry.get("course_code", ""),
                "title": crn_entry.get("title", ""),
                "section": crn_entry.get("section", ""),
                "status": status,
            }

        except Exception as e:
            logger.error(f"Error fetching detail for CRN {crn}: {e}")
            return None

    def _parse_seat_availability(self, soup: BeautifulSoup, crn: str) -> str:
        """
        Parse seat availability from Banner detail page.
        Expects SEPARATE cells: Capacity | Actual | Remaining

        Args:
            soup: BeautifulSoup parsed HTML
            crn: CRN for logging

        Returns:
            "Open" if remaining > 0, else "Closed"
        """
        status = "Closed"  # Default conservative

        # Find the table with caption "Registration Availability"
        for table in soup.find_all("table", {"class": "datadisplaytable"}):
            caption = table.find("caption")
            if not caption or "Registration Availability" not in caption.get_text():
                continue

            # Look for "Seats" row with separate Capacity/Actual/Remaining cells
            for row in table.find_all("tr"):
                cells = row.find_all(["th", "td"])

                # Check if this is the header row (Capacity | Actual | Remaining)
                if len(cells) >= 3:
                    cell_texts = [c.get_text(strip=True) for c in cells]

                    # Look for row with "Seats" label
                    if "Seats" in cell_texts:
                        # Find the Remaining cell
                        for i, text in enumerate(cell_texts):
                            if text == "Remaining":
                                # Next row should have the values
                                next_row = row.find_next_sibling("tr")
                                if next_row:
                                    value_cells = next_row.find_all("td")
                                    if len(value_cells) > i:
                                        remaining_text = value_cells[i].get_text(
                                            strip=True
                                        )
                                        try:
                                            remaining = int(remaining_text)
                                            status = (
                                                "Open" if remaining > 0 else "Closed"
                                            )
                                            logger.debug(
                                                f"CRN {crn}: {remaining} remaining seats → {status}"
                                            )
                                            return status
                                        except ValueError:
                                            logger.warning(
                                                f"CRN {crn}: Could not parse remaining seats from '{remaining_text}'"
                                            )

                # Also try simpler pattern: row with "Seats" text followed by cells
                if len(cells) >= 4:
                    # Pattern: <th>Seats</th><td>XX</td><td>YY</td><td>ZZ</td>
                    # where cells are Capacity, Actual, Remaining
                    first_cell = cells[0].get_text(strip=True)
                    if first_cell == "Seats" and len(cells) >= 4:
                        try:
                            remaining = int(cells[3].get_text(strip=True))
                            status = "Open" if remaining > 0 else "Closed"
                            logger.debug(
                                f"CRN {crn}: {remaining} remaining seats → {status}"
                            )
                            return status
                        except (ValueError, IndexError) as e:
                            logger.warning(
                                f"CRN {crn}: Could not parse remaining from cells: {e}"
                            )

        # If we didn't find Remaining, log warning and keep Closed
        logger.warning(
            f"CRN {crn}: Could not find 'Remaining' cell in seat table, "
            "defaulting to Closed (never invent Open)"
        )
        return status

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
                    raise Exception(
                        f"Request budget exceeded: {self.total_request_count} > "
                        f"{self.MAX_TOTAL_REQUESTS} (failing loud)"
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
