"""
PrismCore - Core business logic for the Prism CLI using .prism/ storage.

Orchestrates manager classes for all business operations.
Uses StorageManager for .prism/ folder-based storage exclusively.
Uses EventBus for decoupled event-driven architecture.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from prism.exceptions import ValidationError
from prism.managers import (
    AutoArchiveListener,
    CompletionTracker,
    ItemManager,
    NavigationManager,
    ProjectManager,
    StorageManager,
    TaskManager,
    get_event_bus,
    subscribe_listener,
)
from prism.models.base import (
    Action,
    Deliverable,
    Milestone,
    Objective,
    Phase,
)


class PrismCore:
    """
    Core class for business logic operations with new storage.

    Orchestrates manager classes:
    - ProjectManager: Build/save project structure
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
        Initialize the PrismCore with a .prism/ directory.

        Args:
            prism_dir: Path to .prism/ directory. Defaults to .prism/ in current directory.
            auto_archive_enabled: Whether to enable auto-archive on completion.
        """
        self.storage = StorageManager(prism_dir)
        self.project_manager = ProjectManager(self.storage)

        # Load project from storage
        self.project = self.project_manager.load()

        # Initialize managers
        self.navigator = NavigationManager(self.project)
        self.completion_tracker = CompletionTracker(self.navigator, emit_events=True)
        self.item_manager = ItemManager(self.project, self.navigator)
        self.task_manager = TaskManager(
            self.project,
            self.navigator,
            self._save_project,
            self.completion_tracker,
        )

        # Set up event-driven architecture
        self.event_bus = get_event_bus()

        # Subscribe auto-archive listener
        if auto_archive_enabled:
            self.auto_archive_listener = AutoArchiveListener(
                self.storage,
                self.project,
                auto_archive_enabled=True,
            )
            subscribe_listener(self.auto_archive_listener)

    def _save_project(self) -> None:
        """Save project to storage."""
        self.project_manager.save(self.project)

    def add_item(
        self,
        item_type: str,
        name: str,
        description: Optional[str],
        parent_path: Optional[str],
        status: Optional[str] = None,
    ) -> Any:
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
    ) -> Any:
        """Update an existing item."""
        return self.item_manager.update_item(path, name, description, due_date, status)

    def delete_item(self, path: str) -> None:
        """Delete an existing item."""
        self.item_manager.delete_item(path)

    def get_current_action(self) -> Optional[Action]:
        """Get the current action from cursor."""
        return self.task_manager.get_current_action()

    def start_next_action(self) -> Optional[Action]:
        """Start the next pending action."""
        return self.task_manager.start_next_action()

    def complete_current_action(self) -> Optional[Action]:
        """Complete the current action."""
        return self.task_manager.complete_current_action()

    def complete_current_and_start_next(
        self,
    ) -> tuple[Optional[Action], Optional[Action]]:
        """Complete current action and start next."""
        return self.task_manager.complete_current_and_start_next()

    def calculate_completion_percentage(self, item: Any) -> Dict[str, float]:
        """Calculate completion percentage for an item."""
        return self.completion_tracker.calculate_completion_percentage(item)

    def is_exec_tree_complete(self, objective_path: str) -> bool:
        """Check if execution tree is complete."""
        objective = self.navigator.get_item_by_path(objective_path)
        if not objective:
            return False
        if not isinstance(objective, Objective):
            return False
        return self.completion_tracker.is_exec_tree_complete(objective)

    def get_item_by_path(self, path: str) -> Optional[Any]:
        """Get an item by its path."""
        return self.navigator.get_item_by_path(path)

    def get_item_path(self, item: Any) -> Optional[str]:
        """Get the path of an item."""
        return self.navigator.get_item_path(item)

    def get_current_objective(self) -> Optional[Any]:
        """Get the current objective."""
        return self.navigator.get_current_objective()

    def get_current_strategic_items(self) -> Dict[str, Optional[Any]]:
        """Get current phase, milestone, and objective."""
        return self.navigator.get_current_strategic_items()

    def add_exec_tree(self, tree_data: List[Dict[str, Any]], mode: str) -> None:
        """Add an execution tree."""
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

        self._save_project()

    def get_status_summary(
        self, phase_path: Optional[str] = None, milestone_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get a summary of project status."""
        summary = {
            "item_counts": {
                "Phase": {"pending": 0, "completed": 0, "total": 0},
                "Milestone": {"pending": 0, "completed": 0, "total": 0},
                "Objective": {"pending": 0, "completed": 0, "total": 0},
                "Deliverable": {"pending": 0, "completed": 0, "total": 0},
                "Action": {"pending": 0, "completed": 0, "total": 0},
            },
            "overdue_actions": [],
            "orphaned_items": [],
        }

        def _traverse(items, parent_path="", parent_is_completed=False):
            for item in items:
                item_type = type(item).__name__
                current_path = (
                    f"{parent_path}/{item.slug}" if parent_path else item.slug
                )
                is_completed = item.status == "completed"

                summary["item_counts"][item_type]["total"] += 1
                if is_completed:
                    summary["item_counts"][item_type]["completed"] += 1
                else:
                    summary["item_counts"][item_type]["pending"] += 1

                if parent_is_completed and not is_completed:
                    summary["orphaned_items"].append(
                        {"path": current_path, "type": item_type}
                    )

                if (
                    isinstance(item, Action)
                    and not is_completed
                    and item.due_date
                    and item.due_date < datetime.now()
                ):
                    summary["overdue_actions"].append(
                        {"path": current_path, "due_date": item.due_date.isoformat()}
                    )

                children = []
                if isinstance(item, Phase):
                    children = item.milestones
                elif isinstance(item, Milestone):
                    children = item.objectives
                elif isinstance(item, Objective):
                    children = item.deliverables
                elif isinstance(item, Deliverable):
                    children = item.actions

                if children:
                    _traverse(
                        children,
                        parent_path=current_path,
                        parent_is_completed=is_completed,
                    )

        start_items = self.project.phases
        if milestone_path:
            milestone = self.navigator.get_item_by_path(milestone_path)
            if milestone and isinstance(milestone, Milestone):
                start_items = [milestone]
        elif phase_path:
            phase = self.navigator.get_item_by_path(phase_path)
            if phase and isinstance(phase, Phase):
                start_items = [phase]

        _traverse(start_items)
        return summary
