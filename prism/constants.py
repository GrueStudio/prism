"""
Constants for the Prism CLI application.

Note: These constants serve as default fallback values.
Actual values are loaded from .prism/config.json at runtime via ConfigManager.
"""
from pathlib import Path
from typing import Any, Optional
import json

# =============================================================================
# Default Fallback Values
# These are used if config.json doesn't exist or doesn't specify a value.
# =============================================================================

# Slug-related defaults
DEFAULT_SLUG_MAX_LENGTH = 15
DEFAULT_SLUG_REGEX_PATTERN = r"^[a-z0-9-]+$"  # Full pattern for slug validation
DEFAULT_SLUG_WORD_LIMIT = 3
DEFAULT_SLUG_FILLER_WORDS = [
    "a", "an", "and", "as", "at", "by", "for", "from", "if", "in",
    "into", "of", "on", "or", "the", "to", "with"
]

# Status command defaults
DEFAULT_STATUS_HEADER_WIDTH = 25

# Percentage calculation defaults
DEFAULT_PERCENTAGE_ROUND_PRECISION = 1

# Validation error messages (not configurable)
VALIDATION_NAME_REQUIRED = "Name is required for all items."
VALIDATION_INVALID_STATUS = "Status must be one of: pending, in-progress, completed, cancelled, archived."
VALIDATION_DUPLICATE_SLUG = "An item with this slug already exists in the same parent. Please use a unique name."

# Status constants (not configurable)
DEFAULT_STATUS = "pending"
VALID_STATUSES = ["pending", "in-progress", "completed", "cancelled", "archived"]
COMPLETED_STATUS = "completed"
ARCHIVED_STATUS = "archived"
IN_PROGRESS_STATUS = "in-progress"

# Date format defaults
DEFAULT_DATE_FORMATS = [
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
DEFAULT_DATE_MAX_YEARS_FUTURE = 10
DEFAULT_DATE_MAX_YEARS_PAST = 1

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
    f"Invalid date format. Supported formats: YYYY-MM-DD, YYYY/MM/DD, DD-MM-YYYY, DD/MM/YYYY, "
    f"MM-DD-YYYY, MM/DD/YYYY, YYYYMMDD, 'DD Month YYYY', 'Month DD, YYYY'. "
    f"Examples: 2024-12-31, 31/12/2024, 12-31-2024, '31 December 2024', 'December 31, 2024'."
)

# Aliases for backward compatibility
STATUS_HEADER_WIDTH = DEFAULT_STATUS_HEADER_WIDTH
PERCENTAGE_ROUND_PRECISION = DEFAULT_PERCENTAGE_ROUND_PRECISION
DATE_FORMATS = DEFAULT_DATE_FORMATS
DATE_MAX_YEARS_FUTURE = DEFAULT_DATE_MAX_YEARS_FUTURE
DATE_MAX_YEARS_PAST = DEFAULT_DATE_MAX_YEARS_PAST


# =============================================================================
# Config Loader
# Load values from .prism/config.json at runtime.
# =============================================================================

_config_manager_instance: Optional['ConfigManager'] = None


