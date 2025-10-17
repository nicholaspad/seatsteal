#!/usr/bin/env python3
"""
Script to clear course/class data for a college.

This removes all courses, classes, and enrollments for a specific college,
but keeps the college record itself. Useful for re-scraping or cleaning up bad data.

Usage:
    python clear_college.py --college princeton --confirm
"""

import asyncio
import argparse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete
from uuid import uuid4

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from models.college import College
from models.course import Course
from models.class_model import Class
from models.enrollment import Enrollment
from models.subscription import Subscription


async def clear_college_data(college_short_name: str, keep_subscriptions: bool = False):
    """
    Clear all course data for a college.

    Args:
        college_short_name: College short name identifier
        keep_subscriptions: If True, keep subscription records (just deactivate)

    Returns:
        Dict with counts of deleted records
    """
    engine = create_async_engine(
        settings.async_database_url,
        connect_args={"prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__"},
    )
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with AsyncSessionLocal() as db:
        # Find college
        result = await db.execute(
            select(College).where(College.short_name == college_short_name)
        )
        college = result.scalar_one_or_none()

        if not college:
            print(f"❌ College '{college_short_name}' not found!")
            return None

        print(f"🔍 Clearing data for: {college.name} ({college.short_name})")

        # Get course IDs for this college
        course_result = await db.execute(
            select(Course.id).where(Course.college_id == college.id)
        )
        course_ids = [row[0] for row in course_result.all()]

        print(f"   Found {len(course_ids)} courses")

        if not course_ids:
            print("   No data to clear.")
            return {"courses": 0, "classes": 0, "enrollments": 0, "subscriptions": 0}

        # Get class IDs
        class_result = await db.execute(
            select(Class.class_id).where(Class.course_id.in_(course_ids))
        )
        class_ids = [row[0] for row in class_result.all()]

        print(f"   Found {len(class_ids)} classes")

        # Delete enrollments
        if class_ids:
            enrollment_delete = delete(Enrollment).where(
                Enrollment.class_id.in_(class_ids)
            )
            enrollment_result = await db.execute(enrollment_delete)
            enrollments_deleted = enrollment_result.rowcount
            print(f"   Deleted {enrollments_deleted} enrollment records")
        else:
            enrollments_deleted = 0

        # Handle subscriptions
        subscriptions_affected = 0
        if class_ids:
            if keep_subscriptions:
                # Deactivate instead of delete
                subscription_result = await db.execute(
                    select(Subscription).where(Subscription.class_id.in_(class_ids))
                )
                subscriptions = subscription_result.scalars().all()
                for sub in subscriptions:
                    sub.is_active = False
                subscriptions_affected = len(subscriptions)
                print(f"   Deactivated {subscriptions_affected} subscriptions")
            else:
                # Delete subscriptions
                subscription_delete = delete(Subscription).where(
                    Subscription.class_id.in_(class_ids)
                )
                subscription_result = await db.execute(subscription_delete)
                subscriptions_affected = subscription_result.rowcount
                print(f"   Deleted {subscriptions_affected} subscriptions")

        # Delete classes
        if class_ids:
            class_delete = delete(Class).where(Class.course_id.in_(course_ids))
            class_result = await db.execute(class_delete)
            classes_deleted = class_result.rowcount
            print(f"   Deleted {classes_deleted} classes")
        else:
            classes_deleted = 0

        # Delete courses
        course_delete = delete(Course).where(Course.college_id == college.id)
        course_result = await db.execute(course_delete)
        courses_deleted = course_result.rowcount
        print(f"   Deleted {courses_deleted} courses")

        # Commit all deletions
        await db.commit()

        print(f"\n✅ Data cleared successfully for {college.name}")

        return {
            "courses": courses_deleted,
            "classes": classes_deleted,
            "enrollments": enrollments_deleted,
            "subscriptions": subscriptions_affected,
        }

    await engine.dispose()


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
        help="Keep subscription records (deactivate instead of delete)",
    )

    parser.add_argument(
        "--confirm", action="store_true", help="Confirm deletion (required for safety)"
    )

    args = parser.parse_args()

    if not args.confirm:
        print(
            "⚠️  WARNING: This will delete all course data for the specified college!"
        )
        print("   Use --confirm flag to proceed")
        return

    result = asyncio.run(
        clear_college_data(
            args.college.lower(), keep_subscriptions=args.keep_subscriptions
        )
    )

    if result:
        print("\nSummary:")
        print(f"  Courses deleted: {result['courses']}")
        print(f"  Classes deleted: {result['classes']}")
        print(f"  Enrollments deleted: {result['enrollments']}")
        if args.keep_subscriptions:
            print(f"  Subscriptions deactivated: {result['subscriptions']}")
        else:
            print(f"  Subscriptions deleted: {result['subscriptions']}")


if __name__ == "__main__":
    main()
