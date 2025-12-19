"""Add referrals table for user referral program

Revision ID: 015
Revises: 014
Create Date: 2025-12-19 00:00:00

This migration creates a table to track user referrals and rewards.
Each user gets a unique referral code. When someone signs up with it,
both the referrer and referee get 1 week of Pro free via Stripe coupon.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create referrals table
    op.create_table(
        "referrals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "referrer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profiles.id"),
            nullable=False,
        ),
        sa.Column("referral_code", sa.String(20), nullable=False),
        sa.Column(
            "referee_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profiles.id"),
            nullable=True,
        ),
        sa.Column(
            "referrer_rewarded", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "referee_rewarded", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("referrer_coupon_id", sa.String(), nullable=True),
        sa.Column("referee_coupon_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("referral_code"),
    )

    # Indexes for lookups
    op.create_index("referrals_referrer_id_idx", "referrals", ["referrer_id"])
    op.create_index("referrals_referee_id_idx", "referrals", ["referee_id"])
    op.create_index("referrals_referral_code_idx", "referrals", ["referral_code"])

    # Enable RLS
    op.execute("ALTER TABLE referrals ENABLE ROW LEVEL SECURITY")

    # Allow users to see their own referrals (as referrer or referee)
    op.execute(
        """
        CREATE POLICY "Users can view own referrals"
        ON referrals
        FOR SELECT
        USING (
            auth.uid() = referrer_id OR
            auth.uid() = referee_id
        )
        """
    )


def downgrade() -> None:
    # Drop RLS policy
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'referrals') THEN
                DROP POLICY IF EXISTS "Users can view own referrals" ON referrals;
                ALTER TABLE referrals DISABLE ROW LEVEL SECURITY;
            END IF;
        END $$;
        """
    )

    # Drop indexes
    op.execute("DROP INDEX IF EXISTS referrals_referrer_id_idx")
    op.execute("DROP INDEX IF EXISTS referrals_referee_id_idx")
    op.execute("DROP INDEX IF EXISTS referrals_referral_code_idx")

    # Drop table
    op.execute("DROP TABLE IF EXISTS referrals")
