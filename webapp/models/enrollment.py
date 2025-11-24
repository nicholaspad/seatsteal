from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from models.base import Base


class Enrollment(Base):
    """
    Enrollment status tracking over time.
    
    This table uses a status-change-only storage strategy to limit growth:
    - A new row is inserted ONLY when enrollment_status changes (e.g., open → closed)
    - When status is unchanged, the existing row's scraped_at timestamp is updated
    
    The scraped_at field represents the last time the class was scraped, and may be
    updated multiple times for the same enrollment record if the status remains stable.
    
    This approach dramatically reduces table size (by ~90%+) while preserving:
    - All meaningful enrollment status transitions
    - Ability to track when each class was last checked
    """

    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False, index=True)
    class_id = Column(
        Integer, ForeignKey("classes.class_id"), nullable=False, index=True
    )

    # Enrollment data: 'open', 'closed', 'unknown'
    enrollment_status = Column(String, nullable=False)

    # Scraping metadata: last time this class was scraped (updated when status unchanged)
    scraped_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    raw_text = Column(Text)

    __table_args__ = (
        Index("enrollments_class_id_idx", "class_id"),
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
