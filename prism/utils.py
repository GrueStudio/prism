"""
Utility functions for the Prism CLI application.
"""

from datetime import datetime
from typing import Optional, Tuple

from prism.constants import DATE_FORMATS, DATE_MAX_YEARS_FUTURE, DATE_MAX_YEARS_PAST


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


def validate_date_range(date: datetime) -> Tuple[bool, Optional[str]]:
    """
    Validate that a date is within acceptable range.
    
    Args:
        date: The datetime object to validate.
        
    Returns:
        A tuple of (is_valid, error_message). If valid, error_message is None.
    """
    now = datetime.now()
    min_date = datetime(now.year - DATE_MAX_YEARS_PAST, now.month, now.day)
    max_date = datetime(now.year + DATE_MAX_YEARS_FUTURE, now.month, now.day)
    
    if date < min_date:
        return False, (
            f"Date {date.strftime('%Y-%m-%d')} is too far in the past. "
            f"Dates must be within the last {DATE_MAX_YEARS_PAST} year."
        )
    
    if date > max_date:
        return False, (
            f"Date {date.strftime('%Y-%m-%d')} is too far in the future. "
            f"Dates must be within the next {DATE_MAX_YEARS_FUTURE} years."
        )
    
    return True, None


def format_date(date: datetime) -> str:
    """
    Format a datetime object to the standard ISO 8601 format.
    
    Args:
        date: The datetime object to format.
        
    Returns:
        A string in YYYY-MM-DD format.
    """
    return date.strftime("%Y-%m-%d")
