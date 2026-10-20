"""Shrink enrollments: drop redundant indexes, reindex kept ones, safer retention

Revision ID: 021
Revises: 020
Create Date: 2026-10-20

PROD IS NOT MIGRATED ON DEPLOY. Apply by hand (see runbook in PR body).
DROP/REINDEX ... CONCURRENTLY cannot run inside a transaction block, so each
statement runs in an autocommit_block. No rows are deleted by this migration.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DROPPED = [
    # (name, definition used by downgrade)
    ("enrollments_status_scraped_idx", "(enrollment_status, scraped_at)"),
    ("enrollments_status_idx", "(enrollment_status)"),
    ("enrollments_college_status_idx", "(college_id, enrollment_status)"),
    (
        "enrollments_class_status_scraped_idx",
        "(class_id, enrollment_status, scraped_at)",
    ),
    # Last: strict prefix of enrollments_class_scraped_idx
    ("enrollments_class_id_idx", "(class_id)"),
]

KEPT = [
    "enrollments_class_scraped_idx",
    "enrollments_pkey",
    "enrollments_scraped_at_idx",
    "enrollments_college_scraped_idx",
]

SAFE_CLEANUP = (
    "DELETE FROM enrollments e "
    "WHERE e.scraped_at < NOW() - INTERVAL '30 days' "
    "AND EXISTS (SELECT 1 FROM enrollments n "
    "WHERE n.class_id = e.class_id AND (n.scraped_at, n.id) > (e.scraped_at, e.id))"
)
OLD_CLEANUP = "DELETE FROM enrollments WHERE scraped_at < NOW() - INTERVAL '30 days'"


def _cron_available() -> bool:
    bind = op.get_bind()
    return bool(
        bind.exec_driver_sql(
            "SELECT 1 FROM pg_extension WHERE extname = 'pg_cron'"
        ).scalar()
    )


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("SET statement_timeout = 0")
        op.execute("SET lock_timeout = '5s'")
        for name, _ in DROPPED:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")
        if op.get_bind().dialect.name == "postgresql":
            for name in KEPT:
                op.execute(f"REINDEX INDEX CONCURRENTLY {name}")

    # Retention: never delete a class's latest row
    if _cron_available():
        op.execute("SELECT cron.unschedule('cleanup-old-enrollments')")
        op.execute(
            f"SELECT cron.schedule('cleanup-old-enrollments', '0 2 * * *', $${SAFE_CLEANUP}$$)"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("SET statement_timeout = 0")
        for name, cols in reversed(DROPPED):
            op.execute(
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {name} ON enrollments {cols}"
            )
    if _cron_available():
        op.execute("SELECT cron.unschedule('cleanup-old-enrollments')")
        op.execute(
            f"SELECT cron.schedule('cleanup-old-enrollments', '0 2 * * *', $${OLD_CLEANUP}$$)"
        )
