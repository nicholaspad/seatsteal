from typing import List, Dict, Any, Optional
import httpx
from scraper.base import BaseScraper
from scraper.utils.logger import scraper_logger as logger
from scraper.utils.term_code_db import get_term_code_from_db


class OsuScraper(BaseScraper):
    """
    Ohio State University course scraper.

    Scrapes course data from the OSU Content API.
    API returns paginated courses (200 per page).

    Term codes: YYSN format (e.g., "1262" = Spring 2026)
    - YY: year minus 2000 (26 = 2026)
    - S: season indicator (2 = Spring)
    - N: unknown digit
    """

    BASE_API_URL = "https://content.osu.edu/v2/classes/search"

    def __init__(self, db_session=None):
        super().__init__("osu")
        self.client: Optional[httpx.AsyncClient] = None
        # Term code format: "YYSN" (e.g., "1262")
        self.current_term = get_term_code_from_db(db_session, "osu")
        logger.info(f"Initialized OSU scraper with term: {self.current_term}")

    async def _ensure_client(self):
        """Ensure HTTP client is initialized"""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "SeatSteal/1.0",
                    "Accept": "application/json",
                },
            )

    async def scrape_courses(
        self, department: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape OSU courses for a specific department or all courses.

        Args:
            department: Department code (e.g., 'CSE', 'MATH') or 'ALL' for all courses
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries with class information
        """
        logger.info(
            f"Scraping OSU {department} courses (limit: {limit}, term: {self.current_term})"
        )

        await self._ensure_client()

        try:
            # Fetch courses from OSU API (paginated)
            if department.upper() == "ALL":
                raw_courses = await self._fetch_all_courses(limit)
            else:
                raw_courses = await self._fetch_department_courses(department, limit)

            # Transform API response to standard format
            courses_data = self._transform_courses(raw_courses)

            logger.info(f"Successfully scraped {len(courses_data)} courses from OSU")
            return courses_data

        except Exception as e:
            logger.error(f"Failed to scrape OSU {department}: {e}")
            raise
        finally:
            if self.client:
                await self.client.aclose()
                self.client = None

    async def _fetch_all_courses(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch all courses from OSU API (paginated).

        Args:
            limit: Optional limit on number of courses

        Returns:
            List of raw course data
        """
        all_courses = []
        page = 1
        
        logger.info(f"Fetching all OSU courses (limit: {limit})")

        while True:
            params = {
                "q": "",  # Empty query returns all courses
                "campus": "col",  # Columbus campus
                "term": self.current_term,
                "p": str(page),
            }

            logger.info(f"Fetching OSU page {page}")
            response_data = await self._make_api_request(params)
            
            courses = response_data.get("data", {}).get("courses", [])
            
            if not courses:
                logger.info(f"No more courses found at page {page}")
                break
            
            all_courses.extend(courses)
            logger.info(f"Fetched {len(courses)} courses from page {page} (total: {len(all_courses)})")
            
            # Check if we've hit the limit
            if limit and len(all_courses) >= limit:
                logger.info(f"Reached course limit of {limit}")
                all_courses = all_courses[:limit]
                break
            
            # Check if there are more pages
            # OSU API returns ~200 courses per page
            if len(courses) < 200:
                logger.info(f"Last page reached (only {len(courses)} courses)")
                break
            
            page += 1

        logger.info(f"Fetched total of {len(all_courses)} courses from OSU")
        return all_courses

    async def _fetch_department_courses(
        self, department: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch courses for a specific department from OSU API.

        Args:
            department: Department code (e.g., 'CSE')
            limit: Optional limit on number of courses

        Returns:
            List of raw course data
        """
        all_courses = []
        page = 1

        logger.info(f"Fetching OSU {department} courses")

        while True:
            params = {
                "q": department,
                "campus": "col",
                "term": self.current_term,
                "p": str(page),
            }

            logger.info(f"Fetching OSU {department} page {page}")
            response_data = await self._make_api_request(params)
            
            courses = response_data.get("data", {}).get("courses", [])
            
            if not courses:
                logger.info(f"No more courses found for {department} at page {page}")
                break
            
            all_courses.extend(courses)
            logger.info(
                f"Fetched {len(courses)} courses from {department} page {page} "
                f"(total: {len(all_courses)})"
            )
            
            # Check if we've hit the limit
            if limit and len(all_courses) >= limit:
                logger.info(f"Reached course limit of {limit}")
                all_courses = all_courses[:limit]
                break
            
            # Check if there are more pages
            if len(courses) < 200:
                logger.info(f"Last page reached (only {len(courses)} courses)")
                break
            
            page += 1

        logger.info(f"Fetched total of {len(all_courses)} courses for {department}")
        return all_courses

    async def _make_api_request(self, params: Dict[str, str]) -> Dict[str, Any]:
        """
        Make an API request to the OSU Content API.

        Args:
            params: Query parameters

        Returns:
            API response data

        Raises:
            Exception: If API request fails
        """
        try:
            response = await self.client.get(self.BASE_API_URL, params=params)
            response.raise_for_status()
            self.request_count += 1

            data = self.decode_json_response(response)
            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching OSU courses: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching OSU courses: {e}")
            raise

    def _transform_courses(self, raw_courses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform OSU API course data to standard format.

        Args:
            raw_courses: List of raw course data from API

        Returns:
            List of course dictionaries in standard format
        """
        courses_data = []

        for raw_course in raw_courses:
            try:
                course_data = self._transform_single_course(raw_course)
                if course_data and course_data.get("classes"):
                    courses_data.append(course_data)
            except Exception as e:
                course_id = raw_course.get("course", {}).get("code", "unknown")
                logger.warning(f"Error transforming course {course_id}: {e}")
                continue

        # Deduplicate courses with the same course_code
        courses_data = self._deduplicate_courses(courses_data)

        return courses_data
    
    def _deduplicate_courses(
        self, courses: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Deduplicate courses with the same course_code by merging their sections.

        OSU API can return duplicate course codes representing different course
        offerings with separate sections. This method merges them into a single
        course entry with all sections combined.

        Args:
            courses: List of course dictionaries

        Returns:
            Deduplicated list of course dictionaries
        """
        from typing import Dict as TypeDict
        
        # Group courses by course_code
        course_map: TypeDict[str, List[Dict[str, Any]]] = {}
        for course in courses:
            course_code = course.get("course_code", "")
            if course_code not in course_map:
                course_map[course_code] = []
            course_map[course_code].append(course)

        # Merge duplicates
        deduplicated = []
        duplicates_found = 0

        for course_code, course_list in course_map.items():
            if len(course_list) == 1:
                # No duplicates, keep as-is
                deduplicated.append(course_list[0])
            else:
                # Merge duplicate courses
                duplicates_found += len(course_list) - 1
                logger.info(
                    f"Merging {len(course_list)} duplicate courses with code {course_code}"
                )

                # Combine all classes from all duplicate courses
                all_classes = []
                titles = []
                for course in course_list:
                    all_classes.extend(course.get("classes", []))
                    titles.append(course.get("title", ""))

                # Choose the longest/most descriptive title
                best_title = max(titles, key=len) if titles else ""

                # Deduplicate classes by class_number (keep first occurrence)
                seen_class_numbers = set()
                unique_classes = []
                for cls in all_classes:
                    class_number = cls.get("class_number")
                    if class_number not in seen_class_numbers:
                        seen_class_numbers.add(class_number)
                        unique_classes.append(cls)

                # Create merged course
                merged_course = {
                    "course_code": course_code,
                    "title": best_title,
                    "classes": unique_classes,
                }
                deduplicated.append(merged_course)

        if duplicates_found > 0:
            logger.info(
                f"Deduplicated {duplicates_found} duplicate courses "
                f"({len(courses)} -> {len(deduplicated)} unique courses)"
            )

        return deduplicated

    def _transform_single_course(
        self, raw_course: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Transform a single OSU course to standard format.

        Args:
            raw_course: Raw course data from API

        Returns:
            Transformed course dictionary or None if invalid
        """
        try:
            course_info = raw_course.get("course", {})
            
            # Get course code (e.g., "ACCTMIS 3400")
            # OSU API provides subject and catalogNumber separately
            subject = course_info.get("subject", "").strip()
            catalog_number = course_info.get("catalogNumber", "").strip()
            
            if not subject or not catalog_number:
                logger.warning(f"Skipping course with missing subject or catalog number: {course_info}")
                return None
                
            course_code = f"{subject} {catalog_number}"

            # Get title
            title = course_info.get("title", "").strip()

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
        Transform an OSU section to standard class format.

        Args:
            section: Section data from API

        Returns:
            Class dictionary or None if invalid
        """
        try:
            # Get section number (unique identifier)
            section_number = section.get("section", "")
            if not section_number:
                logger.warning("Skipping section with missing section number")
                return None

            # Get enrollment status
            enrollment_status = section.get("enrollmentStatus", "").strip()
            
            # Map status to standard format
            if enrollment_status.lower() == "open":
                status = "Open"
            elif enrollment_status.lower() == "closed":
                status = "Closed"
            else:
                # Default to Closed for unknown statuses
                status = "Closed"
                logger.debug(
                    f"Unknown enrollment status '{enrollment_status}' for section {section_number}"
                )

            return {
                "class_number": str(section_number),
                "section": str(section_number),
                "status": status,
            }

        except Exception as e:
            logger.warning(f"Error transforming section: {e}")
            return None
