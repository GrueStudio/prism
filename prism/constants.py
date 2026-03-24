"""
Constants for the Prism CLI application.

Note: These constants serve as default fallback values.
Actual values are loaded from .prism/config.json at runtime via ConfigManager.
"""

# =============================================================================
# Default Fallback Values
# These are used if config.json doesn't exist or doesn't specify a value.
# =============================================================================

# Slug-related defaults
DEFAULT_SLUG_MAX_LENGTH = 15
DEFAULT_SLUG_REGEX_PATTERN = r"[a-z0-9-]"  # Character class for slug validation
DEFAULT_SLUG_WORD_LIMIT = 3
DEFAULT_SLUG_FILLER_WORDS = [
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "for",
    "from",
    "if",
    "in",
    "into",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
]

# Status command defaults
DEFAULT_STATUS_HEADER_WIDTH = 25

# Percentage calculation defaults
DEFAULT_PERCENTAGE_ROUND_PRECISION = 1

# Validation error messages (not configurable)
VALIDATION_NAME_REQUIRED = "Name is required for all items."
VALIDATION_INVALID_STATUS = (
    "Status must be one of: pending, in-progress, completed, cancelled, archived."
)
VALIDATION_DUPLICATE_SLUG = "An item with this slug already exists in the same parent. Please use a unique name."

# Status constants (not configurable)
DEFAULT_STATUS = "pending"
VALID_STATUSES = ["pending", "in-progress", "completed", "cancelled", "archived"]
COMPLETED_STATUS = "completed"
ARCHIVED_STATUS = "archived"
IN_PROGRESS_STATUS = "in-progress"
PENDING_STATUS = "pending"
CANCELLED_STATUS = "cancelled"
PAUSED_STATUS = "paused"

# Date format defaults
DEFAULT_DATE_FORMATS = [
    "%Y-%m-%d",  # YYYY-MM-DD (ISO 8601)
    "%Y/%m/%d",  # YYYY/MM/DD
    "%d-%m-%Y",  # DD-MM-YYYY
    "%d/%m/%Y",  # DD/MM/YYYY
    "%m-%d-%Y",  # MM-DD-YYYY
    "%m/%d/%Y",  # MM/DD/YYYY
    "%Y%m%d",  # YYYYMMDD
    "%d %B %Y",  # DD Month YYYY (e.g., 31 December 2024)
    "%d %b %Y",  # DD Mon YYYY (e.g., 31 Dec 2024)
    "%B %d, %Y",  # Month DD, YYYY (e.g., December 31, 2024)
    "%b %d, %Y",  # Mon DD, YYYY (e.g., Dec 31, 2024)
]
DEFAULT_DATE_MAX_YEARS_FUTURE = 10
DEFAULT_DATE_MAX_YEARS_PAST = 1

# Orphan defaults
DEFAULT_ORPHAN_NAME_REGEX = r"^[a-zA-Z0-9\s\-_'\"]+$"
DEFAULT_ORPHAN_DEFAULT_PRIORITY = 0
DEFAULT_ORPHAN_PRIORITY_MIN = -100
DEFAULT_ORPHAN_PRIORITY_MAX = 100
DEFAULT_ORPHAN_PRIORITY_LABELS: dict[str, int] = {
    "low": -10,
    "medium": 0,
    "high": 10,
    "critical": 50,
}

# Error messages (constructed from defaults, not configurable)
SLUG_MAX_LENGTH = DEFAULT_SLUG_MAX_LENGTH
SLUG_REGEX_PATTERN = DEFAULT_SLUG_REGEX_PATTERN
SLUG_ERROR_MESSAGE = f"Slug must be kebab-case, alphanumeric with hyphens, and max {SLUG_MAX_LENGTH} characters."
SLUG_ERROR_DETAILED = (
    f"Slugs must follow kebab-case format (lowercase letters, digits, and hyphens only), "
    f"with a maximum length of {SLUG_MAX_LENGTH} characters. "
    f"Example: 'my-awesome-project'"
)
DATE_FORMAT_ERROR = (
    "Invalid date format. Supported formats: YYYY-MM-DD, YYYY/MM/DD, DD-MM-YYYY, DD/MM/YYYY, "
    "MM-DD-YYYY, MM/DD/YYYY, YYYYMMDD, 'DD Month YYYY', 'Month DD, YYYY'. "
    "Examples: 2024-12-31, 31/12/2024, 12-31-2024, '31 December 2024', 'December 31, 2024'."
)

# Aliases for backward compatibility
STATUS_HEADER_WIDTH = DEFAULT_STATUS_HEADER_WIDTH
PERCENTAGE_ROUND_PRECISION = DEFAULT_PERCENTAGE_ROUND_PRECISION
DATE_FORMATS = DEFAULT_DATE_FORMATS
DATE_MAX_YEARS_FUTURE = DEFAULT_DATE_MAX_YEARS_FUTURE
DATE_MAX_YEARS_PAST = DEFAULT_DATE_MAX_YEARS_PAST
