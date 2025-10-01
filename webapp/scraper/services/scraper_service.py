from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
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
    'princeton': PrincetonScraper,
    'brown': BrownScraper,
    'bu': BUScraper,
    'cornell': CornellScraper,
    'neu': NEUScraper,
    'usc': USCScraper,
}


class ScraperService:
    """Service for managing course scraping operations"""

    def __init__(self, db: AsyncSession):
        """
        Initialize scraper service.

        Args:
            db: SQLAlchemy async database session
        """
        self.db = db
        self.log_service = ScraperLogService(db)

    async def scrape_college(
        self,
        college_short_name: str,
        department: str,
        limit: Optional[int] = None
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
        result = await self.db.execute(
            select(College).where(College.short_name == college_short_name)
        )
        college = result.scalar_one_or_none()

        if not college:
            raise ValueError(f"College '{college_short_name}' not found in database")

        if not college.is_active:
            raise ValueError(f"College '{college_short_name}' is not active")

        # Start scraper log
        log_id = await self.log_service.start_log(college.id)

        try:
            # Get appropriate scraper
            scraper_class = SCRAPER_MAP.get(college_short_name)
            if not scraper_class:
                raise ValueError(f"No scraper implementation found for '{college_short_name}'")

            scraper = scraper_class()

            # Scrape courses
            logger.info(f"Starting scrape for {college_short_name} {department} (limit: {limit})")
            courses_data = await scraper.scrape_courses(department, limit)
            logger.info(f"Scraped {len(courses_data)} courses from {college_short_name} {department}")

            # Save to database
            courses_saved = 0
            classes_saved = 0
            enrollments_saved = 0

            for course_data in courses_data:
                try:
                    # Upsert course
                    course = await self._upsert_course(
                        college.id,
                        course_data['course_code'],
                        course_data['title']
                    )
                    courses_saved += 1

                    # Upsert classes
                    for class_data in course_data.get('classes', []):
                        class_obj = await self._upsert_class(course.id, class_data)
                        classes_saved += 1

                        # Create enrollment snapshot
                        await self._create_enrollment_snapshot(class_obj.class_id, class_data)
                        enrollments_saved += 1

                except Exception as e:
                    logger.error(f"Failed to save course {course_data.get('course_code')}: {e}")
                    continue

            await self.db.commit()

            # Calculate duration
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Complete scraper log
            await self.log_service.complete_log(
                log_id,
                status='success',
                courses_scraped=courses_saved,
                classes_scraped=classes_saved
            )

            logger.info(
                f"Scrape complete: {courses_saved} courses, {classes_saved} classes, "
                f"{enrollments_saved} enrollment snapshots in {duration:.2f}s"
            )

            return {
                'college': college_short_name,
                'department': department,
                'courses_saved': courses_saved,
                'classes_saved': classes_saved,
                'enrollments_saved': enrollments_saved,
                'duration_seconds': duration,
                'success': True,
                'error': None
            }

        except Exception as e:
            # Log error
            await self.log_service.complete_log(
                log_id,
                status='failed',
                error_message=str(e)
            )

            logger.error(f"Scrape failed for {college_short_name} {department}: {e}")

            duration = (datetime.now() - start_time).total_seconds()

            return {
                'college': college_short_name,
                'department': department,
                'courses_saved': 0,
                'classes_saved': 0,
                'enrollments_saved': 0,
                'duration_seconds': duration,
                'success': False,
                'error': str(e)
            }

    async def _upsert_course(
        self,
        college_id: int,
        course_code: str,
        title: str
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
        result = await self.db.execute(
            select(Course).where(
                Course.college_id == college_id,
                Course.course_code == course_code
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
                is_active=True
            )
            self.db.add(course)

        await self.db.flush()
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
        class_number = class_data.get('class_number', '')

        # Check if class exists
        result = await self.db.execute(
            select(Class).where(
                Class.course_id == course_id,
                Class.class_number == class_number
            )
        )
        class_obj = result.scalar_one_or_none()

        if class_obj:
            # Update existing class
            class_obj.section_code = class_data.get('section', '')
            class_obj.is_active = True
            class_obj.updated_at = datetime.now()
        else:
            # Create new class
            class_obj = Class(
                course_id=course_id,
                class_number=class_number,
                section_code=class_data.get('section', ''),
                is_active=True
            )
            self.db.add(class_obj)

        await self.db.flush()
        return class_obj

    async def _create_enrollment_snapshot(self, class_id: int, class_data: Dict):
        """
        Create an enrollment snapshot for tracking.

        Args:
            class_id: Class ID
            class_data: Class data with enrollment information
        """
        enrollment = Enrollment(
            class_id=class_id,
            enrolled=class_data.get('enrolled', 0),
            capacity=class_data.get('capacity', 0),
            waitlist=class_data.get('waitlist', 0),
            status=class_data.get('status', 'Unknown'),
            instructor=class_data.get('instructor', ''),
            schedule=class_data.get('schedule', ''),
            location=class_data.get('location', ''),
        )
        self.db.add(enrollment)
        await self.db.flush()
