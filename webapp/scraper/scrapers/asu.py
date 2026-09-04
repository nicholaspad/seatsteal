from typing import List, Dict, Any, Optional
import asyncio
import httpx
from scraper.base import BaseScraper
from scraper.utils.logger import scraper_logger as logger
from scraper.utils.term_code_db import get_term_code_from_db


class AsuScraper(BaseScraper):
    """
    Arizona State University course scraper.

    Scrapes course data from ASU's eAdvs-CSCC Catalog API.
    Strategy: Fetch subjects for term → for each subject fetch classes with pagination.

    API Requirements:
    - Required header: Authorization: Bearer null (401 without it)
    - Pagination: Elasticsearch-style scrollId with 200 max page size
    - Rate limiting: 100-200ms between calls, backoff on 429/5xx

    Term codes: 2YYX format (e.g., "2267" = Fall 2026)
    - 2YY: 200 + year minus 2000 (226 = 2026)
    - X: semester indicator (7 = Fall, 1 = Spring, 4 = Summer)
    """

    BASE_API_URL = (
        "https://eadvs-cscc-catalog-api.apps.asu.edu/catalog-microservices/api/v1"
    )
    MAX_PAGES_PER_SUBJECT = 50  # Safety cap for pagination

    def __init__(self, db_session=None):
        super().__init__("asu")
        self.client: Optional[httpx.AsyncClient] = None
        self.current_term = get_term_code_from_db(db_session, "asu")
        logger.info(f"Initialized ASU scraper with term: {self.current_term}")

    async def _ensure_client(self):
        """Ensure HTTP client is initialized"""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "SeatSteal/1.0",
                    "Accept": "application/json",
                    "Authorization": "Bearer null",  # Required by ASU API
                },
            )

    async def scrape_courses(
        self, department: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape ASU courses for a specific department or all courses.

        Args:
            department: Department code (e.g., 'CSE', 'MATH') or 'ALL' for all courses
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries with class information
        """
        logger.info(
            f"Scraping ASU {department} courses (limit: {limit}, term: {self.current_term})"
        )

        await self._ensure_client()

        try:
            # Fetch subjects for the term
            subjects = await self._fetch_subjects()
            logger.info(f"Found {len(subjects)} subjects for term {self.current_term}")

            # Filter by department if not ALL
            if department.upper() != "ALL":
                subjects = [s for s in subjects if s.upper() == department.upper()]
                if not subjects:
                    logger.warning(
                        f"No subject found matching department: {department}"
                    )
                    return []
                logger.info(f"Filtered to subject: {subjects[0]}")

            # Fetch classes for each subject
            all_raw_classes = []
            for subject in subjects:
                logger.info(f"Fetching classes for subject: {subject}")
                subject_classes = await self._fetch_subject_classes(subject)
                all_raw_classes.extend(subject_classes)
                logger.info(
                    f"Subject {subject}: {len(subject_classes)} classes "
                    f"(total: {len(all_raw_classes)})"
                )

                # Check limit
                if limit and len(all_raw_classes) >= limit:
                    logger.info(f"Reached limit of {limit} classes")
                    all_raw_classes = all_raw_classes[:limit]
                    break

                # Rate limiting between subjects
                await asyncio.sleep(0.15)

            # Transform to standard format
            courses_data = self._transform_classes(all_raw_classes)
            logger.info(
                f"Successfully scraped {len(courses_data)} courses from ASU "
                f"({len(all_raw_classes)} total classes)"
            )
            return courses_data

        except Exception as e:
            logger.error(f"Failed to scrape ASU {department}: {e}")
            raise
        finally:
            if self.client:
                await self.client.aclose()
                self.client = None

    async def _fetch_subjects(self) -> List[str]:
        """
        Fetch available subjects for the current term.

        Returns:
            List of subject codes (e.g., ['CSE', 'MATH', 'ENG'])
        """
        try:
            url = f"{self.BASE_API_URL}/search/subjects"
            params = {"term": self.current_term}

            response = await self.client.get(url, params=params)
            response.raise_for_status()
            self.request_count += 1

            data = self.decode_json_response(response)

            # Extract subject codes from response
            subjects = []
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        subject = item.get("subject") or item.get("code")
                        if subject:
                            subjects.append(subject)
                    elif isinstance(item, str):
                        subjects.append(item)

            logger.info(f"Fetched {len(subjects)} subjects from ASU API")
            return subjects

        except Exception as e:
            logger.error(f"Error fetching ASU subjects: {e}")
            raise

    async def _fetch_subject_classes(self, subject: str) -> List[Dict[str, Any]]:
        """
        Fetch all classes for a subject using scrollId-based pagination.

        Args:
            subject: Subject code (e.g., 'CSE')

        Returns:
            List of raw class data from API
        """
        all_classes = []
        scroll_id = None
        page = 1

        while page <= self.MAX_PAGES_PER_SUBJECT:
            try:
                classes_data = await self._fetch_classes_page(subject, scroll_id)

                classes = classes_data.get("classes", [])
                if not classes:
                    logger.info(
                        f"Subject {subject}: Empty page at page {page}, stopping"
                    )
                    break

                all_classes.extend(classes)
                logger.debug(
                    f"Subject {subject} page {page}: {len(classes)} classes "
                    f"(total: {len(all_classes)})"
                )

                # Get scrollId for next page
                scroll_id = classes_data.get("scrollId")
                if not scroll_id:
                    logger.info(
                        f"Subject {subject}: No scrollId returned, stopping at page {page}"
                    )
                    break

                page += 1

                # Rate limiting between pages
                await asyncio.sleep(0.12)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # Rate limited, backoff and retry
                    wait_time = 2 ** min(page - 1, 5)  # Exponential backoff, max 32s
                    logger.warning(
                        f"Rate limited on subject {subject} page {page}, "
                        f"backing off {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                elif e.response.status_code >= 500:
                    # Server error, log and continue
                    logger.warning(
                        f"Server error {e.response.status_code} on subject {subject} "
                        f"page {page}, stopping pagination"
                    )
                    break
                else:
                    raise

        if page > self.MAX_PAGES_PER_SUBJECT:
            logger.warning(
                f"Subject {subject}: Hit max pages cap ({self.MAX_PAGES_PER_SUBJECT})"
            )

        logger.info(
            f"Subject {subject}: Fetched {len(all_classes)} classes "
            f"across {page - 1} pages"
        )
        return all_classes

    async def _fetch_classes_page(
        self, subject: str, scroll_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch a single page of classes from the ASU API.

        Args:
            subject: Subject code
            scroll_id: Optional scrollId for pagination

        Returns:
            Dictionary with 'classes' and 'scrollId' keys
        """
        url = f"{self.BASE_API_URL}/search/classes"

        params = {
            "refine": "Y",
            "subject": subject,
            "term": self.current_term,
        }

        if scroll_id:
            params["scrollId"] = scroll_id

        response = await self.client.get(url, params=params)
        response.raise_for_status()
        self.request_count += 1

        data = self.decode_json_response(response)
        return data

    def _transform_classes(
        self, raw_classes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Transform ASU API class data to standard format.

        Args:
            raw_classes: List of raw class data from API

        Returns:
            List of course dictionaries grouped by course_code
        """
        # First, transform individual classes
        transformed_classes = []
        for raw_class in raw_classes:
            try:
                class_data = self._transform_single_class(raw_class)
                if class_data:
                    transformed_classes.append(class_data)
            except Exception as e:
                class_id = raw_class.get("CLASSNBR", "unknown")
                logger.warning(f"Error transforming class {class_id}: {e}")
                continue

        # Group by course_code
        courses_dict: Dict[str, Dict[str, Any]] = {}
        for class_data in transformed_classes:
            course_code = class_data["course_code"]

            if course_code not in courses_dict:
                courses_dict[course_code] = {
                    "course_code": course_code,
                    "title": class_data["title"],
                    "classes": [],
                }

            # Add class to course
            courses_dict[course_code]["classes"].append(
                {
                    "class_number": class_data["class_number"],
                    "section": class_data["section"],
                    "status": class_data["status"],
                }
            )

        # Convert to list and deduplicate classes within each course
        courses_data = []
        for course in courses_dict.values():
            # Deduplicate classes by class_number
            seen_class_numbers = set()
            unique_classes = []
            for cls in course["classes"]:
                class_number = cls["class_number"]
                if class_number not in seen_class_numbers:
                    seen_class_numbers.add(class_number)
                    unique_classes.append(cls)

            course["classes"] = unique_classes
            courses_data.append(course)

        logger.info(
            f"Transformed {len(transformed_classes)} classes into "
            f"{len(courses_data)} courses"
        )
        return courses_data

    def _transform_single_class(
        self, raw_class: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Transform a single ASU class to include course and class info.

        Args:
            raw_class: Raw class data from API

        Returns:
            Dictionary with course_code, title, class_number, section, status
        """
        try:
            # Build course_code from SUBJECT and CATALOGNBR
            subject = raw_class.get("SUBJECT", "").strip()
            catalog_nbr = raw_class.get("CATALOGNBR", "").strip()

            if not subject or not catalog_nbr:
                logger.warning(
                    f"Skipping class with missing subject or catalog number: {raw_class}"
                )
                return None

            course_code = f"{subject} {catalog_nbr}"

            # Get title (prefer COURSETITLELONG, fallback to TITLE)
            title = (
                raw_class.get("COURSETITLELONG", "").strip()
                or raw_class.get("TITLE", "").strip()
            )

            # Get class number (CLASSNBR)
            class_number = str(raw_class.get("CLASSNBR", "")).strip()
            if not class_number:
                logger.warning(f"Skipping class with missing CLASSNBR: {raw_class}")
                return None

            # Get section (CLASSSECTION)
            section = str(raw_class.get("CLASSSECTION", "")).strip()

            # Get enrollment status (ENRLSTAT)
            enrl_stat = raw_class.get("ENRLSTAT", "").strip().upper()

            # Map ENRLSTAT to status
            if enrl_stat == "O":
                status = "Open"
            elif enrl_stat == "C":
                status = "Closed"
            else:
                # Unknown status - log and treat conservatively as Closed
                logger.debug(
                    f"Unknown ENRLSTAT '{enrl_stat}' for class {class_number}, "
                    f"treating as Closed"
                )
                status = "Closed"

            return {
                "course_code": course_code,
                "title": title,
                "class_number": class_number,
                "section": section,
                "status": status,
            }

        except Exception as e:
            logger.warning(f"Error transforming single class: {e}")
            return None
