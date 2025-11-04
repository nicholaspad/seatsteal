from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
from loguru import logger

from models.college import College
from models.course import Course
from models.class_model import Class
from models.enrollment import Enrollment
from scraper.scrapers.cornell import CornellScraper
from scraper.scrapers.brown import BrownScraper
from scraper.scrapers.bu import BuScraper
from scraper.scrapers.neu import NeuScraper


# Map college short names to scraper classes
SCRAPER_MAP = {
    "cornell": CornellScraper,
    "brown": BrownScraper,
    "bu": BuScraper,
    "neu": NeuScraper,
}


class ScraperService:
    """Service for managing course scraping operations"""

    def __init__(self, db: Session):
        """
        Initialize scraper service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    async def scrape_college(
        self, college_short_name: str, department: str, limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Scrape courses for a specific college and department.

        Args:
            college_short_name: College identifier (e.g., 'princeton', 'brown')
            department: Department code (e.g., 'CS', 'MATH')
            limit: Optional limit on number of courses to scrape

        Returns:
            Dictionary with scraping results:
            {
                'college': str,
                'department': str,
                'courses_saved': int,
                'classes_saved': int,
                'enrollments_saved': int,
                'duration_seconds': float,
                'success': bool,
                'error': Optional[str]
            }

        Raises:
            ValueError: If college not found or scraper not available
        """
        start_time = datetime.now()

        # Get college from database
        result = self.db.execute(
            select(College).where(College.short_name == college_short_name)
        )
        college = result.scalar_one_or_none()

        if not college:
            raise ValueError(f"College '{college_short_name}' not found in database")

        if not college.is_active:
            raise ValueError(f"College '{college_short_name}' is not active")

        try:
            # Get appropriate scraper
            scraper_class = SCRAPER_MAP.get(college_short_name)
            if not scraper_class:
                raise ValueError(
                    f"No scraper implementation found for '{college_short_name}'"
                )

            # All scrapers need database session to get term code
            scraper = scraper_class(self.db)

            # Scrape courses
            logger.info(
                f"Starting scrape for {college_short_name} {department} (limit: {limit})"
            )
            courses_data = await scraper.scrape_courses(department, limit)
            logger.info(
                f"Scraped {len(courses_data)} courses from {college_short_name} {department}"
            )

            # Step 1: Collect all course data
            course_list = []
            for course_data in courses_data:
                course_list.append(
                    {
                        "course_code": course_data["course_code"],
                        "title": course_data["title"],
                    }
                )

            # Step 2: Batch upsert all courses
            logger.info(f"Batch upserting {len(course_list)} courses")
            course_mapping = self._batch_upsert_courses(college.id, course_list)
            courses_saved = len(course_mapping)

            # Step 3: Collect all class data with course_ids
            class_list = []
            class_to_enrollment_map = (
                []
            )  # Track which class data belongs to which enrollment

            for course_data in courses_data:
                course_code = course_data["course_code"]
                course_id = course_mapping.get(course_code)

                if not course_id:
                    logger.warning(
                        f"Course {course_code} not found in mapping, skipping classes"
                    )
                    continue

                for class_data in course_data.get("classes", []):
                    class_number = class_data.get("class_number", "")
                    class_list.append(
                        {
                            "course_id": course_id,
                            "class_number": class_number,
                            "section_code": class_data.get("section", ""),
                        }
                    )
                    # Store mapping for enrollment data creation later
                    class_to_enrollment_map.append(
                        {
                            "course_id": course_id,
                            "class_number": class_number,
                            "class_data": class_data,
                        }
                    )

            # Step 4: Batch upsert all classes
            logger.info(f"Batch upserting {len(class_list)} classes")
            class_mapping = self._batch_upsert_classes(class_list)
            classes_saved = len(class_mapping)

            # Step 5: Collect all enrollment data with class_ids
            enrollment_data_list = []
            for item in class_to_enrollment_map:
                class_key = (item["course_id"], item["class_number"])
                class_id = class_mapping.get(class_key)

                if not class_id:
                    logger.warning(
                        f"Class {class_key} not found in mapping, skipping enrollment"
                    )
                    continue

                enrollment_data = self._create_enrollment_data(
                    class_id, college.id, item["class_data"]
                )
                enrollment_data_list.append(enrollment_data)

            # Step 6: Batch insert all enrollments
            logger.info(f"Batch inserting {len(enrollment_data_list)} enrollments")
            enrollments_saved = self._batch_insert_enrollments(enrollment_data_list)

            # Calculate duration
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Commit all data changes
            self.db.commit()

            logger.info(
                f"Scrape complete: {courses_saved} courses, {classes_saved} classes, "
                f"{enrollments_saved} enrollment snapshots in {duration:.2f}s"
            )

            return {
                "college": college_short_name,
                "department": department,
                "courses_saved": courses_saved,
                "classes_saved": classes_saved,
                "enrollments_saved": enrollments_saved,
                "duration_seconds": duration,
                "success": True,
                "error": None,
            }

        except Exception as e:
            # Rollback any partial data transaction
            self.db.rollback()

            logger.error(f"Scrape failed for {college_short_name} {department}: {e}")

            duration = (datetime.now() - start_time).total_seconds()

            return {
                "college": college_short_name,
                "department": department,
                "courses_saved": 0,
                "classes_saved": 0,
                "enrollments_saved": 0,
                "duration_seconds": duration,
                "success": False,
                "error": str(e),
            }

    async def _upsert_course(
        self, college_id: int, course_code: str, title: str
    ) -> Course:
        """
        Insert or update a course.

        Args:
            college_id: College ID
            course_code: Course code (e.g., 'CS 101')
            title: Course title

        Returns:
            Course object
        """
        # Check if course exists
        result = self.db.execute(
            select(Course).where(
                Course.college_id == college_id, Course.course_code == course_code
            )
        )
        course = result.scalar_one_or_none()

        if course:
            # Update existing course
            course.title = title
            course.is_active = True
            course.updated_at = datetime.now()
        else:
            # Create new course
            course = Course(
                college_id=college_id,
                course_code=course_code,
                title=title,
                is_active=True,
            )
            self.db.add(course)

        self.db.flush()
        return course

    async def _upsert_class(self, course_id: int, class_data: Dict) -> Class:
        """
        Insert or update a class/section.

        Args:
            course_id: Course ID
            class_data: Class data dictionary

        Returns:
            Class object
        """
        class_number = class_data.get("class_number", "")

        # Check if class exists
        result = self.db.execute(
            select(Class).where(
                Class.course_id == course_id, Class.class_number == class_number
            )
        )
        class_obj = result.scalar_one_or_none()

        if class_obj:
            # Update existing class
            class_obj.section_code = class_data.get("section", "")
            class_obj.is_active = True
            class_obj.updated_at = datetime.now()
        else:
            # Create new class
            class_obj = Class(
                course_id=course_id,
                class_number=class_number,
                section_code=class_data.get("section", ""),
                is_active=True,
            )
            self.db.add(class_obj)

        self.db.flush()
        return class_obj

    def _normalize_enrollment_status(self, status: str) -> str:
        """
        Normalize enrollment status to standard values.

        Args:
            status: Raw status string from scraper

        Returns:
            Normalized status: 'open', 'closed', or 'unknown'
        """
        status_lower = status.lower().strip()

        if status_lower in ["open", "available"]:
            return "open"
        elif status_lower in ["closed", "full", "filled", "waitlist"]:
            return "closed"
        else:
            return "unknown"

    def _create_enrollment_data(
        self, class_id: int, college_id: int, class_data: Dict
    ) -> Dict[str, Any]:
        """
        Create enrollment data dictionary for batch insertion.

        Args:
            class_id: Class ID
            college_id: College ID
            class_data: Class data with enrollment information

        Returns:
            Dictionary with enrollment data ready for batch insert
        """
        import json

        # Normalize status
        raw_status = class_data.get("status", "Unknown")
        enrollment_status = self._normalize_enrollment_status(raw_status)

        # Create raw_text with useful debugging info
        raw_text = json.dumps(
            {
                "class_number": class_data.get("class_number"),
                "section": class_data.get("section"),
                "raw_status": raw_status,
            }
        )

        return {
            "class_id": class_id,
            "college_id": college_id,
            "enrollment_status": enrollment_status,
            "raw_text": raw_text,
        }

    def _batch_upsert_courses(
        self,
        college_id: int,
        course_data_list: List[Dict[str, str]],
        batch_size: int = 500,
    ) -> Dict[str, int]:
        """
        Batch upsert courses using PostgreSQL's ON CONFLICT with true multi-row INSERT.

        Args:
            college_id: College ID for all courses
            course_data_list: List of dicts with 'course_code' and 'title'
            batch_size: Number of records to upsert per batch (default: 500)

        Returns:
            Dictionary mapping course_code to course.id
        """
        from sqlalchemy import text
        from datetime import datetime

        if not course_data_list:
            return {}

        course_mapping = {}
        now = datetime.now()

        # Process in batches
        for i in range(0, len(course_data_list), batch_size):
            batch = course_data_list[i : i + batch_size]

            # Build multi-row VALUES clause with unique parameter names
            placeholders = []
            params = {}

            for idx, course in enumerate(batch):
                placeholders.append(
                    f"(:college_id_{idx}, :course_code_{idx}, :title_{idx}, "
                    f":is_active_{idx}, :created_at_{idx}, :updated_at_{idx})"
                )
                params[f"college_id_{idx}"] = college_id
                params[f"course_code_{idx}"] = course["course_code"]
                params[f"title_{idx}"] = course["title"]
                params[f"is_active_{idx}"] = True
                params[f"created_at_{idx}"] = now
                params[f"updated_at_{idx}"] = now

            values_clause = ", ".join(placeholders)

            # Build the multi-row INSERT ... ON CONFLICT query with RETURNING
            query = text(
                f"""
                INSERT INTO courses (college_id, course_code, title, is_active, created_at, updated_at)
                VALUES {values_clause}
                ON CONFLICT (college_id, course_code)
                DO UPDATE SET
                    title = EXCLUDED.title,
                    is_active = EXCLUDED.is_active,
                    updated_at = EXCLUDED.updated_at
                RETURNING id, course_code
                """
            )

            # Execute single query for entire batch and collect results
            result = self.db.execute(query, params)
            for row in result:
                course_mapping[row[1]] = row[0]  # course_code -> id

            logger.debug(
                f"Upserted batch {i // batch_size + 1}: {len(batch)} courses in single query"
            )

        logger.info(f"Batch upsert complete: {len(course_mapping)} courses processed")
        return course_mapping

    def _batch_upsert_classes(
        self, class_data_list: List[Dict[str, Any]], batch_size: int = 500
    ) -> Dict[tuple, int]:
        """
        Batch upsert classes using PostgreSQL's ON CONFLICT with true multi-row INSERT.

        Args:
            class_data_list: List of dicts with 'course_id', 'class_number', 'section_code'
            batch_size: Number of records to upsert per batch (default: 500)

        Returns:
            Dictionary mapping (course_id, class_number) to class_id
        """
        from sqlalchemy import text
        from datetime import datetime

        if not class_data_list:
            return {}

        class_mapping = {}
        now = datetime.now()

        # Process in batches
        for i in range(0, len(class_data_list), batch_size):
            batch = class_data_list[i : i + batch_size]

            # Build multi-row VALUES clause with unique parameter names
            placeholders = []
            params = {}

            for idx, cls in enumerate(batch):
                placeholders.append(
                    f"(:course_id_{idx}, :class_number_{idx}, :section_code_{idx}, "
                    f":is_active_{idx}, :created_at_{idx}, :updated_at_{idx})"
                )
                params[f"course_id_{idx}"] = cls["course_id"]
                params[f"class_number_{idx}"] = cls["class_number"]
                params[f"section_code_{idx}"] = cls["section_code"]
                params[f"is_active_{idx}"] = True
                params[f"created_at_{idx}"] = now
                params[f"updated_at_{idx}"] = now

            values_clause = ", ".join(placeholders)

            # Build the multi-row INSERT ... ON CONFLICT query with RETURNING
            query = text(
                f"""
                INSERT INTO classes (course_id, class_number, section_code, is_active, created_at, updated_at)
                VALUES {values_clause}
                ON CONFLICT (course_id, class_number)
                DO UPDATE SET
                    section_code = EXCLUDED.section_code,
                    is_active = EXCLUDED.is_active,
                    updated_at = EXCLUDED.updated_at
                RETURNING class_id, course_id, class_number
                """
            )

            # Execute single query for entire batch and collect results
            result = self.db.execute(query, params)
            for row in result:
                class_mapping[(row[1], row[2])] = row[
                    0
                ]  # (course_id, class_number) -> class_id

            logger.debug(
                f"Upserted batch {i // batch_size + 1}: {len(batch)} classes in single query"
            )

        logger.info(f"Batch upsert complete: {len(class_mapping)} classes processed")
        return class_mapping

    def _batch_insert_enrollments(
        self, enrollment_data_list: List[Dict[str, Any]], batch_size: int = 500
    ) -> int:
        """
        Batch insert enrollments for performance optimization.

        Args:
            enrollment_data_list: List of enrollment data dictionaries
            batch_size: Number of records to insert per batch (default: 500)

        Returns:
            Number of enrollments inserted
        """
        from datetime import datetime

        if not enrollment_data_list:
            return 0

        total_inserted = 0

        # Add scraped_at timestamp to all records
        scraped_at = datetime.now()
        for record in enrollment_data_list:
            record["scraped_at"] = scraped_at

        # Process in batches using bulk_insert_mappings
        for i in range(0, len(enrollment_data_list), batch_size):
            batch = enrollment_data_list[i : i + batch_size]

            # Use SQLAlchemy's bulk_insert_mappings for efficient batch insert
            self.db.bulk_insert_mappings(Enrollment, batch)
            total_inserted += len(batch)

            logger.debug(
                f"Inserted batch {i // batch_size + 1}: {len(batch)} enrollments"
            )

        logger.info(f"Batch insert complete: {total_inserted} enrollments processed")
        return total_inserted
