"""
Constants for the Prism CLI application.
"""

# Slug-related constants
SLUG_MAX_LENGTH = 15
SLUG_REGEX_PATTERN = r"[a-z0-9\-]"
SLUG_ERROR_MESSAGE = f"Slug must be kebab-case, alphanumeric with hyphens, and max {SLUG_MAX_LENGTH} characters."
SLUG_ERROR_DETAILED = (
    f"Slugs must follow kebab-case format (lowercase letters, digits, and hyphens only), "
    f"with a maximum length of {SLUG_MAX_LENGTH} characters. "
    f"Example: 'my-awesome-project'"
)

# Status command constants
STATUS_HEADER_WIDTH = 25

# Percentage calculation precision
PERCENTAGE_ROUND_PRECISION = 1

# Validation error messages
VALIDATION_NAME_REQUIRED = "Name is required for all items."
VALIDATION_INVALID_STATUS = "Status must be one of: pending, in-progress, completed, cancelled, archived."
VALIDATION_DUPLICATE_SLUG = "An item with this slug already exists in the same parent. Please use a unique name."

# Status constants
DEFAULT_STATUS = "pending"
VALID_STATUSES = ["pending", "in-progress", "completed", "cancelled", "archived"]
COMPLETED_STATUS = "completed"
ARCHIVED_STATUS = "archived"
IN_PROGRESS_STATUS = "in-progress"

# Date formats
DATE_FORMATS = [
    "%Y-%m-%d",      # YYYY-MM-DD (ISO 8601)
    "%Y/%m/%d",      # YYYY/MM/DD
    "%d-%m-%Y",      # DD-MM-YYYY
    "%d/%m/%Y",      # DD/MM/YYYY
    "%m-%d-%Y",      # MM-DD-YYYY
    "%m/%d/%Y",      # MM/DD/YYYY
    "%Y%m%d",        # YYYYMMDD
    "%d %B %Y",      # DD Month YYYY (e.g., 31 December 2024)
    "%d %b %Y",      # DD Mon YYYY (e.g., 31 Dec 2024)
    "%B %d, %Y",     # Month DD, YYYY (e.g., December 31, 2024)
    "%b %d, %Y",     # Mon DD, YYYY (e.g., Dec 31, 2024)
]
DATE_FORMAT_ERROR = (
    f"Invalid date format. Supported formats: YYYY-MM-DD, YYYY/MM/DD, DD-MM-YYYY, DD/MM/YYYY, "
    f"MM-DD-YYYY, MM/DD/YYYY, YYYYMMDD, 'DD Month YYYY', 'Month DD, YYYY'. "
    f"Examples: 2024-12-31, 31/12/2024, 12-31-2024, '31 December 2024', 'December 31, 2024'."
)

# Date validation constants
DATE_MAX_YEARS_FUTURE = 10  # Maximum years in the future for due dates
DATE_MAX_YEARS_PAST = 1  # Maximum years in the past allowed (for historical tracking)
