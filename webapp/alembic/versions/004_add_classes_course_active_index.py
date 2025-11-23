"""Add composite index on classes (course_id, is_active)

Revision ID: 004
Revises: 003
Create Date: 2025-11-23 00:00:00

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add composite index on (course_id, is_active) for better query performance."""
    op.create_index(
        "classes_course_active_idx",
        "classes",
        ["course_id", "is_active"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the composite index."""
    op.drop_index("classes_course_active_idx", table_name="classes")
