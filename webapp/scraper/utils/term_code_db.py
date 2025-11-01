"""
Shared utility for retrieving term codes from the database.

All scrapers should use this module to get term codes instead of
generating them or using hardcoded fallbacks.
"""

from sqlalchemy import select
from scraper.utils.logger import scraper_logger as logger


def get_term_code_from_db(db_session, college_short_name: str) -> str:
    """
    Get the current term code for a college from the database.

    Args:
        db_session: SQLAlchemy database session
        college_short_name: College short name (e.g., 'bu', 'cornell', 'brown')

    Returns:
        Term code string from the database

    Raises:
        ValueError: If college not found or term_code is missing/empty
        Exception: If database query fails
    """
    if not db_session:
        raise ValueError(
            f"Database session is required to get term code for {college_short_name}"
        )

    try:
        from models.college import College

        college = db_session.execute(
            select(College).where(College.short_name == college_short_name)
        ).scalar_one_or_none()

        if not college:
            raise ValueError(
                f"College '{college_short_name}' not found in database. "
                f"Please add the college using the add_college script."
            )

        if not college.term_code or college.term_code.strip() == "":
            raise ValueError(
                f"Term code for college '{college_short_name}' is empty in database. "
                f"Please update the colleges table with a valid term code. "
                f"See TERM_CODES.md for instructions on finding term codes."
            )

        logger.info(
            f"Using term code from database for {college_short_name}: {college.term_code}"
        )
        return college.term_code

    except ValueError:
        # Re-raise ValueError as-is
        raise
    except Exception as e:
        raise Exception(
            f"Failed to query term code for {college_short_name} from database: {e}"
        ) from e
