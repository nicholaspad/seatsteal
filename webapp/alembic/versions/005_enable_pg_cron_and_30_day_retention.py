"""Enable pg_cron extension and schedule 30-day enrollment cleanup

Revision ID: 005
Revises: 004
Create Date: 2025-11-23 00:00:00

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable the pg_cron extension for scheduled jobs
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_cron")

    # Schedule daily cleanup job at 2 AM UTC to delete enrollments older than 30 days
    op.execute(
        """
        SELECT cron.schedule(
            'cleanup-old-enrollments',
            '0 2 * * *',
            $$DELETE FROM enrollments WHERE scraped_at < NOW() - INTERVAL '30 days'$$
        )
        """
    )


def downgrade() -> None:
    # Unschedule the cleanup job
    op.execute("SELECT cron.unschedule('cleanup-old-enrollments')")

    # Drop the pg_cron extension
    op.execute("DROP EXTENSION IF EXISTS pg_cron")
