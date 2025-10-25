from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional


class CollegeBase(BaseModel):
    """Base college schema"""

    name: str
    short_name: str = Field(..., alias="shortName")
    domain: Optional[str] = None
    term_code: Optional[str] = Field(None, alias="termCode")
    term_name: Optional[str] = Field(None, alias="termName")
    email_enabled: bool = Field(True, alias="emailEnabled")
    sms_enabled: bool = Field(False, alias="smsEnabled")


class CollegeCreate(CollegeBase):
    """Schema for creating a college"""

    pass


class CollegeResponse(CollegeBase):
    """Schema for college responses"""

    id: int
    created_at: datetime = Field(..., alias="createdAt")
    is_active: bool = Field(..., alias="isActive")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
