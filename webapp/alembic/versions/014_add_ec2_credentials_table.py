"""Add ec2_credentials table for persisting EC2 credentials

Revision ID: 014
Revises: 013
Create Date: 2025-12-17 00:00:00

This migration creates a table to store EC2 instance credentials (SSH key and
host info) so they persist across terminal-server redeployments on Render.

The table stores:
- pem_contents: The SSH private key for connecting to EC2
- host_info: JSON with instance_id, public_dns, region, instance_type
- is_active: Only one row should be active at a time
- created_at: Timestamp for auditing

Only the service role can access this table (no RLS policies = service role only).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ec2_credentials table
    op.create_table(
        "ec2_credentials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pem_contents", sa.Text(), nullable=False),
        sa.Column("host_info", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Index for finding active credentials quickly
    op.create_index(
        "ec2_credentials_active_idx",
        "ec2_credentials",
        ["is_active"],
        unique=False,
        postgresql_where=sa.text("is_active = true"),
    )

    # Enable RLS - with no policies, only service_role can access
    op.execute("ALTER TABLE ec2_credentials ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    # Disable RLS (use IF EXISTS pattern for safety)
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'ec2_credentials') THEN
                ALTER TABLE ec2_credentials DISABLE ROW LEVEL SECURITY;
            END IF;
        END $$;
        """
    )

    # Drop index (IF EXISTS is implicit in drop_index)
    op.execute("DROP INDEX IF EXISTS ec2_credentials_active_idx")

    # Drop table
    op.execute("DROP TABLE IF EXISTS ec2_credentials")
