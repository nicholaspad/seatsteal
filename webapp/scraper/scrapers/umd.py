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
        Fetch course details and sections in batches.
        Processes 10 courses per batch, with 2 batches running concurrently.

        Args:
            course_ids: List of course ID dictionaries

        Returns:
            List of transformed course dictionaries
        """
        all_courses = []
        courses_per_batch = 10  # Courses per batch
        concurrent_batches = 1  # Number of batches to run simultaneously

        total_batches = (len(course_ids) + courses_per_batch - 1) // courses_per_batch

        # Process in groups of concurrent_batches
        for group_start in range(0, len(course_ids), courses_per_batch * concurrent_batches):
            # Get courses for this group of batches
            group_courses = course_ids[group_start : group_start + (courses_per_batch * concurrent_batches)]

            # Split into individual batches
            batch_tasks = []
            for i in range(0, len(group_courses), courses_per_batch):
                batch = group_courses[i : i + courses_per_batch]
                batch_num = (group_start + i) // courses_per_batch + 1
                logger.info(f"Queueing batch {batch_num}/{total_batches} ({len(batch)} courses)...")
                batch_tasks.append(self._fetch_single_batch(batch))

            # Execute batches in this group concurrently
            group_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Collect results
            for result in group_results:
                if isinstance(result, Exception):
                    logger.warning(f"Batch failed: {result}")
                    continue
                all_courses.extend(result)

            # Delay between groups to avoid overwhelming the server
            if group_start + (courses_per_batch * concurrent_batches) < len(course_ids):
                await asyncio.sleep(0.5)

        logger.info(f"Successfully fetched {len(all_courses)} courses with sections")
        return all_courses

    async def _fetch_single_batch(
        self, batch_courses: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Fetch a single batch of courses concurrently.

        Args:
            batch_courses: List of course dictionaries for this batch

        Returns:
            List of successfully fetched course data
        """
        tasks = [self._fetch_course_with_sections(course) for course in batch_courses]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        batch_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Course fetch failed: {result}")
                continue
            elif result is not None:
                batch_results.append(result)

        return batch_results

    async def _fetch_course_with_sections(
        self, course_info: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a single course with its sections.

        Args:
            course_info: Dictionary with course_id and name

        Returns:
            Transformed course dictionary or None on error
        """
        try:
            course_id = (
                course_info["course_id"]
                if isinstance(course_info, dict)
                else course_info
            )
            course_name = (
                course_info.get("name", "") if isinstance(course_info, dict) else ""
            )

            # Fetch sections for this course
            url = f"{self.BASE_API_URL}/courses/sections"
            params = {"course_id": course_id, "semester": self.current_term}

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

        except Exception as e:
            logger.warning(f"Error fetching course {course_id}: {e}")
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
