from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from .base import Base


class NotificationLog(Base):
    """Notification logs table - tracks all notifications sent"""

    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False, index=True)
    subscription_id = Column(
        Integer, ForeignKey("subscriptions.id"), nullable=False, index=True
    )

    # Notification details: 'email', 'sms'
    notification_type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    # Status: 'sent', 'failed', 'pending'
    status = Column(String, nullable=False)

    # Enrollment context
    seats_remaining = Column(Integer)
    enrollment_status = Column(String)

    # Metadata
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        # Performance optimization: Critical indexes for analytics queries
        # For time-based analytics queries (most common)
        Index("notification_logs_sent_at_idx", "sent_at"),
        # For subscription-specific analytics
        Index("notification_logs_subscription_sent_idx", "subscription_id", "sent_at"),
        # For college analytics with time ordering
        Index("notification_logs_college_sent_idx", "college_id", "sent_at"),
        # For status filtering with time (success rate analytics)
        Index("notification_logs_status_sent_idx", "status", "sent_at"),
        # For college + status analytics (most comprehensive)
        Index(
            "notification_logs_college_status_sent_idx",
            "college_id",
            "status",
            "sent_at",
        ),
    )
