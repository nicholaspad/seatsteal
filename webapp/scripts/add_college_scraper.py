#!/usr/bin/env python3
"""
Interactive script to add a new college and its scraper to the database.

Usage:
    python add_college_scraper.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from config import settings
from models.college import College
from models.scraper import Scraper


def get_input(prompt: str, required: bool = True, default: str = None) -> str:
    """Get user input with optional default value."""
    if default:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "

    value = input(full_prompt).strip()

    if not value and default:
        return default
    if not value and required:
        print("Error: This field is required.")
        return get_input(prompt, required, default)
    return value


def add_college_and_scraper():
    """Interactively add a new college and linked scraper to the database."""

    print("Add New College & Scraper")
    print("=" * 40)
    print()

    # Get college information from user
    name = get_input("Full college name (e.g., Princeton University)")
    short_name = get_input("Short name (lowercase, no spaces, e.g., princeton)").lower()
    domain = get_input("Domain (e.g., princeton.edu)", required=False)
    term_code = get_input(
        "Current term code (e.g., 1262 for Princeton)", required=False
    )
    term_name = get_input("Current term name (e.g., Fall 2025)", required=False)

    print()
    print("Summary:")
    print(f"  Name: {name}")
    print(f"  Short Name: {short_name}")
    print(f"  Domain: {domain or 'N/A'}")
    print(f"  Term Code: {term_code or 'N/A'}")
    print(f"  Term Name: {term_name or 'N/A'}")
    print()

    confirm = input("Proceed with adding this college? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Operation cancelled.")
        return False

    # Create database engine (sync)
    engine = create_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)

    with Session(engine) as db:
        # Check if college already exists
        existing_college = db.execute(
            select(College).where(College.short_name == short_name)
        ).scalar_one_or_none()

        if existing_college:
            print(f"\nError: College with short_name '{short_name}' already exists!")
            print(f"   ID: {existing_college.id}")
            print(f"   Name: {existing_college.name}")
            engine.dispose()
            return False

        # Create new college
        college = College(
            name=name,
            short_name=short_name,
            domain=domain or None,
            term_code=term_code or None,
            term_name=term_name or None,
            email_enabled=True,
            sms_enabled=False,
            is_active=True,
        )

        db.add(college)
        db.flush()  # Get the college ID before committing

        print(f"\nCollege created with ID: {college.id}")

        # Create linked scraper
        scraper = Scraper(
            college_id=college.id,
            status="idle",
            run_count=0,
            success_count=0,
            error_count=0,
        )

        db.add(scraper)
        db.commit()
        db.refresh(scraper)

        print(f"Scraper created with ID: {scraper.id}")
        print()
        print("Successfully added college and scraper!")
        print(f"  College ID: {college.id}")
        print(f"  College Name: {college.name}")
        print(f"  Short Name: {college.short_name}")
        print(f"  Domain: {college.domain or 'N/A'}")
        print(f"  Term: {college.term_name or 'N/A'} ({college.term_code or 'N/A'})")
        print(f"  Scraper ID: {scraper.id}")
        print(f"  Scraper Status: {scraper.status}")

    engine.dispose()
    return True


def main():
    try:
        add_college_and_scraper()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
