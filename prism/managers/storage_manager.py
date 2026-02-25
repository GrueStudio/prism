"""
Storage manager for the Prism CLI.

Handles loading and saving of all JSON files in the .prism/ directory.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import ValidationError

from prism.exceptions import StorageError
from prism.models.files import (
    ArchivedStrategicFile,
    ConfigFile,
    CursorFile,
    ExecutionFile,
    OrphansFile,
    StrategicFile,
)


class StorageManager:
    """
    Manages persistence of project data to JSON files in the .prism/ directory.

    Handles atomic writes to prevent data corruption.
    """

    def __init__(self, prism_dir: Optional[Path] = None) -> None:
        """
        Initialize the StorageManager with a .prism/ directory path.

        Args:
            prism_dir: Path to the .prism/ directory. Defaults to .prism/ in current directory.
        """
        self.prism_dir = prism_dir if prism_dir else Path(".prism")
        self.archive_dir = self.prism_dir / "archive"
        self._ensure_prism_dir()

    def _ensure_prism_dir(self) -> None:
        """Create the .prism/ directory and archive subdirectory if they don't exist."""
        self.prism_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(exist_ok=True)

    def _atomic_write(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Write data to a JSON file atomically to prevent corruption.

        Args:
            file_path: Path to the file to write.
            data: Dictionary data to write as JSON.

        Raises:
            StorageError: If writing to file fails.
        """
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self.prism_dir, prefix=".tmp_prism_", suffix=".json"
        )

        try:
            with os.fdopen(temp_fd, "w") as temp_file:
                json.dump(data, temp_file, indent=2)
            os.replace(temp_path, file_path)
        except Exception as e:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise StorageError(f"Failed to write to {file_path}: {e}")

    # =========================================================================
    # Strategic File (active)
    # =========================================================================

    def load_strategic(self) -> StrategicFile:
        """Load strategic.json and return as StrategicFile model."""
        file_path = self.prism_dir / "strategic.json"
        if not file_path.exists():
            return StrategicFile()

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            return StrategicFile.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise StorageError(f"Failed to load strategic.json: {e}")

    def save_strategic(self, data: StrategicFile) -> None:
        """Save StrategicFile model to strategic.json."""
        file_path = self.prism_dir / "strategic.json"
        self._atomic_write(file_path, data.model_dump(mode="json"))

    # =========================================================================
    # Execution File (active)
    # =========================================================================

    def load_execution(self) -> ExecutionFile:
        """Load execution.json and return as ExecutionFile model."""
        file_path = self.prism_dir / "execution.json"
        if not file_path.exists():
            return ExecutionFile()

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            return ExecutionFile.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise StorageError(f"Failed to load execution.json: {e}")

    def save_execution(self, data: ExecutionFile) -> None:
        """Save ExecutionFile model to execution.json."""
        file_path = self.prism_dir / "execution.json"
        self._atomic_write(file_path, data.model_dump(mode="json"))

    # =========================================================================
    # Config File
    # =========================================================================

    def load_config(self) -> ConfigFile:
        """Load config.json and return as ConfigFile model."""
        file_path = self.prism_dir / "config.json"
        if not file_path.exists():
            return ConfigFile()

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            return ConfigFile.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise StorageError(f"Failed to load config.json: {e}")

    def save_config(self, data: ConfigFile) -> None:
        """Save ConfigFile model to config.json."""
        file_path = self.prism_dir / "config.json"
        self._atomic_write(file_path, data.model_dump(mode="json"))

    # =========================================================================
    # Orphans File
    # =========================================================================

    def load_orphans(self) -> OrphansFile:
        """Load orphans.json and return as OrphansFile model."""
        file_path = self.prism_dir / "orphans.json"
        if not file_path.exists():
            return OrphansFile()

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            return OrphansFile.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise StorageError(f"Failed to load orphans.json: {e}")

    def save_orphans(self, data: OrphansFile) -> None:
        """Save OrphansFile model to orphans.json."""
        file_path = self.prism_dir / "orphans.json"
        self._atomic_write(file_path, data.model_dump(mode="json"))

    # =========================================================================
    # Archived Strategic File
    # =========================================================================

    def load_archived_strategic(self) -> ArchivedStrategicFile:
        """Load archive/strategic.json and return as ArchivedStrategicFile model."""
        file_path = self.archive_dir / "strategic.json"
        if not file_path.exists():
            return ArchivedStrategicFile()

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            return ArchivedStrategicFile.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise StorageError(f"Failed to load archived strategic.json: {e}")

    def save_archived_strategic(self, data: ArchivedStrategicFile) -> None:
        """Save ArchivedStrategicFile model to archive/strategic.json."""
        file_path = self.archive_dir / "strategic.json"
        self._atomic_write(file_path, data.model_dump(mode="json"))

    # =========================================================================
    # Archived Execution Tree (per-objective)
    # =========================================================================

    def load_archived_execution_tree(
        self, objective_uuid: str
    ) -> Optional[ExecutionFile]:
        """Load archived execution tree for a specific objective UUID.

        Args:
            objective_uuid: UUID of the archived objective.

        Returns:
            ExecutionFile model or None if not found.
        """
        file_path = self.archive_dir / f"{objective_uuid}.exec.json"
        if not file_path.exists():
            return None

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            return ExecutionFile.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise StorageError(f"Failed to load archived execution tree: {e}")

    def save_archived_execution_tree(
        self, objective_uuid: str, data: ExecutionFile
    ) -> None:
        """Save archived execution tree for a specific objective UUID.

        Args:
            objective_uuid: UUID of the archived objective.
            data: ExecutionFile model to save.
        """
        file_path = self.archive_dir / f"{objective_uuid}.exec.json"
        self._atomic_write(file_path, data.model_dump(mode="json"))

    # =========================================================================
    # Cursor File
    # =========================================================================

    def load_cursor(self) -> CursorFile:
        """Load cursor.json and return as CursorFile model."""
        file_path = self.prism_dir / "cursor.json"
        if not file_path.exists():
            return CursorFile()

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            return CursorFile.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise StorageError(f"Failed to load cursor.json: {e}")

    def save_cursor(self, data: CursorFile) -> None:
        """Save CursorFile model to cursor.json."""
        file_path = self.prism_dir / "cursor.json"
        self._atomic_write(file_path, data.model_dump(mode="json"))
