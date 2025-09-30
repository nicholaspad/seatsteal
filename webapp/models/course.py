from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False, index=True)
    course_code = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False, index=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    college = relationship("College", backref="courses")

    __table_args__ = (
        # Unique constraint for college + course_code combination
        Index("courses_college_course_code_idx", "college_id", "course_code", unique=True),
        # Composite index for common queries
        Index("courses_college_active_idx", "college_id", "is_active"),
        # Performance optimization for time-based queries
        Index("courses_college_active_updated_idx", "college_id", "is_active", "updated_at"),
    )