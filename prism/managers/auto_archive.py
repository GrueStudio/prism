"""
Auto-archive listener for completed strategic items.

Automatically archives completed strategic items with their execution trees.
"""
from typing import List, Optional

from prism.managers.events import Event, EventListener, EventType, ItemEvent
from prism.managers.storage_manager import StorageManager
from prism.managers.project_manager import Project


class AutoArchiveListener(EventListener):
    """
    Automatically archives completed strategic items.
    
    When a strategic item (phase, milestone, objective) is completed:
    1. Archive the strategic item to archive/strategic-{uuid}.json
    2. If objective, archive execution tree to archive/objective-{slug}.exec.json
    3. Remove from active strategic.json and execution.json
    """
    
    def __init__(
        self, 
        storage: StorageManager, 
        project: Project,
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
        
        # Archive strategic item
        strategic_data = objective.model_dump(mode='json')
        self.storage.archive_strategic(objective.uuid, strategic_data)

        # Archive execution tree (deliverables and actions)
        execution_data = {
            "objective_uuid": objective.uuid,
            "objective_slug": objective.slug,
            "deliverables": [],
            "actions": []
        }

        for deliverable in objective.deliverables:
            del_data = deliverable.model_dump(mode='json')
            execution_data["deliverables"].append(del_data)

            for action in deliverable.actions:
                act_data = action.model_dump(mode='json')
                execution_data["actions"].append(act_data)
        
        self.storage.archive_execution_tree(objective.slug, execution_data)
        
        # Remove from active files (will be implemented after migration)
        # For now, just archive - removal happens after migration to new storage
        
        import click
        click.echo(f"  ✓ Archived objective '{event.item_name}' to archive/")
        click.echo(f"    - Strategic: archive/strategic-{objective.uuid}.json")
        click.echo(f"    - Execution: archive/objective-{objective.slug}.exec.json")
