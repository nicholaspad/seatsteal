"""Add college_data_waitlist for stale-data recovery notifications

Revision ID: 020
Revises: 019
Create Date: 2026-10-18

Additive only: new table so we can count demand per school and send a
one-time 'data is back' notification. Rows are never deleted.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "college_data_waitlist",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["college_id"], ["colleges.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "user_id IS NOT NULL OR email IS NOT NULL",
            name="college_data_waitlist_user_or_email",
        ),
    )
    op.create_index(
        "ix_college_data_waitlist_college_id",
        "college_data_waitlist",
        ["college_id"],
        unique=False,
    )
    op.create_index(
        "college_data_waitlist_college_user_uidx",
        "college_data_waitlist",
        ["college_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    op.execute("""
        CREATE UNIQUE INDEX college_data_waitlist_college_email_uidx
        ON college_data_waitlist (college_id, lower(email))
        WHERE email IS NOT NULL
        """)
    op.create_index(
        "college_data_waitlist_pending_idx",
        "college_data_waitlist",
        ["college_id"],
        unique=False,
        postgresql_where=sa.text("notified_at IS NULL AND attempts < 5"),
    )

    op.execute("ALTER TABLE college_data_waitlist ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_tables WHERE tablename = 'college_data_waitlist'
            ) THEN
                ALTER TABLE college_data_waitlist DISABLE ROW LEVEL SECURITY;
            END IF;
        END $$;
        """)
    op.execute("DROP INDEX IF EXISTS college_data_waitlist_pending_idx")
    op.execute("DROP INDEX IF EXISTS college_data_waitlist_college_email_uidx")
    op.execute("DROP INDEX IF EXISTS college_data_waitlist_college_user_uidx")
    op.execute("DROP INDEX IF EXISTS ix_college_data_waitlist_college_id")
    op.execute("DROP TABLE IF EXISTS college_data_waitlist")
