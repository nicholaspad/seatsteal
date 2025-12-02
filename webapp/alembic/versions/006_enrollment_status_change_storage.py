"""Implement status-change-only enrollment storage

Revision ID: 006
Revises: 005
Create Date: 2025-11-24 00:00:00

This migration documents the change to status-change-only enrollment storage.
No schema changes are required, but the application logic has been updated to:
- INSERT new enrollment record only when enrollment_status changes
- UPDATE existing enrollment's scraped_at timestamp when status unchanged

This reduces table growth by ~90% while preserving all meaningful status transitions.
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add comment to enrollments table documenting the status-change-only behavior
    op.execute(
        """
        COMMENT ON TABLE enrollments IS 
        'Enrollment status tracking over time. Uses status-change-only storage: 
        new rows inserted only when enrollment_status changes (e.g., open→closed), 
        existing rows have scraped_at updated when status is unchanged. This reduces 
        table growth by ~90% while preserving all meaningful status transitions.'
        """
    )

    # Add comment to scraped_at column explaining its dual purpose
    op.execute(
        """
        COMMENT ON COLUMN enrollments.scraped_at IS 
        'Timestamp of last scrape for this class. Updated on every scrape when status 
        unchanged, or set to status change time when new row inserted.'
        """
    )


def downgrade() -> None:
    # Remove comments
    op.execute("COMMENT ON TABLE enrollments IS NULL")
    op.execute("COMMENT ON COLUMN enrollments.scraped_at IS NULL")
