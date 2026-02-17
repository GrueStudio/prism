"""
Storage manager for the Prism CLI.

Handles loading and saving of all JSON files in the .prism/ directory.
"""
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from prism.newmodels import (
    StrategicFile,
    ExecutionFile,
    OrphansFile,
    ConfigFile,
    Phase,
    Milestone,
    Objective,
    Deliverable,
    Action,
    Orphan,
)


class StorageManager:
    """
    Manages persistence of project data to JSON files in the .prism/ directory.
    
    Handles atomic writes to prevent data corruption.
    """

    def __init__(self, prism_dir: Optional[Path] = None):
        """
        Initialize the StorageManager with a .prism/ directory path.

        Args:
            prism_dir: Path to the .prism/ directory. Defaults to .prism/ in current directory.
        """
        self.prism_dir = prism_dir if prism_dir else Path(".prism")
        self._ensure_prism_dir()

    def _ensure_prism_dir(self) -> None:
        """Create the .prism/ directory if it doesn't exist."""
        self.prism_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, filename: str) -> Path:
        """Get the full path for a file in the .prism/ directory.

        Args:
            filename: Name of the file.

        Returns:
            Full path to the file.
        """
        return self.prism_dir / filename

    def _atomic_write(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Write data to a JSON file atomically to prevent corruption.

        Args:
            file_path: Path to the file to write.
            data: Dictionary data to write as JSON.

        Raises:
            Exception: Re-raises any exception after cleaning up temp file.
        """
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self.prism_dir,
            prefix='.tmp_prism_',
            suffix='.json'
        )

        try:
            with os.fdopen(temp_fd, 'w') as temp_file:
                json.dump(data, temp_file, indent=2)
            os.replace(temp_path, file_path)
        except Exception as e:
            try:
                os.unlink(temp_path)
            except OSError:
                pass  # Ignore errors during cleanup
            raise e

    def load_strategic(self) -> StrategicFile:
        """
        Load strategic items from strategic.json.

        Returns:
            StrategicFile: The loaded strategic file data, or empty if file doesn't exist.
        """
        file_path = self._get_file_path("strategic.json")
        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                return StrategicFile.model_validate(data)
            except (json.JSONDecodeError, Exception) as e:
                raise Exception(f"Error loading strategic data from {file_path}: {e}")
        return StrategicFile()

    def save_strategic(self, data: StrategicFile) -> None:
        """
        Save strategic items to strategic.json.

        Args:
            data: StrategicFile data to save.
        """
        file_path = self._get_file_path("strategic.json")
        self._atomic_write(file_path, data.model_dump())

    def load_execution(self) -> ExecutionFile:
        """
        Load execution items from execution.json.

        Returns:
            ExecutionFile: The loaded execution file data, or empty if file doesn't exist.
        """
        file_path = self._get_file_path("execution.json")
        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                return ExecutionFile.model_validate(data)
            except (json.JSONDecodeError, Exception) as e:
                raise Exception(f"Error loading execution data from {file_path}: {e}")
        return ExecutionFile()

    def save_execution(self, data: ExecutionFile) -> None:
        """
        Save execution items to execution.json.

        Args:
            data: ExecutionFile data to save.
        """
        file_path = self._get_file_path("execution.json")
        self._atomic_write(file_path, data.model_dump())

    def load_config(self) -> ConfigFile:
        """
        Load configuration from config.json.

        Returns:
            ConfigFile: The loaded config data, or default config if file doesn't exist.
        """
        file_path = self._get_file_path("config.json")
        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                return ConfigFile.model_validate(data)
            except (json.JSONDecodeError, Exception) as e:
                raise Exception(f"Error loading config from {file_path}: {e}")
        return ConfigFile()

    def save_config(self, data: ConfigFile) -> None:
        """
        Save configuration to config.json.

        Args:
            data: ConfigFile data to save.
        """
        file_path = self._get_file_path("config.json")
        self._atomic_write(file_path, data.model_dump())

    def load_orphans(self) -> OrphansFile:
        """
        Load orphan ideas from orphans.json.

        Returns:
            OrphansFile: The loaded orphans file data, or empty if file doesn't exist.
        """
        file_path = self._get_file_path("orphans.json")
        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                return OrphansFile.model_validate(data)
            except (json.JSONDecodeError, Exception) as e:
                raise Exception(f"Error loading orphans data from {file_path}: {e}")
        return OrphansFile()

    def save_orphans(self, data: OrphansFile) -> None:
        """
        Save orphan ideas to orphans.json.

        Args:
            data: OrphansFile data to save.
        """
        file_path = self._get_file_path("orphans.json")
        self._atomic_write(file_path, data.model_dump())
