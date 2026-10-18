"""Add colleges.data_available admin override flag

Revision ID: 019
Revises: 018
Create Date: 2026-10-18

Additive only: new boolean column defaulting to true. Used with
auto-derived scraper health to expose data_status on the college API.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "colleges",
        sa.Column(
            "data_available",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("colleges", "data_available")
