from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID
from .class_schema import ClassWithCourse


class SubscriptionBase(BaseModel):
    """Base subscription schema"""

    college_id: int
    class_id: int


class SubscriptionCreate(SubscriptionBase):
    """Schema for creating a subscription"""

    pass


class SubscriptionResponse(SubscriptionBase):
    """Schema for subscription responses"""

    id: int
    user_id: UUID
    is_active: bool
    last_notified: Optional[datetime] = None
    notification_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubscriptionWithDetails(SubscriptionResponse):
    """Subscription with nested class, course, and college details"""

    class_: ClassWithCourse

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
