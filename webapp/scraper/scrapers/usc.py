from typing import List, Dict, Any, Optional
import asyncio
import httpx
from scraper.base import BaseScraper
from scraper.utils.logger import scraper_logger as logger
from scraper.utils.term_code_db import get_term_code_from_db


class UscScraper(BaseScraper):
    """
    University of Southern California course scraper.

    Scrapes course data from USC's public class search API.
    Migrated from working TypeScript implementation.
    """

    SCHOOLS_API_URL = "https://classes.usc.edu/api/Schools/TermCode"
    COURSES_API_URL = "https://classes.usc.edu/api/Courses/CoursesByTermSchoolProgram"

    def __init__(self, db_session=None):
        super().__init__("usc")
        self.client: Optional[httpx.AsyncClient] = None
        self.current_term = get_term_code_from_db(db_session, "usc")

    async def _ensure_client(self):
        """Ensure HTTP client is initialized"""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Cache-Control": "no-cache",
                },
            )

    async def scrape_courses(
        self, department: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape USC courses for a specific department or all courses.

        Args:
            department: Department/program code (e.g., 'CSCI', 'MATH') or 'ALL' for all courses
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries with class information
        """
        logger.info(
            f"Scraping USC {department} courses (limit: {limit}, term: {self.current_term})"
        )

        await self._ensure_client()

        try:
            if department.upper() == "ALL":
                return await self._fetch_all_courses(limit)
            else:
                return await self._fetch_subject_courses(department, limit)

        except Exception as e:
            logger.error(f"Failed to scrape USC {department}: {e}")
            raise
        finally:
            if self.client:
                await self.client.aclose()
                self.client = None

    async def _fetch_all_courses(
        self, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all courses from USC's API using 3-step flow.

        Step 1: Use configured term code
        Step 2: Get all school/program combinations
        Step 3: Process school/program combinations in batches

        Args:
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries
        """
        try:
            # Step 1: Use configured term code
            logger.info(f"Step 1: Using configured term code: {self.current_term}")
            term_code = self.current_term

            # Step 2: Get all school/program combinations
            logger.info("Step 2: Fetching school/program combinations...")
            school_programs = await self._fetch_school_programs(term_code)
            logger.info(
                f"Found {len(school_programs)} school/program combinations to process"
            )

            if len(school_programs) == 0:
                logger.warning("No school/program combinations found")
                return []

            # Step 3: Process school/program combinations in batches
            logger.info("Step 3: Fetching courses for all programs...")
            all_classes = []
            batch_size = 18  # Process 18 programs concurrently (matching TypeScript)

            for i in range(0, len(school_programs), batch_size):
                batch = school_programs[i : i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(school_programs) + batch_size - 1) // batch_size

                logger.info(
                    f"Processing program batch {batch_num}/{total_batches} "
                    f"({len(batch)} programs: {', '.join(p['program'] for p in batch)})"
                )

                # Create tasks for this batch of programs
                batch_tasks = [
                    self._fetch_program_courses(term_code, school_program)
                    for school_program in batch
                ]

                # Execute program batch concurrently
                batch_results = await asyncio.gather(
                    *batch_tasks, return_exceptions=True
                )

                # Process results and collect classes
                for j, result in enumerate(batch_results):
                    school_program = batch[j]

                    if isinstance(result, Exception):
                        logger.warning(
                            f"Program {school_program['school']}/{school_program['program']} failed: {result}"
                        )
                    elif result is not None:
                        all_classes.extend(result)
                        logger.info(
                            f"Program {school_program['school']}/{school_program['program']}: "
                            f"{len(result)} classes extracted"
                        )

                # Add delay between batches to be respectful
                if i + batch_size < len(school_programs):
                    await asyncio.sleep(0.5)

            logger.info(
                f"Extracted {len(all_classes)} classes total from {len(school_programs)} programs"
            )

            # Group classes by course
            courses_data = self._group_classes_by_course(all_classes)
            logger.info(f"Grouped into {len(courses_data)} unique courses")

            # Apply limit if specified
            if limit:
                courses_data = courses_data[:limit]

            return courses_data

        except Exception as e:
            logger.error(f"Error during USC API course fetch: {e}")
            raise

    async def _fetch_subject_courses(
        self, subject: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch courses for a specific subject/program.

        Args:
            subject: Subject/program code (e.g., 'CSCI', 'MATH')
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries
        """
        try:
            term_code = self.current_term

            # Get all school/program combinations
            school_programs = await self._fetch_school_programs(term_code)

            # Find programs that match the subject
            matching_programs = [
                sp for sp in school_programs if sp["program"].upper() == subject.upper()
            ]

            if len(matching_programs) == 0:
                logger.warning(f"No programs found for subject {subject}")
                return []

            logger.info(
                f"Found {len(matching_programs)} programs for subject {subject}"
            )

            # Fetch courses for matching programs
            all_classes = []
            for school_program in matching_programs:
                try:
                    program_classes = await self._fetch_program_courses(
                        term_code, school_program
                    )
                    all_classes.extend(program_classes)
                except Exception as e:
                    logger.warning(
                        f"Error fetching {school_program['school']}/{school_program['program']}: {e}"
                    )

            logger.info(f"Found {len(all_classes)} classes for subject {subject}")

            # Group classes by course
            courses_data = self._group_classes_by_course(all_classes)
            logger.info(f"Grouped into {len(courses_data)} unique courses")

            # Apply limit if specified
            if limit:
                courses_data = courses_data[:limit]

            return courses_data

        except Exception as e:
            logger.error(f"Error fetching subject {subject}: {e}")
            raise

    async def _fetch_school_programs(self, term_code: str) -> List[Dict[str, str]]:
        """
        Fetch all school/program combinations from USC Schools API.

        Args:
            term_code: Term code (e.g., '20253')

        Returns:
            List of school/program dictionaries with keys: school, program, schoolName, programName
        """
        try:
            url = f"{self.SCHOOLS_API_URL}?termCode={term_code}"
            logger.debug(f"Making API request to: {url}")

            response = await self.client.get(url)
            response.raise_for_status()
            self.request_count += 1

            schools_data = response.json()

            if not schools_data or not isinstance(schools_data, list):
                raise Exception("Invalid response format from USC Schools API")

            # Flatten school/program combinations
            school_programs = []

            for school in schools_data:
                programs = school.get("programs", [])
                for program in programs:
                    school_programs.append(
                        {
                            "school": school.get("prefix", ""),
                            "program": program.get("prefix", ""),
                            "schoolName": school.get("name", ""),
                            "programName": program.get("name", ""),
                        }
                    )

            logger.info(f"Found {len(school_programs)} school/program combinations")
            return school_programs

        except Exception as e:
            logger.error(f"Error fetching school/program combinations: {e}")
            raise

    async def _fetch_program_courses(
        self, term_code: str, school_program: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Fetch courses for a specific school/program combination.

        Args:
            term_code: Term code
            school_program: Dictionary with school and program keys

        Returns:
            List of class dictionaries (not yet grouped by course)
        """
        try:
            url = (
                f"{self.COURSES_API_URL}?termCode={term_code}"
                f"&school={school_program['school']}&program={school_program['program']}"
            )
            logger.debug(f"Making API request to: {url}")

            response = await self.client.get(url)
            response.raise_for_status()
            self.request_count += 1

            program_response = response.json()

            if (
                not program_response
                or not isinstance(program_response, dict)
                or "courses" not in program_response
            ):
                logger.warning(
                    f"Invalid response format for {school_program['school']}/{school_program['program']}"
                )
                return []

            courses = program_response.get("courses", [])

            # Transform USC courses to class dictionaries
            all_classes = []

            for course in courses:
                sections = course.get("sections", [])
                for section in sections:
                    class_data = self._transform_section_to_class(course, section)
                    if class_data:
                        all_classes.append(class_data)

            return all_classes

        except Exception as e:
            logger.error(
                f"Error fetching courses for {school_program['school']}/{school_program['program']}: {e}"
            )
            raise

    def _transform_section_to_class(
        self, course: Dict[str, Any], section: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Transform USC API section data to standard class dictionary format.

        Args:
            course: Course data from USC API
            section: Section data from USC API

        Returns:
            Class dictionary or None if invalid data
        """
        try:
            # Validate required fields
            sis_section_id = section.get("sisSectionId", "")
            full_course_name = course.get("fullCourseName", "")

            if not sis_section_id or not full_course_name:
                logger.warning(
                    f"Skipping section with missing required fields: "
                    f"sisSectionId={sis_section_id}, courseName={full_course_name}"
                )
                return None

            # Calculate enrollment status based on available seats
            total_seats = section.get("totalSeats", 0)
            registered_seats = section.get("registeredSeats", 0)
            available_seats = total_seats - registered_seats
            enrollment_status = "open" if available_seats > 0 else "closed"

            return {
                "class_number": sis_section_id,
                "course_code": full_course_name,
                "title": course.get("name", ""),
                "section": sis_section_id,  # Using sisSectionId as section identifier
                "status": enrollment_status,
            }

        except Exception as e:
            logger.warning(f"Error transforming USC section data: {e}")
            return None

    def _group_classes_by_course(
        self, classes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Group individual class sections by course code.

        USC API returns individual sections, so we need to group them
        into courses with multiple class sections.

        Args:
            classes: List of class dictionaries

        Returns:
            List of course dictionaries with grouped classes
        """
        course_dict: Dict[str, Dict[str, Any]] = {}

        for class_data in classes:
            try:
                course_code = class_data.get("course_code", "")
                title = class_data.get("title", "")

                if not course_code:
                    logger.warning("Skipping class with missing course code")
                    continue

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
                        "class_number": class_data.get("class_number", ""),
                        "section": class_data.get("section", ""),
                        "status": class_data.get("status", "unknown"),
                    }
                )

            except Exception as e:
                logger.error(f"Error grouping class: {e}")
                continue

        return list(course_dict.values())
