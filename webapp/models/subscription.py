from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from models.base import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False, index=True)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False, index=True
    )
    class_id = Column(
        Integer, ForeignKey("classes.class_id"), nullable=False, index=True
    )

    # Status tracking
    is_active = Column(Boolean, default=True, nullable=False)
    last_notified = Column(DateTime(timezone=True))
    notification_count = Column(Integer, default=0, nullable=False)

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
        # Performance indexes for notification job queries
        Index("subscriptions_active_idx", "is_active"),
        Index("subscriptions_class_active_idx", "class_id", "is_active"),
        Index("subscriptions_user_active_idx", "user_id", "is_active"),
        Index("subscriptions_college_active_idx", "college_id", "is_active"),
        # Composite index for the main notification query join
        Index(
            "subscriptions_class_college_active_idx",
            "class_id",
            "college_id",
            "is_active",
        ),
    )
