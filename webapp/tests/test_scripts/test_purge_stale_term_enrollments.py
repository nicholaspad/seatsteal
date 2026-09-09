"""Tests for purge_stale_term_enrollments.py script."""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from sqlalchemy.orm import Session

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from purge_stale_term_enrollments import purge_stale_enrollments, preview_counts

from models.college import College
from models.course import Course
from models.class_model import Class
from models.enrollment import Enrollment
from models.subscription import Subscription
from models.user import Profile


@pytest.fixture
def cornell_college(test_db: Session) -> College:
    """Create a Cornell test college."""
    college = College(
        name="Cornell University",
        short_name="cornell",
        is_active=True,
    )
    test_db.add(college)
    test_db.commit()
    test_db.refresh(college)
    return college


@pytest.fixture
def stale_data_setup(test_db: Session, cornell_college: College, test_user: Profile):
    """
    Set up stale term data scenario:
    - Old term course with old enrollments (scraped 30 days ago)
    - New term course with recent enrollments (scraped 1 day ago)
    - Mixed course with both old and new enrollments
    """
    now = datetime.now(timezone.utc)
    old_timestamp = now - timedelta(days=30)
    new_timestamp = now - timedelta(days=1)

    # Old term course (should be deleted)
    old_course = Course(
        college_id=cornell_college.id,
        course_code="CS2110",
        title="Object-Oriented Programming and Data Structures",
        is_active=True,
    )
    test_db.add(old_course)
    test_db.commit()
    test_db.refresh(old_course)

    old_class = Class(
        course_id=old_course.id,
        class_number="12345",
        section_code="LEC",
        is_active=True,
    )
    test_db.add(old_class)
    test_db.commit()
    test_db.refresh(old_class)

    # Backdate created_at to make it "old" (created_at < cutoff)
    test_db.execute(
        text("UPDATE classes SET created_at = :old_time WHERE class_id = :class_id"),
        {"old_time": old_timestamp, "class_id": old_class.class_id},
    )
    test_db.commit()
    test_db.refresh(old_class)

    old_enrollment = Enrollment(
        class_id=old_class.class_id,
        college_id=cornell_college.id,
        enrollment_status="closed",
        scraped_at=old_timestamp,
    )
    test_db.add(old_enrollment)

    # New term course (should NOT be deleted)
    new_course = Course(
        college_id=cornell_college.id,
        course_code="CS3110",
        title="Data Structures and Functional Programming",
        is_active=True,
    )
    test_db.add(new_course)
    test_db.commit()
    test_db.refresh(new_course)

    new_class = Class(
        course_id=new_course.id,
        class_number="54321",
        section_code="LEC",
        is_active=True,
    )
    test_db.add(new_class)
    test_db.commit()
    test_db.refresh(new_class)

    new_enrollment = Enrollment(
        class_id=new_class.class_id,
        college_id=cornell_college.id,
        enrollment_status="open",
        scraped_at=new_timestamp,
    )
    test_db.add(new_enrollment)

    # Mixed course - has both old and new enrollments (should keep course/class, delete old enrollment)
    mixed_course = Course(
        college_id=cornell_college.id,
        course_code="CS4410",
        title="Operating Systems",
        is_active=True,
    )
    test_db.add(mixed_course)
    test_db.commit()
    test_db.refresh(mixed_course)

    mixed_class = Class(
        course_id=mixed_course.id,
        class_number="99999",
        section_code="LEC",
        is_active=True,
    )
    test_db.add(mixed_class)
    test_db.commit()
    test_db.refresh(mixed_class)

    mixed_old_enrollment = Enrollment(
        class_id=mixed_class.class_id,
        college_id=cornell_college.id,
        enrollment_status="closed",
        scraped_at=old_timestamp,
    )
    test_db.add(mixed_old_enrollment)

    mixed_new_enrollment = Enrollment(
        class_id=mixed_class.class_id,
        college_id=cornell_college.id,
        enrollment_status="open",
        scraped_at=new_timestamp,
    )
    test_db.add(mixed_new_enrollment)

    test_db.commit()

    return {
        "cornell_college": cornell_college,
        "old_course": old_course,
        "old_class": old_class,
        "old_enrollment": old_enrollment,
        "new_course": new_course,
        "new_class": new_class,
        "new_enrollment": new_enrollment,
        "mixed_course": mixed_course,
        "mixed_class": mixed_class,
        "mixed_old_enrollment": mixed_old_enrollment,
        "mixed_new_enrollment": mixed_new_enrollment,
        "cutoff_timestamp": now - timedelta(days=15),  # Cutoff between old and new
    }


