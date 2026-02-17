"""
NewPrismCore - Core business logic for the Prism CLI using new storage.

Orchestrates manager classes for all business operations.
Uses StorageManager for .prism/ folder-based storage.
Uses EventBus for decoupled event-driven architecture.
"""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from prism.models import Action, BaseItem
from prism.managers import (
    ItemManager,
    TaskManager,
    CompletionTracker,
    NavigationManager,
    StorageManager,
    AutoArchiveListener,
    get_event_bus,
    subscribe_listener,
)
from prism.exceptions import (
    PrismError,
    ValidationError,
    NotFoundError,
    InvalidOperationError,
    DuplicateError,
)


class NewPrismCore:
    """
    Core class for business logic operations with new storage.

    Orchestrates manager classes:
    - StorageManager: Persistence to .prism/ folder
    - NavigationManager: Path resolution
    - ItemManager: CRUD operations
    - TaskManager: Task operations (start, complete, next)
    - CompletionTracker: Cascade completion and percentages
    - EventBus: Event-driven communication
    - AutoArchiveListener: Auto-archive completed items
    """

    def __init__(
        self, 
        prism_dir: Optional[Path] = None,
        auto_archive_enabled: bool = True,
    ):
        """
        Initialize the NewPrismCore with a .prism/ directory.

        Args:
            prism_dir: Path to .prism/ directory. Defaults to .prism/ in current directory.
            auto_archive_enabled: Whether to enable auto-archive on completion.
        """
        self.storage = StorageManager(prism_dir)

        # Load project data from storage
        self._load_project_data()

        # Initialize managers
        self.navigator = NavigationManager(self.project_data)
        self.item_manager = ItemManager(self.project_data, self.navigator)
        self.task_manager = TaskManager(
            self.project_data,
            self.navigator,
            self._save_project_data
        )
        self.completion_tracker = CompletionTracker(
            self.navigator, 
            emit_events=True
        )

        # Set up event-driven architecture
        self.event_bus = get_event_bus()
        
        # Subscribe auto-archive listener
        if auto_archive_enabled:
            self.auto_archive_listener = AutoArchiveListener(
                self.storage, 
                self.navigator,
                auto_archive_enabled=True,
            )
            subscribe_listener(self.auto_archive_listener)

    def _load_project_data(self) -> None:
        """Load project data from storage."""
        # For now, load from old format
        # Will be replaced with new storage format after migration
        from prism.data_store import DataStore
        
        # Load from project.json for backward compatibility
        data_store = DataStore()
        self.project_data = data_store.load_project_data()

    def _save_project_data(self) -> None:
        """Save project data to storage."""
        # For now, save to old format
        # Will be replaced with new storage format after migration
        from prism.data_store import DataStore
        
        data_store = DataStore()
        data_store.save_project_data(self.project_data)

    # Delegate to ItemManager
    def add_item(
        self,
        item_type: str,
        name: str,
        description: Optional[str],
        parent_path: Optional[str],
        status: Optional[str] = None,
    ) -> BaseItem:
        """Add a new item to the project."""
        return self.item_manager.add_item(
            item_type, name, description, parent_path, status
        )

    def update_item(
        self,
        path: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        due_date: Optional[str] = None,
        status: Optional[str] = None,
    ) -> BaseItem:
        """Update an existing item."""
        return self.item_manager.update_item(
            path, name, description, due_date, status
        )

    def delete_item(self, path: str) -> None:
        """Delete an existing item."""
        self.item_manager.delete_item(path)

    # Delegate to TaskManager
    def get_current_action(self) -> Optional[Action]:
        """Get the current action from cursor."""
        return self.task_manager.get_current_action()

    def start_next_action(self) -> Optional[Action]:
        """Start the next pending action."""
        return self.task_manager.start_next_action()

    def complete_current_action(self) -> Optional[Action]:
        """Complete the current action."""
        return self.task_manager.complete_current_action()

    def complete_current_and_start_next(self) -> tuple[Optional[Action], Optional[Action]]:
        """Complete current action and start next."""
        return self.task_manager.complete_current_and_start_next()

    # Delegate to CompletionTracker
    def calculate_completion_percentage(self, item: BaseItem) -> Dict[str, float]:
        """Calculate completion percentage for an item."""
        return self.completion_tracker.calculate_completion_percentage(item)

    def is_exec_tree_complete(self, objective_path: str) -> bool:
        """Check if execution tree is complete."""
        objective = self.navigator.get_item_by_path(objective_path)
        if not objective:
            return False
        from prism.models import Objective
        if not isinstance(objective, Objective):
            return False
        return self.completion_tracker.is_exec_tree_complete(objective)

    # Delegate to NavigationManager
    def get_item_by_path(self, path: str) -> Optional[BaseItem]:
        """Get an item by its path."""
        return self.navigator.get_item_by_path(path)

    def get_item_path(self, item: BaseItem) -> Optional[str]:
        """Get the path of an item."""
        return self.navigator.get_item_path(item)

    def get_current_objective(self) -> Optional[Any]:
        """Get the current objective."""
        return self.navigator.get_current_objective()

    def get_current_strategic_items(self) -> Dict[str, Optional[BaseItem]]:
        """Get current phase, milestone, and objective."""
        return self.navigator.get_current_strategic_items()

    # Keep existing methods that aren't in managers yet
    def add_exec_tree(self, tree_data: List[Dict[str, Any]], mode: str) -> None:
        """Add an execution tree."""
        # This will be moved to ItemManager or a dedicated ExecTreeManager
        current_objective = self.navigator.get_current_objective()
        if current_objective is None:
            raise ValueError("No current objective found.")

        if mode == "replace":
            current_objective.deliverables = []
        elif mode != "append":
            raise ValueError(f"Invalid mode: {mode}. Must be 'append' or 'replace'.")

        for del_data in tree_data:
            del_name = del_data.get("name")
            del_desc = del_data.get("description")
            if not del_name:
                raise ValidationError("Deliverable name is required in addtree input.")

            deliverable_slug = self.item_manager._generate_unique_slug(
                current_objective.deliverables, del_name
            )
            from prism.models import Deliverable, Action
            new_deliverable = Deliverable(
                name=del_name, description=del_desc, slug=deliverable_slug
            )

            for act_data in del_data.get("actions", []):
                act_name = act_data.get("name")
                act_desc = act_data.get("description")
                if not act_name:
                    raise ValidationError("Action name is required in addtree input.")

                action_slug = self.item_manager._generate_unique_slug(
                    new_deliverable.actions, act_name
                )
                new_action = Action(
                    name=act_name, description=act_desc, slug=action_slug
                )
                new_deliverable.actions.append(new_action)

            current_objective.deliverables.append(new_deliverable)

        self._save_project_data()

    def get_status_summary(
        self, 
        phase_path: Optional[str] = None, 
        milestone_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get a summary of project status."""
        # This will be moved to a dedicated StatusManager
        from prism.core import Core as OldCore
        # Delegate to old Core for now
        old_core = OldCore.__new__(OldCore)
        old_core.project_data = self.project_data
        old_core.navigator = self.navigator
        return old_core.get_status_summary(phase_path, milestone_path)