class ConfigManager:
    """
    Manages loading configuration from a config.json file with fallback to defaults.
    
    This class is independent of StorageManager to avoid cyclic dependencies.
    StorageManager handles persistence; ConfigManager handles runtime access.

    Usage:
        # With default path (.prism/config.json)
        config = ConfigManager()
        slug_max_length = config.get('slug_max_length', DEFAULT_SLUG_MAX_LENGTH)
        
        # With custom path
        config = ConfigManager(config_path=Path("/custom/path/config.json"))
        date_formats = config.get('date_formats', DEFAULT_DATE_FORMATS)
    """
    
    def __init__(self, config_path: Optional[Path] = None, prism_dir: Optional[Path] = None) -> None:
        """
        Initialize ConfigManager.
        
        Args:
            config_path: Direct path to config.json file. Takes precedence over prism_dir.
            prism_dir: Path to .prism/ directory. Config path will be prism_dir/config.json.
        """
        self._config: Optional[dict] = None
        
        if config_path is not None:
            self._config_path = config_path
        elif prism_dir is not None:
            self._config_path = prism_dir / "config.json"
        else:
            self._config_path = Path(".prism") / "config.json"
    
    def _load_config(self) -> dict:
        """Load config from config.json file."""
        if self._config is not None:
            return self._config
        
        if self._config_path.exists():
            try:
                with open(self._config_path, "r") as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._config = {}
        else:
            self._config = {}
        
        return self._config
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a config value with fallback to default.

        Args:
            key: Configuration key name.
            default: Default value if key not found.

        Returns:
            Config value or default.
        """
        config = self._load_config()
        return config.get(key, default)

    def get_int(self, key: str, default: int) -> int:
        """Get an integer config value with fallback."""
        value = self.get(key, default)
        return int(value) if value is not None else default

    def get_list(self, key: str, default: list) -> list:
        """Get a list config value with fallback."""
        value = self.get(key, default)
        return list(value) if isinstance(value, (list, tuple)) else default

    def get_str(self, key: str, default: str) -> str:
        """Get a string config value with fallback."""
        value = self.get(key, default)
        return str(value) if value is not None else default
    
    def reload(self) -> dict:
        """Force reload of config from disk."""
        self._config = None
        return self._load_config()
    
    @property
    def config_path(self) -> Path:
        """Get the config file path."""
        return self._config_path


def get_config_manager(reset: bool = False) -> ConfigManager:
    """
    Get the singleton ConfigManager instance with default path.
    
    Args:
        reset: If True, reset the singleton and create a new instance.
    
    Returns:
        ConfigManager singleton instance.
    """
    global _config_manager_instance
    if _config_manager_instance is None or reset:
        _config_manager_instance = ConfigManager()
    return _config_manager_instance


def reset_config_manager() -> None:
    """Reset the singleton ConfigManager instance (useful for testing)."""
    global _config_manager_instance
    _config_manager_instance = None


# Convenience functions for common config access
# These use the singleton with default path (.prism/config.json)
def get_slug_max_length() -> int:
    """Get slug max length from config or default."""
    return get_config_manager().get_int('slug_max_length', DEFAULT_SLUG_MAX_LENGTH)


def get_slug_regex_pattern() -> str:
    """Get slug regex pattern from config or default."""
    return get_config_manager().get_str('slug_regex_pattern', DEFAULT_SLUG_REGEX_PATTERN)


def get_slug_word_limit() -> int:
    """Get slug word limit from config or default."""
    return get_config_manager().get_int('slug_word_limit', DEFAULT_SLUG_WORD_LIMIT)


def get_slug_filler_words() -> list:
    """Get slug filler words from config or default."""
    return get_config_manager().get_list('slug_filler_words', DEFAULT_SLUG_FILLER_WORDS)


def get_date_formats() -> list:
    """Get date formats from config or default."""
    return get_config_manager().get_list('date_formats', DEFAULT_DATE_FORMATS)


def get_date_max_years_future() -> int:
    """Get date max years future from config or default."""
    return get_config_manager().get_int('date_max_years_future', DEFAULT_DATE_MAX_YEARS_FUTURE)


def get_date_max_years_past() -> int:
    """Get date max years past from config or default."""
    return get_config_manager().get_int('date_max_years_past', DEFAULT_DATE_MAX_YEARS_PAST)


def get_status_header_width() -> int:
    """Get status header width from config or default."""
    return get_config_manager().get_int('status_header_width', DEFAULT_STATUS_HEADER_WIDTH)


def get_percentage_round_precision() -> int:
    """Get percentage round precision from config or default."""
    return get_config_manager().get_int('percentage_round_precision', DEFAULT_PERCENTAGE_ROUND_PRECISION)
