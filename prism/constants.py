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