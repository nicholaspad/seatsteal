"""Remove seats_remaining and enrollment_status from notification_logs

Revision ID: 013
Revises: 012
Create Date: 2025-12-09 00:00:00

This migration removes the seats_remaining and enrollment_status columns from
the notification_logs table. These columns were never populated and always
contained NULL values, providing no functional value.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the unused columns
    op.drop_column("notification_logs", "seats_remaining")
    op.drop_column("notification_logs", "enrollment_status")


def downgrade() -> None:
    # Recreate the columns if needed (for rollback)
    op.add_column(
        "notification_logs", sa.Column("enrollment_status", sa.String, nullable=True)
    )
    op.add_column(
        "notification_logs", sa.Column("seats_remaining", sa.Integer, nullable=True)
    )
