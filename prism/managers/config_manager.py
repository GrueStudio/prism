"""
Configuration manager for the Prism CLI.

Handles loading, saving, and dynamic access to configuration settings.
Features:
- Dynamic uppercase attribute access (e.g., config.SLUG_MAX_LENGTH).
- Automatic persistence on change.
- List operations (add, remove).
- Schema-backed by ConfigFile Pydantic model.
- Reflection: Updates static variables in models when configuration changes.
"""

import json
from pathlib import Path
from typing import Any, List, Optional

from prism.models.config import ConfigFile, BugType
from prism.managers.storage_manager import StorageManager


_config_manager_instance: Optional["ConfigManager"] = None


class ConfigManager:
    """
    Manages project configuration with dynamic access and automatic persistence.
    
    Acts as the single source of truth for configuration in the application.
    """

    def __init__(self, prism_dir: Optional[Path] = None, storage: Optional[StorageManager] = None):
        """
        Initialize the ConfigManager.

        Args:
            prism_dir: Path to .prism/ directory.
            storage: Optional StorageManager instance. If not provided, a new one is created.
        """
        self.storage = storage if storage else StorageManager(prism_dir)
        self._config: ConfigFile = self.storage.load_config()
        self._reflect_to_models()

    def __getattr__(self, name: str) -> Any:
        """
        Allow uppercase attribute access for configuration keys.
        
        Example: config.SLUG_MAX_LENGTH -> self._config.slug_max_length
        """
        # Convert UPPER_CASE to lower_case for Pydantic model access
        attr_name = name.lower()
        if hasattr(self._config, attr_name):
            return getattr(self._config, attr_name)
        
        # Also check if it's a direct attribute of the manager
        if name in self.__dict__:
            return self.__dict__[name]
            
        raise AttributeError(f"ConfigManager has no attribute '{name}'")

    def _reflect_to_models(self) -> None:
        """
        Update static variables in models with current configuration.
        
        This breaks circular dependencies by pushing config to models
        instead of models pulling from ConfigManager.
        """
        # Update Orphan model
        from prism.models.orphan import Orphan
        Orphan.NAME_REGEX = self.ORPHAN_NAME_REGEX
        Orphan.DEFAULT_PRIORITY = self.ORPHAN_DEFAULT_PRIORITY
        Orphan.PRIORITY_MIN = self.ORPHAN_PRIORITY_MIN
        Orphan.PRIORITY_MAX = self.ORPHAN_PRIORITY_MAX
        Orphan.PRIORITY_LABELS = self.ORPHAN_PRIORITY_LABELS

        # Update utils date settings
        from prism import utils
        utils.DATE_FORMATS = self.DATE_FORMATS
        utils.DATE_MAX_YEARS_PAST = self.DATE_MAX_YEARS_PAST
        utils.DATE_MAX_YEARS_FUTURE = self.DATE_MAX_YEARS_FUTURE

    def get_model(self) -> ConfigFile:
        """Get the underlying ConfigFile model."""
        return self._config

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value and persist to disk.

        Args:
            key: Configuration key (case-insensitive).
            value: New value.
        """
        key = key.lower()
        if not hasattr(self._config, key):
            raise AttributeError(f"Configuration key '{key}' not found.")
        
        # Handle type conversion if necessary
        field_type = type(getattr(self._config, key))
        try:
            if field_type == int:
                value = int(value)
            elif field_type == bool:
                if isinstance(value, str):
                    value = value.lower() in ("true", "yes", "1")
        except (ValueError, TypeError):
            raise ValueError(f"Invalid value for key '{key}'. Expected {field_type.__name__}.")

        setattr(self._config, key, value)
        self.save()

    def add(self, key: str, value: Any) -> None:
        """
        Add an item to a list configuration field.

        Args:
            key: Configuration key (case-insensitive).
            value: Item to add (or JSON string for complex objects).
        """
        key = key.lower()
        current_value = getattr(self._config, key, None)

        if not isinstance(current_value, list):
            raise ValueError(f"Configuration key '{key}' is not a list.")

        # Handle complex objects like bug_types
        if key == "bug_types":
            if isinstance(value, str):
                try:
                    data = json.loads(value)
                    new_item = BugType(**data)
                except (json.JSONDecodeError, ValueError) as e:
                    raise ValueError(f"Invalid bug type data: {e}")
            elif isinstance(value, dict):
                new_item = BugType(**value)
            else:
                new_item = value
            
            # Check for duplicates by prefix
            if any(bt.prefix == new_item.prefix for bt in current_value):
                raise ValueError(f"Bug type with prefix '{new_item.prefix}' already exists.")
            current_value.append(new_item)
        
        else:
            # String lists (slug_filler_words, date_formats)
            if value in current_value:
                raise ValueError(f"Value '{value}' already exists in '{key}'.")
            current_value.append(value)

        self.save()

    def remove(self, key: str, value: str) -> None:
        """
        Remove an item from a list configuration field.

        Args:
            key: Configuration key (case-insensitive).
            value: Item to remove (or identifier like prefix for bug_types).
        """
        key = key.lower()
        current_value = getattr(self._config, key, None)

        if not isinstance(current_value, list):
            raise ValueError(f"Configuration key '{key}' is not a list.")

        if key == "bug_types":
            # Remove by prefix
            original_len = len(current_value)
            new_list = [bt for bt in current_value if bt.prefix != value]
            if len(new_list) == original_len:
                raise ValueError(f"Bug type with prefix '{value}' not found.")
            setattr(self._config, key, new_list)
        else:
            # String lists
            if value not in current_value:
                raise ValueError(f"Value '{value}' not found in '{key}'.")
            current_value.remove(value)

        self.save()

    def update_dict(self, key: str, item_key: str, item_value: Any) -> None:
        """
        Update a dictionary configuration field.
        """
        key = key.lower()
        current_value = getattr(self._config, key, None)

        if not isinstance(current_value, dict):
            raise ValueError(f"Configuration key '{key}' is not a dictionary.")

        current_value[item_key] = item_value
        self.save()

    def remove_from_dict(self, key: str, item_key: str) -> None:
        """Remove a key from a dictionary configuration field."""
        key = key.lower()
        current_value = getattr(self._config, key, None)

        if not isinstance(current_value, dict):
            raise ValueError(f"Configuration key '{key}' is not a dictionary.")

        if item_key not in current_value:
            raise KeyError(f"Key '{item_key}' not found in '{key}'.")

        del current_value[item_key]
        self.save()

    def save(self) -> None:
        """Persist current configuration to disk."""
        self.storage.save_config(self._config)
        self._reflect_to_models()

    def reload(self) -> None:
        """Reload configuration from disk."""
        self._config = self.storage.load_config()
        self._reflect_to_models()

    def get_bug_types(self) -> List[BugType]:
        """Get all configured bug types."""
        return self._config.bug_types

    def get_bug_type(self, name: str) -> Optional[BugType]:
        """
        Get a bug type by its name.

        Args:
            name: The name of the bug type (case-insensitive).
        """
        name_lower = name.lower()
        for bt in self._config.bug_types:
            if bt.name.lower() == name_lower:
                return bt
        return None


def get_config_manager(prism_dir: Optional[Path] = None, reset: bool = False) -> ConfigManager:
    """
    Get the singleton ConfigManager instance.

    Args:
        prism_dir: Path to .prism/ directory.
        reset: If True, reset the singleton and create a new instance.

    Returns:
        ConfigManager singleton instance.
    """
    global _config_manager_instance
    if _config_manager_instance is None or reset:
        _config_manager_instance = ConfigManager(prism_dir=prism_dir)
    return _config_manager_instance


def reset_config_manager() -> None:
    """Reset the singleton ConfigManager instance."""
    global _config_manager_instance
    _config_manager_instance = None
