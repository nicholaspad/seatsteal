from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, or_, and_, text
from typing import Optional
import math

from db.session import get_db
from models.course import Course
from models.college import College
from models.class_model import Class
from models.enrollment import Enrollment
from models.subscription import Subscription
from models.notification_log import NotificationLog
from schemas.course import (
    CourseWithClasses,
    PaginatedResponse,
    PaginationMetadata,
    EnrollmentStatus,
    ClassInCourse,
)
from schemas.college import CollegeResponse
from api.middleware.auth import require_auth
from utils.premium import require_premium_access

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.get("/")
async def get_courses(
    q: Optional[str] = Query(None, description="Search query"),
    college_id: Optional[int] = Query(
        None, alias="collegeId", description="Filter by college ID"
    ),
    enrollment: str = Query("all", description="Filter by enrollment status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    """
    Get courses with search, filtering, and pagination.

    Supports:
    - Search by course code or title
    - Filter by college
    - Pagination
    """
    try:
        # Build base query
        conditions = [Course.is_active == True]

        if college_id and college_id != 0:
            conditions.append(Course.college_id == college_id)

        # Add fuzzy search conditions using trigram similarity
        similarity_threshold = 0.1
        search_query = None
        if q:
            search_term = q.strip()
            # Calculate combined similarity score for course_code and title
            code_similarity = func.coalesce(
                func.similarity(Course.course_code, search_term), 0
            )
            title_similarity = func.coalesce(
                func.similarity(Course.title, search_term), 0
            )
            combined_similarity = code_similarity + title_similarity

            # Filter by minimum similarity threshold
            conditions.append(combined_similarity >= similarity_threshold)

            # Store the similarity expression for ordering
            search_query = combined_similarity

        # Get total count
        count_query = select(func.count()).select_from(Course).where(and_(*conditions))
        total_result = db.execute(count_query)
        total = total_result.scalar()

        # Calculate offset
        offset = (page - 1) * limit

        # Get courses with college
        courses_query = (
            select(Course)
            .options(joinedload(Course.college))
            .where(and_(*conditions))
            .order_by(
                search_query.desc() if search_query is not None else Course.course_code
            )
            .offset(offset)
            .limit(limit)
        )
        courses_result = db.execute(courses_query)
        courses = courses_result.unique().scalars().all()

        # For each course, get classes with latest enrollment
        result_data = []
        for course in courses:
            # Get classes for this course
            classes_query = (
                select(Class)
                .where(and_(Class.course_id == course.id, Class.is_active == True))
                .order_by(Class.class_number)
            )
            classes_result = db.execute(classes_query)
            classes = classes_result.scalars().all()

            # Get latest enrollment for each class
            classes_with_enrollment = []
            for class_obj in classes:
                # Get latest enrollment
                enrollment_query = (
                    select(Enrollment)
                    .where(Enrollment.class_id == class_obj.class_id)
                    .order_by(Enrollment.scraped_at.desc())
                    .limit(1)
                )
                enrollment_result = db.execute(enrollment_query)
                enrollment = enrollment_result.scalar_one_or_none()

                # Build class response
                class_data = ClassInCourse(
                    class_id=class_obj.class_id,
                    course_id=class_obj.course_id,
                    class_number=class_obj.class_number,
                    section_code=class_obj.section_code,
                    created_at=class_obj.created_at,
                    updated_at=class_obj.updated_at,
                    is_active=class_obj.is_active,
                    current_enrollment=(
                        EnrollmentStatus(
                            enrollment_status=enrollment.enrollment_status,
                            scraped_at=enrollment.scraped_at.isoformat(),
                        )
                        if enrollment
                        else None
                    ),
                )
                classes_with_enrollment.append(class_data)

            # Build course response
            course_data = CourseWithClasses(
                id=course.id,
                college_id=course.college_id,
                course_code=course.course_code,
                title=course.title,
                created_at=course.created_at,
                updated_at=course.updated_at,
                is_active=course.is_active,
                college=CollegeResponse.model_validate(course.college),
                classes=classes_with_enrollment,
            )
            result_data.append(course_data)

        # Build pagination metadata
        pagination = PaginationMetadata(
            page=page,
            limit=limit,
            total=total,
            total_pages=math.ceil(total / limit) if total > 0 else 0,
        )

        paginated_response = PaginatedResponse(data=result_data, pagination=pagination)

        return {
            "success": True,
            "data": {
                "data": paginated_response.data,
                "pagination": paginated_response.pagination,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch courses: {str(e)}"
        )


@router.get("/{course_id}")
async def get_course(course_id: int, db: Session = Depends(get_db)):
    """Get course details with classes and college"""
    try:
        # Get course with college
        course_query = (
            select(Course)
            .options(joinedload(Course.college))
            .where(and_(Course.id == course_id, Course.is_active == True))
        )
        result = db.execute(course_query)
        course = result.unique().scalar_one_or_none()

        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        # Get classes for this course
        classes_query = (
            select(Class)
            .where(and_(Class.course_id == course_id, Class.is_active == True))
            .order_by(Class.class_number)
        )
        classes_result = db.execute(classes_query)
        classes = classes_result.scalars().all()

        # Get latest enrollment for each class
        classes_with_enrollment = []
        for class_obj in classes:
            enrollment_query = (
                select(Enrollment)
                .where(Enrollment.class_id == class_obj.class_id)
                .order_by(Enrollment.scraped_at.desc())
                .limit(1)
            )
            enrollment_result = db.execute(enrollment_query)
            enrollment = enrollment_result.scalar_one_or_none()

            class_data = ClassInCourse(
                class_id=class_obj.class_id,
                course_id=class_obj.course_id,
                class_number=class_obj.class_number,
                section_code=class_obj.section_code,
                created_at=class_obj.created_at,
                updated_at=class_obj.updated_at,
                is_active=class_obj.is_active,
                current_enrollment=(
                    EnrollmentStatus(
                        enrollment_status=enrollment.enrollment_status,
                        scraped_at=enrollment.scraped_at.isoformat(),
                    )
                    if enrollment
                    else None
                ),
            )
            classes_with_enrollment.append(class_data)

        # Build response
        course_data = CourseWithClasses(
            id=course.id,
            college_id=course.college_id,
            course_code=course.course_code,
            title=course.title,
            created_at=course.created_at,
            updated_at=course.updated_at,
            is_active=course.is_active,
            college=CollegeResponse.model_validate(course.college),
            classes=classes_with_enrollment,
        )

        return {
            "success": True,
            "data": course_data,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch course details: {str(e)}"
        )


@router.get("/{course_id}/classes")
async def get_course_classes(course_id: int, db: Session = Depends(get_db)):
    """Get classes for a specific course"""
    try:
        # Verify course exists
        course_result = db.execute(
            select(Course).where(and_(Course.id == course_id, Course.is_active == True))
        )
        course = course_result.scalar_one_or_none()

        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        # Get classes with latest enrollment
        classes_query = (
            select(Class)
            .where(and_(Class.course_id == course_id, Class.is_active == True))
            .order_by(Class.class_number)
        )
        classes_result = db.execute(classes_query)
        classes = classes_result.scalars().all()

        # Build response with enrollments
        classes_with_enrollment = []
        for class_obj in classes:
            enrollment_query = (
                select(Enrollment)
                .where(Enrollment.class_id == class_obj.class_id)
                .order_by(Enrollment.scraped_at.desc())
                .limit(1)
            )
            enrollment_result = db.execute(enrollment_query)
            enrollment = enrollment_result.scalar_one_or_none()

            class_data = {
                "classId": class_obj.class_id,
                "courseId": class_obj.course_id,
                "classNumber": class_obj.class_number,
                "sectionCode": class_obj.section_code,
                "createdAt": class_obj.created_at,
                "updatedAt": class_obj.updated_at,
                "isActive": class_obj.is_active,
                "currentEnrollment": (
                    {
                        "enrollmentStatus": enrollment.enrollment_status,
                        "scrapedAt": enrollment.scraped_at.isoformat(),
                    }
                    if enrollment
                    else None
                ),
            }
            classes_with_enrollment.append(class_data)

        return {"success": True, "data": classes_with_enrollment}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch course classes: {str(e)}"
        )


@router.get("/{course_id}/summary")
async def get_course_summary(
    course_id: int,
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get course summary statistics (Premium feature)"""
    try:
        # Require premium access
        await require_premium_access(user.id, db)

        # Verify course exists
        course_result = db.execute(
            select(Course).where(and_(Course.id == course_id, Course.is_active == True))
        )
        if not course_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Course not found")

        # Get total classes for this course
        total_classes_result = db.execute(
            select(func.count())
            .select_from(Class)
            .where(and_(Class.course_id == course_id, Class.is_active == True))
        )
        total_classes = total_classes_result.scalar() or 0

        # Get total subscriptions for classes in this course
        total_subs_result = db.execute(
            select(func.count())
            .select_from(Subscription)
            .join(Class, Subscription.class_id == Class.class_id)
            .where(
                and_(
                    Class.course_id == course_id,
                    Subscription.is_active == True,
                    Class.is_active == True,
                )
            )
        )
        total_subscriptions = total_subs_result.scalar() or 0

        # Get classes with subscriptions count
        classes_with_subs_result = db.execute(
            select(func.count(func.distinct(Class.class_id)))
            .select_from(Class)
            .join(Subscription, Class.class_id == Subscription.class_id)
            .where(
                and_(
                    Class.course_id == course_id,
                    Subscription.is_active == True,
                    Class.is_active == True,
                )
            )
        )
        classes_with_subscriptions = classes_with_subs_result.scalar() or 0

        # Get unique subscribed users count
        unique_users_result = db.execute(
            select(func.count(func.distinct(Subscription.user_id)))
            .select_from(Subscription)
            .join(Class, Subscription.class_id == Class.class_id)
            .where(
                and_(
                    Class.course_id == course_id,
                    Subscription.is_active == True,
                    Class.is_active == True,
                )
            )
        )
        unique_subscribed_users = unique_users_result.scalar() or 0

        # Get total notifications sent
        total_notifs_result = db.execute(
            select(func.count())
            .select_from(NotificationLog)
            .join(Subscription, NotificationLog.subscription_id == Subscription.id)
            .join(Class, Subscription.class_id == Class.class_id)
            .where(
                and_(
                    Class.course_id == course_id,
                    NotificationLog.status == "sent",
                    Class.is_active == True,
                )
            )
        )
        total_notifications_sent = total_notifs_result.scalar() or 0

        from datetime import datetime

        return {
            "success": True,
            "data": {
                "courseId": course_id,
                "totalSubscriptions": total_subscriptions,
                "classesWithSubscriptions": classes_with_subscriptions,
                "uniqueSubscribedUsers": unique_subscribed_users,
                "totalNotificationsSent": total_notifications_sent,
                "totalClasses": total_classes,
                "generatedAt": datetime.utcnow().isoformat(),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch course summary: {str(e)}"
        )
