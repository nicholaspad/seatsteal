from typing import List, Dict, Any, Optional
import asyncio
import httpx
from scraper.base import BaseScraper
from scraper.utils.logger import scraper_logger as logger
from scraper.utils.term_code_db import get_term_code_from_db


class BuScraper(BaseScraper):
    """
    Boston University course scraper.

    Scrapes course data from BU's public class search API.
    Migrated from working TypeScript implementation.
    """

    BASE_API_URL = "https://public.mybustudent.bu.edu/psc/BUPRD/EMPLOYEE/SA/s/WEBLIB_HCX_CM.H_CLASS_SEARCH.FieldFormula.IScript_ClassSearch"
    INSTITUTION = "BU001"
    SESSION_COOKIE = "public-PORTAL-PSJSESSIONID=1;"

    def __init__(self, db_session=None):
        super().__init__("bu")
        self.client: Optional[httpx.AsyncClient] = None
        self.current_term = get_term_code_from_db(db_session, "bu")

    async def _ensure_client(self):
        """Ensure HTTP client is initialized"""
        if self.client is None:
            # Use 120 second timeout since BU API is slow
            self.client = httpx.AsyncClient(
                timeout=120.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Cache-Control": "no-cache",
                    "Cookie": self.SESSION_COOKIE,
                },
            )

    async def scrape_courses(
        self, department: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape BU courses for a specific department or all courses.

        Args:
            department: Department code (e.g., 'CASCG', 'CS', 'MATH') or 'ALL' for all courses
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries with class information
        """
        logger.info(
            f"Scraping BU {department} courses (limit: {limit}, term: {self.current_term})"
        )

        await self._ensure_client()

        try:
            if department.upper() == "ALL":
                return await self._fetch_all_pages(limit)
            else:
                return await self._fetch_subject_courses(department, limit)

        except Exception as e:
            logger.error(f"Failed to scrape BU {department}: {e}")
            raise
        finally:
            if self.client:
                await self.client.aclose()
                self.client = None

    async def _fetch_all_pages(
        self, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all courses from BU's paginated API.

        Fetches pages in batches of 20 concurrently until at least one page
        returns empty. BU API is slow, so we use 120 second timeout per request.

        Args:
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries
        """
        try:
            all_classes = []
            batch_size = 20  # Fetch 20 pages concurrently
            current_page = 1
            pages_fetched = 0
            empty_page_found = False

            logger.info("Starting BU API fetch (will continue until empty page found)")

            while not empty_page_found:
                # Calculate page range for this batch
                start_page = current_page
                end_page = current_page + batch_size - 1

                logger.info(f"Fetching pages {start_page}-{end_page} concurrently...")

                # Create promises for this batch of pages
                page_batch_promises = [
                    self._fetch_single_page(page)
                    for page in range(start_page, end_page + 1)
                ]

                # Execute page batch concurrently
                batch_results = await asyncio.gather(
                    *page_batch_promises, return_exceptions=True
                )

                # Process results and collect classes
                for i, result in enumerate(batch_results):
                    page_number = start_page + i

                    if isinstance(result, Exception):
                        logger.warning(f"Page {page_number} failed: {result}")
                        # Don't count failures as empty pages
                        continue
                    elif result and result.get("classes"):
                        page_classes = result["classes"]
                        if len(page_classes) == 0:
                            logger.info(
                                f"Page {page_number}: Empty page found - stopping"
                            )
                            empty_page_found = True
                        else:
                            all_classes.extend(page_classes)
                            pages_fetched += 1
                            logger.info(
                                f"Page {page_number}: {len(page_classes)} classes extracted"
                            )
                    else:
                        logger.info(f"Page {page_number}: Empty page found - stopping")
                        empty_page_found = True

                # Move to next batch
                current_page = end_page + 1

                # Log progress
                logger.info(
                    f"Progress: {pages_fetched} pages fetched, {len(all_classes)} classes total"
                )

                # Add small delay between batches to be respectful
                if not empty_page_found:
                    await asyncio.sleep(0.5)

            logger.info(
                f"Extracted {len(all_classes)} classes total from {pages_fetched} pages"
            )

            # Transform classes to course format
            courses_data = self._group_classes_by_course(all_classes)
            logger.info(f"Grouped into {len(courses_data)} unique courses")

            # Apply limit if specified
            if limit:
                courses_data = courses_data[:limit]

            return courses_data

        except Exception as e:
            logger.error(f"Error during BU API page fetch: {e}")
            raise

    async def _fetch_subject_courses(
        self, subject: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch courses for a specific subject.

        Args:
            subject: Subject code (e.g., 'CASCG', 'CS')
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries
        """
        try:
            # Fetch all courses and filter by subject
            all_courses = await self._fetch_all_pages()
            logger.info(
                f"Found {len(all_courses)} total courses, filtering for {subject}"
            )

            # Filter courses by subject
            subject_courses = [
                course
                for course in all_courses
                if course["course_code"].startswith(subject)
            ]
            logger.info(f"Found {len(subject_courses)} courses for {subject}")

            # Apply limit if specified
            if limit:
                subject_courses = subject_courses[:limit]

            return subject_courses

        except Exception as e:
            logger.error(f"Error fetching subject {subject}: {e}")
            raise

    async def _fetch_single_page(self, page_number: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a single page from BU's API.

        Args:
            page_number: Page number to fetch (1-indexed)

        Returns:
            API response dictionary with 'pageCount' and 'classes' keys
        """
        try:
            url = self._build_page_url(page_number)
            logger.debug(f"Fetching page {page_number}: {url}")

            response = await self.client.get(url)
            response.raise_for_status()
            self.request_count += 1

            # Parse JSON response
            content_type = response.headers.get("content-type", "")

            if "application/json" not in content_type:
                logger.warning(
                    f"Page {page_number}: Expected JSON response, got {content_type}"
                )
                return None

            data = response.json()

            if (
                not data
                or "classes" not in data
                or not isinstance(data["classes"], list)
            ):
                logger.warning(f"Page {page_number}: Invalid response format")
                return None

            return data

        except Exception as e:
            logger.error(f"Error fetching page {page_number}: {e}")
            return None

    def _build_page_url(self, page_number: int) -> str:
        """
        Build the API URL for a specific page.

        Args:
            page_number: Page number to fetch

        Returns:
            Full API URL with query parameters
        """
        return f"{self.BASE_API_URL}?institution={self.INSTITUTION}&term={self.current_term}&page={page_number}"

    def _group_classes_by_course(
        self, classes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Group BU API classes by course code.

        BU API returns individual class sections, so we need to group them
        into courses with multiple class sections.

        Args:
            classes: List of class dictionaries from BU API

        Returns:
            List of course dictionaries with grouped classes
        """
        course_dict: Dict[str, Dict[str, Any]] = {}

        for bu_class in classes:
            try:
                # Validate required fields
                if (
                    not bu_class.get("class_nbr")
                    or not bu_class.get("subject")
                    or not bu_class.get("catalog_nbr")
                ):
                    logger.warning(
                        f"Skipping class with missing required fields: {bu_class.get('class_nbr')}"
                    )
                    continue

                # Build course code
                course_code = f"{bu_class['subject']} {bu_class['catalog_nbr']}".strip()
                title = bu_class.get("descr", "")

                # Transform class data
                class_data = self._transform_to_class_dict(bu_class)
                if not class_data:
                    continue

                # Group by course code
                if course_code not in course_dict:
                    course_dict[course_code] = {
                        "course_code": course_code,
                        "title": title,
                        "classes": [],
                    }

                course_dict[course_code]["classes"].append(class_data)

            except Exception as e:
                logger.error(f"Error processing class: {e}")
                continue

        return list(course_dict.values())

    def _transform_to_class_dict(
        self, bu_class: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Transform BU API class data to standard class dictionary format.

        Args:
            bu_class: Class data from BU API

        Returns:
            Class dictionary or None if invalid data
        """
        try:
            class_number = str(bu_class.get("class_nbr", ""))
            section = bu_class.get("class_section", "A1")

            # Validate required fields
            if not class_number or not class_number.strip():
                logger.warning("Skipping class with empty class_nbr")
                return None

            # Determine enrollment status based on availability
            enrollment_available = bu_class.get("enrollment_available", 0)
            enrollment_status = "open" if enrollment_available > 0 else "closed"

            return {
                "class_number": class_number,
                "section": section,
                "status": enrollment_status,
            }

        except Exception as e:
            logger.error(f"Error transforming class data: {e}")
            return None
