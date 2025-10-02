from sqlalchemy import Column, Integer, String, Boolean, DateTime, Index
from sqlalchemy.sql import func
from .base import Base


class EarlyAccessEmail(Base):
    """Early access emails table - controls who can log in"""

    __tablename__ = "early_access_emails"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_active = Column(Boolean, default=True, nullable=False)

    __table_args__ = (Index("early_access_emails_email_idx", "email", unique=True),)
