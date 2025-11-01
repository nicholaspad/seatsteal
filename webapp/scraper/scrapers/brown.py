from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import asyncio
import json
from urllib.parse import quote
import httpx
from scraper.base import BaseScraper
from scraper.utils.logger import scraper_logger as logger
from scraper.utils.term_code_db import get_term_code_from_db


class BrownScraper(BaseScraper):
    """
    Brown University course scraper.

    Scrapes course data from Brown's Courses@Brown system (CAB) using their API.
    Migrated from working TypeScript implementation.
    """

    BASE_URL = "https://cab.brown.edu"
    COURSE_SEARCH_URL = (
        "https://cab.brown.edu/api/?page=fose&route=search&is_ind_study=N&is_canc=N"
    )
    CLASS_DETAILS_URL = "https://cab.brown.edu/api/?page=fose&route=details"

    def __init__(self, db_session=None):
        super().__init__("brown")
        self.current_term = get_term_code_from_db(db_session, "brown")
        self.client: Optional[httpx.AsyncClient] = None

    async def _ensure_client(self):
        """Ensure HTTP client is initialized"""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "Cache-Control": "no-cache",
                    "X-Requested-With": "XMLHttpRequest",
                },
            )

    async def scrape_courses(
        self, department: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape Brown courses for a specific department or all courses.

        Args:
            department: Department code (e.g., 'CSCI', 'MATH', 'ENGL') or 'ALL' for all courses
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries with class information
        """
        logger.info(
            f"Scraping Brown {department} courses (limit: {limit}, term: {self.current_term})"
        )

        await self._ensure_client()

        try:
            if department.upper() == "ALL":
                return await self._fetch_all_courses(limit)
            else:
                return await self._fetch_subject_courses(department, limit)

        except Exception as e:
            logger.error(f"Failed to scrape Brown {department}: {e}")
            raise
        finally:
            if self.client:
                await self.client.aclose()
                self.client = None

    async def _fetch_all_courses(
        self, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all courses from Brown's API.

        Args:
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries
        """
        try:
            # Step 1: Get all courses from the search API
            courses = await self._fetch_course_list()
            logger.info(f"Found {len(courses)} courses from Brown API")

            if not courses:
                logger.warning("No courses found via Brown API")
                return []

            # Apply limit if specified
            if limit:
                courses = courses[:limit]

            # Step 2: Process courses in batches to get class details
            all_course_data = []
            batch_size = 100  # Process 100 courses concurrently

            for i in range(0, len(courses), batch_size):
                batch = courses[i : i + batch_size]
                logger.info(
                    f"Processing course batch {i // batch_size + 1}/{(len(courses) + batch_size - 1) // batch_size} ({len(batch)} courses)"
                )

                # Process batch concurrently
                tasks = [self._fetch_course_classes(course) for course in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.warning(f"Course fetch failed: {result}")
                    elif result:
                        all_course_data.append(result)

                # Add delay between batches
                if i + batch_size < len(courses):
                    await asyncio.sleep(1)

            logger.info(f"Successfully processed {len(all_course_data)} courses")

            # Deduplicate courses and merge classes
            deduplicated = self._deduplicate_courses(all_course_data)
            logger.info(f"Deduplicated to {len(deduplicated)} unique courses")
            return deduplicated

        except Exception as e:
            logger.error(f"Error during Brown API course fetch: {e}")
            raise

    async def _fetch_subject_courses(
        self, subject: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch courses for a specific subject.

        Args:
            subject: Subject code (e.g., 'CSCI')
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries
        """
        try:
            # Get all courses and filter by subject
            all_courses = await self._fetch_course_list()
            logger.info(
                f"Found {len(all_courses)} total courses, filtering for {subject}"
            )

            # Filter courses by subject
            subject_courses = [
                course for course in all_courses if course["code"].startswith(subject)
            ]
            logger.info(f"Found {len(subject_courses)} courses for {subject}")

            # Apply limit if specified
            if limit:
                subject_courses = subject_courses[:limit]

            # Fetch class details for filtered courses
            all_course_data = []
            batch_size = 10

            for i in range(0, len(subject_courses), batch_size):
                batch = subject_courses[i : i + batch_size]

                tasks = [self._fetch_course_classes(course) for course in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.warning(f"Course fetch failed: {result}")
                    elif result:
                        all_course_data.append(result)

                # Add delay between batches
                if i + batch_size < len(subject_courses):
                    await asyncio.sleep(0.5)

            logger.info(
                f"Successfully processed {len(all_course_data)} courses for {subject}"
            )

            # Deduplicate courses and merge classes
            deduplicated = self._deduplicate_courses(all_course_data)
            logger.info(
                f"Deduplicated to {len(deduplicated)} unique courses for {subject}"
            )
            return deduplicated

        except Exception as e:
            logger.error(f"Error fetching subject {subject}: {e}")
            raise

    async def _fetch_course_list(self) -> List[Dict[str, Any]]:
        """
        Fetch the list of all courses from Brown's API.

        Returns:
            List of course dictionaries from API
        """
        try:
            logger.debug(f"Fetching course list from: {self.COURSE_SEARCH_URL}")

            request_body = {
                "other": {"srcdb": self.current_term},
                "criteria": [
                    {"field": "is_ind_study", "value": "N"},
                    {"field": "is_canc", "value": "N"},
                ],
            }

            response_data = await self._make_api_request(
                self.COURSE_SEARCH_URL, request_body
            )

            if not response_data or "results" not in response_data:
                raise ValueError("Invalid response format from course search API")

            courses = response_data["results"]
            logger.info(f"Successfully fetched {len(courses)} courses")
            return courses

        except Exception as e:
            logger.error(f"Error fetching course list: {e}")
            raise

    async def _fetch_course_classes(
        self, course: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Extract class information from course data.

        Brown's search API includes all necessary class information,
        so we don't need to make separate detail API calls.

        Args:
            course: Course dictionary from search API

        Returns:
            Course dictionary with classes
        """
        try:
            classes = []

            # Main class from the course CRN
            main_class = self._transform_course_to_class(course)
            if main_class:
                classes.append(main_class)

            # Linked CRNs (additional sections/labs)
            if course.get("linked_crns"):
                # Linked CRNs would need separate detail calls, but for now
                # we'll just use the main class since the details API seems unreliable
                pass

            return {
                "course_code": course["code"],
                "title": course["title"],
                "classes": classes,
            }

        except Exception as e:
            logger.error(f"Error fetching classes for course {course.get('code')}: {e}")
            return None

    async def _fetch_class_details(self, crn: str) -> Optional[Dict[str, Any]]:
        """
        Fetch details for a specific class by CRN.

        Args:
            crn: Course Reference Number

        Returns:
            Class details dictionary
        """
        try:
            request_body = {"key": f"crn:{crn}"}

            response_data = await self._make_api_request(
                self.CLASS_DETAILS_URL, request_body
            )

            if not response_data:
                logger.warning(f"No details found for CRN {crn}")
                return None

            return {
                "crn": response_data.get("crn", crn),
                "section": response_data.get("section")
                or response_data.get("no")
                or "S01",
                "seats": response_data.get("seats", ""),
                "code": response_data.get("code", ""),
                "title": response_data.get("title", ""),
            }

        except Exception as e:
            logger.error(f"Error fetching class details for CRN {crn}: {e}")
            return None

    def _transform_course_to_class(
        self, course: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Transform course data from search API into class dictionary format.

        Brown's search API includes class information in the course object.

        Args:
            course: Course dictionary from search API

        Returns:
            Class dictionary or None if invalid data
        """
        try:
            crn = course.get("crn", "")
            section = course.get("no", "S01")  # 'no' field contains section number
            status_code = course.get("stat", "")  # Status code from API

            # Validate required fields
            if not crn or not crn.strip():
                logger.warning(
                    f"Skipping class with empty CRN for course {course.get('code')}"
                )
                return None

            # Map status code to enrollment status
            # Common Brown status codes:
            # 'A' = Active/Available
            # 'C' = Closed
            # 'X' = Cancelled
            enrollment_status = self._map_status_code(status_code)

            return {
                "class_number": crn,
                "section": section,
                "status": enrollment_status,
            }

        except Exception as e:
            logger.error(f"Error transforming class data: {e}")
            return None

    def _transform_to_class_dict(
        self, course: Dict[str, Any], class_details: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Transform API response into class dictionary format.

        Args:
            course: Course dictionary from API
            class_details: Class details from API

        Returns:
            Class dictionary or None if invalid data
        """
        try:
            crn = class_details.get("crn", "")
            section = class_details.get("section", "")

            # Validate required fields
            if not crn or not crn.strip():
                logger.warning(
                    f"Skipping class with empty CRN for course {course.get('code')}"
                )
                return None

            # Parse enrollment status from seats HTML
            enrollment_status = self._parse_enrollment_status(
                class_details.get("seats", "")
            )

            return {
                "class_number": crn,
                "section": section,
                "status": enrollment_status,
            }

        except Exception as e:
            logger.error(f"Error transforming class data: {e}")
            return None

    def _map_status_code(self, status_code: str) -> str:
        """
        Map Brown's status codes to standard enrollment status.

        Args:
            status_code: Status code from Brown API

        Returns:
            Status: 'Open', 'Closed', or 'Unknown'
        """
        status_code_upper = status_code.upper().strip()

        if status_code_upper == "A":  # Active/Available
            return "Open"
        elif status_code_upper == "C":  # Closed
            return "Closed"
        elif status_code_upper == "X":  # Cancelled
            return "Closed"
        else:
            return "Unknown"

    def _deduplicate_courses(
        self, courses_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Deduplicate courses by course_code and merge their classes.

        Brown API returns separate entries for each section of a course,
        so we need to merge them into a single course with multiple classes.

        Args:
            courses_data: List of course dictionaries (may contain duplicates)

        Returns:
            List of deduplicated course dictionaries with merged classes
        """
        course_dict = {}

        for course_data in courses_data:
            course_code = course_data["course_code"]

            if course_code not in course_dict:
                # First occurrence - create new entry
                course_dict[course_code] = {
                    "course_code": course_code,
                    "title": course_data["title"],
                    "classes": course_data.get("classes", []).copy(),
                }
            else:
                # Duplicate course_code - merge classes
                course_dict[course_code]["classes"].extend(
                    course_data.get("classes", [])
                )

        return list(course_dict.values())

    def _parse_enrollment_status(self, seats_html: str) -> str:
        """
        Parse enrollment status from the HTML in the seats field.

        Args:
            seats_html: HTML string containing seat availability

        Returns:
            Status: 'Open', 'Closed', or 'Unknown'
        """
        try:
            if not seats_html:
                return "Unknown"

            # Parse HTML to extract seats_avail
            soup = BeautifulSoup(seats_html, "html.parser")
            seats_avail_elem = soup.select_one(".seats_avail")

            if seats_avail_elem:
                seats_avail_text = seats_avail_elem.text.strip()
                try:
                    seats_avail = int(seats_avail_text)
                    return "Open" if seats_avail > 0 else "Closed"
                except ValueError:
                    pass

            return "Unknown"

        except Exception as e:
            logger.warning(f"Error parsing enrollment status: {e}")
            return "Unknown"

    async def _make_api_request(
        self, url: str, body: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Make a POST request to Brown's API with URL-encoded JSON body.

        Args:
            url: API endpoint URL
            body: Request body dictionary

        Returns:
            Response data as dictionary
        """
        try:
            logger.debug(f"Making API request to: {url}")

            # Encode the body as URL-encoded JSON string (matching Brown's API expectations)
            json_string = json.dumps(body)
            encoded_body = quote(json_string)

            # Make POST request using httpx
            response = await self.client.post(url, content=encoded_body)

            response.raise_for_status()
            self.request_count += 1

            # Parse JSON response
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                return response.json()
            else:
                # Try to parse as JSON anyway
                return response.json()

        except Exception as e:
            logger.error(f"API request failed for {url}: {e}")
            raise
