from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List, Generic, TypeVar
from .college import CollegeResponse

T = TypeVar("T")


class CourseBase(BaseModel):
    """Base course schema"""

    course_code: str
    title: str


class CourseCreate(CourseBase):
    """Schema for creating a course"""

    college_id: int


class CourseResponse(CourseBase):
    """Schema for course responses"""

    id: int
    college_id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class EnrollmentStatus(BaseModel):
    """Current enrollment status for a class"""

    enrollment_status: str
    scraped_at: str


class ClassInCourse(BaseModel):
    """Class details within a course"""

    class_id: int
    course_id: int
    class_number: str
    section_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool
    current_enrollment: Optional[EnrollmentStatus] = None

    model_config = ConfigDict(from_attributes=True)


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
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""

    data: List[T]
    pagination: PaginationMetadata
