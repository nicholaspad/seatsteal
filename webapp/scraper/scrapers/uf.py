from typing import List, Dict, Any, Optional, Tuple
import asyncio
import httpx
from scraper.base import BaseScraper
from scraper.utils.logger import scraper_logger as logger
from scraper.utils.term_code_db import get_term_code_from_db


class UfScraper(BaseScraper):
    """University of Florida course scraper."""

    BASE_URL = "https://one.uf.edu/apix/soc"
    CATEGORIES = ["CWSP", "RES", "HUR"]  # All course categories

    def __init__(self, db_session=None):
        super().__init__("uf")
        self.client: Optional[httpx.AsyncClient] = None
        self.current_term = get_term_code_from_db(db_session, "uf")

    async def _ensure_client(self):
        """Ensure HTTP client is initialized"""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=60.0,  # Longer timeout for large responses
                follow_redirects=True,
                headers={
                    "User-Agent": "SeatSteal/1.0",
                    "Accept": "application/json",
                },
            )

    async def scrape_courses(
        self, department: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Scrape UF courses for specified department or all."""
        logger.info(
            f"Scraping UF {department} courses (limit: {limit}, term: {self.current_term})"
        )

        await self._ensure_client()

        try:
            # Fetch courses from all categories
            all_courses = await self._fetch_all_categories()

            # Filter by department if needed
            if department.upper() != "ALL":
                all_courses = [
                    c
                    for c in all_courses
                    if department.upper() in c.get("code", "").upper()
                ]

            # Transform to standard format
            courses_data = self._transform_courses(all_courses, limit)

            logger.info(f"Scraped {len(courses_data)} courses from UF")
            return courses_data

        except Exception as e:
            logger.error(f"Failed to scrape UF {department}: {e}")
            raise
        finally:
            if self.client:
                await self.client.aclose()
                self.client = None

    async def _fetch_all_categories(self) -> List[Dict[str, Any]]:
        """Fetch courses from all UF categories and combine."""
        all_courses = []

        for category in self.CATEGORIES:
            try:
                logger.info(f"Fetching UF category: {category}")
                courses = await self._fetch_category(category)
                all_courses.extend(courses)

                # Rate limiting between categories
                await asyncio.sleep(1.0)

            except Exception as e:
                logger.warning(f"Failed to fetch category {category}: {e}")
                continue

        return all_courses

    async def _fetch_single_page(
        self, category: str, control_number: int
    ) -> Tuple[int, List[Dict[str, Any]], int, int]:
        """
        Fetch a single page and return its data.

        Args:
            category: Course category (CWSP, RES, HUR)
            control_number: The last-control-number to use for this request

        Returns:
            Tuple of (request_control_number, courses, next_control_number, total_rows)
        """
        url = f"{self.BASE_URL}/schedule"
        params = {
            "category": category,
            "term": self.current_term,
            "last-control-number": str(control_number),
        }

        response = await self.client.get(url, params=params)
        response.raise_for_status()
        self.request_count += 1

        data = self.decode_json_response(response)

        if not data or len(data) == 0:
            return (control_number, [], control_number, 0)

        response_data = data[0]
        courses = response_data.get("COURSES", [])
        next_control_number = response_data.get("LASTCONTROLNUMBER", control_number)
        total_rows = response_data.get("TOTALROWS", 0)

        return (control_number, courses, next_control_number, total_rows)

    async def _fetch_pages_batch(
        self, category: str, control_numbers: List[int]
    ) -> List[Tuple[int, List[Dict[str, Any]], int, int]]:
        """
        Fetch multiple pages concurrently given their control numbers.

        Args:
            category: Course category
            control_numbers: List of control numbers to fetch

        Returns:
            List of results from _fetch_single_page, with exceptions filtered out
        """
        tasks = [self._fetch_single_page(category, cn) for cn in control_numbers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and log them
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(
                    f"Failed to fetch page with control number {control_numbers[i]}: {result}"
                )
            else:
                valid_results.append(result)

        return valid_results

    async def _fetch_category(self, category: str) -> List[Dict[str, Any]]:
        """Fetch all courses for a category using concurrent batch pagination."""
        BATCH_SIZE = 5
        all_courses = []

        # First request to get page size and initial data
        logger.debug(f"Fetching first page of {category} to determine page size")
        first_result = await self._fetch_single_page(category, 0)
        req_control, courses, next_control, total_rows = first_result

        if not courses:
            logger.info(f"No courses found for category {category}")
            return []

        all_courses.extend(courses)
        page_size = len(courses)

        logger.info(
            f"First page of {category}: {len(courses)} courses, "
            f"page_size={page_size}, total_rows={total_rows}"
        )

        # If first page got everything, we're done
        if next_control == req_control or len(all_courses) >= total_rows:
            logger.info(
                f"Completed pagination for {category}: {len(all_courses)} courses"
            )
            return all_courses

        # Continue fetching in batches of 5 concurrently
        current_control = next_control
        seen_controls = {0, next_control}

        while True:
            # Generate next batch of control numbers (speculative based on page size)
            batch_controls = []
            for i in range(BATCH_SIZE):
                speculative_control = current_control + (i * page_size)
                if speculative_control not in seen_controls:
                    batch_controls.append(speculative_control)
                    seen_controls.add(speculative_control)

            if not batch_controls:
                break

            logger.debug(
                f"Fetching batch of {len(batch_controls)} pages for {category}: "
                f"control numbers {batch_controls}"
            )

            # Fetch batch concurrently
            results = await self._fetch_pages_batch(category, batch_controls)

            if not results:
                logger.info(f"No more results for {category}")
                break

            # Sort results by control number to process in order
            results.sort(key=lambda x: x[0])

            batch_courses = 0
            max_next_control = current_control
            reached_end = False

            for req_ctrl, courses, next_ctrl, _ in results:
                if courses:
                    all_courses.extend(courses)
                    batch_courses += len(courses)
                    seen_controls.add(next_ctrl)

                    # Track the highest next_control we've seen
                    if next_ctrl > max_next_control:
                        max_next_control = next_ctrl

                # Check if this page indicates end of data
                if next_ctrl == req_ctrl or not courses:
                    reached_end = True

            logger.info(
                f"Batch complete for {category}: {batch_courses} courses, "
                f"total so far: {len(all_courses)}/{total_rows}"
            )

            if reached_end or len(all_courses) >= total_rows:
                logger.info(
                    f"Completed pagination for {category}: {len(all_courses)} courses"
                )
                break

            # Move to next batch using the highest control number we found
            current_control = max_next_control

            # Small delay between batches to be respectful to the API
            await asyncio.sleep(0.1)

        return all_courses

    def _transform_courses(
        self, raw_courses: List[Dict[str, Any]], limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Transform UF API data to standard format."""
        courses_data = []
        seen_codes = set()

        for raw_course in raw_courses:
            try:
                course_code = raw_course.get("code", "").strip()

                # Skip duplicates
                if course_code in seen_codes:
                    continue
                seen_codes.add(course_code)

                course = self._transform_single_course(raw_course)
                if course and course.get("classes"):
                    courses_data.append(course)

                    if limit and len(courses_data) >= limit:
                        logger.info(f"Reached course limit of {limit}")
                        break

            except Exception as e:
                logger.warning(f"Error transforming course: {e}")
                continue

        return courses_data

    def _transform_single_course(
        self, raw_course: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Transform single UF course to standard format."""
        try:
            course_code = raw_course.get("code", "").strip()
            title = raw_course.get("name", "").strip()
            sections = raw_course.get("sections", [])

            if not course_code or not title:
                return None

            if not sections:
                logger.debug(f"Course {course_code} has no sections")
                return None

            # Transform sections
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
            logger.warning(f"Error transforming course: {e}")
            return None

    def _transform_section(self, section: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform UF section to standard class format."""
        try:
            class_number = str(section.get("classNumber", ""))
            section_code = section.get("number", "")

            if not class_number:
                return None

            # Determine status
            add_eligible = section.get("addEligible")
            waitlist = section.get("waitList", {})

            if add_eligible == "Y":
                status = "Open"
            elif add_eligible == "N":
                if waitlist.get("isEligible") == "Y":
                    status = "Waitlist"
                else:
                    status = "Closed"
            else:
                status = "Unknown"

            return {
                "class_number": class_number,
                "section": section_code,
                "status": status,
            }

        except Exception as e:
            logger.warning(f"Error transforming section: {e}")
            return None
