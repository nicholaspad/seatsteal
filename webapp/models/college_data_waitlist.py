from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from models.base import Base


class CollegeDataWaitlist(Base):
    """Demand list for a college whose seat data is currently unavailable.

    Rows are never deleted. ``notified_at`` is set after a one-time
    "data is back" notification is sent.
    """

    __tablename__ = "college_data_waitlist"

    id = Column(Integer, primary_key=True)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)
    email = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    notified_at = Column(DateTime(timezone=True), nullable=True)
    attempts = Column(Integer, nullable=False, server_default="0", default=0)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index(
            "college_data_waitlist_college_user_uidx",
            "college_id",
            "user_id",
            unique=True,
            postgresql_where=text("user_id IS NOT NULL"),
        ),
        Index(
            "college_data_waitlist_college_email_uidx",
            "college_id",
            func.lower(email),
            unique=True,
            postgresql_where=text("email IS NOT NULL"),
        ),
        Index(
            "college_data_waitlist_pending_idx",
            "college_id",
            postgresql_where=text("notified_at IS NULL AND attempts < 5"),
        ),
    )
