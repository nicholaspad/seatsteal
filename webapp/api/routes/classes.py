from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload

from ...db.session import get_db
from ...models.class_model import Class
from ...models.course import Course
from ...models.college import College
from ...models.enrollment import Enrollment
from ...schemas.class_schema import ClassWithCourse
from ...schemas.course import EnrollmentStatus, CourseWithCollege
from ...schemas.college import CollegeResponse

router = APIRouter(prefix="/api/classes", tags=["classes"])


@router.get("/{class_id}", response_model=ClassWithCourse)
async def get_class(class_id: int, db: AsyncSession = Depends(get_db)):
    """Get class details with course, college, and latest enrollment"""
    try:
        # Get class with related course and college
        class_query = (
            select(Class, Course, College)
            .join(Course, Class.course_id == Course.id)
            .join(College, Course.college_id == College.id)
            .where(and_(Class.class_id == class_id, Class.is_active == True))
        )
        result = await db.execute(class_query)
        row = result.first()

        if not row:
            raise HTTPException(status_code=404, detail="Class not found")

        class_obj, course, college = row

        # Get latest enrollment
        enrollment_query = (
            select(Enrollment)
            .where(Enrollment.class_id == class_id)
            .order_by(Enrollment.scraped_at.desc())
            .limit(1)
        )
        enrollment_result = await db.execute(enrollment_query)
        enrollment = enrollment_result.scalar_one_or_none()

        # Build response
        return ClassWithCourse(
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
            course=CourseWithCollege(
                id=course.id,
                college_id=course.college_id,
                course_code=course.course_code,
                title=course.title,
                created_at=course.created_at,
                updated_at=course.updated_at,
                is_active=course.is_active,
                college=CollegeResponse.model_validate(college),
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch class details: {str(e)}")