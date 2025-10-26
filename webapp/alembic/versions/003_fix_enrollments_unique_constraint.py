"""Fix enrollments table - placeholder migration for future use

Revision ID: 003
Revises: 002
Create Date: 2025-10-26 15:45:00

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Placeholder - no changes needed. Keeping non-unique index for historical enrollment data."""
    pass


def downgrade() -> None:
    """Placeholder - no changes to revert."""
    pass
