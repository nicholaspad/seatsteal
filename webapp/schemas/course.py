from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List, Generic, TypeVar
from .college import CollegeResponse

T = TypeVar("T")


class CourseBase(BaseModel):
    """Base course schema"""

    course_code: str = Field(..., alias="courseCode")
    title: str


class CourseCreate(CourseBase):
    """Schema for creating a course"""

    college_id: int = Field(..., alias="collegeId")


class CourseResponse(CourseBase):
    """Schema for course responses"""

    id: int
    college_id: int = Field(..., alias="collegeId")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    is_active: bool = Field(..., alias="isActive")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class EnrollmentStatus(BaseModel):
    """Current enrollment status for a class"""

    enrollment_status: str = Field(..., alias="enrollmentStatus")
    scraped_at: str = Field(..., alias="scrapedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ClassInCourse(BaseModel):
    """Class details within a course"""

    class_id: int = Field(..., alias="classId")
    course_id: int = Field(..., alias="courseId")
    class_number: str = Field(..., alias="classNumber")
    section_code: Optional[str] = Field(None, alias="sectionCode")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    is_active: bool = Field(..., alias="isActive")
    current_enrollment: Optional[EnrollmentStatus] = Field(
        None, alias="currentEnrollment"
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class CourseWithCollege(CourseResponse):
    """Course with nested college details"""

    college: CollegeResponse


class CourseWithClasses(CourseWithCollege):
    """Course with nested classes and college"""

    classes: List[ClassInCourse] = []


class CourseSearchParams(BaseModel):
    """Search parameters for courses"""

    q: Optional[str] = None
    college_id: Optional[int] = Field(None, alias="collegeId")
    enrollment: str = "all"
    page: int = 1
    limit: int = Field(20, le=100)


class PaginationMetadata(BaseModel):
    """Pagination metadata"""

    page: int
    limit: int
    total: int
    total_pages: int = Field(..., alias="totalPages")

    model_config = ConfigDict(populate_by_name=True)


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""

    data: List[T]
    pagination: PaginationMetadata
