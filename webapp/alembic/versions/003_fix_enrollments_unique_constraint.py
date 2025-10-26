"""fix enrollments unique constraint

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
    """Drop and recreate enrollments_class_id_idx without unique constraint."""
    # Drop the existing unique index
    op.drop_index("enrollments_class_id_idx", table_name="enrollments")

    # Recreate as non-unique index
    op.create_index(
        "enrollments_class_id_idx", "enrollments", ["class_id"], unique=False
    )


def downgrade() -> None:
    """Revert to unique constraint (not recommended)."""
    # Drop the non-unique index
    op.drop_index("enrollments_class_id_idx", table_name="enrollments")

    # Recreate as unique index (this may fail if there are duplicate class_ids)
    op.create_index(
        "enrollments_class_id_idx", "enrollments", ["class_id"], unique=True
    )
