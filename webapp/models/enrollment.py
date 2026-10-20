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

    id = Column(Integer, primary_key=True)
    # No index=True: that would create ix_enrollments_college_id, which prod
    # does not have. college_scraped_idx covers college_id-leading lookups.
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.class_id"), nullable=False)

    # Enrollment data: 'open', 'closed', 'unknown'
    enrollment_status = Column(String, nullable=False)

    # Scraping metadata: last time this class was scraped (updated when status unchanged)
    scraped_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    raw_text = Column(Text)

    __table_args__ = (
        # Kept indexes only (see alembic 021). Every scrape UPDATEs scraped_at,
        # which is never HOT, so each extra index costs one write per class per
        # scrape. Do not add indexes here without a query that needs them.
        # (class_id, scraped_at) serves latest-per-class, notifs, analytics and the class_id FK.
        Index("enrollments_class_scraped_idx", "class_id", "scraped_at"),
        # cron 30-day cleanup + admin recent changes
        Index("enrollments_scraped_at_idx", "scraped_at"),
        # purge script / per-college ops + college_id FK
        Index("enrollments_college_scraped_idx", "college_id", "scraped_at"),
    )
