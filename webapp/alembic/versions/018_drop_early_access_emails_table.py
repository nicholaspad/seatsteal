"""Drop early_access_emails table

Revision ID: 018
Revises: 017
Create Date: 2025-12-30

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop indexes first
    op.drop_index("early_access_emails_email_idx", table_name="early_access_emails")
    op.drop_index(
        op.f("ix_early_access_emails_id"), table_name="early_access_emails"
    )
    # Drop table
    op.drop_table("early_access_emails")


def downgrade() -> None:
    # Recreate early_access_emails table
    op.create_table(
        "early_access_emails",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_early_access_emails_id"), "early_access_emails", ["id"], unique=False
    )
    op.create_index(
        "early_access_emails_email_idx", "early_access_emails", ["email"], unique=True
    )
