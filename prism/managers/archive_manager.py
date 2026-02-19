"""
ArchiveManager for Prism CLI.

Handles all archive operations including:
- Archiving completed items
- Lazy-loading archived items via ArchivedItem wrapper
- Managing archived item metadata and order
- Auto-archiving on item completion via EventBus
"""

from typing import Any, Dict, List, Optional

from prism.managers.events import Event, EventListener, EventType, ItemEvent
from prism.managers.storage_manager import StorageManager
from prism.models.archived import ArchivedItem
from prism.models.project import Project


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
        item_data["position"] = position

        # Load existing archived items
        archived = self.storage.load_all_archived_strategic()

        # Determine item type and add to appropriate list
        item_type = self._infer_item_type(item_data)
        if item_type == "phase":
            archived["phases"].append(item_data)
        elif item_type == "milestone":
            archived["milestones"].append(item_data)
        elif item_type == "objective":
            archived["objectives"].append(item_data)

        # Save back
        archive_path = self.storage._get_archive_file_path("strategic.json")
        self.storage._atomic_write(archive_path, archived)

    def archive_execution_tree(
        self, objective_uuid: str, tree_data: Dict[str, Any]
    ) -> None:
        """
        Archive an execution tree (deliverables and actions).

        Args:
            objective_uuid: UUID of the objective being archived
            tree_data: Dictionary with deliverables and actions lists
        """
        # Add position metadata to deliverables and actions
        for i, deliv in enumerate(tree_data.get("deliverables", [])):
            deliv["position"] = i
        for i, action in enumerate(tree_data.get("actions", [])):
            action["position"] = i

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
        for item_type in ["phases", "milestones", "objectives"]:
            for item_data in archived.get(item_type, []):
                if item_data.get("uuid") == uuid:
                    return ArchivedItem(
                        uuid=item_data["uuid"],
                        name=item_data["name"],
                        slug=item_data["slug"],
                        item_type=item_type[:-1],  # 'phases' -> 'phase'
                        status=item_data.get("status", "archived"),
                        parent_uuid=item_data.get("parent_uuid"),
                        description=item_data.get("description"),
                        position=item_data.get("position", 0),
                        storage=self.storage,
                    )

        return None

    def list_archived_items(
        self, item_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
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
        for type_key in ["phases", "milestones", "objectives"]:
            all_items.extend(archived.get(type_key, []))
        return all_items

    def _infer_item_type(self, item_data: Dict[str, Any]) -> str:
        """Infer item type from data structure and parent_uuid relationship."""
        # Check for type-specific fields first
        if "deliverables" in item_data:
            return "objective"
        if "actions" in item_data:
            return "deliverable"

        # Fall back to parent_uuid relationship
        parent_uuid = item_data.get("parent_uuid")
        if parent_uuid is None:
            # Could be a phase or an objective with missing parent_uuid
            # Check if it has objective characteristics
            if "child_uuids" in item_data or item_data.get("status") == "completed":
                return "objective"
            return "phase"

        archived = self.storage.load_all_archived_strategic()
        # Check if parent is a phase
        for phase in archived["phases"]:
            if phase["uuid"] == parent_uuid:
                return "milestone"
        # Check if parent is a milestone
        for milestone in archived["milestones"]:
            if milestone["uuid"] == parent_uuid:
                return "objective"

        # Default to objective (parent is likely a milestone not yet archived)
        return "objective"


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
        project: "Project",
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
        self.archive_manager.archive_strategic(objective.model_dump(mode="json"))

        # Archive execution tree (deliverables and actions)
        execution_data = {"deliverables": [], "actions": []}

        for deliverable in objective.deliverables:
            del_data = deliverable.model_dump(mode="json")
            execution_data["deliverables"].append(del_data)

            for action in deliverable.actions:
                act_data = action.model_dump(mode="json")
                execution_data["actions"].append(act_data)

        self.storage.archive_execution_tree(objective.uuid, execution_data)

        import click

        click.echo(f"  ✓ Archived objective '{event.item_name}' to archive/")
        click.echo(f"    - Strategic: archive/strategic.json (appended)")
        click.echo(f"    - Execution: archive/{objective.uuid}.exec.json")
