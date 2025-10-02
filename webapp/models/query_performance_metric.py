from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from sqlalchemy.sql import func
from .base import Base


class QueryPerformanceMetric(Base):
    """Query performance metrics table - stores individual query execution data for P50/P90 analysis"""

    __tablename__ = "query_performance_metrics"

    id = Column(Integer, primary_key=True, index=True)
    query_name = Column(String, nullable=False)
    execution_time = Column(Integer, nullable=False)  # milliseconds
    result_count = Column(Integer)  # optional
    parameters = Column(Text)  # JSON string of parameters

    # Timing
    executed_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Metadata
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        # Critical indexes for P50/P90 hourly aggregation queries
        Index("qpm_query_name_executed_idx", "query_name", "executed_at"),
        # For cleanup job (time-based deletion)
        Index("qpm_executed_at_idx", "executed_at"),
        # For performance analysis queries
        Index("qpm_query_exec_time_idx", "query_name", "execution_time"),
        # Composite index for most common query patterns
        Index("qpm_query_time_exec_idx", "query_name", "executed_at", "execution_time"),
    )
