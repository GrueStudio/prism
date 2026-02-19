"""
Storage manager for the Prism CLI.

Handles loading and saving of all JSON files in the .prism/ directory.
"""
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from prism.exceptions import PrismError
from prism.models import StrategicFile, ExecutionFile, OrphansFile, ConfigFile


# File name constants
STRATEGIC_FILE = "strategic.json"
EXECUTION_FILE = "execution.json"
CONFIG_FILE = "config.json"
ORPHANS_FILE = "orphans.json"
ARCHIVE_STRATEGIC_FILE = "strategic.json"
ARCHIVE_EXECUTION_PREFIX = ""
ARCHIVE_EXECUTION_SUFFIX = ".exec.json"


class StorageError(PrismError):
    """Exception raised for storage-related errors."""
    pass


class StorageManager:
    """
    Manages persistence of project data to JSON files in the .prism/ directory.

    Handles atomic writes to prevent data corruption.
    Supports archiving of completed items to .prism/archive/ subdirectory.

    Files managed:
        - strategic.json: Phases, milestones, objectives
        - execution.json: Deliverables and actions
        - config.json: Project configuration
        - orphans.json: Orphan ideas
        - archive/: Archived completed items
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

    def _get_file_path(self, filename: str) -> Path:
        """Get the full path for a file in the .prism/ directory.

        Args:
            filename: Name of the file.

        Returns:
            Full path to the file.
        """
        return self.prism_dir / filename

    def _get_archive_file_path(self, filename: str) -> Path:
        """Get the full path for a file in the .prism/archive/ directory.

        Args:
            filename: Name of the file.

        Returns:
            Full path to the archive file.
        """
        return self.archive_dir / filename

    def _atomic_write(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Write data to a JSON file atomically to prevent corruption.

        Args:
            file_path: Path to the file to write.
            data: Dictionary data to write as JSON.

        Raises:
            StorageError: If writing to file fails.
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
            raise StorageError(f"Failed to write to {file_path}: {e}")

    def load_strategic(self) -> StrategicFile:
        """
        Load strategic items from strategic.json.

        Returns:
            StrategicFile: The loaded strategic file data, or empty if file doesn't exist.

        Raises:
            StorageError: If loading from file fails.
        """
        file_path = self._get_file_path(STRATEGIC_FILE)
        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                return StrategicFile.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as e:
                raise StorageError(f"Failed to load strategic data from {file_path}: {e}")
        return StrategicFile()

    def save_strategic(self, data: StrategicFile) -> None:
        """
        Save strategic items to strategic.json.

        Args:
            data: StrategicFile data to save.
        """
        file_path = self._get_file_path(STRATEGIC_FILE)
        self._atomic_write(file_path, data.model_dump())

    def load_execution(self) -> ExecutionFile:
        """
        Load execution items from execution.json.

        Returns:
            ExecutionFile: The loaded execution file data, or empty if file doesn't exist.

        Raises:
            StorageError: If loading from file fails.
        """
        file_path = self._get_file_path(EXECUTION_FILE)
        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                return ExecutionFile.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as e:
                raise StorageError(f"Failed to load execution data from {file_path}: {e}")
        return ExecutionFile()

    def save_execution(self, data: ExecutionFile) -> None:
        """
        Save execution items to execution.json.

        Args:
            data: ExecutionFile data to save.
        """
        file_path = self._get_file_path(EXECUTION_FILE)
        self._atomic_write(file_path, data.model_dump())

    def load_config(self) -> ConfigFile:
        """
        Load configuration from config.json.

        Returns:
            ConfigFile: The loaded config data, or default config if file doesn't exist.

        Raises:
            StorageError: If loading from file fails.
        """
        file_path = self._get_file_path(CONFIG_FILE)
        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                return ConfigFile.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as e:
                raise StorageError(f"Failed to load config from {file_path}: {e}")
        return ConfigFile()

    def save_config(self, data: ConfigFile) -> None:
        """
        Save configuration to config.json.

        Args:
            data: ConfigFile data to save.
        """
        file_path = self._get_file_path(CONFIG_FILE)
        self._atomic_write(file_path, data.model_dump())

    def load_orphans(self) -> OrphansFile:
        """
        Load orphan ideas from orphans.json.

        Returns:
            OrphansFile: The loaded orphans file data, or empty if file doesn't exist.

        Raises:
            StorageError: If loading from file fails.
        """
        file_path = self._get_file_path(ORPHANS_FILE)
        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                return OrphansFile.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as e:
                raise StorageError(f"Failed to load orphans data from {file_path}: {e}")
        return OrphansFile()

    def save_orphans(self, data: OrphansFile) -> None:
        """
        Save orphan ideas to orphans.json.

        Args:
            data: OrphansFile data to save.
        """
        file_path = self._get_file_path(ORPHANS_FILE)
        self._atomic_write(file_path, data.model_dump())

    def archive_strategic(self, item_data: Dict[str, Any]) -> None:
        """
        Archive a strategic item to archive/strategic.json.

        Appends to the flat list of archived strategic items.

        Args:
            item_data: Dictionary data of the item to archive.
        """
        file_path = self._get_archive_file_path(ARCHIVE_STRATEGIC_FILE)
        
        # Load existing archived items
        archived = []
        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    archived = data.get("items", [])
            except (json.JSONDecodeError, IOError):
                archived = []
        
        # Append new item
        archived.append(item_data)
        
        # Save back
        self._atomic_write(file_path, {"items": archived})

    def archive_execution_tree(self, objective_uuid: str, tree_data: Dict[str, Any]) -> None:
        """
        Archive an execution tree (deliverables and actions) to the archive folder.

        Creates individual file per objective: archive/objective-{uuid}.exec.json

        Args:
            objective_uuid: UUID of the objective being archived.
            tree_data: Dictionary data containing deliverables and actions to archive.
        """
        file_path = self._get_archive_file_path(
            f"{ARCHIVE_EXECUTION_PREFIX}{objective_uuid}{ARCHIVE_EXECUTION_SUFFIX}"
        )
        self._atomic_write(file_path, tree_data)

    def load_archived_strategic(self, item_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Load an archived strategic item by UUID from archive/strategic.json.

        Args:
            item_uuid: UUID of the archived item.

        Returns:
            Dictionary data of the archived item, or None if not found.
        """
        file_path = self._get_archive_file_path(ARCHIVE_STRATEGIC_FILE)
        if not file_path.exists():
            return None

        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            # New structure: phases, milestones, objectives fields
            for item_type in ['phases', 'milestones', 'objectives']:
                items = data.get(item_type, [])
                for item in items:
                    if item.get("uuid") == item_uuid:
                        item['type'] = item_type[:-1]  # 'phases' -> 'phase', etc.
                        return item
            return None
        except (json.JSONDecodeError, IOError):
            return None

    def load_all_archived_strategic(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load all archived strategic items from archive/strategic.json.

        Returns:
            Dictionary with 'phases', 'milestones', 'objectives' lists.
        """
        file_path = self._get_archive_file_path(ARCHIVE_STRATEGIC_FILE)
        if not file_path.exists():
            return {'phases': [], 'milestones': [], 'objectives': []}

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            return {
                'phases': data.get('phases', []),
                'milestones': data.get('milestones', []),
                'objectives': data.get('objectives', []),
            }
        except (json.JSONDecodeError, IOError):
            return {'phases': [], 'milestones': [], 'objectives': []}

    def load_archived_execution_tree(self, objective_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Load an archived execution tree by objective UUID.

        Args:
            objective_uuid: UUID of the archived objective.

        Returns:
            Dictionary data of the archived execution tree, or None if not found.
        """
        file_path = self._get_archive_file_path(
            f"{ARCHIVE_EXECUTION_PREFIX}{objective_uuid}{ARCHIVE_EXECUTION_SUFFIX}"
        )
        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return None
        return None

    def list_archived_strategic(self) -> List[str]:
        """
        List all archived strategic item UUIDs.

        Returns:
            List of UUIDs of archived strategic items.
        """
        file_path = self._get_archive_file_path(ARCHIVE_STRATEGIC_FILE)
        if not file_path.exists():
            return []

        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            # New structure: phases, milestones, objectives fields
            uuids = []
            for item_type in ['phases', 'milestones', 'objectives']:
                items = data.get(item_type, [])
                uuids.extend([item.get("uuid", "") for item in items if item.get("uuid")])
            return uuids
        except (json.JSONDecodeError, IOError):
            return []

    def list_archived_execution_trees(self) -> List[str]:
        """
        List all archived objective UUIDs.

        Returns:
            List of objective UUIDs with archived execution trees.
        """
        archived = []
        pattern = f"{ARCHIVE_EXECUTION_PREFIX}*{ARCHIVE_EXECUTION_SUFFIX}"
        for file_path in self.archive_dir.glob(pattern):
            # Extract UUID from filename: objective-{uuid}.exec.json
            name = file_path.name
            uuid = name.replace(ARCHIVE_EXECUTION_PREFIX, "").replace(
                ARCHIVE_EXECUTION_SUFFIX, ""
            )
            archived.append(uuid)
        return archived
