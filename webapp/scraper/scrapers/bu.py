from typing import List, Dict, Any, Optional
import asyncio
import json
import httpx
from scraper.base import BaseScraper
from scraper.utils.logger import scraper_logger as logger
from scraper.utils.term_code_db import get_term_code_from_db


class BuFetchError(Exception):
    """BU ClassSearch fetch/parse failure. Includes HTTP status and body size."""


class BuScraper(BaseScraper):
    """
    Boston University course scraper.

    Scrapes course data from BU's public class search API.
    Migrated from working TypeScript implementation.

    Term 2268 = Fall 2026 (STRM). Do not silently switch terms: phpbin
    course-search now 302s to this same PeopleSoft iScript, and live probes
    of 2268 / 2272 / 2262 all return the same HTTP 502 HTML gateway page.
    """

    BASE_API_URL = "https://public.mybustudent.bu.edu/psc/BUPRD/EMPLOYEE/SA/s/WEBLIB_HCX_CM.H_CLASS_SEARCH.FieldFormula.IScript_ClassSearch"
    INSTITUTION = "BU001"
    SESSION_COOKIE = "public-PORTAL-PSJSESSIONID=1;"

    def __init__(self, db_session=None):
        super().__init__("bu")
        self.client: Optional[httpx.AsyncClient] = None
        self.current_term = get_term_code_from_db(db_session, "bu")
        self.last_fetch: Dict[str, Any] = {
            "status": None,
            "size": None,
            "content_type": None,
            "reason": None,
            "url": None,
        }

    def format_empty_reason(self) -> str:
        """Describe why a fetch produced no classes (HTTP status + body size)."""
        meta = self.last_fetch
        status = meta.get("status")
        size = meta.get("size")
        content_type = meta.get("content_type") or "unknown"
        reason = meta.get("reason") or "unknown"
        return (
            f"term={self.current_term} status={status} "
            f"response_size={size} content_type={content_type} reason={reason}"
        )

    def _record_fetch(self, **kwargs: Any) -> None:
        self.last_fetch.update(kwargs)

    async def _ensure_client(self):
        """Ensure HTTP client is initialized"""
        if self.client is None:
            # Use 120 second timeout since BU API is slow
            self.client = httpx.AsyncClient(
                timeout=120.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "SeatSteal/1.0",
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
                courses_data = await self._fetch_all_pages(limit)
            else:
                courses_data = await self._fetch_subject_courses(department, limit)

            if not courses_data:
                why = self.format_empty_reason()
                logger.warning(f"BU scrape returned 0 courses ({why})")

            return courses_data

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
        returns empty. HTTP / parse failures are not treated as empty pages:
        they fail the scrape when no classes have been collected yet.

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
                        if not all_classes:
                            logger.error(
                                f"Page {page_number} failed before any classes: {result}"
                            )
                            raise result
                        logger.warning(
                            f"Page {page_number} failed after {len(all_classes)} classes; "
                            f"stopping pagination: {result}"
                        )
                        empty_page_found = True
                        break
                    elif result and result.get("classes"):
                        page_classes = result["classes"]
                        all_classes.extend(page_classes)
                        pages_fetched += 1
                        logger.info(
                            f"Page {page_number}: {len(page_classes)} classes extracted"
                        )
                    else:
                        logger.info(
                            f"Page {page_number}: Empty page found - stopping "
                            f"({self.format_empty_reason()})"
                        )
                        empty_page_found = True
                        break

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

            if not courses_data:
                logger.warning(
                    f"BU grouped 0 courses from {len(all_classes)} raw classes "
                    f"({self.format_empty_reason()})"
                )

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

    def _extract_classes_payload(self, data: Any) -> Optional[Dict[str, Any]]:
        """
        Normalize BU ClassSearch JSON to ``{pageCount, classes}``.

        Live/historical shapes:
        - ``{"pageCount": N, "classes": [...]}`` (wrapped)
        - a raw list of class dicts (older iScript / some HCX versions)
        - ``{"data": {"classes": [...]}}`` or ``{"data": [...]}``
        """
        if isinstance(data, list):
            if data and not all(isinstance(item, dict) for item in data):
                return None
            return {"pageCount": 1 if data else 0, "classes": data}

        if not isinstance(data, dict):
            return None

        classes = data.get("classes")
        if isinstance(classes, list):
            return {
                "pageCount": data.get("pageCount", 1 if classes else 0),
                "classes": classes,
            }

        nested = data.get("data")
        if isinstance(nested, dict) and isinstance(nested.get("classes"), list):
            nested_classes = nested["classes"]
            return {
                "pageCount": nested.get("pageCount", data.get("pageCount", 1)),
                "classes": nested_classes,
            }
        if isinstance(nested, list):
            if nested and not all(isinstance(item, dict) for item in nested):
                return None
            return {"pageCount": 1 if nested else 0, "classes": nested}

        return None

    def _parse_json_body(self, response: httpx.Response, content: bytes) -> Any:
        """Parse JSON from a response, ignoring misleading content-types."""
        try:
            return self.decode_json_response(response)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError):
            text = content.decode("utf-8", errors="replace")
            return json.loads(text)

    async def _fetch_single_page(self, page_number: int) -> Dict[str, Any]:
        """
        Fetch a single page from BU's API.

        Args:
            page_number: Page number to fetch (1-indexed)

        Returns:
            API response dictionary with 'pageCount' and 'classes' keys

        Raises:
            BuFetchError: On HTTP errors or unparseable bodies. Callers must not
            treat these as empty catalog pages.
        """
        url = self._build_page_url(page_number)
        logger.debug(f"Fetching page {page_number}: {url}")

        try:
            response = await self.client.get(url)
        except Exception as e:
            self._record_fetch(
                status=None,
                size=0,
                content_type=None,
                reason=f"transport_error:{type(e).__name__}",
                url=url,
            )
            raise BuFetchError(
                f"BU page {page_number} transport error ({self.format_empty_reason()}): {e}"
            ) from e

        content = response.content or b""
        status = response.status_code
        size = len(content)
        content_type = response.headers.get("content-type", "")
        self.request_count += 1
        self._record_fetch(
            status=status,
            size=size,
            content_type=content_type,
            reason="ok",
            url=url,
        )

        snippet = content.decode("utf-8", errors="replace")[:180]

        if status >= 400:
            self._record_fetch(reason=f"http_{status}")
            logger.warning(
                f"BU page {page_number}: HTTP {status} response_size={size} "
                f"content_type={content_type!r} snippet={snippet!r}"
            )
            raise BuFetchError(
                f"BU page {page_number} HTTP {status} response_size={size} "
                f"content_type={content_type} term={self.current_term}"
            )

        try:
            data = self._parse_json_body(response, content)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as e:
            self._record_fetch(reason="non_json")
            logger.warning(
                f"BU page {page_number}: non-JSON response status={status} "
                f"response_size={size} content_type={content_type!r} "
                f"snippet={snippet!r}"
            )
            raise BuFetchError(
                f"BU page {page_number} non-JSON response status={status} "
                f"response_size={size} content_type={content_type} "
                f"term={self.current_term}"
            ) from e

        payload = self._extract_classes_payload(data)
        if payload is None:
            if isinstance(data, dict):
                keys = sorted(data.keys())
            else:
                keys = type(data).__name__
            self._record_fetch(reason=f"invalid_format keys={keys}")
            logger.warning(
                f"BU page {page_number}: invalid JSON format status={status} "
                f"response_size={size} keys={keys}"
            )
            raise BuFetchError(
                f"BU page {page_number} invalid JSON format status={status} "
                f"response_size={size} keys={keys} term={self.current_term}"
            )

        if not payload["classes"]:
            self._record_fetch(reason="empty_classes")
            logger.warning(
                f"BU page {page_number}: 0 classes in JSON status={status} "
                f"response_size={size} term={self.current_term}"
            )

        return payload

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
