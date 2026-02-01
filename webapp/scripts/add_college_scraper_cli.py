#!/usr/bin/env python3
"""
Non-interactive CLI script to add a new college and its scraper to the database.

Usage:
    python add_college_scraper_cli.py --name "Ohio State University" --short-name "osu" --domain "osu.edu" --term-code "1252" --term-name "Spring 2025"
    
Required arguments:
    --name: Full college name (e.g., "Ohio State University")
    --short-name: Short name (lowercase, no spaces, e.g., "osu")
    
Optional arguments:
    --domain: College domain (e.g., "osu.edu")
    --term-code: Current term code (e.g., "1252")
    --term-name: Current term name (e.g., "Spring 2025")
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from config import settings
from models.college import College
from models.scraper import Scraper


def add_college_and_scraper(
    name: str,
    short_name: str,
    domain: str = None,
    term_code: str = None,
    term_name: str = None,
) -> bool:
    """Add a new college and linked scraper to the database.
    
    Args:
        name: Full college name
        short_name: Short name (lowercase, no spaces)
        domain: Optional college domain
        term_code: Optional current term code
        term_name: Optional current term name
        
    Returns:
        True if successful, False otherwise
    """
    
    print("Add New College & Scraper (CLI)")
    print("=" * 40)
    print()
    print("College Details:")
    print(f"  Name: {name}")
    print(f"  Short Name: {short_name}")
    print(f"  Domain: {domain or 'N/A'}")
    print(f"  Term Code: {term_code or 'N/A'}")
    print(f"  Term Name: {term_name or 'N/A'}")
    print()

    # Create database engine (sync)
    engine = create_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)

    with Session(engine) as db:
        # Check if college already exists
        existing_college = db.execute(
            select(College).where(College.short_name == short_name)
        ).scalar_one_or_none()

        if existing_college:
            print(f"Error: College with short_name '{short_name}' already exists!")
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

        print(f"College created with ID: {college.id}")

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
        print("✅ Successfully added college and scraper!")
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
    parser = argparse.ArgumentParser(
        description="Add a new college and scraper to the database (non-interactive)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python add_college_scraper_cli.py --name "Ohio State University" --short-name "osu" --domain "osu.edu" --term-code "1252" --term-name "Spring 2025"
  
  python add_college_scraper_cli.py --name "University of Michigan" --short-name "umich" --domain "umich.edu"
        """
    )
    
    parser.add_argument(
        "--name",
        required=True,
        help='Full college name (e.g., "Ohio State University")'
    )
    
    parser.add_argument(
        "--short-name",
        required=True,
        help='Short name - lowercase, no spaces (e.g., "osu")'
    )
    
    parser.add_argument(
        "--domain",
        help='College domain (e.g., "osu.edu")'
    )
    
    parser.add_argument(
        "--term-code",
        help='Current term code (e.g., "1252")'
    )
    
    parser.add_argument(
        "--term-name",
        help='Current term name (e.g., "Spring 2025")'
    )
    
    args = parser.parse_args()
    
    try:
        success = add_college_and_scraper(
            name=args.name,
            short_name=args.short_name,
            domain=args.domain,
            term_code=args.term_code,
            term_name=args.term_name,
        )
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
