"""
ArchivedItem - Read-only lazy-loading wrapper for archived Prism items.

Provides transparent access to archived items without loading them into memory
until accessed. Archived items cannot be modified.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
from prism.managers.storage_manager import StorageManager


class ArchivedItem:
    """
    Lazy-loading read-only wrapper for archived items.
    
    Stores minimal metadata (uuid, name, slug, type, status, parent_uuid)
    and loads full data from archive only when accessed.
    
    All write operations raise ArchivedItemError.
    """
    
    def __init__(
        self,
        uuid: str,
        name: str,
        slug: str,
        item_type: str,  # 'phase', 'milestone', 'objective', 'deliverable', 'action'
        status: str = 'archived',
        parent_uuid: Optional[str] = None,
        description: Optional[str] = None,
        storage: Optional[StorageManager] = None,
    ):
        """
        Initialize archived item wrapper.
        
        Args:
            uuid: Item UUID
            name: Item name
            slug: Item slug
            item_type: Type of item (phase, milestone, objective, deliverable, action)
            status: Item status (default: 'archived')
            parent_uuid: Parent item UUID
            description: Optional description
            storage: StorageManager for lazy loading (optional, can be set later)
        """
        self._uuid = uuid
        self._name = name
        self._slug = slug
        self._item_type = item_type
        self._status = status
        self._parent_uuid = parent_uuid
        self._description = description
        self._storage = storage
        self._loaded_data: Optional[Dict[str, Any]] = None
        self._children: Optional[List['ArchivedItem']] = None
    
    @property
    def uuid(self) -> str:
        return self._uuid
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def slug(self) -> str:
        return self._slug
    
    @property
    def item_type(self) -> str:
        return self._item_type
    
    @property
    def status(self) -> str:
        return self._status
    
    @property
    def parent_uuid(self) -> Optional[str]:
        return self._parent_uuid
    
    @property
    def description(self) -> Optional[str]:
        return self._description
    
    @property
    def created_at(self) -> Optional[datetime]:
        self._ensure_loaded()
        if self._loaded_data and 'created_at' in self._loaded_data:
            return datetime.fromisoformat(self._loaded_data['created_at'])
        return None
    
    @property
    def updated_at(self) -> Optional[datetime]:
        self._ensure_loaded()
        if self._loaded_data and 'updated_at' in self._loaded_data:
            return datetime.fromisoformat(self._loaded_data['updated_at'])
        return None
    
    @property
    def children(self) -> List['ArchivedItem']:
        """Get child items (milestones for phase, objectives for milestone, etc.)."""
        if self._children is None:
            self._load_children()
        return self._children
    
    def _ensure_loaded(self) -> None:
        """Load full data from archive if not already loaded."""
        if self._loaded_data is None and self._storage:
            if self._item_type in ['phase', 'milestone', 'objective']:
                self._loaded_data = self._storage.load_archived_strategic(self._uuid)
            # For deliverables/actions, they're loaded via parent objective
    
    def _load_children(self) -> None:
        """Load child items from archive."""
        self._children = []
        
        if self._item_type == 'phase' and self._storage:
            # Load archived milestones for this phase
            archived = self._storage.load_all_archived_strategic()
            for milestone_data in archived['milestones']:
                if milestone_data.get('parent_uuid') == self._uuid:
                    self._children.append(ArchivedItem(
                        uuid=milestone_data['uuid'],
                        name=milestone_data['name'],
                        slug=milestone_data['slug'],
                        item_type='milestone',
                        status=milestone_data.get('status', 'archived'),
                        parent_uuid=self._uuid,
                        description=milestone_data.get('description'),
                        storage=self._storage,
                    ))
        
        elif self._item_type == 'milestone' and self._storage:
            # Load archived objectives for this milestone
            archived = self._storage.load_all_archived_strategic()
            for objective_data in archived['objectives']:
                if objective_data.get('parent_uuid') == self._uuid:
                    self._children.append(ArchivedItem(
                        uuid=objective_data['uuid'],
                        name=objective_data['name'],
                        slug=objective_data['slug'],
                        item_type='objective',
                        status=objective_data.get('status', 'archived'),
                        parent_uuid=self._uuid,
                        description=objective_data.get('description'),
                        storage=self._storage,
                    ))
        
        elif self._item_type == 'objective' and self._storage:
            # Load archived execution tree for this objective
            try:
                exec_tree = self._storage.load_archived_execution_tree(self._uuid)
                if exec_tree:
                    for deliv_data in exec_tree.get('deliverables', []):
                        self._children.append(ArchivedItem(
                            uuid=deliv_data['uuid'],
                            name=deliv_data['name'],
                            slug=deliv_data['slug'],
                            item_type='deliverable',
                            status=deliv_data.get('status', 'archived'),
                            parent_uuid=self._uuid,
                            description=deliv_data.get('description'),
                            storage=self._storage,
                        ))
            except Exception:
                pass
    
    def get_deliverables(self) -> List['ArchivedItem']:
        """Get deliverables (for objective type)."""
        if self._item_type != 'objective':
            return []
        return [c for c in self.children if c.item_type == 'deliverable']
    
    def get_actions(self) -> List['ArchivedItem']:
        """Get actions (for deliverable type)."""
        if self._item_type != 'deliverable':
            return []
        # Load actions from archived execution tree
        actions = []
        if self._storage and self._parent_uuid:
            try:
                exec_tree = self._storage.load_archived_execution_tree(self._parent_uuid)
                if exec_tree:
                    for action_data in exec_tree.get('actions', []):
                        if action_data.get('parent_uuid') == self._uuid:
                            actions.append(ArchivedItem(
                                uuid=action_data['uuid'],
                                name=action_data['name'],
                                slug=action_data['slug'],
                                item_type='action',
                                status=action_data.get('status', 'archived'),
                                parent_uuid=self._uuid,
                                description=action_data.get('description'),
                                storage=self._storage,
                            ))
            except Exception:
                pass
        return actions
    
    # Write operations always fail for archived items
    def __setattr__(self, name: str, value: Any) -> None:
        # Allow setting private attributes during initialization
        if name.startswith('_') or name in ['uuid', 'name', 'slug', 'item_type', 'status', 'parent_uuid', 'description', 'created_at', 'updated_at']:
            if name.startswith('_'):
                super().__setattr__(name, value)
            else:
                raise ArchivedItemError(f"Cannot modify archived item property '{name}'")
        else:
            raise ArchivedItemError(f"Cannot modify archived item property '{name}'")
    
    def __repr__(self) -> str:
        return f"ArchivedItem({self._item_type}, '{self._name}', uuid='{self._uuid}')"
    
    def __eq__(self, other: Any) -> bool:
        if isinstance(other, ArchivedItem):
            return self._uuid == other._uuid
        return False
    
    def __hash__(self) -> int:
        return hash(self._uuid)


class ArchivedItemError(Exception):
    """Raised when attempting to modify an archived item."""
    pass
