from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class TermUpdateRequest(BaseModel):
    """Request schema for updating a college's term code"""

    term_code: str = Field(..., alias="termCode", min_length=1)
    term_name: Optional[str] = Field(None, alias="termName")

    model_config = ConfigDict(populate_by_name=True)


class TermUpdateCleanupStats(BaseModel):
    """Statistics about data cleaned up during term update"""

    subscriptions_deactivated: int = Field(..., alias="subscriptionsDeactivated")
    enrollments_deleted: int = Field(..., alias="enrollmentsDeleted")
    classes_deleted: int = Field(..., alias="classesDeleted")
    courses_deleted: int = Field(..., alias="coursesDeleted")

    model_config = ConfigDict(populate_by_name=True)


class TermUpdateResponse(BaseModel):
    """Response schema for term update endpoint"""

    college_id: int = Field(..., alias="collegeId")
    short_name: str = Field(..., alias="shortName")
    old_term_code: Optional[str] = Field(None, alias="oldTermCode")
    new_term_code: str = Field(..., alias="newTermCode")
    old_term_name: Optional[str] = Field(None, alias="oldTermName")
    new_term_name: Optional[str] = Field(None, alias="newTermName")
    cleanup: TermUpdateCleanupStats

    model_config = ConfigDict(populate_by_name=True)
