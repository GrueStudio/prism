"""
ArchivedItem - Read-only lazy-loading wrapper for archived Prism items.

Provides transparent access to archived items without loading them into memory
until accessed. Uses signals to request data loading from ArchiveManager.

Load States:
    NOT_LOADED: No data loaded from archive.
    LOADED: Full item data loaded from archive.
    CHILDREN_LOADED: Item data and children loaded from archive.

Signals:
    request_load: Emitted when item data is accessed but not loaded.
    request_load_children: Emitted when children are accessed but not loaded.
"""

from enum import Enum, auto
from typing import Any, List, Optional

from prism.models.base import BaseItem
from prism.signals import signal


class LoadState(Enum):
    """Load state for ArchivedItem."""

    NOT_LOADED = auto()
    LOADED = auto()
    CHILDREN_LOADED = auto()


class ArchivedItem:
    """
    Lazy-loading read-only wrapper for archived items.

    Stores minimal state. All data is loaded on-demand via signals
    when properties are accessed.

    Attributes:
        _wrapped_item: The loaded BaseItem instance (None until loaded).
        _load_state: Current load state.
        _load_context: Optional context dict for loading (set by creator).

    Signals:
        request_load: Emitted when item data access requires loading.
        request_load_children: Emitted when children access requires loading.
    """

    def __init__(self, uuid: str, **kwargs):
        """
        Initialize archived item wrapper.

        Accepts optional keyword arguments for load context.
        The signal handler uses this context to determine what to load.

        Args:
            **kwargs: Optional context for loading (e.g., uuid, path, index)
        """
        self._uuid = uuid
        self._wrapped_item: Optional[BaseItem] = None
        self._load_state = LoadState.NOT_LOADED
        self._load_context: dict = kwargs

    # =========================================================================
    # Signal Declarations
    # =========================================================================

    @signal
    def request_load(self) -> None:
        """
        Emitted when item data access requires loading from archive.

        Connected handlers should load the full item data and set
        _wrapped_item and _load_state appropriately.
        """
        pass

    @signal
    def request_load_children(self) -> None:
        """
        Emitted when children access requires loading from archive.

        Connected handlers should load children and attach them to
        _wrapped_item._children, then update _load_state.
        """
        pass

    # =========================================================================
    # Load State Management
    # =========================================================================

    def _ensure_loaded(self) -> None:
        """Ensure item data is loaded, emitting request_load if needed."""
        if self._load_state == LoadState.NOT_LOADED:
            self.request_load()

    def _ensure_children_loaded(self) -> None:
        """Ensure children are loaded, emitting request_load_children if needed."""
        self._ensure_loaded()
        if self._load_state != LoadState.CHILDREN_LOADED:
            self.request_load_children()

    def mark_loaded(self, wrapped_item: BaseItem) -> None:
        """
        Mark item as loaded with the provided wrapped item.

        Called by signal handlers after loading item data.

        Args:
            wrapped_item: The loaded BaseItem instance.
        """
        if self._uuid != wrapped_item.uuid:
            raise ValueError("UUID mismatch")
        self._wrapped_item = wrapped_item
        self._load_state = LoadState.LOADED

    def mark_children_loaded(self) -> None:
        """
        Mark children as loaded.

        Called by signal handlers after loading children.
        Assumes _wrapped_item is already set with children populated.
        """
        self._load_state = LoadState.CHILDREN_LOADED

    # =========================================================================
    # Properties (all trigger load on first access)
    # =========================================================================

    @property
    def uuid(self) -> str:
        """Item UUID (loaded on first access)."""
        return self._uuid

    @property
    def name(self) -> str:
        """Item name (loaded on first access)."""
        self._ensure_loaded()
        if self._wrapped_item is None:
            raise ValueError(f"ArchivedItem {id(self)} not loaded")
        return self._wrapped_item.name

    @property
    def slug(self) -> str:
        """Item slug (loaded on first access)."""
        self._ensure_loaded()
        if self._wrapped_item is None:
            raise ValueError(f"ArchivedItem {id(self)} not loaded")
        return self._wrapped_item.slug

    @property
    def item_type(self) -> str:
        """Item type (loaded on first access)."""
        self._ensure_loaded()
        if self._wrapped_item is None:
            raise ValueError(f"ArchivedItem {id(self)} not loaded")
        return self._wrapped_item.item_type

    @property
    def status(self) -> str:
        """Item status (loaded on first access)."""
        self._ensure_loaded()
        if self._wrapped_item is None:
            raise ValueError(f"ArchivedItem {id(self)} not loaded")
        return self._wrapped_item.status

    @property
    def parent_uuid(self) -> Optional[str]:
        """Parent item UUID (loaded on first access)."""
        self._ensure_loaded()
        if self._wrapped_item is None:
            raise ValueError(f"ArchivedItem {id(self)} not loaded")
        return self._wrapped_item.parent_uuid

    @property
    def description(self) -> Optional[str]:
        """Item description (loaded on first access)."""
        self._ensure_loaded()
        if self._wrapped_item is None:
            raise ValueError(f"ArchivedItem {id(self)} not loaded")
        return self._wrapped_item.description

    @property
    def position(self) -> int:
        """Position among siblings (loaded on first access)."""
        # Position is metadata, not on BaseItem - get from context or wrapped item
        self._ensure_loaded()
        return self._load_context.get("position", 0)

    @property
    def wrapped_item(self) -> Optional[BaseItem]:
        """
        Get the wrapped BaseItem instance.

        Triggers load if not yet loaded.

        Returns:
            The loaded BaseItem, or None if loading failed.
        """
        self._ensure_loaded()
        return self._wrapped_item

    @property
    def children(self) -> List["ArchivedItem"]:
        """
        Get child items.

        Triggers load of item and children if not yet loaded.

        Returns:
            List of ArchivedItem wrappers for children.
        """
        self._ensure_children_loaded()
        if self._wrapped_item:
            return [
                ArchivedItem.from_wrapped_item(child)
                for child in self._wrapped_item.children
            ]
        return []

    @property
    def child_uuids(self) -> List[str]:
        """
        Get child UUIDs.

        Triggers load if not yet loaded.

        Returns:
            List of child UUIDs.
        """
        self._ensure_loaded()
        if self._wrapped_item:
            return self._wrapped_item.child_uuids
        return []

    @property
    def created_at(self) -> Optional[Any]:
        """
        Get created_at timestamp from wrapped item.

        Triggers load if not yet loaded.

        Returns:
            Created timestamp or None.
        """
        self._ensure_loaded()
        if self._wrapped_item:
            return self._wrapped_item.created_at
        return None

    @property
    def updated_at(self) -> Optional[Any]:
        """
        Get updated_at timestamp from wrapped item.

        Triggers load if not yet loaded.

        Returns:
            Updated timestamp or None.
        """
        self._ensure_loaded()
        if self._wrapped_item:
            return self._wrapped_item.updated_at
        return None

    @property
    def time_spent(self) -> Optional[Any]:
        """
        Get time_spent from wrapped item.

        Triggers load if not yet loaded.

        Returns:
            Time spent or None.
        """
        self._ensure_loaded()
        if self._wrapped_item:
            return self._wrapped_item.time_spent
        return None

    def add_child(self, child):
        if not self._load_state == LoadState.LOADED or not self._wrapped_item:
            raise ValueError("Tried to add child to unloaded item")

        self._wrapped_item.add_child(child)

        if (
            self._load_state != LoadState.CHILDREN_LOADED
            and None not in self._wrapped_item.children
        ):
            self.mark_children_loaded()

    # =========================================================================
    # Factory Methods
    # =========================================================================

    @classmethod
    def from_wrapped_item(cls, item: BaseItem) -> "ArchivedItem":
        """
        Create an ArchivedItem wrapper from a loaded BaseItem.

        Used to wrap children when they are loaded.

        Args:
            item: The loaded BaseItem to wrap.

        Returns:
            ArchivedItem wrapper with item pre-loaded.
        """
        wrapper = cls(uuid=item.uuid)
        wrapper._wrapped_item = item

        if None not in item.children:
            wrapper._load_state = LoadState.CHILDREN_LOADED
        else:
            wrapper._load_state = LoadState.LOADED

        return wrapper

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_deliverables(self) -> List["ArchivedItem"]:
        """
        Get deliverable children (for objective type).

        Returns:
            List of deliverable ArchivedItem wrappers.
        """
        if self.item_type != "objective":
            return []
        return [c for c in self.children if c.item_type == "deliverable"]

    def get_actions(self) -> List["ArchivedItem"]:
        """
        Get action children (for deliverable type).

        Returns:
            List of action ArchivedItem wrappers.
        """
        if self.item_type != "deliverable":
            return []
        return [c for c in self.children if c.item_type == "action"]

    def __repr__(self) -> str:
        uuid_str = self.uuid if self._load_state != LoadState.NOT_LOADED else "unloaded"
        return f"ArchivedItem(uuid={uuid_str!r}, state={self._load_state.name})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, ArchivedItem):
            # Compare by UUID if both loaded, otherwise by identity
            if (
                self._load_state != LoadState.NOT_LOADED
                and other._load_state != LoadState.NOT_LOADED
            ):
                return self.uuid == other.uuid
            return id(self) == id(other)
        return False

    def __hash__(self) -> int:
        # Use object identity for unloaded items, UUID for loaded
        if self._load_state != LoadState.NOT_LOADED and self.uuid:
            return hash(self.uuid)
        return hash(id(self))
