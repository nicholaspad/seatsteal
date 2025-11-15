from typing import List, Dict, Any, Optional
import asyncio
import httpx
from scraper.base import BaseScraper
from scraper.utils.logger import scraper_logger as logger
from scraper.utils.term_code_db import get_term_code_from_db


class UmdScraper(BaseScraper):
    """
    University of Maryland course scraper.

    Scrapes course data from UMD's public umd.io API.
    """

    BASE_API_URL = "https://api.umd.io/v1"

    def __init__(self, db_session=None):
        super().__init__("umd")
        self.client: Optional[httpx.AsyncClient] = None
        self.current_term = get_term_code_from_db(db_session, "umd")

    async def _ensure_client(self):
        """Ensure HTTP client is initialized"""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Accept": "application/json",
                },
            )

    async def scrape_courses(
        self, department: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape UMD courses for a specific department or all courses.

        Args:
            department: Department code (e.g., 'CMSC', 'MATH') or 'ALL' for all courses
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries with class information
        """
        logger.info(
            f"Scraping UMD {department} courses (limit: {limit}, term: {self.current_term})"
        )

        await self._ensure_client()

        try:
            if department.upper() == "ALL":
                # Get all departments first
                courses_data = await self._fetch_all_courses(limit)
            else:
                # Get courses for specific department
                courses_data = await self._fetch_department_courses(
                    department.upper(), limit
                )

            logger.info(f"Successfully scraped {len(courses_data)} courses from UMD")
            return courses_data

        except Exception as e:
            logger.error(f"Failed to scrape UMD {department}: {e}")
            raise
        finally:
            if self.client:
                await self.client.aclose()
                self.client = None

    async def _fetch_all_courses(
        self, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all courses across all departments.

        Args:
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries
        """
        try:
            # First get list of all courses
            logger.info("Fetching list of all courses...")
            url = f"{self.BASE_API_URL}/courses/list"
            params = {"semester": self.current_term}

            response = await self.client.get(url, params=params)
            response.raise_for_status()
            self.request_count += 1

            all_course_ids = response.json()
            logger.info(f"Found {len(all_course_ids)} total courses")

            # Apply limit if specified
            if limit:
                all_course_ids = all_course_ids[:limit]
                logger.info(f"Limited to {len(all_course_ids)} courses")

            # Fetch details for each course in batches
            courses_data = await self._fetch_courses_batch(all_course_ids)

            return courses_data

        except Exception as e:
            logger.error(f"Error fetching all courses: {e}")
            raise

    async def _fetch_department_courses(
        self, dept_id: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch courses for a specific department.

        Args:
            dept_id: Department ID (e.g., 'CMSC')
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries
        """
        try:
            logger.info(f"Fetching courses for department {dept_id}...")
            url = f"{self.BASE_API_URL}/courses"
            params = {"semester": self.current_term, "dept_id": dept_id}

            response = await self.client.get(url, params=params)
            response.raise_for_status()
            self.request_count += 1

            courses = response.json()

            if not courses:
                logger.warning(f"No courses found for department {dept_id}")
                return []

            logger.info(f"Found {len(courses)} courses for {dept_id}")

            # Apply limit if specified
            if limit:
                courses = courses[:limit]

            # Get course IDs and fetch details
            course_ids = [
                {"course_id": c["course_id"], "name": c.get("name", "")}
                for c in courses
            ]
            courses_data = await self._fetch_courses_batch(course_ids)

            return courses_data

        except Exception as e:
            logger.error(f"Error fetching department {dept_id} courses: {e}")
            raise

    async def _fetch_courses_batch(
        self, course_ids: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Fetch course details and sections with smooth rate limiting.
        Uses a semaphore to limit concurrency and staggers request start times
        to spread load evenly and avoid overwhelming the server.

        Args:
            course_ids: List of course ID dictionaries

        Returns:
            List of transformed course dictionaries
        """
        all_courses = []

        # Rate limiting parameters
        max_concurrent = 10  # Maximum concurrent requests
        request_delay = 0.3  # Delay between starting each request (seconds)
        log_interval = 6  # Log progress every N courses

        semaphore = asyncio.Semaphore(max_concurrent)
        completed_count = 0
        total_courses = len(course_ids)

        async def fetch_with_rate_limit(course_info: Dict[str, str], index: int):
            """Fetch a single course with rate limiting."""
            nonlocal completed_count

            # Stagger request start times to avoid bursts
            await asyncio.sleep(index * request_delay)

            async with semaphore:
                result = await self._fetch_course_with_sections(course_info)
                completed_count += 1

                # Log progress at intervals
                if (
                    completed_count % log_interval == 0
                    or completed_count == total_courses
                ):
                    logger.info(
                        f"Progress: {completed_count}/{total_courses} courses fetched "
                        f"({completed_count * 100 // total_courses}%)"
                    )

                return result

        logger.info(
            f"Fetching {total_courses} courses with rate limiting "
            f"(max_concurrent={max_concurrent}, delay={request_delay}s)..."
        )

        # Create all tasks with staggered delays
        tasks = [
            fetch_with_rate_limit(course_info, i)
            for i, course_info in enumerate(course_ids)
        ]

        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                course_id = (
                    course_ids[i].get("course_id", "unknown")
                    if isinstance(course_ids[i], dict)
                    else course_ids[i]
                )
                logger.warning(f"Course fetch failed for {course_id}: {result}")
                continue
            elif result is not None:
                all_courses.append(result)

        logger.info(f"Successfully fetched {len(all_courses)} courses with sections")
        return all_courses

    async def _fetch_course_with_sections(
        self, course_info: Dict[str, str], max_retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a single course with its sections, with retry logic.

        Args:
            course_info: Dictionary with course_id and name
            max_retries: Maximum number of retry attempts

        Returns:
            Transformed course dictionary or None on error
        """
        course_id = (
            course_info["course_id"] if isinstance(course_info, dict) else course_info
        )
        course_name = (
            course_info.get("name", "") if isinstance(course_info, dict) else ""
        )

        url = f"{self.BASE_API_URL}/courses/sections"
        params = {"course_id": course_id, "semester": self.current_term}
        retry_delay = 1.0  # Start with 1 second delay

        for attempt in range(max_retries):
            try:
                response = await self.client.get(url, params=params)
                response.raise_for_status()
                self.request_count += 1

                sections = response.json()

                if not sections:
                    logger.debug(f"No sections found for {course_id}")
                    return None

                # Transform to standard format
                course_data = self._transform_course_sections(
                    course_id, sections, course_name
                )
                return course_data

            except httpx.HTTPStatusError as e:
                if e.response.status_code in (500, 502, 503, 504):
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Server error {e.response.status_code} for {course_id} "
                            f"(attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s..."
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        logger.warning(
                            f"Failed to fetch {course_id} after {max_retries} attempts: {e}"
                        )
                else:
                    logger.warning(f"Error fetching course {course_id}: {e}")
                return None

            except Exception as e:
                logger.warning(f"Error fetching course {course_id}: {e}")
                return None

        return None

    def _transform_course_sections(
        self, course_id: str, sections: List[Dict[str, Any]], course_title: str = ""
    ) -> Dict[str, Any]:
        """
        Transform UMD API sections to standard course format.

        Args:
            course_id: Course ID (e.g., 'CMSC131')
            sections: List of section dictionaries from UMD API
            course_title: Course title from /courses endpoint

        Returns:
            Transformed course dictionary
        """
        if not sections:
            return None

        course_code = course_id

        classes = []
        for section in sections:
            try:
                # Determine status based on open_seats
                open_seats = int(section.get("open_seats", 0))
                if open_seats > 0:
                    status = "open"
                else:
                    status = "closed"

                class_data = {
                    "class_number": section.get("section_id", ""),
                    "section": section.get("number", ""),
                    "status": status,
                }

                classes.append(class_data)

            except Exception as e:
                logger.warning(f"Error transforming section: {e}")
                continue

        if not classes:
            return None

        return {
            "course_code": course_code,
            "title": course_title,
            "classes": classes,
        }
