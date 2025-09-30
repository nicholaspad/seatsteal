from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from .course import EnrollmentStatus, CourseWithCollege


class ClassBase(BaseModel):
    """Base class schema"""

    class_number: str
    section_code: Optional[str] = None


class ClassCreate(ClassBase):
    """Schema for creating a class"""

    course_id: int


class ClassResponse(ClassBase):
    """Schema for class responses"""

    class_id: int
    course_id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ClassWithEnrollment(ClassResponse):
    """Class with current enrollment status"""

    current_enrollment: Optional[EnrollmentStatus] = None


class ClassWithCourse(ClassWithEnrollment):
    """Class with nested course and college details"""

    course: CourseWithCollege