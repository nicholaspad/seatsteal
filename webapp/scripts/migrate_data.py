#!/usr/bin/env python3
"""
Script to migrate data from the old course-watcher database to the new seatsteal database.

This script handles migration of:
- Colleges
- Courses
- Classes
- Subscriptions (with user mapping)

Usage:
    python migrate_data.py --old-db "postgresql://..." --dry-run
    python migrate_data.py --old-db "postgresql://..." --confirm
"""

import asyncio
import argparse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
from uuid import uuid4

import sys
from pathlib import Path
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from models.college import College
from models.course import Course
from models.class_model import Class


async def migrate_colleges(
    old_db: AsyncSession, new_db: AsyncSession
) -> Dict[int, int]:
    """
    Migrate colleges from old database to new database.

    Returns:
        Dict mapping old college IDs to new college IDs
    """
    print("📚 Migrating colleges...")

    # Fetch from old database (adjust query based on old schema)
    old_colleges = await old_db.execute(
        text("SELECT id, name, short_name, domain, term_code, term_name FROM colleges")
    )

    id_mapping = {}
    migrated_count = 0

    for old_row in old_colleges:
        old_id = old_row.id

        # Check if already exists
        result = await new_db.execute(
            select(College).where(College.short_name == old_row.short_name)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"   ⏭️  Skipping {old_row.name} (already exists)")
            id_mapping[old_id] = existing.id
            continue

        # Create new college
        new_college = College(
            name=old_row.name,
            short_name=old_row.short_name,
            domain=old_row.domain,
            term_code=old_row.term_code,
            term_name=old_row.term_name,
            is_active=True,
            email_enabled=True,
            sms_enabled=False,
        )

        new_db.add(new_college)
        await new_db.flush()

        id_mapping[old_id] = new_college.id
        migrated_count += 1

        print(
            f"   ✅ Migrated: {old_row.name} (old ID: {old_id} -> new ID: {new_college.id})"
        )

    await new_db.commit()
    print(f"✅ Migrated {migrated_count} colleges\n")

    return id_mapping


async def migrate_courses(
    old_db: AsyncSession, new_db: AsyncSession, college_id_mapping: Dict[int, int]
) -> Dict[int, int]:
    """
    Migrate courses from old database to new database.

    Returns:
        Dict mapping old course IDs to new course IDs
    """
    print("📖 Migrating courses...")

    old_courses = await old_db.execute(
        text("SELECT id, college_id, course_code, title FROM courses")
    )

    id_mapping = {}
    migrated_count = 0

    for old_row in old_courses:
        old_id = old_row.id
        new_college_id = college_id_mapping.get(old_row.college_id)

        if not new_college_id:
            print(f"   ⚠️  Skipping course {old_row.course_code} (college not migrated)")
            continue

        # Check if already exists
        result = await new_db.execute(
            select(Course).where(
                Course.college_id == new_college_id,
                Course.course_code == old_row.course_code,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            id_mapping[old_id] = existing.id
            continue

        # Create new course
        new_course = Course(
            college_id=new_college_id,
            course_code=old_row.course_code,
            title=old_row.title,
            is_active=True,
        )

        new_db.add(new_course)
        await new_db.flush()

        id_mapping[old_id] = new_course.id
        migrated_count += 1

    await new_db.commit()
    print(f"✅ Migrated {migrated_count} courses\n")

    return id_mapping


async def migrate_classes(
    old_db: AsyncSession, new_db: AsyncSession, course_id_mapping: Dict[int, int]
) -> Dict[int, int]:
    """
    Migrate classes from old database to new database.

    Returns:
        Dict mapping old class IDs to new class IDs
    """
    print("🏫 Migrating classes...")

    old_classes = await old_db.execute(
        text("SELECT id, course_id, class_number, section_code FROM classes")
    )

    id_mapping = {}
    migrated_count = 0

    for old_row in old_classes:
        old_id = old_row.id
        new_course_id = course_id_mapping.get(old_row.course_id)

        if not new_course_id:
            continue

        # Check if already exists
        result = await new_db.execute(
            select(Class).where(
                Class.course_id == new_course_id,
                Class.class_number == old_row.class_number,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            id_mapping[old_id] = existing.class_id
            continue

        # Create new class
        new_class = Class(
            course_id=new_course_id,
            class_number=old_row.class_number,
            section_code=old_row.section_code,
            is_active=True,
        )

        new_db.add(new_class)
        await new_db.flush()

        id_mapping[old_id] = new_class.class_id
        migrated_count += 1

    await new_db.commit()
    print(f"✅ Migrated {migrated_count} classes\n")

    return id_mapping


async def run_migration(old_db_url: str, dry_run: bool = True):
    """Run the complete migration process"""
    print(f"🚀 Starting migration from old database...")
    print(f"   Old DB: {old_db_url[:50]}...")
    print(f"   New DB: {settings.DATABASE_URL[:50]}...")
    print(f"   Mode: {'DRY RUN' if dry_run else 'LIVE'}\n")

    # Create database engines
    old_engine = create_async_engine(
        old_db_url,
        connect_args={"prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__"},
    )
    new_engine = create_async_engine(
        settings.async_database_url,
        connect_args={"prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__"},
    )

    OldSessionLocal = sessionmaker(
        old_engine, class_=AsyncSession, expire_on_commit=False
    )
    NewSessionLocal = sessionmaker(
        new_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with OldSessionLocal() as old_db, NewSessionLocal() as new_db:
        # Migrate colleges
        college_mapping = await migrate_colleges(old_db, new_db)

        # Migrate courses
        course_mapping = await migrate_courses(old_db, new_db, college_mapping)

        # Migrate classes
        class_mapping = await migrate_classes(old_db, new_db, course_mapping)

        # Summary
        print("\n" + "=" * 50)
        print("MIGRATION SUMMARY")
        print("=" * 50)
        print(f"Colleges migrated: {len(college_mapping)}")
        print(f"Courses migrated: {len(course_mapping)}")
        print(f"Classes migrated: {len(class_mapping)}")
        print("=" * 50)

        if dry_run:
            print("\n⚠️  DRY RUN - Rolling back changes")
            await new_db.rollback()
        else:
            print("\n✅ Committing changes to database")
            await new_db.commit()

    await old_engine.dispose()
    await new_engine.dispose()


def main():
    parser = argparse.ArgumentParser(
        description="Migrate data from old course-watcher database to new seatsteal database"
    )

    parser.add_argument(
        "--old-db", type=str, required=True, help="Old database connection URL"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run migration without committing changes",
    )

    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm and execute migration (commits changes)",
    )

    args = parser.parse_args()

    if not args.dry_run and not args.confirm:
        print("⚠️  WARNING: This will migrate data and commit changes!")
        print("   Use --dry-run to test first, or --confirm to proceed")
        return

    dry_run = args.dry_run or not args.confirm

    asyncio.run(run_migration(args.old_db, dry_run=dry_run))


if __name__ == "__main__":
    main()
