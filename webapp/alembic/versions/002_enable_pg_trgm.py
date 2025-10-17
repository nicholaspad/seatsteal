"""Enable pg_trgm extension for fuzzy search

Revision ID: 002
Revises: 001
Create Date: 2025-10-16 12:00:00

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable the pg_trgm extension for trigram similarity search
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


def downgrade() -> None:
    # Drop the pg_trgm extension
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
