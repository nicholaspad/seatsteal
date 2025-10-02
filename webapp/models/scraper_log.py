from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from .base import Base


class ScraperLog(Base):
    """Detailed logging for individual scraper runs"""

    __tablename__ = "scraper_logs"

    id = Column(Integer, primary_key=True, index=True)
    scraper_id = Column(Integer, ForeignKey("scrapers.id"), nullable=False, index=True)

    # Run outcome: 'success', 'error', 'partial', 'timeout'
    outcome = Column(String, nullable=False)

    # Timing information
    started_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at = Column(DateTime(timezone=True))
    duration_ms = Column(Integer)

    # Error tracking
    error_message = Column(Text)
    stack_trace = Column(Text)

    # Performance metrics
    courses_created = Column(Integer, default=0, nullable=False)
    classes_created = Column(Integer, default=0, nullable=False)
    enrollments_saved = Column(Integer, default=0, nullable=False)

    # Metadata
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("scraper_logs_scraper_id_idx", "scraper_id"),
        Index("scraper_logs_outcome_idx", "outcome"),
        Index("scraper_logs_started_at_idx", "started_at"),
        Index("scraper_logs_scraper_started_idx", "scraper_id", "started_at"),
    )
