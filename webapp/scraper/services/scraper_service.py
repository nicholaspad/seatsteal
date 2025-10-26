from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
from loguru import logger

from models.college import College
from models.course import Course
from models.class_model import Class
from models.enrollment import Enrollment
from scraper.scrapers.princeton import PrincetonScraper
from scraper.scrapers.brown import BrownScraper
from scraper.scrapers.bu import BUScraper
from scraper.scrapers.cornell import CornellScraper
from scraper.scrapers.neu import NEUScraper
from scraper.scrapers.usc import USCScraper
from scraper.services.scraper_log import ScraperLogService


# Map college short names to scraper classes
SCRAPER_MAP = {
    "princeton": PrincetonScraper,
    "brown": BrownScraper,
    "bu": BUScraper,
    "cornell": CornellScraper,
    "neu": NEUScraper,
    "usc": USCScraper,
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
        self.log_service = ScraperLogService(db)

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

        # Get scraper_id and start scraper log
        scraper_id = await self.log_service.get_scraper_id_from_college(college.id)
        if not scraper_id:
            raise ValueError(f"No scraper found for college '{college_short_name}'")

        log_id = await self.log_service.start_log(scraper_id)

        try:
            # Get appropriate scraper
            scraper_class = SCRAPER_MAP.get(college_short_name)
            if not scraper_class:
                raise ValueError(
                    f"No scraper implementation found for '{college_short_name}'"
                )

            scraper = scraper_class()

            # Scrape courses
            logger.info(
                f"Starting scrape for {college_short_name} {department} (limit: {limit})"
            )
            courses_data = await scraper.scrape_courses(department, limit)
            logger.info(
                f"Scraped {len(courses_data)} courses from {college_short_name} {department}"
            )

            # Save to database
            courses_saved = 0
            classes_saved = 0
            enrollment_data_list = []  # Collect enrollment data for batch upsert

            for course_data in courses_data:
                try:
                    # Upsert course
                    course = await self._upsert_course(
                        college.id, course_data["course_code"], course_data["title"]
                    )
                    courses_saved += 1

                    # Upsert classes and collect enrollment data
                    for class_data in course_data.get("classes", []):
                        class_obj = await self._upsert_class(course.id, class_data)
                        classes_saved += 1

                        # Collect enrollment data for batch insert
                        enrollment_data = self._create_enrollment_data(
                            class_obj.class_id, college.id, class_data
                        )
                        enrollment_data_list.append(enrollment_data)

                except Exception as e:
                    logger.error(
                        f"Failed to save course {course_data.get('course_code')}: {e}"
                    )
                    continue

            # Batch insert all enrollments
            enrollments_saved = self._batch_insert_enrollments(enrollment_data_list)

            self.db.commit()

            # Calculate duration
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Complete scraper log
            await self.log_service.complete_log(
                log_id,
                outcome="success",
                courses_created=courses_saved,
                classes_created=classes_saved,
            )

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
            # Log error
            await self.log_service.complete_log(
                log_id, outcome="error", error_message=str(e)
            )

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
                "enrolled": class_data.get("enrolled"),
                "capacity": class_data.get("capacity"),
                "waitlist": class_data.get("waitlist"),
                "raw_status": raw_status,
                "instructor": class_data.get("instructor"),
                "schedule": class_data.get("schedule"),
                "location": class_data.get("location"),
            }
        )

        return {
            "class_id": class_id,
            "college_id": college_id,
            "enrollment_status": enrollment_status,
            "raw_text": raw_text,
        }

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
