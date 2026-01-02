from typing import List, Dict, Any, Optional
import httpx
from scraper.base import BaseScraper
from scraper.utils.logger import scraper_logger as logger
from scraper.utils.term_code_db import get_term_code_from_db


class UciScraper(BaseScraper):
    """
    UC Irvine course scraper.

    Scrapes course data from the Anteater API (community JSON REST API for UCI WebSoc).
    API returns all courses with sections in a single request.

    Term codes: year:quarter (e.g., "2026:Spring")
    - Year: 4-digit year
    - Quarter: Fall, Winter, Spring, Summer1, Summer10wk, Summer2
    """

    BASE_API_URL = "https://anteaterapi.com/v2/rest/websoc"

    def __init__(self, db_session=None):
        super().__init__("uci")
        self.client: Optional[httpx.AsyncClient] = None
        # Term code format: "year:quarter" (e.g., "2026:Spring")
        self.current_term = get_term_code_from_db(db_session, "uci")
        self._parse_term_code()

    def _parse_term_code(self):
        """
        Parse term code into year and quarter components.

        Expected format: "year:quarter" (e.g., "2026:Spring")
        """
        parts = self.current_term.split(":")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid UCI term code format: {self.current_term}. "
                f"Expected format: 'year:quarter' (e.g., '2026:Spring')"
            )
        self.year = parts[0]
        self.quarter = parts[1]
        logger.info(f"Parsed UCI term code: year={self.year}, quarter={self.quarter}")

    async def _ensure_client(self):
        """Ensure HTTP client is initialized"""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=120.0,  # Longer timeout for large API response
                follow_redirects=True,
                headers={
                    "User-Agent": "SeatSteal/1.0",
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip, deflate, br",
                },
            )

    async def scrape_courses(
        self, department: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape UCI courses for a specific department or all courses.

        Args:
            department: Department code (e.g., 'COMPSCI', 'MATH') or 'ALL' for all courses
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries with class information
        """
        logger.info(
            f"Scraping UCI {department} courses (limit: {limit}, term: {self.current_term})"
        )

        await self._ensure_client()

        try:
            # Fetch courses from Anteater API
            if department.upper() == "ALL":
                raw_data = await self._fetch_all_courses()
            else:
                raw_data = await self._fetch_department_courses(department)

            # Transform API response to standard format
            courses_data = self._transform_courses(raw_data, limit)

            logger.info(f"Successfully scraped {len(courses_data)} courses from UCI")
            return courses_data

        except Exception as e:
            logger.error(f"Failed to scrape UCI {department}: {e}")
            raise
        finally:
            if self.client:
                await self.client.aclose()
                self.client = None

    async def _fetch_all_courses(self) -> Dict[str, Any]:
        """
        Fetch all courses from Anteater API.

        Returns:
            Raw API response data
        """
        params = {
            "year": self.year,
            "quarter": self.quarter,
        }

        logger.info(f"Fetching all UCI courses with params: {params}")
        return await self._make_api_request(params)

    async def _fetch_department_courses(self, department: str) -> Dict[str, Any]:
        """
        Fetch courses for a specific department from Anteater API.

        Args:
            department: Department code (e.g., 'COMPSCI')

        Returns:
            Raw API response data
        """
        params = {
            "year": self.year,
            "quarter": self.quarter,
            "department": department,
        }

        logger.info(f"Fetching UCI {department} courses with params: {params}")
        return await self._make_api_request(params)

    async def _make_api_request(self, params: Dict[str, str]) -> Dict[str, Any]:
        """
        Make an API request to the Anteater API.

        Args:
            params: Query parameters

        Returns:
            API response data

        Raises:
            Exception: If API request fails or returns error
        """
        try:
            response = await self.client.get(self.BASE_API_URL, params=params)
            response.raise_for_status()
            self.request_count += 1

            data = response.json()

            if not data.get("ok"):
                error_msg = data.get("message", "Unknown API error")
                raise Exception(f"Anteater API error: {error_msg}")

            return data.get("data", {})

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching UCI courses: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching UCI courses: {e}")
            raise

    def _transform_courses(
        self, raw_data: Dict[str, Any], limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Transform Anteater API course data to standard format.

        UCI has "variable topic" courses where the same course code (e.g., "ECO EVO 200B")
        can have different topics/titles. We aggregate all sections under the same course_code
        to avoid duplicate key errors in the database.

        Args:
            raw_data: Raw API response data
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries in standard format
        """
        # Use a dict to aggregate courses by course_code
        courses_by_code: Dict[str, Dict[str, Any]] = {}
        schools = raw_data.get("schools", [])

        for school in schools:
            departments = school.get("departments", [])

            for department in departments:
                courses = department.get("courses", [])

                for raw_course in courses:
                    try:
                        course_data = self._transform_single_course(raw_course)
                        if course_data and course_data.get("classes"):
                            course_code = course_data["course_code"]

                            if course_code in courses_by_code:
                                # Aggregate sections from duplicate course codes
                                courses_by_code[course_code]["classes"].extend(
                                    course_data["classes"]
                                )
                            else:
                                courses_by_code[course_code] = course_data

                                # Check limit (only count unique courses)
                                if limit and len(courses_by_code) >= limit:
                                    logger.info(f"Reached course limit of {limit}")
                                    return list(courses_by_code.values())

                    except Exception as e:
                        course_id = f"{raw_course.get('deptCode', '')} {raw_course.get('courseNumber', '')}"
                        logger.warning(f"Error transforming course {course_id}: {e}")
                        continue

        return list(courses_by_code.values())

    def _transform_single_course(
        self, raw_course: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Transform a single UCI course to standard format.

        Args:
            raw_course: Raw course data from API

        Returns:
            Transformed course dictionary or None if invalid
        """
        try:
            dept_code = raw_course.get("deptCode", "").strip()
            course_number = raw_course.get("courseNumber", "").strip()
            title = raw_course.get("courseTitle", "").strip()

            if not dept_code or not course_number:
                logger.warning("Skipping course with missing dept or number")
                return None

            # Build course code: "COMPSCI 161"
            course_code = f"{dept_code} {course_number}"

            # Transform sections to classes
            sections = raw_course.get("sections", [])
            classes = []

            for section in sections:
                class_data = self._transform_section(section)
                if class_data:
                    classes.append(class_data)

            if not classes:
                logger.debug(f"Course {course_code} has no valid sections")
                return None

            return {
                "course_code": course_code,
                "title": title,
                "classes": classes,
            }

        except Exception as e:
            logger.warning(f"Error transforming single course: {e}")
            return None

    def _transform_section(self, section: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Transform a UCI section to standard class format.

        Args:
            section: Section data from API

        Returns:
            Class dictionary or None if invalid
        """
        try:
            # Section code is the unique identifier (CRN equivalent)
            section_code = section.get("sectionCode", "")
            section_type = section.get("sectionType", "")
            section_num = section.get("sectionNum", "")

            if not section_code:
                logger.warning("Skipping section with missing sectionCode")
                return None

            # Build section string: "Lec A" or "Dis 1"
            section_str = f"{section_type} {section_num}".strip()

            # Map status to standard format
            raw_status = section.get("status", "").upper()
            if raw_status == "OPEN":
                status = "Open"
            elif raw_status == "FULL":
                status = "Closed"
            elif raw_status in ("WAITL", "WAITLIST"):
                status = "Waitlist"
            elif raw_status == "NEWONLY":
                status = "Open"  # NewOnly means open for new students
            else:
                # Default to Closed for unknown statuses
                status = "Closed"
                logger.debug(
                    f"Unknown status '{raw_status}' for section {section_code}"
                )

            return {
                "class_number": section_code,
                "section": section_str,
                "status": status,
            }

        except Exception as e:
            logger.warning(f"Error transforming section: {e}")
            return None
