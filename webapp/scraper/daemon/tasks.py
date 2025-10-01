from celery import Celery
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
import asyncio
from loguru import logger

from config import settings
from models.college import College
from scraper.services.scraper_service import ScraperService

# Initialize Celery
celery_app = Celery(
    'scraper',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
)

# Database engine for Celery workers
engine = create_async_engine(settings.async_database_url)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


@celery_app.task(name='scraper.scrape_college', bind=True)
def scrape_college_task(self, college_short_name: str, department: str, limit: int = None):
    """
    Celery task to scrape a specific college and department.

    Args:
        college_short_name: College identifier (e.g., 'princeton')
        department: Department code (e.g., 'CS')
        limit: Optional limit on number of courses

    Returns:
        Dict with scraping results
    """
    logger.info(f"[Task {self.request.id}] Starting scrape: {college_short_name} {department}")

    async def run_scrape():
        async with AsyncSessionLocal() as db:
            service = ScraperService(db)
            return await service.scrape_college(college_short_name, department, limit)

    try:
        result = asyncio.run(run_scrape())
        logger.info(f"[Task {self.request.id}] Scrape completed: {result}")
        return result
    except Exception as e:
        logger.error(f"[Task {self.request.id}] Scrape failed: {e}")
        raise


@celery_app.task(name='scraper.scrape_all_colleges', bind=True)
def scrape_all_colleges_task(self, department: str = None):
    """
    Celery task to scrape all active colleges.

    If department is not specified, scrapes a default set of departments
    (e.g., CS, MATH, ENG).

    Args:
        department: Optional specific department to scrape

    Returns:
        Dict with overall results
    """
    logger.info(f"[Task {self.request.id}] Starting scrape for all colleges")

    async def run_scrape_all():
        async with AsyncSessionLocal() as db:
            # Get all active colleges
            result = await db.execute(
                select(College).where(College.is_active == True)
            )
            colleges = result.scalars().all()

            logger.info(f"Found {len(colleges)} active colleges to scrape")

            results = []
            service = ScraperService(db)

            for college in colleges:
                # Determine departments to scrape
                departments_to_scrape = [department] if department else ['CS', 'MATH']

                for dept in departments_to_scrape:
                    try:
                        logger.info(f"Scraping {college.short_name} {dept}")
                        result = await service.scrape_college(
                            college.short_name,
                            dept,
                            limit=None
                        )
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Failed to scrape {college.short_name} {dept}: {e}")
                        results.append({
                            'college': college.short_name,
                            'department': dept,
                            'success': False,
                            'error': str(e)
                        })

            return {
                'colleges_scraped': len(colleges),
                'total_jobs': len(results),
                'successful_jobs': sum(1 for r in results if r.get('success')),
                'failed_jobs': sum(1 for r in results if not r.get('success')),
                'results': results
            }

    try:
        result = asyncio.run(run_scrape_all())
        logger.info(f"[Task {self.request.id}] All colleges scrape completed")
        return result
    except Exception as e:
        logger.error(f"[Task {self.request.id}] All colleges scrape failed: {e}")
        raise


@celery_app.task(name='scraper.scrape_college_all_departments', bind=True)
def scrape_college_all_departments_task(self, college_short_name: str):
    """
    Celery task to scrape all common departments for a specific college.

    Args:
        college_short_name: College identifier

    Returns:
        Dict with results for all departments
    """
    logger.info(f"[Task {self.request.id}] Starting full scrape for {college_short_name}")

    # Common department codes across universities
    common_departments = [
        'CS', 'CSCI', 'COS',  # Computer Science variants
        'MATH', 'MA',  # Math variants
        'ENG', 'ENGL',  # English variants
        'PHYS', 'PHY',  # Physics variants
        'CHEM', 'CHM',  # Chemistry variants
        'BIO', 'BIOL',  # Biology variants
        'ECON', 'ECO',  # Economics variants
        'PSYCH', 'PSY',  # Psychology variants
    ]

    async def run_scrape_departments():
        async with AsyncSessionLocal() as db:
            service = ScraperService(db)
            results = []

            for dept in common_departments:
                try:
                    result = await service.scrape_college(
                        college_short_name,
                        dept,
                        limit=None
                    )
                    if result.get('success') and result.get('courses_saved', 0) > 0:
                        results.append(result)
                except Exception as e:
                    logger.debug(f"Department {dept} not found or failed for {college_short_name}: {e}")
                    continue

            return {
                'college': college_short_name,
                'departments_scraped': len(results),
                'total_courses': sum(r.get('courses_saved', 0) for r in results),
                'total_classes': sum(r.get('classes_saved', 0) for r in results),
                'results': results
            }

    try:
        result = asyncio.run(run_scrape_departments())
        logger.info(f"[Task {self.request.id}] Full scrape completed for {college_short_name}")
        return result
    except Exception as e:
        logger.error(f"[Task {self.request.id}] Full scrape failed for {college_short_name}: {e}")
        raise


# Health check task
@celery_app.task(name='scraper.health_check')
def health_check():
    """Simple health check task"""
    return {'status': 'healthy', 'service': 'scraper'}
