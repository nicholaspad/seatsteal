from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from models.base import Base


class DeviceToken(Base):
    """Device tokens for push notifications via Firebase Cloud Messaging"""

    __tablename__ = "device_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False, index=True
    )
    token = Column(String, nullable=False, unique=True, index=True)
    platform = Column(String, nullable=False)  # 'ios' or 'android'
    
    # Status tracking
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime(timezone=True))
    
    # Metadata
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        # Performance indexes for notification queries
        Index("device_tokens_user_active_idx", "user_id", "is_active"),
        Index("device_tokens_token_idx", "token", unique=True),
    )

