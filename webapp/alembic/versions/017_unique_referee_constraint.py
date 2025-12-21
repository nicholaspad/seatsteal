"""Add unique constraint on referee_id to prevent multiple referral claims

Revision ID: 017
Revises: 016
Create Date: 2025-12-20 12:00:00

This migration enforces that each user can only claim one referral code total.
This prevents users from claiming unlimited Pro trials by using different referral codes.

Before applying this migration, check for existing duplicate redemptions:
    SELECT referee_id, COUNT(*) as count
    FROM referral_redemptions
    GROUP BY referee_id
    HAVING COUNT(*) > 1;

If duplicates exist, decide whether to:
1. Keep only the first redemption per user (recommended)
2. Manually resolve duplicates before running migration
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # First, remove any duplicate redemptions (keep only the earliest one per user)
    # This ensures the unique constraint can be added without conflicts
    op.execute(
        """
        DELETE FROM referral_redemptions
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM referral_redemptions
            GROUP BY referee_id
        );
        """
    )

    # Drop the existing composite unique constraint
    op.drop_constraint("uq_referral_referee", "referral_redemptions", type_="unique")

    # Add new unique constraint on referee_id only
    # This ensures each user can only claim one referral code total
    op.create_unique_constraint(
        "uq_referee_single_redemption", "referral_redemptions", ["referee_id"]
    )

    # Note: We keep the composite index (referral_id, referee_id) for query performance
    # even though the unique constraint is now only on referee_id


def downgrade() -> None:
    # Remove the single-referee constraint
    op.drop_constraint(
        "uq_referee_single_redemption", "referral_redemptions", type_="unique"
    )

    # Restore the original composite constraint
    op.create_unique_constraint(
        "uq_referral_referee", "referral_redemptions", ["referral_id", "referee_id"]
    )
