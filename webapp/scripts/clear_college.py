#!/usr/bin/env python3
"""
Script to clear course/class data for a college.

This removes all courses, classes, enrollments, notification_logs, and optionally
subscriptions for a specific college, but keeps the college record itself.
Useful for re-scraping or cleaning up bad data.

Usage:
    python clear_college.py --college princeton --confirm
    python clear_college.py --college cornell --keep-subscriptions --confirm
"""

import argparse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from models.college import College


def clear_college_data(college_short_name: str, keep_subscriptions: bool = False):
    """
    Clear all course data for a college using raw SQL in correct dependency order.

    Args:
        college_short_name: College short name identifier
        keep_subscriptions: If True, keep notification_logs and subscription records

    Returns:
        Dict with counts of deleted records or None if college not found
    """
    # Create sync engine
    engine = create_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )

    with Session(engine) as db:
        # Find college
        college = (
            db.query(College).filter(College.short_name == college_short_name).first()
        )

        if not college:
            print(f"❌ College '{college_short_name}' not found!")
            return None

        print(f"🔍 Clearing data for: {college.name} ({college.short_name})")
        college_id = college.id

        # Check if college has any courses
        result = db.execute(
            text("SELECT COUNT(*) FROM courses WHERE college_id = :college_id"),
            {"college_id": college_id},
        )
        course_count = result.scalar()

        if course_count == 0:
            print("   No data to clear.")
            return {
                "courses": 0,
                "classes": 0,
                "enrollments": 0,
                "subscriptions": 0,
                "notification_logs": 0,
            }

        print(f"   Found {course_count} courses")

        # Manual CASCADE deletion in correct dependency order:
        # 1. notification_logs -> 2. subscriptions -> 3. enrollments -> 4. classes -> 5. courses

        counts = {
            "notification_logs": 0,
            "subscriptions": 0,
            "enrollments": 0,
            "classes": 0,
            "courses": 0,
        }

        if not keep_subscriptions:
            # Delete notification_logs (references subscriptions + college)
            result = db.execute(
                text("DELETE FROM notification_logs WHERE college_id = :college_id"),
                {"college_id": college_id},
            )
            counts["notification_logs"] = result.rowcount
            print(f"   Deleted {counts['notification_logs']} notification_logs")

            # Delete subscriptions (references classes + college)
            result = db.execute(
                text("DELETE FROM subscriptions WHERE college_id = :college_id"),
                {"college_id": college_id},
            )
            counts["subscriptions"] = result.rowcount
            print(f"   Deleted {counts['subscriptions']} subscriptions")
        else:
            print(
                f"   Keeping notification_logs and subscriptions (--keep-subscriptions)"
            )

        # Delete enrollments (references classes + college)
        result = db.execute(
            text("DELETE FROM enrollments WHERE college_id = :college_id"),
            {"college_id": college_id},
        )
        counts["enrollments"] = result.rowcount
        print(f"   Deleted {counts['enrollments']} enrollments")

        # Delete classes (references courses)
        result = db.execute(
            text(
                "DELETE FROM classes WHERE course_id IN "
                "(SELECT id FROM courses WHERE college_id = :college_id)"
            ),
            {"college_id": college_id},
        )
        counts["classes"] = result.rowcount
        print(f"   Deleted {counts['classes']} classes")

        # Delete courses (references college)
        result = db.execute(
            text("DELETE FROM courses WHERE college_id = :college_id"),
            {"college_id": college_id},
        )
        counts["courses"] = result.rowcount
        print(f"   Deleted {counts['courses']} courses")

        # Commit all deletions
        db.commit()

        print(f"\n✅ Data cleared successfully for {college.name}")

        return counts

    engine.dispose()


def main():
    parser = argparse.ArgumentParser(
        description="Clear course data for a college in the SeatSteal database"
    )

    parser.add_argument(
        "--college",
        type=str,
        required=True,
        help="College short name (e.g., 'princeton')",
    )

    parser.add_argument(
        "--keep-subscriptions",
        action="store_true",
        help="Keep notification_logs and subscription records (useful for testing)",
    )

    parser.add_argument(
        "--confirm", action="store_true", help="Confirm deletion (required for safety)"
    )

    args = parser.parse_args()

    if not args.confirm:
        print("⚠️  WARNING: This will delete all course data for the specified college!")
        print("   Use --confirm flag to proceed")
        return

    result = clear_college_data(
        args.college.lower(), keep_subscriptions=args.keep_subscriptions
    )

    if result:
        print("\nSummary:")
        print(f"  Courses deleted: {result['courses']}")
        print(f"  Classes deleted: {result['classes']}")
        print(f"  Enrollments deleted: {result['enrollments']}")
        if args.keep_subscriptions:
            print(f"  Notification logs kept: (not deleted)")
            print(f"  Subscriptions kept: (not deleted)")
        else:
            print(f"  Notification logs deleted: {result['notification_logs']}")
            print(f"  Subscriptions deleted: {result['subscriptions']}")


if __name__ == "__main__":
    main()
