from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from .base import Base


class Enrollment(Base):
    """Enrollment snapshots over time"""

    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False, index=True)
    class_id = Column(
        Integer, ForeignKey("classes.class_id"), nullable=False, index=True
    )

    # Enrollment data: 'open', 'closed', 'unknown'
    enrollment_status = Column(String, nullable=False)

    # Scraping metadata
    scraped_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    raw_text = Column(Text)

    __table_args__ = (
        Index("enrollments_class_id_idx", "class_id", unique=True),
        Index("enrollments_scraped_at_idx", "scraped_at"),
        Index("enrollments_status_idx", "enrollment_status"),
        Index("enrollments_college_status_idx", "college_id", "enrollment_status"),
        # Performance optimization: Critical composite indexes for heavy queries
        Index("enrollments_class_scraped_idx", "class_id", "scraped_at"),
        Index(
            "enrollments_class_status_scraped_idx",
            "class_id",
            "enrollment_status",
            "scraped_at",
        ),
        Index("enrollments_college_scraped_idx", "college_id", "scraped_at"),
        Index("enrollments_status_scraped_idx", "enrollment_status", "scraped_at"),
    )
