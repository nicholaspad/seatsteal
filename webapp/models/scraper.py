from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from models.base import Base


class Scraper(Base):
    """Scrapers table - daemon orchestration and tracking"""

    __tablename__ = "scrapers"

    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False, index=True)

    # Status tracking: 'idle', 'running', 'error', 'completed'
    status = Column(String, default="idle", nullable=False)

    # Timing information
    last_run_at = Column(DateTime(timezone=True))
    last_success_at = Column(DateTime(timezone=True))
    next_run_at = Column(DateTime(timezone=True))

    # Performance metrics
    run_count = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    error_count = Column(Integer, default=0, nullable=False)

    # Error tracking
    last_error_message = Column(Text)
    last_run_duration_ms = Column(Integer)

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
        Index("scrapers_college_id_idx", "college_id", unique=True),
        Index("scrapers_status_idx", "status"),
        Index("scrapers_next_run_idx", "next_run_at"),
    )
