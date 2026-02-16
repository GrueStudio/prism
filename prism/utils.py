"""
Utility functions for the Prism CLI application.
"""

from datetime import datetime
from typing import Optional

from prism.constants import DATE_FORMATS


def parse_date(date_string: str) -> Optional[datetime]:
    """
    Parse a date string using multiple supported formats.
    
    Args:
        date_string: The date string to parse.
        
    Returns:
        A datetime object if parsing succeeds, None otherwise.
        
    Examples:
        >>> parse_date("2024-12-31")  # ISO 8601
        >>> parse_date("31/12/2024")  # DD/MM/YYYY
        >>> parse_date("12-31-2024")  # MM-DD-YYYY
        >>> parse_date("31 December 2024")  # DD Month YYYY
        >>> parse_date("December 31, 2024")  # Month DD, YYYY
    """
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue
    return None


def format_date(date: datetime) -> str:
    """
    Format a datetime object to the standard ISO 8601 format.
    
    Args:
        date: The datetime object to format.
        
    Returns:
        A string in YYYY-MM-DD format.
    """
    return date.strftime("%Y-%m-%d")
