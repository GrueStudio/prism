"""
OrphanManager for the Prism CLI.

Manages orphan lifecycle with read/write operations using StorageManager.
"""

from typing import List, Optional

from prism.managers.storage_manager import StorageManager
from prism.models.files import OrphansFile
from prism.models.orphan import Orphan


class OrphanManager:
    """
    Manages orphan operations.

    Handles:
    - Reading orphans from storage
    - Writing orphans to storage
    - Finding orphans by UUID or name
    - Adding and removing orphans

    Usage:
        storage = StorageManager()
        orphan_mgr = OrphanManager(storage)

        # Load all orphans
        orphans = orphan_mgr.read()

        # Add new orphan
        orphan = orphan_mgr.add(name="Feature idea", description="A new feature")

        # Find orphan by UUID
        orphan = orphan_mgr.get_by_uuid("uuid-here")

        # Remove orphan
        orphan_mgr.remove(orphan_uuid)
    """

    def __init__(self, storage: StorageManager) -> None:
        """
        Initialize OrphanManager.

        Args:
            storage: StorageManager for loading/saving orphans.json.
        """
        self.storage = storage

    def read(self) -> List[Orphan]:
        """
        Load all orphans from storage.

        Returns:
            List of all Orphan objects.
        """
        orphans_file = self.storage.load_orphans()
        return orphans_file.orphans

    def write(self, orphans: List[Orphan]) -> None:
        """
        Save all orphans to storage.

        Triggers an atomic write of the current orphan list.
        """
        orphans_file = OrphansFile(orphans=orphans)
        self.storage.save_orphans(orphans_file)

    def get_by_uuid(self, uuid: str) -> Optional[Orphan]:
        """
        Find orphan by UUID.

        Args:
            uuid: UUID of the orphan to find.

        Returns:
            Orphan object or None if not found.
        """
        orphans = self.read()
        for orphan in orphans:
            if orphan.uuid == uuid:
                return orphan
        return None

    def get_by_name(self, name: str) -> Optional[Orphan]:
        """
        Find orphan by name (case-insensitive).

        Args:
            name: Name of the orphan to find.

        Returns:
            Orphan object or None if not found.
        """
        name_lower = name.lower()
        orphans = self.read()
        for orphan in orphans:
            if orphan.name.lower() == name_lower:
                return orphan
        return None

    def add(self, name: str, description: str, priority: int = 0) -> Orphan:
        """
        Add a new orphan.

        Args:
            name: Name of the orphan.
            description: Description of the orphan.
            priority: Priority value (default 0).

        Returns:
            The newly created Orphan object.
        """
        orphans = self.read()
        new_orphan = Orphan(name=name, description=description, priority=priority)
        orphans.append(new_orphan)
        self.write(orphans)
        return new_orphan

    def remove(self, uuid: str) -> bool:
        """
        Remove an orphan by UUID.

        Args:
            uuid: UUID of the orphan to remove.

        Returns:
            True if orphan was removed, False if not found.
        """
        orphans = self.read()
        original_count = len(orphans)
        orphans = [o for o in orphans if o.uuid != uuid]

        if len(orphans) < original_count:
            self.write(orphans)
            return True
        return False

    def update(self, uuid: str, **kwargs) -> Optional[Orphan]:
        """
        Update an orphan's fields.

        Args:
            uuid: UUID of the orphan to update.
            **kwargs: Fields to update (name, description, priority).

        Returns:
            Updated Orphan object or None if not found.
        """
        orphans = self.read()
        orphan_to_update = None
        for orphan in orphans:
            if orphan.uuid == uuid:
                orphan_to_update = orphan
                break

        if orphan_to_update:
            for key, value in kwargs.items():
                if hasattr(orphan_to_update, key):
                    setattr(orphan_to_update, key, value)
            self.write(orphans)
            return orphan_to_update
        return None