def test_preview_counts(test_db: Session, stale_data_setup):
    """Test preview_counts function returns correct counts."""
    college_id = stale_data_setup["cornell_college"].id
    cutoff = stale_data_setup["cutoff_timestamp"]

    counts = preview_counts(test_db, college_id, cutoff)

    # Should find 2 stale enrollments (old_enrollment + mixed_old_enrollment)
    assert counts["stale_enrollments"] == 2

    # Should find 1 orphan class (old_class has no new enrollments and created_at < cutoff)
    assert counts["orphan_classes"] == 1

    # Should find 1 empty course (old_course will have no classes after purge)
    assert counts["empty_courses"] == 1

    # No subscriptions yet
    assert counts["blocking_subscriptions"] == 0


def test_purge_dry_run(test_db: Session, stale_data_setup):
    """Test dry run does not delete anything."""
    cutoff = stale_data_setup["cutoff_timestamp"]

    # Count before
    enrollments_before = test_db.query(Enrollment).count()
    classes_before = test_db.query(Class).count()
    courses_before = test_db.query(Course).count()

    # Dry run
    result = purge_stale_enrollments(
        "cornell",
        cutoff,
        dry_run=True,
        force_skip_subscribed=False,
        db_session=test_db,
    )

    # Dry run returns None
    assert result is None

    # Refresh to get latest state
    test_db.expire_all()

    # Nothing should be deleted
    assert test_db.query(Enrollment).count() == enrollments_before
    assert test_db.query(Class).count() == classes_before
    assert test_db.query(Course).count() == courses_before


def test_purge_confirm(test_db: Session, stale_data_setup):
    """Test actual purge with --confirm deletes correct data."""
    cutoff = stale_data_setup["cutoff_timestamp"]

    # Purge with confirmation
    result = purge_stale_enrollments(
        "cornell",
        cutoff,
        dry_run=False,
        force_skip_subscribed=False,
        db_session=test_db,
    )

    # Should delete 2 enrollments, 1 class, 1 course
    assert result["enrollments"] == 2
    assert result["classes"] == 1
    assert result["courses"] == 1

    # Refresh to get latest state after deletion
    test_db.expire_all()

    # Verify old course/class/enrollment are deleted
    assert (
        test_db.query(Course)
        .filter_by(id=stale_data_setup["old_course"].id)
        .first()
        is None
    )
    assert (
        test_db.query(Class)
        .filter_by(class_id=stale_data_setup["old_class"].class_id)
        .first()
        is None
    )
    assert (
        test_db.query(Enrollment)
        .filter_by(id=stale_data_setup["old_enrollment"].id)
        .first()
        is None
    )

    # Verify new course/class/enrollment are NOT deleted
    assert (
        test_db.query(Course)
        .filter_by(id=stale_data_setup["new_course"].id)
        .first()
        is not None
    )
    assert (
        test_db.query(Class)
        .filter_by(class_id=stale_data_setup["new_class"].class_id)
        .first()
        is not None
    )
    assert (
        test_db.query(Enrollment)
        .filter_by(id=stale_data_setup["new_enrollment"].id)
        .first()
        is not None
    )

    # Verify mixed course/class still exist (has new enrollment)
    assert (
        test_db.query(Course)
        .filter_by(id=stale_data_setup["mixed_course"].id)
        .first()
        is not None
    )
    assert (
        test_db.query(Class)
        .filter_by(class_id=stale_data_setup["mixed_class"].class_id)
        .first()
        is not None
    )

    # Verify mixed old enrollment is deleted, new enrollment is NOT deleted
    assert (
        test_db.query(Enrollment)
        .filter_by(id=stale_data_setup["mixed_old_enrollment"].id)
        .first()
        is None
    )
    assert (
        test_db.query(Enrollment)
        .filter_by(id=stale_data_setup["mixed_new_enrollment"].id)
        .first()
        is not None
    )


def test_purge_abort_with_subscriptions(
    test_db: Session, stale_data_setup, test_user: Profile
):
    """Test purge aborts if subscriptions exist on classes that would be deleted."""
    cutoff = stale_data_setup["cutoff_timestamp"]
    old_class_id = stale_data_setup["old_class"].class_id
    cornell_id = stale_data_setup["cornell_college"].id

    # Add subscription to old class
    subscription = Subscription(
        user_id=test_user.id,
        class_id=old_class_id,
        college_id=cornell_id,
        is_active=True,
        notification_count=0,
    )
    test_db.add(subscription)
    test_db.commit()

    # Should abort without force_skip_subscribed
    result = purge_stale_enrollments(
        "cornell",
        cutoff,
        dry_run=False,
        force_skip_subscribed=False,
        db_session=test_db,
    )

    # Should return None (aborted)
    assert result is None

    # Refresh to get latest state
    test_db.expire_all()

    # Nothing should be deleted
    assert (
        test_db.query(Enrollment)
        .filter_by(id=stale_data_setup["old_enrollment"].id)
        .first()
        is not None
    )


