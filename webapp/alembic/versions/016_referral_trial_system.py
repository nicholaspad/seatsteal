"""Migrate referral system from coupons to trials

Revision ID: 016
Revises: 015
Create Date: 2025-12-19 12:00:00

This migration transforms the referral system from Stripe coupons to direct trials.
- Simplifies referrals table to one reusable code per user
- Creates referral_redemptions table to track each use of a code
- Removes coupon-related columns
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop RLS policy on referrals table (will recreate after schema changes)
    op.execute('DROP POLICY IF EXISTS "Users can view own referrals" ON referrals')

    # Drop indexes that reference columns we're removing
    op.execute("DROP INDEX IF EXISTS referrals_referee_id_idx")

    # Remove unused columns from referrals table
    op.drop_column("referrals", "referee_id")
    op.drop_column("referrals", "used_at")
    op.drop_column("referrals", "referrer_rewarded")
    op.drop_column("referrals", "referee_rewarded")
    op.drop_column("referrals", "referrer_coupon_id")
    op.drop_column("referrals", "referee_coupon_id")

    # Create referral_redemptions table
    op.create_table(
        "referral_redemptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "referral_id",
            sa.Integer(),
            sa.ForeignKey("referrals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "referee_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profiles.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("referee_trial_subscription_id", sa.String(), nullable=True),
        sa.Column("referrer_trial_subscription_id", sa.String(), nullable=True),
        sa.Column("referrer_previous_tier", sa.String(), nullable=True),
        sa.Column("referrer_trial_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("referee_trial_end", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("referral_id", "referee_id", name="uq_referral_referee"),
    )

    # Create indexes for referral_redemptions
    op.create_index(
        "referral_redemptions_referral_id_idx",
        "referral_redemptions",
        ["referral_id"],
    )
    op.create_index(
        "referral_redemptions_referee_id_idx",
        "referral_redemptions",
        ["referee_id"],
    )

    # Enable RLS on referral_redemptions
    op.execute("ALTER TABLE referral_redemptions ENABLE ROW LEVEL SECURITY")

    # Update RLS policy for referrals table (users can only see their own code)
    op.execute(
        """
        CREATE POLICY "Users can view own referral code"
        ON referrals
        FOR SELECT
        USING (auth.uid() = referrer_id)
        """
    )

    # RLS policy for referral_redemptions (users can see redemptions they're part of)
    op.execute(
        """
        CREATE POLICY "Users can view own redemptions"
        ON referral_redemptions
        FOR SELECT
        USING (
            EXISTS (
                SELECT 1 FROM referrals
                WHERE referrals.id = referral_redemptions.referral_id
                AND referrals.referrer_id = auth.uid()
            ) OR
            referee_id = auth.uid()
        )
        """
    )


def downgrade() -> None:
    # Drop RLS policies
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'referral_redemptions') THEN
                DROP POLICY IF EXISTS "Users can view own redemptions" ON referral_redemptions;
                ALTER TABLE referral_redemptions DISABLE ROW LEVEL SECURITY;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'referrals') THEN
                DROP POLICY IF EXISTS "Users can view own referral code" ON referrals;
            END IF;
        END $$;
        """
    )

    # Drop indexes
    op.execute("DROP INDEX IF EXISTS referral_redemptions_referral_id_idx")
    op.execute("DROP INDEX IF EXISTS referral_redemptions_referee_id_idx")

    # Drop referral_redemptions table
    op.execute("DROP TABLE IF EXISTS referral_redemptions")

    # Add back removed columns to referrals table
    op.add_column(
        "referrals",
        sa.Column(
            "referee_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profiles.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "referrals",
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "referrals",
        sa.Column(
            "referrer_rewarded", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "referrals",
        sa.Column(
            "referee_rewarded", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "referrals", sa.Column("referrer_coupon_id", sa.String(), nullable=True)
    )
    op.add_column(
        "referrals", sa.Column("referee_coupon_id", sa.String(), nullable=True)
    )

    # Recreate dropped index
    op.create_index("referrals_referee_id_idx", "referrals", ["referee_id"])

    # Recreate original RLS policy
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
