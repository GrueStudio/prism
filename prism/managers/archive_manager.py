"""
ArchiveManager for Prism CLI.

Handles all archive operations including:
- Archiving completed items
- Lazy-loading archived items via ArchivedItem wrapper
- Managing archived item metadata and order
- Auto-archiving on item completion via EventBus
"""
import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from prism.managers.storage_manager import StorageManager
from prism.managers.events import Event, EventListener, EventType, ItemEvent

if TYPE_CHECKING:
    from prism.managers.project_manager import Project


class ArchivedItemError(Exception):
    """Raised when attempting to modify an archived item."""
    pass


class ArchivedItem:
    """
    Lazy-loading read-only wrapper for archived items.
    
    Stores minimal metadata (uuid, name, slug, type, status, parent_uuid, position)
    and loads full data from archive only when accessed.
    
    All write operations raise ArchivedItemError.
    """
    
    def __init__(
        self,
        uuid: str,
        name: str,
        slug: str,
        item_type: str,
        status: str = 'archived',
        parent_uuid: Optional[str] = None,
        description: Optional[str] = None,
        position: int = 0,  # Position among siblings for ordering
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
            position: Position among siblings (for ordering)
            storage: StorageManager for lazy loading
        """
        self._uuid = uuid
        self._name = name
        self._slug = slug
        self._item_type = item_type
        self._status = status
        self._parent_uuid = parent_uuid
        self._description = description
        self._position = position
        self._storage = storage
        self._loaded_data: Optional[Dict[str, Any]] = None
        self._children: Optional[List['ArchivedItem']] = None
        self._child_uuids: List[str] = []
    
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
    def position(self) -> int:
        return self._position
    
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
        """Get child items in order."""
        if self._children is None:
            self._load_children()
        return self._children
    
    @property
    def child_uuids(self) -> List[str]:
        """Get child UUIDs in order."""
        if not self._child_uuids:
            self._load_children()
        return self._child_uuids
    
    def _ensure_loaded(self) -> None:
        """Load full data from archive if not already loaded."""
        if self._loaded_data is None and self._storage:
            if self._item_type in ['phase', 'milestone', 'objective']:
                self._loaded_data = self._storage.load_archived_strategic(self._uuid)
    
    def _load_children(self) -> None:
        """Load child items from archive in order."""
        self._children = []
        self._child_uuids = []
        
        if self._item_type == 'phase' and self._storage:
            archived = self._storage.load_all_archived_strategic()
            # Get milestones in order
            for milestone_data in archived['milestones']:
                if milestone_data.get('parent_uuid') == self._uuid:
                    pos = milestone_data.get('position', len(self._children))
                    child = ArchivedItem(
                        uuid=milestone_data['uuid'],
                        name=milestone_data['name'],
                        slug=milestone_data['slug'],
                        item_type='milestone',
                        status=milestone_data.get('status', 'archived'),
                        parent_uuid=self._uuid,
                        description=milestone_data.get('description'),
                        position=pos,
                        storage=self._storage,
                    )
                    self._children.append(child)
                    self._child_uuids.append(child.uuid)
            # Sort by position
            self._children.sort(key=lambda c: c.position)
        
        elif self._item_type == 'milestone' and self._storage:
            archived = self._storage.load_all_archived_strategic()
            for objective_data in archived['objectives']:
                if objective_data.get('parent_uuid') == self._uuid:
                    pos = objective_data.get('position', len(self._children))
                    child = ArchivedItem(
                        uuid=objective_data['uuid'],
                        name=objective_data['name'],
                        slug=objective_data['slug'],
                        item_type='objective',
                        status=objective_data.get('status', 'archived'),
                        parent_uuid=self._uuid,
                        description=objective_data.get('description'),
                        position=pos,
                        storage=self._storage,
                    )
                    self._children.append(child)
                    self._child_uuids.append(child.uuid)
            self._children.sort(key=lambda c: c.position)
        
        elif self._item_type == 'objective' and self._storage:
            try:
                exec_tree = self._storage.load_archived_execution_tree(self._uuid)
                if exec_tree:
                    for deliv_data in exec_tree.get('deliverables', []):
                        pos = deliv_data.get('position', len(self._children))
                        child = ArchivedItem(
                            uuid=deliv_data['uuid'],
                            name=deliv_data['name'],
                            slug=deliv_data['slug'],
                            item_type='deliverable',
                            status=deliv_data.get('status', 'archived'),
                            parent_uuid=self._uuid,
                            description=deliv_data.get('description'),
                            position=pos,
                            storage=self._storage,
                        )
                        self._children.append(child)
                        self._child_uuids.append(child.uuid)
                    self._children.sort(key=lambda c: c.position)
            except Exception:
                pass
    
    def get_deliverables(self) -> List['ArchivedItem']:
        """Get deliverables (for objective type) in order."""
        if self._item_type != 'objective':
            return []
        return [c for c in self.children if c.item_type == 'deliverable']
    
    def get_actions(self) -> List['ArchivedItem']:
        """Get actions (for deliverable type) in order."""
        if self._item_type != 'deliverable':
            return []
        actions = []
        if self._storage and self._parent_uuid:
            try:
                exec_tree = self._storage.load_archived_execution_tree(self._parent_uuid)
                if exec_tree:
                    for action_data in exec_tree.get('actions', []):
                        if action_data.get('parent_uuid') == self._uuid:
                            pos = action_data.get('position', len(actions))
                            actions.append((pos, ArchivedItem(
                                uuid=action_data['uuid'],
                                name=action_data['name'],
                                slug=action_data['slug'],
                                item_type='action',
                                status=action_data.get('status', 'archived'),
                                parent_uuid=self._uuid,
                                description=action_data.get('description'),
                                position=pos,
                                storage=self._storage,
                            )))
                    actions.sort(key=lambda x: x[0])
                    return [a[1] for a in actions]
            except Exception:
                pass
        return []
    
    # Write operations always fail for archived items
    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            raise ArchivedItemError(f"Cannot modify archived item property '{name}'")
    
    def __repr__(self) -> str:
        return f"ArchivedItem({self._item_type}, '{self._name}', uuid='{self._uuid}', pos={self._position})"
    
    def __eq__(self, other: Any) -> bool:
        if isinstance(other, ArchivedItem):
            return self._uuid == other._uuid
        return False
    
    def __hash__(self) -> int:
        return hash(self._uuid)


class ArchiveManager:
    """
    Manages all archive operations for Prism.
    
    Handles:
    - Archiving completed strategic items and execution trees
    - Loading archived items (lazy via ArchivedItem wrappers)
    - Managing archived item metadata and ordering
    """
    
    def __init__(self, storage: StorageManager):
        """
        Initialize ArchiveManager.
        
        Args:
            storage: StorageManager for persistence
        """
        self.storage = storage
    
    def archive_strategic(self, item_data: Dict[str, Any], position: int = 0) -> None:
        """
        Archive a strategic item (phase, milestone, or objective).
        
        Args:
            item_data: Item data dict with uuid, name, slug, etc.
            position: Position among siblings (for ordering)
        """
        # Add position metadata
        item_data['position'] = position
        
        # Load existing archived items
        archived = self.storage.load_all_archived_strategic()
        
        # Determine item type and add to appropriate list
        item_type = self._infer_item_type(item_data)
        if item_type == 'phase':
            archived['phases'].append(item_data)
        elif item_type == 'milestone':
            archived['milestones'].append(item_data)
        elif item_type == 'objective':
            archived['objectives'].append(item_data)
        
        # Save back
        archive_path = self.storage._get_archive_file_path('strategic.json')
        self.storage._atomic_write(archive_path, archived)
    
    def archive_execution_tree(self, objective_uuid: str, tree_data: Dict[str, Any]) -> None:
        """
        Archive an execution tree (deliverables and actions).
        
        Args:
            objective_uuid: UUID of the objective being archived
            tree_data: Dictionary with deliverables and actions lists
        """
        # Add position metadata to deliverables and actions
        for i, deliv in enumerate(tree_data.get('deliverables', [])):
            deliv['position'] = i
        for i, action in enumerate(tree_data.get('actions', [])):
            action['position'] = i
        
        self.storage.archive_execution_tree(objective_uuid, tree_data)
    
    def get_archived_item(self, uuid: str) -> Optional[ArchivedItem]:
        """
        Get an archived item by UUID as an ArchivedItem wrapper.
        
        Args:
            uuid: Item UUID
        
        Returns:
            ArchivedItem wrapper or None if not found
        """
        archived = self.storage.load_all_archived_strategic()
        
        # Search in all item types
        for item_type in ['phases', 'milestones', 'objectives']:
            for item_data in archived.get(item_type, []):
                if item_data.get('uuid') == uuid:
                    return ArchivedItem(
                        uuid=item_data['uuid'],
                        name=item_data['name'],
                        slug=item_data['slug'],
                        item_type=item_type[:-1],  # 'phases' -> 'phase'
                        status=item_data.get('status', 'archived'),
                        parent_uuid=item_data.get('parent_uuid'),
                        description=item_data.get('description'),
                        position=item_data.get('position', 0),
                        storage=self.storage,
                    )
        
        return None
    
    def list_archived_items(self, item_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List archived items, optionally filtered by type.
        
        Args:
            item_type: Optional filter ('phase', 'milestone', 'objective')
        
        Returns:
            List of item data dicts
        """
        archived = self.storage.load_all_archived_strategic()
        
        if item_type:
            return archived.get(f"{item_type}s", [])
        
        # Return all items
        all_items = []
        for type_key in ['phases', 'milestones', 'objectives']:
            all_items.extend(archived.get(type_key, []))
        return all_items
    
    def _infer_item_type(self, item_data: Dict[str, Any]) -> str:
        """Infer item type from data structure and parent_uuid relationship."""
        # Check for type-specific fields first
        if 'deliverables' in item_data:
            return 'objective'
        if 'actions' in item_data:
            return 'deliverable'
        
        # Fall back to parent_uuid relationship
        parent_uuid = item_data.get('parent_uuid')
        if parent_uuid is None:
            # Could be a phase or an objective with missing parent_uuid
            # Check if it has objective characteristics
            if 'child_uuids' in item_data or item_data.get('status') == 'completed':
                return 'objective'
            return 'phase'

        archived = self.storage.load_all_archived_strategic()
        # Check if parent is a phase
        for phase in archived['phases']:
            if phase['uuid'] == parent_uuid:
                return 'milestone'
        # Check if parent is a milestone
        for milestone in archived['milestones']:
            if milestone['uuid'] == parent_uuid:
                return 'objective'

        # Default to objective (parent is likely a milestone not yet archived)
        return 'objective'


class AutoArchiveListener(EventListener):
    """
    Automatically archives completed strategic items via EventBus.

    When a strategic item (phase, milestone, objective) is completed:
    1. Archive the strategic item to archive/strategic.json
    2. If objective, archive execution tree to archive/{uuid}.exec.json
    """

    def __init__(
        self,
        storage: StorageManager,
        project: 'Project',
        auto_archive_enabled: bool = True,
    ) -> None:
        """
        Initialize AutoArchiveListener.

        Args:
            storage: StorageManager for archive operations.
            project: Project for item lookup.
            auto_archive_enabled: Whether auto-archive is enabled.
        """
        self.storage = storage
        self.project = project
        self.auto_archive_enabled = auto_archive_enabled
        self.archive_manager = ArchiveManager(storage)

    @property
    def subscribed_events(self) -> List[EventType]:
        """Return list of events this listener handles."""
        return [EventType.STRATEGIC_COMPLETED]

    def handle(self, event: Event) -> None:
        """Handle a strategic completion event.

        Args:
            event: The strategic completion event.
        """
        if not self.auto_archive_enabled:
            return

        if not isinstance(event, ItemEvent):
            return

        # Only archive objectives for now (phases/milestones may need different handling)
        if event.item_type != "objective":
            return

        import click
        click.echo(f"  📦 Auto-archiving objective '{event.item_name}'...")

        try:
            self._archive_objective(event)
        except Exception as e:
            click.echo(f"  ⚠ Failed to archive objective: {e}", err=True)

    def _archive_objective(self, event: ItemEvent) -> None:
        """Archive a completed objective with its execution tree.

        Args:
            event: The item event for the completed objective.
        """
        # Get the objective item by UUID
        objective = self.project.get_by_uuid(event.item_uuid)
        if not objective:
            raise ValueError(f"Objective not found: {event.item_uuid}")

        # Archive strategic item via ArchiveManager
        self.archive_manager.archive_strategic(objective.model_dump(mode='json'))

        # Archive execution tree (deliverables and actions)
        execution_data = {
            "deliverables": [],
            "actions": []
        }

        for deliverable in objective.deliverables:
            del_data = deliverable.model_dump(mode='json')
            execution_data["deliverables"].append(del_data)

            for action in deliverable.actions:
                act_data = action.model_dump(mode='json')
                execution_data["actions"].append(act_data)

        self.storage.archive_execution_tree(objective.uuid, execution_data)

        import click
        click.echo(f"  ✓ Archived objective '{event.item_name}' to archive/")
        click.echo(f"    - Strategic: archive/strategic.json (appended)")
        click.echo(f"    - Execution: archive/{objective.uuid}.exec.json")
