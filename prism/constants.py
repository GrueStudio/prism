"""
Constants for the Prism CLI application.
"""

# Slug-related constants
SLUG_MAX_LENGTH = 15
SLUG_REGEX_PATTERN = r"[a-z0-9\-]"
SLUG_ERROR_MESSAGE = f"Slug must be kebab-case, alphanumeric with hyphens, and max {SLUG_MAX_LENGTH} characters."

# Status command constants
STATUS_HEADER_WIDTH = 25

# Percentage calculation precision
PERCENTAGE_ROUND_PRECISION = 1