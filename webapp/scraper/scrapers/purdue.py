from typing import List, Dict, Any, Optional, Set
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
    - TT: Term code (10 = Fall, 20 = Spring, 30 = Summer)

    CRITICAL: 
    - Deduplicate by CRN before detail fetches
    - Use bounded concurrency (2-4) for detail pages
    - Never POST registration actions
    - Fail loud if request budget exceeded (no fake-success partial)
    """

    BASE_URL = "https://selfservice.mypurdue.purdue.edu/prod"
    MAX_DETAIL_REQUESTS = 2000  # Hard budget to prevent runaway requests

    def __init__(self, db_session=None):
        super().__init__("purdue")
        self.client: Optional[httpx.AsyncClient] = None
        self.current_term = get_term_code_from_db(db_session, "purdue")
        self.detail_request_count = 0
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

                # Rate limiting between subjects
                await asyncio.sleep(0.2)

            # Deduplicate by CRN before detail fetches
            unique_crns = self._deduplicate_crns(all_crn_entries)
            logger.info(
                f"Deduplicated: {len(all_crn_entries)} sections → {len(unique_crns)} unique CRNs"
            )

            # Check request budget
            if len(unique_crns) > self.MAX_DETAIL_REQUESTS:
                raise Exception(
                    f"Request budget exceeded: {len(unique_crns)} CRNs > "
                    f"{self.MAX_DETAIL_REQUESTS} max (failing loud, no partial success)"
                )

            # Fetch detail pages with bounded concurrency
            courses_data = await self._fetch_details_and_group(unique_crns, limit)

            logger.info(
                f"Successfully scraped {len(courses_data)} courses from Purdue "
                f"({len(unique_crns)} sections processed)"
            )
            return courses_data

        except Exception as e:
            logger.error(f"Failed to scrape Purdue {department}: {e}")
            raise
        finally:
            if self.client:
                await self.client.aclose()
                self.client = None

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

            response = await self.client.post(
                url,
                data=form_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            self.request_count += 1

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

            response = await self.client.post(
                url,
                data=form_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            self.request_count += 1

            soup = BeautifulSoup(response.content, "lxml")

            # Parse section anchors: "Title - CRN - SUBJECT NUMBER - SECTION"
            crn_entries = []
            
            # Find all course title links
            for anchor in soup.find_all("a"):
                onclick = anchor.get("onclick", "")
                if "bwckschd.p_disp_detail_sched" in onclick:
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
                        
                        crn_entries.append({
                            "crn": crn,
                            "course_code": subject_number,  # e.g., "CS 18000"
                            "title": title,
                            "section": section,
                        })

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
        
        for i in range(0, len(crn_entries), batch_size):
            batch = crn_entries[i : i + batch_size]
            batch_tasks = [fetch_with_semaphore(entry) for entry in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.warning(f"Detail fetch failed: {result}")
                elif result:
                    all_classes.append(result)
            
            logger.info(
                f"Progress: {min(i + batch_size, len(crn_entries))}/{len(crn_entries)} "
                f"details fetched"
            )
            
            # Rate limiting between batches
            if i + batch_size < len(crn_entries):
                await asyncio.sleep(0.3)

        logger.info(f"Fetched {len(all_classes)} class details")

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

        Args:
            crn_entry: Dict with crn, course_code, title, section

        Returns:
            Dict with class data including status (Open/Closed)
        """
        try:
            crn = crn_entry.get("crn", "")
            if not crn:
                return None

            # Check request budget
            self.detail_request_count += 1
            if self.detail_request_count > self.MAX_DETAIL_REQUESTS:
                raise Exception(
                    f"Detail request budget exceeded: {self.detail_request_count} > "
                    f"{self.MAX_DETAIL_REQUESTS}"
                )

            url = f"{self.BASE_URL}/bwckschd.p_disp_detail_sched"
            params = {
                "term_in": self.current_term,
                "crn_in": crn,
            }

            response = await self.client.get(url, params=params)
            response.raise_for_status()
            self.request_count += 1

            soup = BeautifulSoup(response.content, "lxml")

            # Parse "Registration Availability" section for remaining seats
            status = "Closed"  # Default conservative
            
            # Find the table with caption "Registration Availability"
            for table in soup.find_all("table", {"class": "datadisplaytable"}):
                caption = table.find("caption")
                if caption and "Registration Availability" in caption.get_text():
                    # Look for "Seats" row (header in th, data in td)
                    for row in table.find_all("tr"):
                        # Check for header cells
                        headers = row.find_all("th")
                        data_cells = row.find_all("td")
                        
                        # Try th/td pattern first
                        if len(headers) >= 1 and len(data_cells) >= 1:
                            label = headers[0].get_text(strip=True)
                            value = data_cells[0].get_text(strip=True)
                            
                            if label == "Seats":
                                # Parse remaining seats (format: "Capacity: X, Actual: Y, Remaining: Z")
                                remaining_text = value.split("Remaining:")
                                if len(remaining_text) > 1:
                                    try:
                                        remaining = int(remaining_text[1].strip())
                                        status = "Open" if remaining > 0 else "Closed"
                                        logger.debug(
                                            f"CRN {crn}: {remaining} remaining seats → {status}"
                                        )
                                    except (ValueError, IndexError):
                                        logger.warning(
                                            f"CRN {crn}: Could not parse remaining seats from '{value}'"
                                        )
                        # Also try td/td pattern as fallback
                        elif len(data_cells) >= 2:
                            label = data_cells[0].get_text(strip=True)
                            value = data_cells[1].get_text(strip=True)
                            
                            if label == "Seats":
                                # Parse remaining seats (format: "Capacity: X, Actual: Y, Remaining: Z")
                                remaining_text = value.split("Remaining:")
                                if len(remaining_text) > 1:
                                    try:
                                        remaining = int(remaining_text[1].strip())
                                        status = "Open" if remaining > 0 else "Closed"
                                        logger.debug(
                                            f"CRN {crn}: {remaining} remaining seats → {status}"
                                        )
                                    except (ValueError, IndexError):
                                        logger.warning(
                                            f"CRN {crn}: Could not parse remaining seats from '{value}'"
                                        )

            if status == "Closed" and "Remaining:" not in str(soup):
                logger.warning(
                    f"CRN {crn}: No 'Remaining' text found, assuming Closed (never invent Open)"
                )

            return {
                "class_number": crn,  # CRN is the class_number
                "course_code": crn_entry.get("course_code", ""),
                "title": crn_entry.get("title", ""),
                "section": crn_entry.get("section", ""),
                "status": status,
            }

        except Exception as e:
            logger.warning(f"Error fetching detail for CRN {crn_entry.get('crn')}: {e}")
            return None
