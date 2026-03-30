"""
Utility functions for the Prism CLI application.
"""

from datetime import datetime, timezone
from typing import Optional, Tuple

# Configuration reflected from ConfigManager
DATE_FORMATS = []
DATE_MAX_YEARS_PAST = 0
DATE_MAX_YEARS_FUTURE = 0


def parse_date(date_string: str) -> Optional[datetime]:
    """
    Parse a date string using multiple supported formats from configuration.
    
    Args:
        date_string: The date string to parse.
        
    Returns:
        A timezone-aware (UTC) datetime object if parsing succeeds, None otherwise.
    """
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(date_string, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def validate_date_range(date: datetime) -> Tuple[bool, Optional[str]]:
    """
    Validate that a date is within acceptable range from configuration.
    
    Args:
        date: The datetime object to validate (should be timezone-aware).
        
    Returns:
        A tuple of (is_valid, error_message). If valid, error_message is None.
    """
    now = datetime.now(timezone.utc)
    
    min_date = datetime(now.year - DATE_MAX_YEARS_PAST, now.month, now.day, tzinfo=timezone.utc)
    max_date = datetime(now.year + DATE_MAX_YEARS_FUTURE, now.month, now.day, tzinfo=timezone.utc)
    
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


def to_local_time(dt: datetime) -> datetime:
    """
    Convert a UTC datetime to the local timezone.
    
    Args:
        dt: The UTC datetime object.
        
    Returns:
        A datetime object in the local timezone.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone()
