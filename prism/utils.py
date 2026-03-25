"""
Utility functions for the Prism CLI application.
"""

from datetime import datetime
from typing import Optional, Tuple

from prism.managers.config_manager import get_config_manager


def parse_date(date_string: str) -> Optional[datetime]:
    """
    Parse a date string using multiple supported formats from configuration.
    
    Args:
        date_string: The date string to parse.
        
    Returns:
        A datetime object if parsing succeeds, None otherwise.
    """
    config = get_config_manager()
    for fmt in config.DATE_FORMATS:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue
    return None


def validate_date_range(date: datetime) -> Tuple[bool, Optional[str]]:
    """
    Validate that a date is within acceptable range from configuration.
    
    Args:
        date: The datetime object to validate.
        
    Returns:
        A tuple of (is_valid, error_message). If valid, error_message is None.
    """
    config = get_config_manager()
    now = datetime.now()
    
    max_past = config.DATE_MAX_YEARS_PAST
    max_future = config.DATE_MAX_YEARS_FUTURE
    
    min_date = datetime(now.year - max_past, now.month, now.day)
    max_date = datetime(now.year + max_future, now.month, now.day)
    
    if date < min_date:
        return False, (
            f"Date {date.strftime('%Y-%m-%d')} is too far in the past. "
            f"Dates must be within the last {max_past} year."
        )
    
    if date > max_date:
        return False, (
            f"Date {date.strftime('%Y-%m-%d')} is too far in the future. "
            f"Dates must be within the next {max_future} years."
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
