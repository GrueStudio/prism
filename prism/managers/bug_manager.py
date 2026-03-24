"""
Bug manager for the Prism CLI.

Handles CRUD operations for bug items, including ID generation and 
log file management.
"""

from datetime import datetime
from typing import List, Optional

from prism.models.bug import BugItem, BugStatus
from prism.models.config import BugType
from prism.managers.storage_manager import StorageManager
from prism.managers.config_manager import ConfigManager


class BugManager:
    """
    Manages bug tracking items and their associated logs.
    """

    def __init__(
        self, 
        storage_manager: Optional[StorageManager] = None,
        config_manager: Optional[ConfigManager] = None
    ) -> None:
        """
        Initialize the BugManager.

        Args:
            storage_manager: Storage manager for persistence.
            config_manager: Config manager for bug types.
        """
        self.storage = storage_manager or StorageManager()
        self.config = config_manager or ConfigManager(storage=self.storage)

    def _load_bugs(self) -> List[BugItem]:
        """Load all bugs from storage."""
        return self.storage.load_bugs().bugs

    def _save_bugs(self, bugs: List[BugItem]) -> None:
        """Save all bugs to storage."""
        from prism.models.files import BugsFile
        self.storage.save_bugs(BugsFile(bugs=bugs))

    def list_bugs(self) -> List[BugItem]:
        """List all tracked bugs."""
        return self._load_bugs()

    def get_bug(self, bug_id: str) -> Optional[BugItem]:
        """
        Get a bug by its human-readable ID.

        Args:
            bug_id: The bug ID (e.g., PHYS100326_01)
        """
        bugs = self._load_bugs()
        for bug in bugs:
            if bug.bug_id == bug_id:
                return bug
        return None

    def add_bug(self, bug_type_name: str, description: str) -> BugItem:
        """
        Create and add a new bug.

        Args:
            bug_type_name: Name of the bug type (must exist in config).
            description: Description of the bug.

        Returns:
            The created BugItem.

        Raises:
            ValueError: If bug type is invalid.
        """
        # Get bug type from config
        bug_type = self.config.get_bug_type(bug_type_name)
        if not bug_type:
            raise ValueError(f"Invalid bug type: '{bug_type_name}'")

        # Generate bug ID
        bug_id, counter = self.generate_bug_id(bug_type)

        # Create bug item
        bug = BugItem(
            bug_type=bug_type,
            bug_id=bug_id,
            description=description,
            counter=counter,
            status=BugStatus.OPEN
        )

        # Save bug
        bugs = self._load_bugs()
        bugs.append(bug)
        self._save_bugs(bugs)

        return bug

    def update_bug(self, bug_id: str, **kwargs) -> BugItem:
        """
        Update bug fields.

        Args:
            bug_id: The ID of the bug to update.
            **kwargs: Fields to update (description, status, steps_to_reproduce, etc.)

        Returns:
            The updated BugItem.

        Raises:
            ValueError: If bug not found or invalid field.
        """
        bugs = self._load_bugs()
        for i, bug in enumerate(bugs):
            if bug.bug_id == bug_id:
                # Handle status transition separately to use validation
                if "status" in kwargs:
                    bug.set_status(kwargs.pop("status"))
                
                # Update other fields
                for key, value in kwargs.items():
                    if hasattr(bug, key):
                        setattr(bug, key, value)
                    else:
                        raise ValueError(f"Invalid field: '{key}'")
                
                bug.updated_at = datetime.now()
                bugs[i] = bug
                self._save_bugs(bugs)
                return bug
        
        raise ValueError(f"Bug not found: '{bug_id}'")

    def delete_bug(self, bug_id: str) -> bool:
        """
        Delete a bug and its logs.

        Args:
            bug_id: The ID of the bug to delete.

        Returns:
            True if deleted, False if not found.
        """
        bugs = self._load_bugs()
        for i, bug in enumerate(bugs):
            if bug.bug_id == bug_id:
                # Delete logs first (optional, but good practice)
                # TODO: Clean up log files from disk
                
                bugs.pop(i)
                self._save_bugs(bugs)
                return True
        return False

    def generate_bug_id(self, bug_type: BugType) -> tuple[str, int]:
        """
        Generate a unique bug ID for a given bug type.
        Format: {PREFIX}{DDMMYY}_{COUNTER}

        Args:
            bug_type: The BugType model.

        Returns:
            A tuple of (bug_id, counter).
        """
        prefix = bug_type.prefix
        date_str = datetime.now().strftime("%d%m%y")
        
        bugs = self._load_bugs()
        
        # Find the highest counter for this prefix and date
        max_counter = 0
        pattern = f"{prefix}{date_str}_"
        
        for bug in bugs:
            if bug.bug_id.startswith(pattern):
                try:
                    counter = int(bug.bug_id.split("_")[-1])
                    if counter > max_counter:
                        max_counter = counter
                except (ValueError, IndexError):
                    continue
        
        new_counter = max_counter + 1
        bug_id = f"{prefix}{date_str}_{new_counter:02d}"
        
        return bug_id, new_counter
