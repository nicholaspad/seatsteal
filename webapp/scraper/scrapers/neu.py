from typing import List, Dict, Any, Optional
import asyncio
import httpx
from scraper.base import BaseScraper
from scraper.utils.logger import scraper_logger as logger
from scraper.utils.term_code_db import get_term_code_from_db


class NeuScraper(BaseScraper):
    """
    Northeastern University course scraper.

    Scrapes course data from NEU's Banner 9 student registration API.
    Migrated from working TypeScript implementation.
    """

    BASE_API_URL = "https://nubanner.neu.edu/StudentRegistrationSsb/ssb"

    def __init__(self, db_session=None):
        super().__init__("neu")
        self.client: Optional[httpx.AsyncClient] = None
        self.session_cookies: Dict[str, str] = {}
        self.current_term = get_term_code_from_db(db_session, "neu")

    async def _ensure_client(self):
        """Ensure HTTP client is initialized"""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0",
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                },
            )

    async def scrape_courses(
        self, department: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape NEU courses for a specific department or all courses.

        Args:
            department: Department code (e.g., 'AMSL', 'CS', 'MATH') or 'ALL' for all courses
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries with class information
        """
        logger.info(
            f"Scraping NEU {department} courses (limit: {limit}, term: {self.current_term})"
        )

        await self._ensure_client()

        try:
            # Setup session with Banner API
            await self._setup_session_for_term(self.current_term)

            # Validate session
            test_response = await self._fetch_api_response(0, 1)
            if not test_response or not test_response.get("success"):
                raise Exception("Session validation failed - API test call unsuccessful")

            logger.info(
                f"Session validated successfully for term: {self.current_term} "
                f"({test_response.get('totalCount', 0)} total sections available)"
            )

            # Fetch all courses
            all_classes = await self._fetch_all_courses(limit)

            # Group classes by course
            courses_data = self._group_classes_by_course(all_classes)
            logger.info(f"Grouped into {len(courses_data)} unique courses")

            # Filter by department if not ALL
            if department.upper() != "ALL":
                courses_data = [
                    course
                    for course in courses_data
                    if course["course_code"].startswith(department.upper())
                ]
                logger.info(
                    f"Filtered to {len(courses_data)} courses for {department}"
                )

            # Apply limit if specified
            if limit:
                courses_data = courses_data[:limit]

            return courses_data

        except Exception as e:
            logger.error(f"Failed to scrape NEU {department}: {e}")
            raise
        finally:
            if self.client:
                await self.client.aclose()
                self.client = None

    async def _setup_session_for_term(self, term_id: str) -> None:
        """
        Setup session cookies for the Banner API by calling term/search endpoint.

        Args:
            term_id: Term code (e.g., '202510')
        """
        try:
            logger.info(f"Setting up session for term {term_id}")

            url = f"{self.BASE_API_URL}/term/search?mode=search"
            form_data = {"term": term_id}

            response = await self.client.post(
                url,
                data=form_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()

            # Manually extract cookies from Set-Cookie headers (like TypeScript implementation)
            set_cookie_headers = response.headers.get_list("set-cookie")
            logger.debug(f"Raw Set-Cookie headers: {set_cookie_headers}")

            if set_cookie_headers:
                for cookie_header in set_cookie_headers:
                    # Parse cookie name and value (before first semicolon)
                    name_value = cookie_header.split(";")[0]
                    if "=" in name_value:
                        name, value = name_value.split("=", 1)
                        self.session_cookies[name.strip()] = value.strip()
                        logger.debug(
                            f"Captured cookie: {name.strip()}={value.strip()[:8]}..."
                        )

                logger.info(
                    f"Captured {len(self.session_cookies)} session cookies: {list(self.session_cookies.keys())}"
                )
            else:
                logger.warning("No Set-Cookie headers found in response")

            logger.info(f"Session setup complete for term {term_id}")

        except Exception as e:
            logger.error(f"Error setting up session for term {term_id}: {e}")
            raise

    async def _fetch_all_courses(
        self, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all courses from NEU's paginated Banner API.

        Fetches pages in batches of 5 concurrently for better performance.

        Args:
            limit: Optional limit on number of courses

        Returns:
            List of transformed class dictionaries
        """
        try:
            all_classes = []
            batch_size = 5  # Fetch 5 pages concurrently
            page_max_size = 500  # Banner 9 supports up to 500 records per page
            current_page = 1
            total_count = 0
            pages_fetched = 0
            empty_page_found = False

            logger.info("Starting NEU API fetch (will continue until empty page found)")

            # Get total count from first response
            first_response = await self._fetch_api_response(0, page_max_size)
            if first_response:
                total_count = first_response.get("totalCount", 0)
                total_pages = (total_count + page_max_size - 1) // page_max_size
                logger.info(
                    f"Starting pagination: {total_count} total sections across {total_pages} pages"
                )

            while not empty_page_found:
                # Calculate page range for this batch
                start_offset = (current_page - 1) * page_max_size
                end_page = current_page + batch_size - 1

                logger.info(f"Fetching pages {current_page}-{end_page} concurrently...")

                # Create tasks for this batch of pages
                page_batch_tasks = [
                    self._fetch_sections_page(
                        (current_page + i - 1) * page_max_size, page_max_size
                    )
                    for i in range(batch_size)
                ]

                # Execute page batch concurrently
                batch_results = await asyncio.gather(
                    *page_batch_tasks, return_exceptions=True
                )

                # Process results and collect classes
                for i, result in enumerate(batch_results):
                    page_number = current_page + i

                    if isinstance(result, Exception):
                        logger.warning(f"Page {page_number} failed: {result}")
                        continue
                    elif result is not None and len(result) > 0:
                        # Transform sections to classes
                        scraped_classes = self._transform_sections_to_classes(result)
                        all_classes.extend(scraped_classes)
                        pages_fetched += 1
                        logger.info(
                            f"Page {page_number}: {len(result)} sections extracted"
                        )
                    else:
                        logger.info(f"Page {page_number}: Empty page found - stopping")
                        empty_page_found = True

                # Move to next batch
                current_page = end_page + 1

                # Show progress
                if total_count > 0:
                    progress = min(100, round((len(all_classes) / total_count) * 100))
                    logger.info(
                        f"Progress: {pages_fetched} pages fetched, {len(all_classes)}/{total_count} sections ({progress}%)"
                    )
                else:
                    logger.info(
                        f"Progress: {pages_fetched} pages fetched, {len(all_classes)} sections total"
                    )

                # Add small delay between batches to be respectful
                if not empty_page_found:
                    await asyncio.sleep(0.5)

            logger.info(
                f"Extracted {len(all_classes)} classes total from {pages_fetched} pages"
            )
            return all_classes

        except Exception as e:
            logger.error(f"Error during NEU API course fetch: {e}")
            raise

    async def _fetch_sections_page(
        self, page_offset: int, page_max_size: int
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch a single page of sections from NEU's Banner API.

        Args:
            page_offset: Offset for pagination
            page_max_size: Maximum number of records per page

        Returns:
            List of section dictionaries or None on error
        """
        try:
            url = f"{self.BASE_API_URL}/searchResults/searchResults"
            params = {
                "txt_term": self.current_term,
                "pageOffset": str(page_offset),
                "pageMaxSize": str(page_max_size),
            }

            # Build cookie string from manually managed cookies
            cookie_string = "; ".join(
                [f"{name}={value}" for name, value in self.session_cookies.items()]
            )

            logger.debug(f"Making API request to: {url}")
            logger.debug(f"Sending cookies: {cookie_string[:50] if cookie_string else '(none)'}")

            # Include all headers explicitly (matching TypeScript implementation)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Cache-Control": "no-cache",
            }
            if cookie_string:
                headers["Cookie"] = cookie_string

            response = await self.client.get(url, params=params, headers=headers)
            response.raise_for_status()
            self.request_count += 1

            api_response = response.json()

            logger.debug(
                f"API Response - success: {api_response.get('success')}, "
                f"totalCount: {api_response.get('totalCount')}, "
                f"dataLength: {len(api_response.get('data', []))}"
            )

            if not api_response.get("success"):
                logger.warning("API returned success: false")
                return []

            data = api_response.get("data")
            if not data or len(data) == 0:
                logger.info(
                    f"No data returned for page offset {page_offset} "
                    f"(totalCount: {api_response.get('totalCount')})"
                )
                return []

            logger.info(
                f"Successfully fetched {len(data)} sections from API "
                f"(total available: {api_response.get('totalCount')})"
            )
            return data

        except Exception as e:
            logger.error(f"Error fetching sections page at offset {page_offset}: {e}")
            return None

    async def _fetch_api_response(
        self, page_offset: int, page_max_size: int
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch raw API response for validation purposes.

        Args:
            page_offset: Offset for pagination
            page_max_size: Maximum number of records per page

        Returns:
            API response dictionary or None on error
        """
        try:
            url = f"{self.BASE_API_URL}/searchResults/searchResults"
            params = {
                "txt_term": self.current_term,
                "pageOffset": str(page_offset),
                "pageMaxSize": str(page_max_size),
            }

            # Build cookie string from manually managed cookies
            cookie_string = "; ".join(
                [f"{name}={value}" for name, value in self.session_cookies.items()]
            )

            # Include all headers explicitly (matching TypeScript implementation)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Cache-Control": "no-cache",
            }
            if cookie_string:
                headers["Cookie"] = cookie_string

            response = await self.client.get(url, params=params, headers=headers)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            logger.error(f"Error fetching API response at offset {page_offset}: {e}")
            return None

    def _transform_sections_to_classes(
        self, sections: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Transform Banner API sections to standard class format.

        Args:
            sections: List of section dictionaries from Banner API

        Returns:
            List of transformed class dictionaries
        """
        classes = []

        for section in sections:
            try:
                # Combine subject and courseNumber to form courseCode
                subject = section.get("subject", "")
                course_number = section.get("courseNumber", "")
                course_code = f"{subject} {course_number}".strip()

                if not course_code:
                    logger.warning("Skipping section with empty course code")
                    continue

                class_data = {
                    "class_number": str(section.get("courseReferenceNumber", "")),
                    "course_code": course_code,
                    "title": section.get("courseTitle", ""),
                    "section": section.get("sequenceNumber", "001"),
                    "status": "open" if section.get("openSection") else "closed",
                }

                classes.append(class_data)

            except Exception as e:
                logger.warning(f"Error transforming section: {e}")
                continue

        return classes

    def _group_classes_by_course(
        self, classes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Group individual class sections by course code.

        Banner API returns individual sections, so we need to group them
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
