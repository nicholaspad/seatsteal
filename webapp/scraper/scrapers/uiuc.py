from typing import List, Dict, Any, Optional
import asyncio
import httpx
from bs4 import BeautifulSoup
from scraper.base import BaseScraper
from scraper.utils.logger import scraper_logger as logger
from scraper.utils.term_code_db import get_term_code_from_db


class UiucScraper(BaseScraper):
    """
    University of Illinois Urbana-Champaign course scraper.

    Scrapes course data from UIUC's Course Explorer XML API.

    Term codes: 6-digit format where:
    - First digit: always 1
    - Next 4 digits: year (e.g., 2026)
    - Last digit: term (0=winter, 1=spring, 5=summer, 8=fall)

    Example: "120261" = Spring 2026
    """

    BASE_API_URL = "https://courses.illinois.edu/cisapp/explorer/schedule"

    # Map term code suffix to season name
    TERM_MAP = {
        "0": "winter",
        "1": "spring",
        "5": "summer",
        "8": "fall",
    }

    def __init__(self, db_session=None):
        super().__init__("uiuc")
        self.client: Optional[httpx.AsyncClient] = None
        self.current_term = get_term_code_from_db(db_session, "uiuc")
        self._parse_term_code()

    def _parse_term_code(self):
        """
        Parse term code into year and season components.

        Expected format: "120261" (6 digits)
        - Digit 1: always 1
        - Digits 2-5: year
        - Digit 6: term (0=winter, 1=spring, 5=summer, 8=fall)
        """
        if len(self.current_term) != 6:
            raise ValueError(
                f"Invalid UIUC term code format: {self.current_term}. "
                f"Expected 6-digit format like '120261' (Spring 2026)"
            )

        self.year = self.current_term[1:5]
        term_suffix = self.current_term[5]

        if term_suffix not in self.TERM_MAP:
            raise ValueError(
                f"Invalid UIUC term suffix: {term_suffix}. "
                f"Expected 0 (winter), 1 (spring), 5 (summer), or 8 (fall)"
            )

        self.season = self.TERM_MAP[term_suffix]
        logger.info(f"Parsed UIUC term code: year={self.year}, season={self.season}")

    async def _ensure_client(self):
        """Ensure HTTP client is initialized"""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=60.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "SeatSteal/1.0",
                    "Accept": "application/xml, text/xml, */*",
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
            if department.upper() == "ALL":
                return await self._fetch_all_subjects(limit)
            else:
                return await self._fetch_subject_courses(department.upper(), limit)

        except Exception as e:
            logger.error(f"Failed to scrape UIUC {department}: {e}")
            raise
        finally:
            if self.client:
                await self.client.aclose()
                self.client = None

    async def _fetch_all_subjects(
        self, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all subjects and their courses.

        Args:
            limit: Optional limit on number of courses per subject

        Returns:
            List of all course dictionaries
        """
        # First, get list of all subjects
        subjects_url = f"{self.BASE_API_URL}/{self.year}/{self.season}.xml"
        logger.info(f"Fetching subjects from: {subjects_url}")

        response = await self.client.get(subjects_url)
        response.raise_for_status()
        self.request_count += 1

        soup = BeautifulSoup(response.text, "xml")
        subjects = []

        for subject_elem in soup.find_all("subject"):
            subject_id = subject_elem.get("id")
            if subject_id:
                subjects.append(subject_id)

        logger.info(f"Found {len(subjects)} subjects to scrape")

        # Scrape subjects concurrently with rate limiting
        max_concurrent = 10
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_subject_with_limit(subject: str) -> List[Dict[str, Any]]:
            async with semaphore:
                logger.info(f"Scraping subject: {subject}")
                courses = await self._fetch_subject_courses(subject, limit)
                logger.info(f"Found {len(courses)} courses for {subject}")
                return courses

        tasks = [fetch_subject_with_limit(subject) for subject in subjects]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_courses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to scrape subject {subjects[i]}: {result}")
            elif result:
                all_courses.extend(result)

        logger.info(f"Scraped total of {len(all_courses)} courses from all subjects")
        return all_courses

    async def _fetch_subject_courses(
        self, subject: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch courses for a specific subject.

        Args:
            subject: Subject code (e.g., 'CS', 'MATH')
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries
        """
        # Get courses for subject
        courses_url = f"{self.BASE_API_URL}/{self.year}/{self.season}/{subject}.xml"
        logger.debug(f"Fetching courses from: {courses_url}")

        response = await self.client.get(courses_url)
        response.raise_for_status()
        self.request_count += 1

        soup = BeautifulSoup(response.text, "xml")
        courses = []

        course_elements = soup.find_all("course")
        if not course_elements:
            logger.warning(f"No courses found for UIUC {subject}")
            return []

        for idx, course_elem in enumerate(course_elements):
            if limit and idx >= limit:
                break

            try:
                course_data = await self._parse_course(subject, course_elem)
                if course_data:
                    courses.append(course_data)
            except Exception as e:
                logger.error(f"Failed to parse course: {e}")
                continue

        return courses

    async def _parse_course(
        self, subject: str, course_elem
    ) -> Optional[Dict[str, Any]]:
        """
        Parse a course element and fetch its sections.

        Args:
            subject: Subject code
            course_elem: BeautifulSoup element for the course

        Returns:
            Course dictionary or None if parsing fails
        """
        course_id = course_elem.get("id")
        course_href = course_elem.get("href")

        if not course_id or not course_href:
            return None

        # Get course title from the element text
        title = course_elem.get_text(strip=True)

        # Build course code
        course_code = f"{subject} {course_id}"

        # Fetch course details to get sections
        try:
            response = await self.client.get(course_href)
            response.raise_for_status()
            self.request_count += 1

            course_soup = BeautifulSoup(response.text, "xml")

            # Get full title from label if available
            label = course_soup.find("label")
            if label:
                title = label.get_text(strip=True)

            # Parse sections
            classes = await self._parse_sections(course_soup)

            if not classes:
                logger.debug(f"Course {course_code} has no valid sections")
                return None

            return {
                "course_code": course_code,
                "title": title,
                "classes": classes,
            }

        except Exception as e:
            logger.warning(f"Error fetching course details for {course_code}: {e}")
            return None

    async def _parse_sections(self, course_soup) -> List[Dict[str, Any]]:
        """
        Parse sections from a course detail page.

        Args:
            course_soup: BeautifulSoup element for the course detail

        Returns:
            List of class dictionaries
        """
        classes = []
        sections = course_soup.find_all("section")

        for section in sections:
            section_id = section.get("id")
            section_href = section.get("href")

            if not section_id or not section_href:
                continue

            # Get section code from the element text
            section_code = section.get_text(strip=True)

            # Fetch section details to get enrollment status
            try:
                response = await self.client.get(section_href)
                response.raise_for_status()
                self.request_count += 1

                section_soup = BeautifulSoup(response.text, "xml")

                # Get enrollment status
                enrollment_elem = section_soup.find("enrollmentStatus")
                status_text = (
                    enrollment_elem.get_text(strip=True) if enrollment_elem else ""
                )

                # Map enrollment status to standard format
                status = self._normalize_enrollment_status(status_text)

                classes.append(
                    {
                        "class_number": section_id,
                        "section": section_code,
                        "status": status,
                    }
                )

                # Brief delay between section requests
                await asyncio.sleep(0.05)

            except Exception as e:
                logger.debug(f"Error fetching section {section_id}: {e}")
                continue

        return classes

    def _normalize_enrollment_status(self, status_text: str) -> str:
        """
        Normalize UIUC enrollment status to standard format.

        UIUC uses various status strings like:
        - "Open"
        - "Closed"
        - "CrossListOpen"
        - "CrossListOpen (Restricted)"
        - "Restricted"
        - "Unknown"

        Args:
            status_text: Raw enrollment status from API

        Returns:
            Normalized status: "Open", "Closed", or "Waitlist"
        """
        status_lower = status_text.lower()

        if "open" in status_lower:
            return "Open"
        elif "closed" in status_lower:
            return "Closed"
        elif "waitlist" in status_lower:
            return "Waitlist"
        elif "restricted" in status_lower:
            # Restricted-only usually means closed to general enrollment
            return "Closed"
        else:
            # Default to Closed for unknown statuses
            logger.debug(f"Unknown UIUC enrollment status: {status_text}")
            return "Closed"
