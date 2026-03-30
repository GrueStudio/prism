"""
Bug manager for the Prism CLI.

Handles CRUD operations for bug items, including ID generation and 
log file management.
"""

from datetime import datetime, timezone
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

    def list_bugs(
        self,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "id",
        order: str = "asc",
    ) -> List[BugItem]:
        """
        List bugs with filtering and sorting.

        Args:
            status_filter: Status shorthand filter (+/- o, r, f, x, i).
            search: Search string (matches ID, description, or root cause).
            sort_by: Field to sort by (id, status, created_at, updated_at).
            order: Sort order (asc, desc).

        Returns:
            List of matching bugs.
        """
        bugs = self._load_bugs()

        # 1. Filter by status
        if status_filter:
            bugs = self._filter_by_status(bugs, status_filter)

        # 2. Filter by search string
        if search:
            search_lower = search.lower()
            bugs = [
                bug for bug in bugs
                if search_lower in bug.bug_id.lower() or
                   search_lower in bug.description.lower() or
                   (bug.root_cause and search_lower in bug.root_cause.lower())
            ]

        # 3. Sort results
        reverse = (order.lower() == "desc")
        
        def _get_sort_key(bug: BugItem):
            if sort_by == "id":
                return bug.bug_id.lower()
            elif sort_by == "status":
                return bug.status.value.lower()
            elif sort_by == "created_at":
                return bug.created_at
            elif sort_by == "updated_at":
                return bug.updated_at
            return bug.bug_id.lower()

        bugs.sort(key=_get_sort_key, reverse=reverse)

        return bugs

    def _filter_by_status(self, bugs: List[BugItem], status_filter: str) -> List[BugItem]:
        """Apply shorthand status filter (+/- shorthand)."""
        shorthand_map = {
            "o": BugStatus.OPEN,
            "r": BugStatus.REPRODUCED,
            "f": BugStatus.FOUND,
            "x": BugStatus.FIXED,
            "i": BugStatus.IMPLEMENTED,
        }

        if not status_filter:
            return bugs

        # Determine mode (+ adds to empty, - removes from all)
        mode = status_filter[0] if status_filter[0] in ("+", "-") else "+"
        chars = status_filter[1:] if status_filter[0] in ("+", "-") else status_filter

        # Map chars to BugStatus values
        target_statuses = set()
        for char in chars.lower():
            if char in shorthand_map:
                target_statuses.add(shorthand_map[char])

        if mode == "+":
            # Include only these statuses
            return [bug for bug in bugs if bug.status in target_statuses]
        else:
            # Exclude these statuses (start with all)
            return [bug for bug in bugs if bug.status not in target_statuses]

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

    def progress_bug_status(self, bug_id: str, description: str) -> BugItem:
        """
        Progress a bug to its next status in the lifecycle and update the relevant description field.

        Args:
            bug_id: The ID of the bug to update.
            description: The description for the update, which is assigned to the correct field
                         (e.g., steps_to_reproduce, root_cause) based on the transition.

        Returns:
            The updated BugItem.

        Raises:
            ValueError: If bug not found, is in a terminal state, or has no next state.
        """
        from prism.models.bug import VALID_STATUS_TRANSITIONS
        bug = self.get_bug(bug_id)
        if not bug:
            raise ValueError(f"Bug not found: '{bug_id}'")

        # Determine the next status
        allowed_transitions = VALID_STATUS_TRANSITIONS.get(bug.status, set())
        if not allowed_transitions:
            raise ValueError(f"Bug '{bug_id}' is in a terminal state '{bug.status.value}' and cannot be updated.")

        next_status = list(allowed_transitions)[0]

        # Determine which field to update based on the current status
        update_payload = {"status": next_status}
        if bug.status == BugStatus.OPEN:
            update_payload["steps_to_reproduce"] = description
        elif bug.status == BugStatus.REPRODUCED:
            update_payload["root_cause"] = description
        elif bug.status == BugStatus.FOUND:
            update_payload["fix_description"] = description
        # No description needed for fixed -> implemented, but we still want to progress the status.

        return self.update_bug(bug_id, **update_payload)

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
                
                bug.updated_at = datetime.now(timezone.utc)
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
        date_str = datetime.now(timezone.utc).strftime("%d%m%y")
        
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
