"""Make notification_logs.subscription_id nullable

Revision ID: 011
Revises: 010
Create Date: 2025-12-07 00:00:00

This migration makes the subscription_id column in notification_logs nullable.
This allows us to preserve notification logs for historical analytics even when
the associated subscriptions are deleted during term code changes.

The notification_logs still retain college_id for college-level analytics.
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make subscription_id nullable in notification_logs
    # This allows preserving notification logs when subscriptions are deleted
    op.alter_column(
        "notification_logs",
        "subscription_id",
        nullable=True,
    )


def downgrade() -> None:
    # Revert to NOT NULL - this may fail if there are NULL values
    # First, delete any rows with NULL subscription_id
    op.execute("DELETE FROM notification_logs WHERE subscription_id IS NULL")

    op.alter_column(
        "notification_logs",
        "subscription_id",
        nullable=False,
    )
