from typing import List, Dict, Any, Optional, Set, Tuple
import asyncio
import re
import httpx
from bs4 import BeautifulSoup
from scraper.base import BaseScraper
from scraper.utils.logger import scraper_logger as logger
from scraper.utils.term_code_db import get_term_code_from_db


class PurdueBudgetExceededError(Exception):
    """
    Non-retryable budget error for Purdue scraper.
    Signals that request budget was exceeded and retry will not help.
    """
    pass


class PurdueScraper(BaseScraper):
    """
    Purdue University course scraper.

    Scrapes course data from Purdue's Banner self-service system.
    Strategy: Validate term via picker → Fetch subjects → POST course search →
    parse CRN list → deduplicate → fetch detail pages for seat counts.

    Term codes: YYYYTT Banner format (e.g., "202710" = Fall 2026)
    - YYYY: 4-digit year
    - TT: Term code (10 = Fall, 13 = Winter, 20 = Spring, 30 = Summer)

    CRITICAL:
    - Validate DB term exists in picker (prefer registerable)
    - Extract CRN from href query (not text split - handles hyphenated titles)
    - Deduplicate by CRN before detail fetches
    - Use bounded concurrency (4) for detail pages
    - Retry with backoff on 429/5xx and transient transport errors
    - Fail loud on any detail fetch failure (no partial success)
    - Never POST registration actions
    - Parse SEPARATE Capacity/Actual/Remaining cells for Seats AND Waitlist Seats
    """

    BASE_URL = "https://selfservice.mypurdue.purdue.edu/prod"
    MAX_TOTAL_REQUESTS = 3000  # Hard budget sized for CS subject (~500-1000 CRNs), not full catalog
    MAX_RETRIES = 3  # Retry count for transient errors
    ALLOWED_DEPARTMENTS = ["CS"]  # Production allowlist: only CS is scraped

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

        # REJECT ALL: Full catalog scraping is not supported (exceeds budget)
        if department.upper() == "ALL":
            raise ValueError(
                f"Purdue scraper does not support department='ALL' (full catalog). "
                f"Full catalog (~21k CRNs) exceeds budget (3000 requests). "
                f"Allowed departments: {', '.join(self.ALLOWED_DEPARTMENTS)}. "
                f"Use a specific department from the allowlist."
            )

        # ENFORCE ALLOWLIST: Only CS is allowed in production
        if department.upper() not in [d.upper() for d in self.ALLOWED_DEPARTMENTS]:
            raise ValueError(
                f"Purdue scraper only supports allowlisted departments: {', '.join(self.ALLOWED_DEPARTMENTS)}. "
                f"Requested department '{department}' is not allowed. "
                f"Full catalog scraping exceeds budget (3000 requests)."
            )

        await self._ensure_client()

        try:
            # CRITICAL: Validate term via picker before scraping
            await self._validate_term_via_picker()

            # Fetch subjects for the term
            subjects = await self._fetch_subjects()
            logger.info(
                f"CARDINALITY: Discovered {len(subjects)} total subjects for term {self.current_term}"
            )

            # Filter by department if not ALL
            if department.upper() != "ALL":
                subjects = [s for s in subjects if s.upper() == department.upper()]
                if not subjects:
                    logger.warning(
                        f"No subject found matching department: {department}"
                    )
                    return []
                logger.info(
                    f"CARDINALITY: Filtered to {len(subjects)} subject(s) for department {department}: {subjects}"
                )

            # Collect all CRN entries from subject searches
            all_crn_entries = []
            listing_requests = 0
            for subject in subjects:
                logger.info(f"Fetching course list for subject: {subject}")
                listing_requests += 1
                crn_entries = await self._fetch_subject_crns(subject)
                all_crn_entries.extend(crn_entries)
                logger.info(
                    f"Subject {subject}: {len(crn_entries)} raw entries "
                    f"(total raw: {len(all_crn_entries)}, listing requests: {listing_requests})"
                )

                # Check request budget after each subject
                if self.total_request_count > self.MAX_TOTAL_REQUESTS:
                    raise PurdueBudgetExceededError(
                        f"Request budget exceeded during listing: {self.total_request_count} > "
                        f"{self.MAX_TOTAL_REQUESTS}. Failing loud, no partial success. "
                        f"CARDINALITY: {len(subjects)} subjects requested, {listing_requests} listing requests, "
                        f"{len(all_crn_entries)} raw entries so far. "
                        f"This is a non-retryable error - reduce scope or increase budget."
                    )

                # Rate limiting between subjects
                await asyncio.sleep(0.2)

            # Deduplicate by CRN before detail fetches
            unique_crns = self._deduplicate_crns(all_crn_entries)
            logger.info(
                f"CARDINALITY: {len(subjects)} subjects, {listing_requests} listing requests, "
                f"{len(all_crn_entries)} raw entries → {len(unique_crns)} unique CRNs"
            )

            # Apply limit before preflight and detail fetches if specified
            limited_crns_count = len(unique_crns)
            if limit and len(unique_crns) > limit:
                unique_crns = unique_crns[:limit]
                limited_crns_count = len(unique_crns)
                logger.info(
                    f"CARDINALITY: Limited to {limited_crns_count} unique CRNs before detail fetches "
                    f"(was {len(unique_crns)} before limit)"
                )

            # Check if detail fetches would exceed budget (worst-case estimate with all retries)
            projected_detail_requests = limited_crns_count * (1 + self.MAX_RETRIES)
            if (
                self.total_request_count + projected_detail_requests
                > self.MAX_TOTAL_REQUESTS
            ):
                raise PurdueBudgetExceededError(
                    f"Request budget would be exceeded by details: "
                    f"{self.total_request_count} + {projected_detail_requests} (projected) > "
                    f"{self.MAX_TOTAL_REQUESTS}. Failing loud, no partial success. "
                    f"CARDINALITY: {len(subjects)} subjects, {listing_requests} listing requests, "
                    f"{len(all_crn_entries)} raw entries, {len(unique_crns)} unique CRNs (before limit), "
                    f"{limited_crns_count} unique CRNs (after limit), "
                    f"{projected_detail_requests} projected detail requests. "
                    f"This is a non-retryable error - reduce scope or increase budget."
                )

            # Fetch detail pages with bounded concurrency and fail-loud on errors
            initial_request_count = self.total_request_count
            courses_data = await self._fetch_details_and_group(unique_crns)
            actual_detail_requests = self.total_request_count - initial_request_count

            logger.info(
                f"Successfully scraped {len(courses_data)} courses from Purdue. "
                f"CARDINALITY: {len(subjects)} subjects, {listing_requests} listing requests, "
                f"{len(all_crn_entries)} raw entries, {len(unique_crns)} unique CRNs, "
                f"{projected_detail_requests} projected detail requests, "
                f"{actual_detail_requests} actual detail requests, "
                f"{self.total_request_count} total requests"
            )
            return courses_data

        except Exception as e:
            logger.error(f"Failed to scrape Purdue {department}: {e}")
            raise
        finally:
            if self.client:
                await self.client.aclose()
                self.client = None

    async def _validate_term_via_picker(self):
        """
        Validate current term by fetching and parsing term picker.
        Ensures DB term exists in picker and is preferably registerable.

        Raises:
            Exception: If term not found in picker or validation fails
        """
        try:
            url = f"{self.BASE_URL}/bwckschd.p_disp_dyn_sched"
            response = await self._make_request_with_retry("GET", url)

            # Parse available terms
            terms = self.parse_term_picker(response.text)
            logger.info(f"Found {len(terms)} terms in picker")

            # Find our term in picker
            term_match = None
            for term in terms:
                if term["code"] == self.current_term:
                    term_match = term
                    break

            if not term_match:
                raise Exception(
                    f"Term {self.current_term} not found in picker. "
                    f"Available terms: {[t['code'] for t in terms[:5]]}"
                )

            if not term_match["registerable"]:
                logger.warning(
                    f"Term {self.current_term} ({term_match['name']}) is marked '(View only)' "
                    "but proceeding as configured in DB"
                )
            else:
                logger.info(
                    f"Term {self.current_term} ({term_match['name']}) validated as registerable"
                )

        except Exception as e:
            logger.error(f"Term validation failed: {e}")
            raise

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
        Fetch available subjects for the current term.

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
            List of dicts with CRN, course_code, title, section, meeting_times info
        """
        try:
            url = f"{self.BASE_URL}/bwckschd.p_get_crse_unsec"

            # Banner multi-select requires dummy seeds before real values
            # Use % for "all" where accepted by Banner
            form_data = {
                "term_in": self.current_term,
                "sel_subj": ["dummy", subject],  # Banner pattern: dummy + value
                "sel_day": "dummy",
                "sel_schd": ["dummy", "%"],  # All schedules
                "sel_insm": ["dummy", "%"],  # All instructional methods
                "sel_camp": ["dummy", "%"],  # All campuses
                "sel_levl": ["dummy", "%"],  # All levels
                "sel_sess": ["dummy", "%"],  # All sessions
                "sel_instr": ["dummy", "%"],  # All instructors
                "sel_ptrm": ["dummy", "%"],  # All parts of term
                "sel_attr": ["dummy", "%"],  # All attributes
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

            # Parse section links and their meeting times
            crn_entries = []

            # Find all course detail links
            for anchor in soup.find_all("a", href=True):
                href = anchor.get("href", "")
                if "bwckschd.p_disp_detail_sched" in href:
                    # Extract CRN from href query parameter (robust)
                    crn = self._extract_crn_from_href(href)
                    if not crn:
                        logger.warning(f"Could not extract CRN from href: {href}")
                        continue

                    # Parse link text robustly: "Title - CRN - SUBJECT NUMBER - SECTION"
                    text = anchor.get_text(strip=True)
                    parsed = self._parse_section_text_robust(text, crn)

                    if parsed:
                        # Parse meeting times for this section
                        meeting_times = self._parse_meeting_times(anchor)
                        parsed["meeting_times"] = meeting_times

                        crn_entries.append(parsed)

            logger.debug(f"Subject {subject}: parsed {len(crn_entries)} CRN entries")
            return crn_entries

        except Exception as e:
            logger.error(f"Error fetching subject CRNs for {subject}: {e}")
            raise

    def _extract_crn_from_href(self, href: str) -> Optional[str]:
        """
        Extract CRN from detail link href query parameter.

        Args:
            href: Link href (e.g., "/prod/bwckschd.p_disp_detail_sched?term_in=202710&crn_in=12345")

        Returns:
            CRN string or None
        """
        # Match crn_in= query parameter
        match = re.search(r"crn_in=(\d+)", href)
        if match:
            return match.group(1)
        return None

    def _parse_section_text_robust(
        self, text: str, crn: str
    ) -> Optional[Dict[str, str]]:
        """
        Parse section link text robustly, handling hyphenated titles.

        Expected format: "Title - CRN - SUBJECT NUMBER - SECTION"
        But title can contain hyphens, so we work backwards from known CRN.

        Args:
            text: Link text
            crn: CRN extracted from href (ground truth)

        Returns:
            Dict with crn, course_code, title, section, or None if parse fails
        """
        # Find CRN position (we know it from href)
        crn_pattern = f" - {re.escape(crn)} - "
        match = re.search(crn_pattern, text)

        if not match:
            logger.warning(
                f"Could not find CRN {crn} in expected format in text: {text}"
            )
            return None

        # Split at CRN position
        title = text[: match.start()].strip()
        remainder = text[match.end() :].strip()

        # Remainder should be "SUBJECT NUMBER - SECTION"
        # Split on last " - " to get section
        parts = remainder.rsplit(" - ", 1)
        if len(parts) == 2:
            course_code = parts[0].strip()
            section = parts[1].strip()
        else:
            # Fallback: take first part as course_code, unknown section
            course_code = remainder.strip()
            section = "001"
            logger.warning(
                f"Could not parse section from remainder '{remainder}', using default"
            )

        return {
            "crn": crn,
            "course_code": course_code,  # e.g., "CS 18000"
            "title": title,
            "section": section,
        }

    def _parse_meeting_times(self, section_anchor) -> List[Dict[str, str]]:
        """
        Parse Scheduled Meeting Times table for a section from listing HTML.

        Looks for the meeting times table following the section anchor and extracts
        structured meeting information.

        Args:
            section_anchor: BeautifulSoup anchor element for the section

        Returns:
            List of meeting time dicts with fields: type, time, days, where,
            date_range, schedule_type, instructors (whatever columns Banner provides)
        """
        meeting_times = []

        try:
            # Navigate to parent row/cell and find the meeting times table
            # Banner typically places meeting info in a table after the course link
            parent_td = section_anchor.find_parent("td")
            if not parent_td:
                return meeting_times

            # Look for "Scheduled Meeting Times" table in the same row or nearby
            # Find the table with caption containing "Scheduled Meeting Times"
            parent_tr = section_anchor.find_parent("tr")
            if parent_tr:
                # Check if next rows contain meeting times table
                for sibling in parent_tr.find_next_siblings("tr", limit=5):
                    table = sibling.find("table", {"class": "datadisplaytable"})
                    if table:
                        caption = table.find("caption")
                        if caption and "Scheduled Meeting Times" in caption.get_text():
                            # Parse the meeting times table
                            meeting_times = self._parse_meeting_times_table(table)
                            break

        except Exception as e:
            logger.debug(f"Could not parse meeting times: {e}")

        return meeting_times

    def _parse_meeting_times_table(self, table) -> List[Dict[str, str]]:
        """
        Parse the Scheduled Meeting Times table rows.

        Args:
            table: BeautifulSoup table element

        Returns:
            List of meeting time dicts with structured fields
        """
        meeting_times = []

        try:
            # Find header row to identify columns
            header_row = table.find("tr")
            if not header_row:
                return meeting_times

            # Extract header names
            headers = []
            for th in header_row.find_all("th"):
                header_text = th.get_text(strip=True)
                headers.append(header_text)

            # Parse data rows
            for row in table.find_all("tr")[1:]:  # Skip header row
                cells = row.find_all("td")
                if len(cells) >= len(headers):
                    meeting = {}
                    for i, header in enumerate(headers):
                        if i < len(cells):
                            cell_text = cells[i].get_text(strip=True)
                            # Normalize header names to snake_case keys
                            key = header.lower().replace(" ", "_")
                            meeting[key] = cell_text

                    if meeting:  # Only add non-empty meetings
                        meeting_times.append(meeting)

        except Exception as e:
            logger.debug(f"Error parsing meeting times table: {e}")

        return meeting_times

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
        self, crn_entries: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Fetch detail pages for CRNs with bounded concurrency and group by course.
        FAIL LOUD on any detail fetch error - no partial success.

        Args:
            crn_entries: List of unique CRN entries (already limited if applicable)

        Returns:
            List of course dictionaries grouped by course_code
        """

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

            # Parse seat availability (main Seats and Waitlist Seats)
            seat_info = self._parse_seat_availability(soup, crn)

            return {
                "class_number": crn,  # CRN is the class_number
                "course_code": crn_entry.get("course_code", ""),
                "title": crn_entry.get("title", ""),
                "section": crn_entry.get("section", ""),
                "status": seat_info["status"],
            }

        except Exception as e:
            logger.error(f"Error fetching detail for CRN {crn}: {e}")
            return None

    def _parse_seat_availability(self, soup: BeautifulSoup, crn: str) -> Dict[str, Any]:
        """
        Parse seat availability from Banner detail page.
        Parses BOTH main Seats and Waitlist Seats with separate Capacity/Actual/Remaining cells.

        Args:
            soup: BeautifulSoup parsed HTML
            crn: CRN for logging

        Returns:
            Dict with 'status' (Open/Closed based on main Seats Remaining)
        """
        status = "Closed"  # Default conservative
        seats_remaining = None
        waitlist_capacity = None
        waitlist_remaining = None

        # Find the Registration Availability table
        for table in soup.find_all("table", {"class": "datadisplaytable"}):
            caption = table.find("caption")
            if not caption or "Registration Availability" not in caption.get_text():
                continue

            # Parse rows for Seats and Waitlist Seats
            rows = table.find_all("tr")

            for row in rows:
                cells = row.find_all(["th", "td"])
                if len(cells) < 4:
                    continue

                # Check first cell for row type
                first_cell_text = cells[0].get_text(strip=True)

                if first_cell_text == "Seats":
                    # Main Seats row: extract Remaining (4th cell)
                    try:
                        seats_remaining = int(cells[3].get_text(strip=True))
                        logger.debug(
                            f"CRN {crn}: Main seats remaining = {seats_remaining}"
                        )
                    except (ValueError, IndexError) as e:
                        logger.warning(
                            f"CRN {crn}: Could not parse main seats remaining: {e}"
                        )

                elif first_cell_text == "Waitlist Seats":
                    # Waitlist Seats row: extract Capacity and Remaining
                    try:
                        waitlist_capacity = int(cells[1].get_text(strip=True))
                        waitlist_remaining = int(cells[3].get_text(strip=True))
                        logger.debug(
                            f"CRN {crn}: Waitlist capacity={waitlist_capacity}, "
                            f"remaining={waitlist_remaining}"
                        )
                    except (ValueError, IndexError) as e:
                        logger.warning(
                            f"CRN {crn}: Could not parse waitlist seats: {e}"
                        )

        # Determine status based on main Seats Remaining (NOT waitlist)
        if seats_remaining is not None:
            status = "Open" if seats_remaining > 0 else "Closed"
            logger.debug(
                f"CRN {crn}: {seats_remaining} main seats remaining → {status}"
            )
        else:
            logger.warning(
                f"CRN {crn}: Could not find main 'Seats' Remaining cell, "
                "defaulting to Closed (never invent Open)"
            )

        # Zero-waitlist capacity is NOT an error - just log for debugging
        if waitlist_capacity == 0:
            logger.debug(
                f"CRN {crn}: Zero waitlist capacity (expected for some courses)"
            )

        return {
            "status": status,
        }

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
                    raise PurdueBudgetExceededError(
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
