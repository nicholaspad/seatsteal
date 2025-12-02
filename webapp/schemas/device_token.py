from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional
from uuid import UUID


class DeviceTokenBase(BaseModel):
    """Base device token schema"""

    token: str
    platform: str  # 'ios' or 'android'


class DeviceTokenCreate(DeviceTokenBase):
    """Schema for registering a device token"""

    pass


class DeviceTokenResponse(DeviceTokenBase):
    """Schema for device token responses"""

    id: int
    user_id: UUID = Field(..., alias="userId")
    is_active: bool = Field(..., alias="isActive")
    last_used_at: Optional[datetime] = Field(None, alias="lastUsedAt")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
