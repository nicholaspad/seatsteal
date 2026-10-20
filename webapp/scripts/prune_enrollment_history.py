#!/usr/bin/env python3
"""Prune old enrollment history while ALWAYS keeping the latest row per class.

Deletes enrollments with scraped_at older than --keep-days (default 30) ONLY when a
newer row exists for the same class_id. Never touches subscriptions,
notification_logs, classes, or courses.

    python prune_enrollment_history.py                 # dry run: counts only
    python prune_enrollment_history.py --confirm       # delete in batches
    python prune_enrollment_history.py --college cornell --keep-days 30 --confirm
"""
import argparse
import sys
import time
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import settings  # noqa: E402

PRUNABLE = """
    FROM enrollments e
    WHERE e.scraped_at < NOW() - make_interval(days => :keep_days)
      AND (CAST(:college_id AS int) IS NULL OR e.college_id = :college_id)
      AND EXISTS (
          SELECT 1 FROM enrollments n
          WHERE n.class_id = e.class_id
            AND (n.scraped_at, n.id) > (e.scraped_at, e.id)
      )
"""


def resolve_college(conn, short_name):
    if not short_name:
        return None
    cid = conn.execute(
        text("SELECT id FROM colleges WHERE short_name = :s"), {"s": short_name}
    ).scalar()
    if cid is None:
        sys.exit(f"College not found: {short_name}")
    return cid


def run_prune(
    conn: Connection,
    *,
    keep_days: int,
    college_id,
    batch_size: int,
    sleep_s: float,
    confirm: bool,
) -> tuple[int, int]:
    """Count (and optionally delete) prunable enrollment rows.

    Returns (prunable_count, deleted_count). deleted_count is 0 on dry run.
    """
    conn.execute(text("SET statement_timeout = '15s'"))
    params = {"keep_days": keep_days, "college_id": college_id}
    total = conn.execute(text("SELECT COUNT(*) " + PRUNABLE), params).scalar()
    # End the autobegin transaction so each DELETE batch can use its own.
    conn.commit()
    print(f"Prunable rows (older than {keep_days}d, newer row exists): {total}")
    if not confirm:
        print("Dry run. Re-run with --confirm to delete.")
        return total, 0

    deleted = 0
    while True:
        with conn.begin():
            n = conn.execute(
                text(
                    "DELETE FROM enrollments WHERE id IN ("
                    "SELECT e.id " + PRUNABLE + " ORDER BY e.id LIMIT :lim)"
                ),
                {**params, "lim": batch_size},
            ).rowcount
        deleted += n
        print(f"  deleted {n} (total {deleted})")
        if n < batch_size:
            break
        time.sleep(sleep_s)
    print(f"Done. Deleted {deleted} rows; latest row per class preserved.")
    return total, deleted


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--keep-days", type=int, default=30)
    p.add_argument("--college", help="college short_name (default: all)")
    p.add_argument("--batch-size", type=int, default=2000)
    p.add_argument("--sleep", type=float, default=0.5, help="seconds between batches")
    p.add_argument("--confirm", action="store_true", help="actually delete")
    a = p.parse_args()
    if a.keep_days < 1:
        sys.exit("--keep-days must be >= 1")

    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    with engine.connect() as conn:
        run_prune(
            conn,
            keep_days=a.keep_days,
            college_id=resolve_college(conn, a.college),
            batch_size=a.batch_size,
            sleep_s=a.sleep,
            confirm=a.confirm,
        )


if __name__ == "__main__":
    main()
