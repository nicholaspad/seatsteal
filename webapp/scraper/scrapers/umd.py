from typing import List, Dict, Any, Optional
import asyncio
import httpx
from scraper.base import BaseScraper
from scraper.utils.logger import scraper_logger as logger
from scraper.utils.term_code_db import get_term_code_from_db


class UmdScraper(BaseScraper):
    """
    University of Maryland course scraper.

    Scrapes course data from UMD's public API (api.umd.io).
    Uses optimized batch processing to fetch all 240+ departments efficiently.
    """

    BASE_API_URL = "https://api.umd.io/v1"

    def __init__(self, db_session=None):
        super().__init__("umd")
        self.client: Optional[httpx.AsyncClient] = None
        # Term code format: YYYYTT (e.g., "202601" for Spring 2026)
        self.current_term = get_term_code_from_db(db_session, "umd")

    async def _ensure_client(self):
        """Ensure HTTP client is initialized"""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "SeatSteal/1.0",
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Cache-Control": "no-cache",
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
                return await self._fetch_all_courses(limit)
            else:
                return await self._fetch_department_courses(department, limit)

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
        Fetch all courses from UMD using optimized batch processing.

        Fetches all 240 departments in batches of 50 with 1-second delays.
        This balances speed with server politeness.

        Args:
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries
        """
        try:
            # Step 1: Get all departments
            logger.info("Step 1: Fetching all departments...")
            departments = await self._fetch_departments()
            logger.info(f"Found {len(departments)} departments to process")

            if len(departments) == 0:
                logger.warning("No departments found")
                return []

            # Step 2: Process departments in batches
            logger.info("Step 2: Fetching sections for all departments...")
            all_sections = []
            batch_size = 50  # Process 50 departments at once

            for i in range(0, len(departments), batch_size):
                batch = departments[i : i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(departments) + batch_size - 1) // batch_size

                logger.info(
                    f"Processing department batch {batch_num}/{total_batches} "
                    f"({len(batch)} departments)"
                )

                # Create tasks for this batch of departments
                batch_tasks = [
                    self._fetch_department_sections(dept["dept_id"]) for dept in batch
                ]

                # Execute batch concurrently
                batch_results = await asyncio.gather(
                    *batch_tasks, return_exceptions=True
                )

                # Process results and collect sections
                for j, result in enumerate(batch_results):
                    dept = batch[j]

                    if isinstance(result, Exception):
                        logger.warning(
                            f"Department {dept['dept_id']} failed: {result}"
                        )
                    elif result is not None and len(result) > 0:
                        all_sections.extend(result)
                        logger.debug(
                            f"Department {dept['dept_id']}: {len(result)} sections"
                        )

                # Add delay between batches to be respectful
                if i + batch_size < len(departments):
                    await asyncio.sleep(1.0)

            logger.info(
                f"Extracted {len(all_sections)} sections total from {len(departments)} departments"
            )

            # Step 3: Group sections by course
            courses_data = self._group_sections_by_course(all_sections)
            logger.info(f"Grouped into {len(courses_data)} unique courses")

            # Apply limit if specified
            if limit:
                courses_data = courses_data[:limit]

            return courses_data

        except Exception as e:
            logger.error(f"Error during UMD API course fetch: {e}")
            raise

    async def _fetch_department_courses(
        self, department: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch courses for a specific department.

        Args:
            department: Department code (e.g., 'CMSC', 'MATH')
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries
        """
        try:
            logger.info(f"Fetching sections for department {department}")
            sections = await self._fetch_department_sections(department)

            if len(sections) == 0:
                logger.warning(f"No sections found for department {department}")
                return []

            logger.info(f"Found {len(sections)} sections for department {department}")

            # Group sections by course
            courses_data = self._group_sections_by_course(sections)
            logger.info(f"Grouped into {len(courses_data)} unique courses")

            # Apply limit if specified
            if limit:
                courses_data = courses_data[:limit]

            return courses_data

        except Exception as e:
            logger.error(f"Error fetching department {department}: {e}")
            raise

    async def _fetch_departments(self) -> List[Dict[str, str]]:
        """
        Fetch all departments from UMD API.

        Returns:
            List of department dictionaries with dept_id and department name
        """
        try:
            url = f"{self.BASE_API_URL}/courses/departments"
            logger.debug(f"Making API request to: {url}")

            response = await self.client.get(url)
            response.raise_for_status()
            self.request_count += 1

            departments = self.decode_json_response(response)

            if not departments or not isinstance(departments, list):
                raise Exception("Invalid response format from UMD departments API")

            logger.info(f"Found {len(departments)} departments")
            return departments

        except Exception as e:
            logger.error(f"Error fetching departments: {e}")
            raise

    async def _fetch_department_sections(
        self, dept_id: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch all sections for a specific department.

        Args:
            dept_id: Department ID (e.g., 'CMSC', 'MATH')

        Returns:
            List of section dictionaries from UMD API
        """
        try:
            url = f"{self.BASE_API_URL}/courses/sections"
            params = {"semester": self.current_term, "dept_id": dept_id}
            logger.debug(f"Making API request to: {url} with params {params}")

            response = await self.client.get(url, params=params)
            response.raise_for_status()
            self.request_count += 1

            sections = self.decode_json_response(response)

            if not isinstance(sections, list):
                logger.warning(
                    f"Invalid response format for department {dept_id}: expected list"
                )
                return []

            return sections

        except Exception as e:
            logger.error(f"Error fetching sections for department {dept_id}: {e}")
            raise

    def _group_sections_by_course(
        self, sections: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Group individual sections by course code.

        UMD API returns individual sections, so we need to group them
        into courses with multiple class sections.

        Args:
            sections: List of section dictionaries from UMD API

        Returns:
            List of course dictionaries with grouped classes
        """
        course_dict: Dict[str, Dict[str, Any]] = {}

        for section in sections:
            try:
                # Transform section to class data
                class_data = self._transform_section(section)
                if not class_data:
                    continue

                course_code = class_data["course_code"]
                title = class_data["title"]

                # Create course entry if it doesn't exist
                if course_code not in course_dict:
                    course_dict[course_code] = {
                        "course_code": course_code,
                        "title": title,
                        "classes": [],
                    }

                # Add class to course
                course_dict[course_code]["classes"].append(
                    {
                        "class_number": class_data["class_number"],
                        "section": class_data["section"],
                        "status": class_data["status"],
                    }
                )

            except Exception as e:
                logger.warning(f"Error processing section: {e}")
                continue

        return list(course_dict.values())

    def _transform_section(
        self, section: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Transform UMD API section data to standard class dictionary format.

        Args:
            section: Section data from UMD API

        Returns:
            Class dictionary or None if invalid data
        """
        try:
            # Validate required fields
            section_id = section.get("section_id", "")
            course_code = section.get("course", "")

            if not section_id or not section_id.strip():
                logger.warning("Skipping section with empty section_id")
                return None

            if not course_code or not course_code.strip():
                logger.warning(
                    f"Skipping section {section_id} with empty course code"
                )
                return None

            # Calculate enrollment status based on open seats
            # If open_seats is not provided or invalid, treat as closed for safety
            try:
                open_seats = int(section.get("open_seats", 0))
            except (ValueError, TypeError):
                logger.warning(
                    f"Invalid open_seats value for section {section_id}, treating as closed"
                )
                open_seats = 0

            enrollment_status = "open" if open_seats > 0 else "closed"

            # Extract section number from section_id (e.g., "CMSC131-0101" -> "0101")
            section_number = section.get("number", "")
            if not section_number:
                # Fallback: extract from section_id
                parts = section_id.split("-")
                section_number = parts[1] if len(parts) > 1 else section_id

            return {
                "class_number": section_id,
                "course_code": course_code,
                "title": "Untitled Course",  # UMD sections API doesn't include title
                "section": section_number,
                "status": enrollment_status,
            }

        except Exception as e:
            logger.warning(f"Error transforming UMD section data: {e}")
            return None
