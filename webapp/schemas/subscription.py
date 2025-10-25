from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional
from uuid import UUID
from schemas.class_schema import ClassWithCourse


class SubscriptionBase(BaseModel):
    """Base subscription schema"""

    college_id: int = Field(..., alias="collegeId")
    class_id: int = Field(..., alias="classId")

    model_config = ConfigDict(populate_by_name=True)


class SubscriptionCreate(SubscriptionBase):
    """Schema for creating a subscription"""

    pass


class SubscriptionResponse(SubscriptionBase):
    """Schema for subscription responses"""

    id: int
    user_id: UUID = Field(..., alias="userId")
    is_active: bool = Field(..., alias="isActive")
    last_notified: Optional[datetime] = Field(None, alias="lastNotified")
    notification_count: int = Field(..., alias="notificationCount")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SubscriptionWithDetails(SubscriptionResponse):
    """Subscription with nested class, course, and college details"""

    class_: ClassWithCourse = Field(..., alias="class")
