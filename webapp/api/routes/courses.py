from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, text
from sqlalchemy.orm import joinedload
from typing import Optional
import math

from ...db.session import get_db
from ...models.course import Course
from ...models.college import College
from ...models.class_model import Class
from ...models.enrollment import Enrollment
from ...schemas.course import (
    CourseWithClasses,
    PaginatedResponse,
    PaginationMetadata,
    EnrollmentStatus,
    ClassInCourse,
)
from ...schemas.college import CollegeResponse

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.get("/", response_model=PaginatedResponse[CourseWithClasses])
async def get_courses(
    q: Optional[str] = Query(None, description="Search query"),
    college_id: Optional[int] = Query(
        None, alias="collegeId", description="Filter by college ID"
    ),
    enrollment: str = Query("all", description="Filter by enrollment status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
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

        # Add search conditions
        if q:
            search_term = q.strip().upper()
            search_conditions = or_(
                func.upper(Course.course_code).like(f"{search_term}%"),
                func.upper(Course.title).like(f"%{search_term}%"),
                func.upper(Course.course_code).like(f"%{search_term}%"),
            )
            conditions.append(search_conditions)

        # Get total count
        count_query = select(func.count()).select_from(Course).where(and_(*conditions))
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Calculate offset
        offset = (page - 1) * limit

        # Get courses with college
        courses_query = (
            select(Course)
            .options(joinedload(Course.college))
            .where(and_(*conditions))
            .order_by(Course.course_code)
            .offset(offset)
            .limit(limit)
        )
        courses_result = await db.execute(courses_query)
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
            classes_result = await db.execute(classes_query)
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
                enrollment_result = await db.execute(enrollment_query)
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

        return PaginatedResponse(data=result_data, pagination=pagination)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch courses: {str(e)}"
        )
