from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional
from schemas.course import EnrollmentStatus, CourseWithCollege


class ClassBase(BaseModel):
    """Base class schema"""

    class_number: str = Field(..., alias="classNumber")
    section_code: Optional[str] = Field(None, alias="sectionCode")


class ClassCreate(ClassBase):
    """Schema for creating a class"""

    course_id: int = Field(..., alias="courseId")


class ClassResponse(ClassBase):
    """Schema for class responses"""

    class_id: int = Field(..., alias="classId")
    course_id: int = Field(..., alias="courseId")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    is_active: bool = Field(..., alias="isActive")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ClassWithEnrollment(ClassResponse):
    """Class with current enrollment status"""

    current_enrollment: Optional[EnrollmentStatus] = Field(
        None, alias="currentEnrollment"
    )


class ClassWithCourse(ClassWithEnrollment):
    """Class with nested course and college details"""

    course: CourseWithCollege
