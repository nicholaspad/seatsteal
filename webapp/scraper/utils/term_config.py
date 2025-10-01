from typing import Dict, Optional
from datetime import datetime


class TermConfig:
    """
    Utility for managing academic term configurations across different colleges.

    Each college may have different term codes and naming conventions.
    This class helps normalize and manage term information.
    """

    # Standard term mappings
    TERM_MAPPING = {
        'fall': ['fall', 'autumn'],
        'spring': ['spring'],
        'summer': ['summer'],
        'winter': ['winter', 'january'],
    }

    # Term code patterns for different colleges
    COLLEGE_TERM_PATTERNS = {
        'princeton': {
            # Princeton uses format: 1252 (1=Fall, 25=2025, 2=Spring)
            'format': 'SYYT',  # S=semester, YY=year, T=term
            'fall': '1',
            'spring': '2',
        },
        'brown': {
            # Brown uses format: 202520 (2025 Spring 20)
            'format': 'YYYYST',
            'fall': '10',
            'spring': '20',
        },
        'bu': {
            # BU uses format: similar to Brown
            'format': 'YYYYST',
            'fall': '09',
            'spring': '01',
            'summer': '05',
        },
        'cornell': {
            # Cornell uses format: FA25 (Fall 2025)
            'format': 'SSYY',
            'fall': 'FA',
            'spring': 'SP',
            'summer': 'SU',
        },
        'neu': {
            # Northeastern uses semester codes
            'format': 'YYYYMM',
            'fall': '09',
            'spring': '01',
            'summer': '05',
        },
        'usc': {
            # USC uses term codes
            'format': 'YYYYT',
            'fall': '3',
            'spring': '1',
            'summer': '2',
        },
    }

    @staticmethod
    def get_current_term(college_short_name: str) -> str:
        """
        Get the current academic term code for a college.

        Args:
            college_short_name: College identifier (e.g., 'princeton', 'brown')

        Returns:
            Term code string for the current academic term
        """
        now = datetime.now()
        month = now.month
        year = now.year

        # Determine current term based on month
        if month >= 8:  # August onwards = Fall
            term = 'fall'
            term_year = year
        elif month <= 5:  # January-May = Spring
            term = 'spring'
            term_year = year
        else:  # June-July = Summer
            term = 'summer'
            term_year = year

        return TermConfig.build_term_code(college_short_name, term, term_year)

    @staticmethod
    def build_term_code(college_short_name: str, term: str, year: int) -> str:
        """
        Build a term code for a specific college, term, and year.

        Args:
            college_short_name: College identifier
            term: Term name ('fall', 'spring', 'summer', 'winter')
            year: Full year (e.g., 2025)

        Returns:
            Formatted term code for the college
        """
        pattern = TermConfig.COLLEGE_TERM_PATTERNS.get(college_short_name)
        if not pattern:
            # Default fallback
            return f"{year}{term[:2].upper()}"

        year_str = str(year)
        year_short = year_str[2:]  # Last 2 digits

        format_type = pattern['format']
        term_code = pattern.get(term, '')

        if format_type == 'SYYT':  # Princeton format
            semester = pattern.get(term, '1')
            return f"{semester}{year_short}{semester}"

        elif format_type == 'YYYYST':  # Brown, BU format
            return f"{year}{term_code}"

        elif format_type == 'SSYY':  # Cornell format
            return f"{term_code}{year_short}"

        elif format_type == 'YYYYMM':  # NEU format
            return f"{year}{term_code}"

        elif format_type == 'YYYYT':  # USC format
            return f"{year}{term_code}"

        else:
            return f"{year}{term[:2].upper()}"

    @staticmethod
    def parse_term_name(term_code: str, college_short_name: str) -> Optional[str]:
        """
        Parse a term code to get a human-readable term name.

        Args:
            term_code: Raw term code
            college_short_name: College identifier

        Returns:
            Human-readable term name (e.g., "Fall 2025") or None
        """
        pattern = TermConfig.COLLEGE_TERM_PATTERNS.get(college_short_name)
        if not pattern:
            return None

        # This is a simplified parser - could be expanded based on needs
        try:
            if 'fall' in term_code.lower() or pattern.get('fall', '') in term_code:
                return f"Fall {term_code}"
            elif 'spring' in term_code.lower() or pattern.get('spring', '') in term_code:
                return f"Spring {term_code}"
            elif 'summer' in term_code.lower() or pattern.get('summer', '') in term_code:
                return f"Summer {term_code}"
            else:
                return term_code
        except Exception:
            return None

    @staticmethod
    def get_next_term(college_short_name: str, current_term_code: str) -> str:
        """
        Get the next academic term code.

        Args:
            college_short_name: College identifier
            current_term_code: Current term code

        Returns:
            Next term code
        """
        # Simplified - just get current term for now
        # Can be expanded to actually calculate next term
        return TermConfig.get_current_term(college_short_name)