def test_purge_force_skip_subscribed(
    test_db: Session, stale_data_setup, test_user: Profile
):
    """Test purge with --force-skip-subscribed skips classes with subscriptions but NEVER deletes them."""
    cutoff = stale_data_setup["cutoff_timestamp"]
    old_class_id = stale_data_setup["old_class"].class_id
    cornell_id = stale_data_setup["cornell_college"].id

    # Add subscription to old class
    subscription = Subscription(
        user_id=test_user.id,
        class_id=old_class_id,
        college_id=cornell_id,
        is_active=True,
        notification_count=0,
    )
    test_db.add(subscription)
    test_db.commit()

    # Should proceed with force_skip_subscribed
    result = purge_stale_enrollments(
        "cornell",
        cutoff,
        dry_run=False,
        force_skip_subscribed=True,
        db_session=test_db,
    )

    # Should delete enrollments but NOT the subscribed class (force_skip means skip, not delete)
    assert result["enrollments"] == 2  # Both old enrollments
    assert result["classes"] == 0  # Old class NOT deleted (has subscription)
    assert result["courses"] == 0  # Old course NOT deleted (still has class)

    # Refresh to get latest state after deletion
    test_db.expire_all()

    # Verify old class still exists (NEVER deleted because of subscription)
    assert (
        test_db.query(Class)
        .filter_by(class_id=stale_data_setup["old_class"].class_id)
        .first()
        is not None
    )

    # Verify subscription still exists (NEVER deleted)
    assert test_db.query(Subscription).filter_by(class_id=old_class_id).first() is not None


def test_purge_nonexistent_college(test_db: Session):
    """Test purge with nonexistent college returns None."""
    cutoff = datetime.now(timezone.utc)

    result = purge_stale_enrollments(
        "nonexistent",
        cutoff,
        dry_run=False,
        force_skip_subscribed=False,
        db_session=test_db,
    )

    assert result is None


def test_purge_no_stale_data(test_db: Session, cornell_college: College):
    """Test purge with no stale data returns zero counts."""
    cutoff = datetime.now(timezone.utc) + timedelta(days=30)  # Future cutoff

    result = purge_stale_enrollments(
        "cornell",
        cutoff,
        dry_run=False,
        force_skip_subscribed=False,
        db_session=test_db,
    )

    assert result == {"enrollments": 0, "classes": 0, "courses": 0}


def test_cross_college_isolation(test_db: Session):
    """Test that purging one college doesn't affect another college's data."""
    now = datetime.now(timezone.utc)
    old_timestamp = now - timedelta(days=30)
    cutoff = now - timedelta(days=15)

    # Create two colleges
    college_a = College(name="College A", short_name="colla", is_active=True)
    college_b = College(name="College B", short_name="collb", is_active=True)
    test_db.add(college_a)
    test_db.add(college_b)
    test_db.commit()
    test_db.refresh(college_a)
    test_db.refresh(college_b)

    # Create old data for both colleges
    for college in [college_a, college_b]:
        course = Course(
            college_id=college.id,
            course_code="CS101",
            title="Test Course",
            is_active=True,
        )
        test_db.add(course)
        test_db.commit()
        test_db.refresh(course)

        cls = Class(
            course_id=course.id,
            class_number="12345",
            section_code="A",
            is_active=True,
        )
        test_db.add(cls)
        test_db.commit()
        test_db.refresh(cls)

        # Backdate created_at
        test_db.execute(
            text("UPDATE classes SET created_at = :old_time WHERE class_id = :class_id"),
            {"old_time": old_timestamp, "class_id": cls.class_id},
        )
        test_db.commit()

        enrollment = Enrollment(
            class_id=cls.class_id,
            college_id=college.id,
            enrollment_status="open",
            scraped_at=old_timestamp,
        )
        test_db.add(enrollment)

    test_db.commit()

    # Count college_b data before purge
    college_b_enrollments = (
        test_db.query(Enrollment).filter_by(college_id=college_b.id).count()
    )
    college_b_courses = (
        test_db.query(Course).filter_by(college_id=college_b.id).count()
    )

    # Purge college A only
    result = purge_stale_enrollments(
        "colla",
        cutoff,
        dry_run=False,
        force_skip_subscribed=False,
        db_session=test_db,
    )

    assert result["enrollments"] == 1
    assert result["classes"] == 1
    assert result["courses"] == 1

    # Refresh to get latest state
    test_db.expire_all()

    # College B data should be untouched
    assert (
        test_db.query(Enrollment).filter_by(college_id=college_b.id).count()
        == college_b_enrollments
    )
    assert (
        test_db.query(Course).filter_by(college_id=college_b.id).count()
        == college_b_courses
    )
