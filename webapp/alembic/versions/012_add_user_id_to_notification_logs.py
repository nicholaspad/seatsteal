"""Add user_id column to notification_logs

Revision ID: 012
Revises: 011
Create Date: 2025-12-08 00:00:00

This migration adds a user_id column to notification_logs table to allow
direct querying of user notifications without joining through subscriptions.
The column is nullable to preserve existing data and for backwards compatibility.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add user_id column (nullable for backwards compatibility)
    op.add_column(
        "notification_logs",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Add foreign key constraint to profiles table
    op.create_foreign_key(
        "notification_logs_user_id_fkey",
        "notification_logs",
        "profiles",
        ["user_id"],
        ["id"],
    )

    # Add index for efficient user-based queries
    op.create_index(
        "notification_logs_user_id_idx",
        "notification_logs",
        ["user_id"],
        unique=False,
    )

    # Add composite index for user + time range queries (used by trends endpoint)
    op.create_index(
        "notification_logs_user_sent_idx",
        "notification_logs",
        ["user_id", "sent_at"],
        unique=False,
    )


def downgrade() -> None:
    # Drop indexes first
    op.drop_index("notification_logs_user_sent_idx", table_name="notification_logs")
    op.drop_index("notification_logs_user_id_idx", table_name="notification_logs")

    # Drop foreign key
    op.drop_constraint(
        "notification_logs_user_id_fkey", "notification_logs", type_="foreignkey"
    )

    # Drop column
    op.drop_column("notification_logs", "user_id")
