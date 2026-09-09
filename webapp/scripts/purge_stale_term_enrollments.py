#!/usr/bin/env python3
"""
Script to purge stale term enrollments after a term flip.

After flipping colleges.term_code to a new term (e.g., Cornell FA25 → SP26), old term
classes and enrollments remain because term lives only on the colleges table (no term
column on courses/classes/enrollments).

This script safely removes:
- Enrollments for a college scraped before a cutoff timestamp
- Classes that have no remaining enrollments and no active subscriptions
- Courses that have no remaining classes

This script NEVER deletes subscriptions, notification_logs, or classes with active subscriptions.
If subscriptions exist on classes that would be deleted, the script aborts by default
(unless --force-skip-subscribed is set, which skips those classes but still never deletes them).

Motivating example: Cornell SP26 term flip (FA25 → SP26)

Usage:
    # Preview mode (default) - shows what would be deleted
    python purge_stale_term_enrollments.py --college cornell --before-scraped-at "2025-01-15T00:00:00Z"
    
    # Actually delete (requires --confirm)
    python purge_stale_term_enrollments.py --college cornell --before-scraped-at "2025-01-15T00:00:00Z" --confirm
    
    # Continue even if subscriptions block some classes (use with caution)
    python purge_stale_term_enrollments.py --college cornell --before-scraped-at "2025-01-15T00:00:00Z" --confirm --force-skip-subscribed
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from models.college import College


def preview_counts(
    db: Session, college_id: int, cutoff_timestamp: datetime
) -> Dict[str, int]:
    """
    Preview counts of what would be deleted.

    Returns:
        Dict with counts for stale_enrollments, orphan_classes, empty_courses, and blocking_subscriptions
    """
    counts = {
        "stale_enrollments": 0,
        "orphan_classes": 0,
        "empty_courses": 0,
        "blocking_subscriptions": 0,
    }

    # Count stale enrollments (scraped before cutoff)
    result = db.execute(
        text(
            """
            SELECT COUNT(*) FROM enrollments 
            WHERE college_id = :college_id 
            AND scraped_at < :cutoff
        """
        ),
        {"college_id": college_id, "cutoff": cutoff_timestamp},
    )
    counts["stale_enrollments"] = result.scalar()

    # Count orphan classes (created before cutoff, no enrollments after deletion, no subscriptions)
    # First, find classes that would have no remaining enrollments
    result = db.execute(
        text(
            """
            SELECT COUNT(DISTINCT c.class_id)
            FROM classes c
            INNER JOIN courses co ON c.course_id = co.id
            WHERE co.college_id = :college_id
            AND c.created_at < :cutoff
            AND NOT EXISTS (
                SELECT 1 FROM enrollments e
                WHERE e.class_id = c.class_id
                AND e.scraped_at >= :cutoff
            )
        """
        ),
        {"college_id": college_id, "cutoff": cutoff_timestamp},
    )
    counts["orphan_classes"] = result.scalar()

    # Count classes that would be deleted but have active subscriptions (BLOCKING)
    result = db.execute(
        text(
            """
            SELECT COUNT(DISTINCT c.class_id)
            FROM classes c
            INNER JOIN courses co ON c.course_id = co.id
            WHERE co.college_id = :college_id
            AND c.created_at < :cutoff
            AND NOT EXISTS (
                SELECT 1 FROM enrollments e
                WHERE e.class_id = c.class_id
                AND e.scraped_at >= :cutoff
            )
            AND EXISTS (
                SELECT 1 FROM subscriptions s
                WHERE s.class_id = c.class_id
            )
        """
        ),
        {"college_id": college_id, "cutoff": cutoff_timestamp},
    )
    counts["blocking_subscriptions"] = result.scalar()

    # Count courses that would be empty after class deletion
    result = db.execute(
        text(
            """
            SELECT COUNT(DISTINCT co.id)
            FROM courses co
            WHERE co.college_id = :college_id
            AND NOT EXISTS (
                SELECT 1 FROM classes c
                WHERE c.course_id = co.id
                AND (
                    c.created_at >= :cutoff
                    OR EXISTS (
                        SELECT 1 FROM enrollments e
                        WHERE e.class_id = c.class_id
                        AND e.scraped_at >= :cutoff
                    )
                )
            )
        """
        ),
        {"college_id": college_id, "cutoff": cutoff_timestamp},
    )
    counts["empty_courses"] = result.scalar()

    return counts


def purge_stale_enrollments(
    college_identifier: str,
    cutoff_timestamp: datetime,
    dry_run: bool = True,
    force_skip_subscribed: bool = False,
    db_session: Optional[Session] = None,
) -> Optional[Dict[str, int]]:
    """
    Purge stale term enrollments for a college.

    Args:
        college_identifier: College short name or id
        cutoff_timestamp: UTC timestamp - delete enrollments scraped before this
        dry_run: If True, only preview counts without deleting
        force_skip_subscribed: If True, skip deletion of classes with subscriptions instead of aborting
        db_session: Optional database session (for testing); if None, creates a new engine

    Returns:
        Dict with counts of deleted records, or None if college not found or aborted
    """
    # Use provided session or create a new engine
    if db_session is not None:
        db = db_session
        should_close = False
    else:
        engine = create_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
        )
        db = Session(engine)
        should_close = True

    try:
        # Find college by short_name or id
        try:
            college_id_int = int(college_identifier)
            college = db.query(College).filter(College.id == college_id_int).first()
        except ValueError:
            college = (
                db.query(College)
                .filter(College.short_name == college_identifier)
                .first()
            )

        if not college:
            print(f"❌ College '{college_identifier}' not found!")
            return None

        print(
            f"🔍 {'DRY RUN: ' if dry_run else ''}Purging stale enrollments for: {college.name} ({college.short_name})"
        )
        print(f"   Cutoff timestamp: {cutoff_timestamp.isoformat()}")
        college_id = college.id

        # Preview counts
        print("\n📊 Preview:")
        counts = preview_counts(db, college_id, cutoff_timestamp)
        print(f"   Stale enrollments (scraped < cutoff): {counts['stale_enrollments']}")
        print(f"   Orphan classes (no enrollments after purge): {counts['orphan_classes']}")
        print(f"   Empty courses (no classes after purge): {counts['empty_courses']}")

        if counts["blocking_subscriptions"] > 0:
            print(
                f"   ⚠️  Classes with active subscriptions: {counts['blocking_subscriptions']}"
            )
            if not force_skip_subscribed:
                print(
                    "\n❌ ABORTED: Active subscriptions exist for classes that would be deleted."
                )
                print(
                    "   Use --force-skip-subscribed to skip deletion of subscribed classes (NOT recommended)."
                )
                print(
                    "   Or manually deactivate subscriptions first using admin tools."
                )
                return None
            else:
                print(
                    "   ⚠️  --force-skip-subscribed set: Will skip classes with subscriptions"
                )

        if counts["stale_enrollments"] == 0:
            print("\n   No stale enrollments to purge.")
            return {
                "enrollments": 0,
                "classes": 0,
                "courses": 0,
            }

        if dry_run:
            print("\n✅ Dry run complete. Use --confirm to actually delete.")
            return None

        # Actual deletion (only with --confirm)
        print("\n🗑️  Deleting...")

        deletion_counts = {
            "enrollments": 0,
            "classes": 0,
            "courses": 0,
        }

        # 1. Delete stale enrollments
        result = db.execute(
            text(
                """
                DELETE FROM enrollments 
                WHERE college_id = :college_id 
                AND scraped_at < :cutoff
            """
            ),
            {"college_id": college_id, "cutoff": cutoff_timestamp},
        )
        deletion_counts["enrollments"] = result.rowcount
        print(f"   Deleted {deletion_counts['enrollments']} enrollments")

        # 2. Delete orphan classes (no remaining enrollments, NEVER with subscriptions)
        # IMPORTANT: ALWAYS check subscriptions - we NEVER delete classes with active subscriptions
        # force_skip_subscribed only disables the early abort above, not this safety check
        result = db.execute(
            text(
                """
                DELETE FROM classes c
                WHERE c.course_id IN (
                    SELECT co.id FROM courses co WHERE co.college_id = :college_id
                )
                AND c.created_at < :cutoff
                AND NOT EXISTS (
                    SELECT 1 FROM enrollments e
                    WHERE e.class_id = c.class_id
                )
                AND NOT EXISTS (
                    SELECT 1 FROM subscriptions s
                    WHERE s.class_id = c.class_id
                )
            """
            ),
            {"college_id": college_id, "cutoff": cutoff_timestamp},
        )
        deletion_counts["classes"] = result.rowcount
        print(f"   Deleted {deletion_counts['classes']} classes")

        # 3. Delete empty courses (no remaining classes)
        result = db.execute(
            text(
                """
                DELETE FROM courses co
                WHERE co.college_id = :college_id
                AND NOT EXISTS (
                    SELECT 1 FROM classes c
                    WHERE c.course_id = co.id
                )
            """
            ),
            {"college_id": college_id},
        )
        deletion_counts["courses"] = result.rowcount
        print(f"   Deleted {deletion_counts['courses']} courses")

        # Commit all deletions
        if db_session is None:
            db.commit()
        else:
            # For test sessions, commit will be handled by the test framework
            db.commit()

        print(f"\n✅ Purge complete for {college.name}")

        return deletion_counts

    finally:
        if should_close:
            db.close()
            if 'engine' in locals():
                engine.dispose()


def main():
    parser = argparse.ArgumentParser(
        description="Purge stale term enrollments after a term flip",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview mode (default - no deletion)
  python purge_stale_term_enrollments.py --college cornell --before-scraped-at "2025-01-15T00:00:00Z"
  
  # Actually delete (requires --confirm)
  python purge_stale_term_enrollments.py --college cornell --before-scraped-at "2025-01-15T00:00:00Z" --confirm
  
  # Force skip classes with subscriptions (use with caution)
  python purge_stale_term_enrollments.py --college cornell --before-scraped-at "2025-01-15T00:00:00Z" --confirm --force-skip-subscribed
        """,
    )

    parser.add_argument(
        "--college",
        type=str,
        required=True,
        help="College short name (e.g., 'cornell') or id",
    )

    parser.add_argument(
        "--before-scraped-at",
        type=str,
        required=True,
        help="UTC timestamp cutoff (ISO format, e.g., '2025-01-15T00:00:00Z'). Delete enrollments scraped before this.",
    )

    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually delete data (default is preview mode)",
    )

    parser.add_argument(
        "--force-skip-subscribed",
        action="store_true",
        help="Continue even if subscriptions block some classes (skips those classes but never deletes them)",
    )

    args = parser.parse_args()

    # Parse timestamp
    try:
        cutoff = datetime.fromisoformat(args.before_scraped_at.replace("Z", "+00:00"))
    except ValueError as e:
        print(f"❌ Invalid timestamp format: {e}")
        print("   Use ISO format with timezone, e.g., '2025-01-15T00:00:00Z'")
        sys.exit(1)

    # Default to dry run unless --confirm is set
    dry_run = not args.confirm

    if dry_run:
        print("⚠️  PREVIEW MODE - No data will be deleted. Use --confirm to actually delete.\n")

    result = purge_stale_enrollments(
        args.college.lower(),
        cutoff,
        dry_run=dry_run,
        force_skip_subscribed=args.force_skip_subscribed,
    )

    if result:
        print("\n📋 Summary:")
        print(f"  Enrollments deleted: {result['enrollments']}")
        print(f"  Classes deleted: {result['classes']}")
        print(f"  Courses deleted: {result['courses']}")
        sys.exit(0)
    elif result is None and not dry_run:
        # Aborted due to blocking subscriptions or not found
        sys.exit(1)
    else:
        # Dry run completed successfully
        sys.exit(0)


if __name__ == "__main__":
    main()
