"""Tests for ScraperService enrollment status-change detection logic."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

import sys
from pathlib import Path

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from scraper.services.scraper_service import ScraperService
from models.college import College
from models.course import Course
from models.class_model import Class
from models.enrollment import Enrollment


@pytest.fixture
def test_college(test_db: Session) -> College:
    """Create a test college."""
    college = College(
        name="Test University",
        short_name="test",
        domain="test.edu",
        term_code="2024FA",
        term_name="Fall 2024",
        is_active=True,
    )
    test_db.add(college)
    test_db.commit()
    test_db.refresh(college)
    return college


@pytest.fixture
def test_course(test_db: Session, test_college: College) -> Course:
    """Create a test course."""
    course = Course(
        college_id=test_college.id,
        course_code="CS 101",
        title="Introduction to Computer Science",
        is_active=True,
    )
    test_db.add(course)
    test_db.commit()
    test_db.refresh(course)
    return course


@pytest.fixture
def test_class(test_db: Session, test_course: Course) -> Class:
    """Create a test class."""
    class_obj = Class(
        course_id=test_course.id,
        class_number="12345",
        section_code="001",
        is_active=True,
    )
    test_db.add(class_obj)
    test_db.commit()
    test_db.refresh(class_obj)
    return class_obj


@pytest.fixture
def scraper_service(test_db: Session) -> ScraperService:
    """Create a ScraperService instance."""
    return ScraperService(test_db)


def test_first_enrollment_insert(
    scraper_service: ScraperService,
    test_db: Session,
    test_college: College,
    test_class: Class,
):
    """Test that first enrollment for a class is inserted."""
    enrollment_data = [
        {
            "class_id": test_class.class_id,
            "college_id": test_college.id,
            "enrollment_status": "closed",
            "raw_text": '{"test": "data"}',
        }
    ]

    # Insert enrollments
    inserted = scraper_service._batch_insert_enrollments(enrollment_data)

    # Verify insertion
    assert inserted == 1

    # Check database
    enrollments = (
        test_db.query(Enrollment).filter_by(class_id=test_class.class_id).all()
    )
    assert len(enrollments) == 1
    assert enrollments[0].enrollment_status == "closed"


def test_status_change_closed_to_open(
    scraper_service: ScraperService,
    test_db: Session,
    test_college: College,
    test_class: Class,
):
    """Test that status change from closed to open inserts new enrollment."""
    # Insert initial enrollment
    initial_enrollment = Enrollment(
        class_id=test_class.class_id,
        college_id=test_college.id,
        enrollment_status="closed",
        raw_text='{"initial": "closed"}',
        scraped_at=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
    )
    test_db.add(initial_enrollment)
    test_db.commit()

    # Scrape with new status (closed -> open)
    enrollment_data = [
        {
            "class_id": test_class.class_id,
            "college_id": test_college.id,
            "enrollment_status": "open",
            "raw_text": '{"changed": "to_open"}',
        }
    ]

    inserted = scraper_service._batch_insert_enrollments(enrollment_data)

    # Verify insertion
    assert inserted == 1

    # Check database - should have 2 enrollments now
    enrollments = (
        test_db.query(Enrollment)
        .filter_by(class_id=test_class.class_id)
        .order_by(Enrollment.scraped_at)
        .all()
    )
    assert len(enrollments) == 2
    assert enrollments[0].enrollment_status == "closed"
    assert enrollments[1].enrollment_status == "open"


def test_status_change_open_to_closed(
    scraper_service: ScraperService,
    test_db: Session,
    test_college: College,
    test_class: Class,
):
    """Test that status change from open to closed inserts new enrollment."""
    # Insert initial enrollment
    initial_enrollment = Enrollment(
        class_id=test_class.class_id,
        college_id=test_college.id,
        enrollment_status="open",
        raw_text='{"initial": "open"}',
        scraped_at=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
    )
    test_db.add(initial_enrollment)
    test_db.commit()

    # Scrape with new status (open -> closed)
    enrollment_data = [
        {
            "class_id": test_class.class_id,
            "college_id": test_college.id,
            "enrollment_status": "closed",
            "raw_text": '{"changed": "to_closed"}',
        }
    ]

    inserted = scraper_service._batch_insert_enrollments(enrollment_data)

    # Verify insertion
    assert inserted == 1

    # Check database - should have 2 enrollments now
    enrollments = (
        test_db.query(Enrollment)
        .filter_by(class_id=test_class.class_id)
        .order_by(Enrollment.scraped_at)
        .all()
    )
    assert len(enrollments) == 2
    assert enrollments[0].enrollment_status == "open"
    assert enrollments[1].enrollment_status == "closed"


def test_status_unchanged_updates_timestamp(
    scraper_service: ScraperService,
    test_db: Session,
    test_college: College,
    test_class: Class,
):
    """Test that unchanged status updates timestamp instead of inserting."""
    # Insert initial enrollment
    initial_scraped_at = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    initial_enrollment = Enrollment(
        class_id=test_class.class_id,
        college_id=test_college.id,
        enrollment_status="closed",
        raw_text='{"initial": "closed"}',
        scraped_at=initial_scraped_at,
    )
    test_db.add(initial_enrollment)
    test_db.commit()
    initial_id = initial_enrollment.id

    # Scrape with same status (closed -> closed)
    enrollment_data = [
        {
            "class_id": test_class.class_id,
            "college_id": test_college.id,
            "enrollment_status": "closed",
            "raw_text": '{"still": "closed"}',
        }
    ]

    inserted = scraper_service._batch_insert_enrollments(enrollment_data)

    # Verify 1 processed (timestamp update)
    assert inserted == 1

    # Check database - should still have only 1 enrollment
    enrollments = (
        test_db.query(Enrollment).filter_by(class_id=test_class.class_id).all()
    )
    assert len(enrollments) == 1

    # But timestamp should be updated
    test_db.refresh(enrollments[0])
    assert enrollments[0].id == initial_id
    assert enrollments[0].enrollment_status == "closed"
    assert enrollments[0].scraped_at > initial_scraped_at


def test_status_unchanged_open_updates_timestamp(
    scraper_service: ScraperService,
    test_db: Session,
    test_college: College,
    test_class: Class,
):
    """Test that unchanged open status updates timestamp instead of inserting."""
    # Insert initial enrollment
    initial_scraped_at = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    initial_enrollment = Enrollment(
        class_id=test_class.class_id,
        college_id=test_college.id,
        enrollment_status="open",
        raw_text='{"initial": "open"}',
        scraped_at=initial_scraped_at,
    )
    test_db.add(initial_enrollment)
    test_db.commit()
    initial_id = initial_enrollment.id

    # Scrape with same status (open -> open)
    enrollment_data = [
        {
            "class_id": test_class.class_id,
            "college_id": test_college.id,
            "enrollment_status": "open",
            "raw_text": '{"still": "open"}',
        }
    ]

    inserted = scraper_service._batch_insert_enrollments(enrollment_data)

    # Verify 1 processed (timestamp update)
    assert inserted == 1

    # Check database - should still have only 1 enrollment
    enrollments = (
        test_db.query(Enrollment).filter_by(class_id=test_class.class_id).all()
    )
    assert len(enrollments) == 1

    # But timestamp should be updated
    test_db.refresh(enrollments[0])
    assert enrollments[0].id == initial_id
    assert enrollments[0].enrollment_status == "open"
    assert enrollments[0].scraped_at > initial_scraped_at


def test_batch_with_mixed_scenarios(
    scraper_service: ScraperService,
    test_db: Session,
    test_college: College,
    test_course: Course,
):
    """Test batch processing with mix of inserts and updates."""
    # Create three classes
    class1 = Class(
        course_id=test_course.id,
        class_number="10001",
        section_code="001",
        is_active=True,
    )
    class2 = Class(
        course_id=test_course.id,
        class_number="10002",
        section_code="002",
        is_active=True,
    )
    class3 = Class(
        course_id=test_course.id,
        class_number="10003",
        section_code="003",
        is_active=True,
    )
    test_db.add_all([class1, class2, class3])
    test_db.commit()
    test_db.refresh(class1)
    test_db.refresh(class2)
    test_db.refresh(class3)

    # Insert initial enrollments for class1 and class2
    enrollment1 = Enrollment(
        class_id=class1.class_id,
        college_id=test_college.id,
        enrollment_status="closed",
        raw_text='{"initial": "closed"}',
        scraped_at=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
    )
    enrollment2 = Enrollment(
        class_id=class2.class_id,
        college_id=test_college.id,
        enrollment_status="open",
        raw_text='{"initial": "open"}',
        scraped_at=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
    )
    test_db.add_all([enrollment1, enrollment2])
    test_db.commit()

    # Scrape batch:
    # - class1: closed -> open (should INSERT)
    # - class2: open -> open (should UPDATE timestamp)
    # - class3: first time (should INSERT)
    enrollment_data = [
        {
            "class_id": class1.class_id,
            "college_id": test_college.id,
            "enrollment_status": "open",  # Changed
            "raw_text": '{"changed": "to_open"}',
        },
        {
            "class_id": class2.class_id,
            "college_id": test_college.id,
            "enrollment_status": "open",  # Unchanged
            "raw_text": '{"still": "open"}',
        },
        {
            "class_id": class3.class_id,
            "college_id": test_college.id,
            "enrollment_status": "closed",  # First time
            "raw_text": '{"first": "time"}',
        },
    ]

    inserted = scraper_service._batch_insert_enrollments(enrollment_data)

    # Should have 3 processed (2 inserts + 1 update)
    assert inserted == 3

    # Verify class1 - should have 2 enrollments (original + new)
    class1_enrollments = (
        test_db.query(Enrollment)
        .filter_by(class_id=class1.class_id)
        .order_by(Enrollment.scraped_at)
        .all()
    )
    assert len(class1_enrollments) == 2
    assert class1_enrollments[0].enrollment_status == "closed"
    assert class1_enrollments[1].enrollment_status == "open"

    # Verify class2 - should still have 1 enrollment with updated timestamp
    class2_enrollments = (
        test_db.query(Enrollment).filter_by(class_id=class2.class_id).all()
    )
    assert len(class2_enrollments) == 1
    test_db.refresh(class2_enrollments[0])
    assert class2_enrollments[0].enrollment_status == "open"
    assert class2_enrollments[0].scraped_at > datetime(
        2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc
    )

    # Verify class3 - should have 1 enrollment (first insert)
    class3_enrollments = (
        test_db.query(Enrollment).filter_by(class_id=class3.class_id).all()
    )
    assert len(class3_enrollments) == 1
    assert class3_enrollments[0].enrollment_status == "closed"


def test_get_latest_enrollments(
    scraper_service: ScraperService,
    test_db: Session,
    test_college: College,
    test_class: Class,
):
    """Test _get_latest_enrollments helper method."""
    # Insert multiple enrollments for the same class
    enrollment1 = Enrollment(
        class_id=test_class.class_id,
        college_id=test_college.id,
        enrollment_status="closed",
        raw_text='{"first": "closed"}',
        scraped_at=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
    )
    enrollment2 = Enrollment(
        class_id=test_class.class_id,
        college_id=test_college.id,
        enrollment_status="open",
        raw_text='{"second": "open"}',
        scraped_at=datetime(2024, 1, 2, 10, 0, 0, tzinfo=timezone.utc),
    )
    enrollment3 = Enrollment(
        class_id=test_class.class_id,
        college_id=test_college.id,
        enrollment_status="closed",
        raw_text='{"third": "closed"}',
        scraped_at=datetime(2024, 1, 3, 10, 0, 0, tzinfo=timezone.utc),
    )
    test_db.add_all([enrollment1, enrollment2, enrollment3])
    test_db.commit()

    # Get latest enrollments
    latest = scraper_service._get_latest_enrollments([test_class.class_id])

    # Should return the most recent one (enrollment3)
    assert len(latest) == 1
    assert test_class.class_id in latest
    assert latest[test_class.class_id]["id"] == enrollment3.id
    assert latest[test_class.class_id]["status"] == "closed"


def test_empty_enrollment_list(scraper_service: ScraperService, test_db: Session):
    """Test that empty enrollment list returns 0."""
    inserted = scraper_service._batch_insert_enrollments([])
    assert inserted == 0


@pytest.mark.asyncio
async def test_zero_courses_marked_as_partial_failure(test_db: Session, test_college: College):
    """Test that scraping 0 courses returns success=False with outcome='partial'."""
    service = ScraperService(test_db)
    
    # Mock the scraper to return empty course list
    with patch('scraper.services.scraper_service.SCRAPER_MAP') as mock_scraper_map:
        mock_scraper_class = MagicMock()
        mock_scraper_instance = MagicMock()
        mock_scraper_instance.scrape_courses = MagicMock(return_value=[])
        mock_scraper_class.return_value = mock_scraper_instance
        mock_scraper_map.get.return_value = mock_scraper_class
        
        result = await service.scrape_college(test_college.short_name, "CS")
        
        # Verify partial failure result
        assert result["success"] is False
        assert result["outcome"] == "partial"
        assert result["courses_saved"] == 0
        assert "0 courses" in result["error"]


@pytest.mark.asyncio
async def test_zero_enrollments_marked_as_partial_failure(test_db: Session, test_college: College):
    """Test that scraping courses but 0 enrollments returns success=False with outcome='partial'."""
    service = ScraperService(test_db)
    
    # Mock the scraper to return courses with missing/invalid enrollment data
    # This simulates the production failure mode from 2026-02-05
    with patch('scraper.services.scraper_service.SCRAPER_MAP') as mock_scraper_map:
        mock_scraper_class = MagicMock()
        mock_scraper_instance = MagicMock()
        # Return courses/classes but with missing status data (no enrollments will be created)
        mock_scraper_instance.scrape_courses = MagicMock(return_value=[
            {
                "course_code": "CS 101",
                "title": "Test Course",
                "classes": [
                    {
                        "class_number": "12345",
                        "section": "001",
                        # Missing 'status' field - will result in 0 enrollments
                    }
                ]
            }
        ])
        mock_scraper_class.return_value = mock_scraper_instance
        mock_scraper_map.get.return_value = mock_scraper_class
        
        result = await service.scrape_college(test_college.short_name, "CS")
        
        # Verify partial failure result
        assert result["success"] is False
        assert result["outcome"] == "partial"
        assert result["courses_saved"] > 0
        assert result["enrollments_saved"] == 0
        assert "0 enrollments" in result["error"]
        assert "seat notifications will not fire" in result["error"]


def test_get_latest_enrollments_empty_list(
    scraper_service: ScraperService, test_db: Session
):
    """Test _get_latest_enrollments with empty list."""
    latest = scraper_service._get_latest_enrollments([])
    assert latest == {}
