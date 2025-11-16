from typing import List, Dict, Any, Optional
import asyncio
import httpx
from scraper.base import BaseScraper
from scraper.utils.logger import scraper_logger as logger
from scraper.utils.term_code_db import get_term_code_from_db


class RutgersScraper(BaseScraper):
    """
    Rutgers University course scraper.

    Scrapes course data from Rutgers' public Schedule of Classes API.
    API returns all courses with sections embedded in a single request.

    Term codes: year:term:campus (e.g., "2025:9:NB")
    - Year: 2025
    - Term: 1=Spring, 7=Summer, 9=Fall, 0=Winter
    - Campus: NB=New Brunswick, NK=Newark, CM=Camden
    """

    BASE_API_URL = "https://classes.rutgers.edu/soc/api"

    def __init__(self, db_session=None):
        super().__init__("rutgers")
        self.client: Optional[httpx.AsyncClient] = None
        # Term code format: "year:term:campus" (e.g., "2025:9:NB")
        self.current_term = get_term_code_from_db(db_session, "rutgers")
        self._parse_term_code()

    def _parse_term_code(self):
        """
        Parse term code into year, term, and campus components.

        Expected format: "year:term:campus" (e.g., "2025:9:NB")
        """
        parts = self.current_term.split(":")
        if len(parts) != 3:
            raise ValueError(
                f"Invalid Rutgers term code format: {self.current_term}. "
                f"Expected format: 'year:term:campus' (e.g., '2025:9:NB')"
            )
        self.year = parts[0]
        self.term = parts[1]
        self.campus = parts[2]
        logger.info(
            f"Parsed Rutgers term code: year={self.year}, term={self.term}, campus={self.campus}"
        )

    async def _ensure_client(self):
        """Ensure HTTP client is initialized"""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=60.0,  # Longer timeout for large API response
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip, deflate",
                },
            )

    async def scrape_courses(
        self, department: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape Rutgers courses for a specific department or all courses.

        Args:
            department: Subject code (e.g., '198' for CS) or 'ALL' for all courses
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries with class information
        """
        logger.info(
            f"Scraping Rutgers {department} courses (limit: {limit}, term: {self.current_term})"
        )

        await self._ensure_client()

        try:
            # Fetch all courses from Rutgers API (returns complete data in single request)
            all_courses = await self._fetch_all_courses()

            if department.upper() == "ALL":
                courses_data = self._transform_courses(all_courses, limit)
            else:
                # Filter by subject code
                filtered_courses = [
                    c for c in all_courses if c.get("subject") == department
                ]
                logger.info(
                    f"Filtered {len(filtered_courses)} courses for subject {department}"
                )
                courses_data = self._transform_courses(filtered_courses, limit)

            logger.info(
                f"Successfully scraped {len(courses_data)} courses from Rutgers"
            )
            return courses_data

        except Exception as e:
            logger.error(f"Failed to scrape Rutgers {department}: {e}")
            raise
        finally:
            if self.client:
                await self.client.aclose()
                self.client = None

    async def _fetch_all_courses(self) -> List[Dict[str, Any]]:
        """
        Fetch all courses from Rutgers API.

        Returns:
            List of raw course dictionaries from Rutgers API
        """
        try:
            url = f"{self.BASE_API_URL}/courses.json"
            params = {
                "year": self.year,
                "term": self.term,
                "campus": self.campus,
            }

            logger.info(
                f"Fetching courses from Rutgers API: {url} with params {params}"
            )
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            self.request_count += 1

            courses = response.json()
            logger.info(f"Fetched {len(courses)} courses from Rutgers API")

            return courses

        except Exception as e:
            logger.error(f"Error fetching Rutgers courses: {e}")
            raise

    def _transform_courses(
        self, raw_courses: List[Dict[str, Any]], limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Transform Rutgers API course data to standard format.

        Args:
            raw_courses: List of raw course data from Rutgers API
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries in standard format
        """
        courses_data = []

        for raw_course in raw_courses:
            try:
                course_data = self._transform_single_course(raw_course)
                if course_data and course_data.get("classes"):
                    courses_data.append(course_data)

                # Check limit
                if limit and len(courses_data) >= limit:
                    logger.info(f"Reached course limit of {limit}")
                    break

            except Exception as e:
                logger.warning(
                    f"Error transforming course {raw_course.get('courseString', 'unknown')}: {e}"
                )
                continue

        return courses_data

    def _transform_single_course(
        self, raw_course: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Transform a single Rutgers course to standard format.

        Args:
            raw_course: Raw course data from Rutgers API

        Returns:
            Transformed course dictionary or None if invalid
        """
        try:
            # Build course code from Rutgers format: "school:subject:courseNumber"
            # e.g., "01:013:111" -> "01:013:111" or we can simplify
            course_string = raw_course.get("courseString", "")
            title = raw_course.get("title", "").strip()

            if not course_string:
                logger.warning("Skipping course with missing courseString")
                return None

            # Extract sections
            sections = raw_course.get("sections", [])
            if not sections:
                logger.debug(f"Course {course_string} has no sections")
                return None

            # Transform sections to classes
            classes = []
            for section in sections:
                class_data = self._transform_section(section)
                if class_data:
                    classes.append(class_data)

            if not classes:
                logger.debug(f"Course {course_string} has no valid sections")
                return None

            return {
                "course_code": course_string,
                "title": title,
                "classes": classes,
            }

        except Exception as e:
            logger.warning(f"Error transforming single course: {e}")
            return None

    def _transform_section(self, section: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Transform a Rutgers section to standard class format.

        Args:
            section: Section data from Rutgers API

        Returns:
            Class dictionary or None if invalid
        """
        try:
            # Section index is the unique identifier (registration index)
            section_index = section.get("index", "")
            section_number = section.get("number", "")

            if not section_index:
                logger.warning("Skipping section with missing index")
                return None

            # Determine status from openStatus boolean
            is_open = section.get("openStatus", False)
            status = "open" if is_open else "closed"

            return {
                "class_number": section_index,
                "section": section_number,
                "status": status,
            }

        except Exception as e:
            logger.warning(f"Error transforming section: {e}")
            return None
