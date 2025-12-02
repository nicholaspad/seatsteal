"""Remove duplicate indexes

Revision ID: 008
Revises: 007
Create Date: 2025-12-02 00:00:00

This migration removes duplicate indexes that were flagged by Supabase linter.
SQLAlchemy's `unique=True` constraint on columns creates implicit unique indexes,
so explicit unique indexes on the same columns are redundant.

Duplicate indexes removed:
- colleges_short_name_idx (duplicate of colleges_short_name_unique)
- stripe_customers_stripe_id_idx (duplicate of stripe_customers_stripe_customer_id_unique)
- stripe_customers_user_id_idx (duplicate of stripe_customers_user_id_unique)
- stripe_subscriptions_stripe_id_idx (duplicate of stripe_subscriptions_stripe_subscription_id_unique)
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop duplicate indexes (keep the unique constraints created by SQLAlchemy)

    # colleges: colleges_short_name_idx duplicates colleges_short_name_unique
    op.execute("DROP INDEX IF EXISTS colleges_short_name_idx")

    # stripe_customers: stripe_customers_stripe_id_idx duplicates stripe_customers_stripe_customer_id_unique
    op.execute("DROP INDEX IF EXISTS stripe_customers_stripe_id_idx")

    # stripe_customers: stripe_customers_user_id_idx duplicates stripe_customers_user_id_unique
    op.execute("DROP INDEX IF EXISTS stripe_customers_user_id_idx")

    # stripe_subscriptions: stripe_subscriptions_stripe_id_idx duplicates stripe_subscriptions_stripe_subscription_id_unique
    op.execute("DROP INDEX IF EXISTS stripe_subscriptions_stripe_id_idx")


def downgrade() -> None:
    # Recreate the dropped indexes

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS colleges_short_name_idx ON colleges (short_name)"
    )

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS stripe_customers_stripe_id_idx ON stripe_customers (stripe_customer_id)"
    )

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS stripe_customers_user_id_idx ON stripe_customers (user_id)"
    )

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS stripe_subscriptions_stripe_id_idx ON stripe_subscriptions (stripe_subscription_id)"
    )
