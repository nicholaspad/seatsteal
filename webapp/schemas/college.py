from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class CollegeBase(BaseModel):
    """Base college schema"""

    name: str
    short_name: str
    domain: Optional[str] = None
    term_code: Optional[str] = None
    term_name: Optional[str] = None
    email_enabled: bool = True
    sms_enabled: bool = False


class CollegeCreate(CollegeBase):
    """Schema for creating a college"""

    pass


class CollegeResponse(CollegeBase):
    """Schema for college responses"""

    id: int
    created_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
