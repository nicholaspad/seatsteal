"""Disable Brown college - AWS WAF blocks API requests

Revision ID: 014
Revises: 013
Create Date: 2025-12-11 00:00:00

Brown's CAB API now uses AWS WAF bot protection that requires JavaScript
challenge execution. Since we cannot pass the WAF challenge without spoofing
a browser User-Agent, we're disabling the Brown scraper.
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE colleges SET is_active = false WHERE short_name = 'brown'")


def downgrade() -> None:
    op.execute("UPDATE colleges SET is_active = true WHERE short_name = 'brown'")
