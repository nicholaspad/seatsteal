#!/usr/bin/env python3
"""
Script to add a new college to the database.

Usage:
    python add_college.py --name "Princeton University" --short-name "princeton" --domain "princeton.edu"
"""

import asyncio
import argparse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from models.college import College


async def add_college(
    name: str,
    short_name: str,
    domain: str = None,
    term_code: str = None,
    term_name: str = None,
    email_enabled: bool = True,
    sms_enabled: bool = False,
):
    """
    Add a new college to the database.

    Args:
        name: Full college name
        short_name: Short identifier (lowercase, no spaces)
        domain: College domain (e.g., "princeton.edu")
        term_code: Current term code
        term_name: Current term name
        email_enabled: Enable email notifications
        sms_enabled: Enable SMS notifications
    """
    # Create database engine
    engine = create_async_engine(settings.async_database_url)
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with AsyncSessionLocal() as db:
        # Check if college already exists
        result = await db.execute(
            select(College).where(College.short_name == short_name)
        )
        existing_college = result.scalar_one_or_none()

        if existing_college:
            print(f"❌ College with short_name '{short_name}' already exists!")
            print(f"   ID: {existing_college.id}")
            print(f"   Name: {existing_college.name}")
            return False

        # Create new college
        college = College(
            name=name,
            short_name=short_name,
            domain=domain,
            term_code=term_code,
            term_name=term_name,
            email_enabled=email_enabled,
            sms_enabled=sms_enabled,
            is_active=True,
        )

        db.add(college)
        await db.commit()
        await db.refresh(college)

        print("✅ College added successfully!")
        print(f"   ID: {college.id}")
        print(f"   Name: {college.name}")
        print(f"   Short Name: {college.short_name}")
        print(f"   Domain: {college.domain or 'N/A'}")
        print(f"   Term: {college.term_name or 'N/A'} ({college.term_code or 'N/A'})")
        print(
            f"   Notifications: Email={college.email_enabled}, SMS={college.sms_enabled}"
        )

        return True

    await engine.dispose()


async def list_colleges():
    """List all colleges in the database"""
    engine = create_async_engine(settings.async_database_url)
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(College).order_by(College.name))
        colleges = result.scalars().all()

        if not colleges:
            print("No colleges found in database.")
            return

        print(f"\nFound {len(colleges)} college(s):\n")
        print(
            f"{'ID':<5} {'Short Name':<15} {'Name':<40} {'Active':<8} {'Notifications'}"
        )
        print("-" * 90)

        for college in colleges:
            notifications = []
            if college.email_enabled:
                notifications.append("Email")
            if college.sms_enabled:
                notifications.append("SMS")
            notif_str = ", ".join(notifications) or "None"

            print(
                f"{college.id:<5} "
                f"{college.short_name:<15} "
                f"{college.name:<40} "
                f"{'Yes' if college.is_active else 'No':<8} "
                f"{notif_str}"
            )

    await engine.dispose()


def main():
    parser = argparse.ArgumentParser(
        description="Add a new college to the SeatSteal database"
    )

    parser.add_argument(
        "--list", action="store_true", help="List all existing colleges"
    )

    parser.add_argument(
        "--name", type=str, help="Full college name (e.g., 'Princeton University')"
    )

    parser.add_argument(
        "--short-name", type=str, help="Short identifier (e.g., 'princeton')"
    )

    parser.add_argument(
        "--domain", type=str, help="College domain (e.g., 'princeton.edu')"
    )

    parser.add_argument("--term-code", type=str, help="Current term code")

    parser.add_argument(
        "--term-name", type=str, help="Current term name (e.g., 'Fall 2025')"
    )

    parser.add_argument(
        "--no-email", action="store_true", help="Disable email notifications"
    )

    parser.add_argument(
        "--enable-sms", action="store_true", help="Enable SMS notifications"
    )

    args = parser.parse_args()

    # List colleges if --list flag provided
    if args.list:
        asyncio.run(list_colleges())
        return

    # Validate required arguments for adding a college
    if not args.name or not args.short_name:
        parser.error("--name and --short-name are required (unless using --list)")

    # Add college
    asyncio.run(
        add_college(
            name=args.name,
            short_name=args.short_name.lower(),
            domain=args.domain,
            term_code=args.term_code,
            term_name=args.term_name,
            email_enabled=not args.no_email,
            sms_enabled=args.enable_sms,
        )
    )


if __name__ == "__main__":
    main()
