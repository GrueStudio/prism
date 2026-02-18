"""
TaskManager for task operations in the Prism CLI.

Handles starting, completing, and navigating through actions.
"""
from datetime import datetime
from typing import Callable, Optional, Tuple

import click

from prism.newmodels import Action, BaseItem, Deliverable, Objective
from prism.managers.project_manager import Project
from prism.managers.navigation_manager import NavigationManager
from prism.constants import COMPLETED_STATUS
from prism.managers.completion_tracker import CompletionTracker


class TaskManager:
    """
    Manages task-related operations.

    Handles:
    - Getting current action from cursor
    - Finding next pending action
    - Starting actions (mark as in-progress)
    - Completing actions
    - Cascading completion up the tree (via CompletionTracker)
    """

    def __init__(
        self,
        project: Project,
        navigator: NavigationManager,
        save_callback: Callable[[], None],
        completion_tracker: Optional[CompletionTracker] = None,
    ) -> None:
        """
        Initialize TaskManager.

        Args:
            project: Project instance containing all items.
            navigator: NavigationManager instance for path resolution.
            save_callback: Callback function to save project data.
            completion_tracker: Optional CompletionTracker for cascade events.
        """
        self.project = project
        self.navigator = navigator
        self._save_callback = save_callback
        self._completion_tracker = completion_tracker

    def get_current_action(self) -> Optional[Action]:
        """Get the action currently referenced by the cursor.

        Returns:
            Current action or None if no cursor.
        """
        if not self.project.cursor:
            return None
        item = self.navigator.get_item_by_path(self.project.cursor)
        if isinstance(item, Action):
            return item
        return None

    def _find_next_pending_action_in_deliverable(
        self, deliverable: Deliverable
    ) -> Optional[Action]:
        """Find the next pending action within a specific deliverable.

        Args:
            deliverable: Deliverable to search in.

        Returns:
            First pending action found, or None.
        """
        for action in deliverable.actions:
            if action.status == "pending":
                return action
        return None

    def _find_next_pending_action_in_objective(
        self, objective: Objective
    ) -> Optional[Action]:
        """Find the next pending action within an objective.

        Prioritizes current deliverable context.

        Args:
            objective: Objective to search in.

        Returns:
            First pending action found, or None.
        """
        # First, try to find pending actions in non-completed deliverables
        for deliverable in objective.deliverables:
            if deliverable.status != "completed":
                pending_action = self._find_next_pending_action_in_deliverable(deliverable)
                if pending_action:
                    return pending_action
        return None

    def _find_next_pending_action(self) -> Optional[Action]:
        """Find the next pending action across the current objective.

        Returns:
            Next pending action, or None if not found.
        """
        current_objective = self.navigator.get_current_objective()
        if not current_objective:
            return None

        return self._find_next_pending_action_in_objective(current_objective)

    def _start_action(self, action: Action) -> None:
        """Mark an action as in-progress and update the cursor.

        Args:
            action: Action to start.
        """
        action.status = "in-progress"
        action_path = self.navigator.get_item_path(action)
        self.project.cursor = action_path
        self._save_callback()

    def start_next_action(self) -> Optional[Action]:
        """Start the next pending action.

        If there's an action in progress, returns it.
        Otherwise, finds the next pending action, sets it to 'in-progress',
        and updates the cursor.

        Returns:
            The started action, or None if no pending action found.
        """
        # Check if there's an action currently in progress
        current_action = self.get_current_action()
        if current_action and current_action.status == "in-progress":
            return current_action

        # If no action in progress, find the next pending one
        next_pending_action = self._find_next_pending_action()

        if next_pending_action:
            self._start_action(next_pending_action)
        else:
            self.project.cursor = None
            self._save_callback()

        return next_pending_action

    def complete_current_action(self) -> Optional[Action]:
        """Complete the current action without advancing to the next one.

        Returns:
            The completed action, or None if no action in progress.
        """
        current_action = self.get_current_action()
        if not current_action or current_action.status != "in-progress":
            return None

        current_action.status = "completed"
        current_action.updated_at = datetime.now()

        # Cascade completion up the tree via CompletionTracker (emits events)
        if self._completion_tracker:
            self._completion_tracker.cascade_completion(current_action)
        else:
            # Fallback to local cascade if no tracker (no events emitted)
            self._cascade_completion_local(current_action)

        self._save_callback()
        return current_action

    def _cascade_completion_local(self, item: BaseItem) -> None:
        """Local cascade completion (without events).

        Fallback when CompletionTracker is not available.

        Args:
            item: The completed item.
        """
        # Get the parent of the completed item
        item_path = self.navigator.get_item_path(item)
        if not item_path:
            return

        segments = item_path.split("/")
        if len(segments) < 2:
            return  # Top-level item, no parent to update

        parent_path = "/".join(segments[:-1])
        parent = self.navigator.get_item_by_path(parent_path)
        if not parent:
            return

        # Check if all children are complete and update parent status
        all_children_complete = False

        if isinstance(item, Action) and isinstance(parent, Deliverable):
            # Check if all actions in deliverable are complete
            if parent.actions:
                all_children_complete = all(
                    a.status == "completed" for a in parent.actions
                )
        elif isinstance(item, Deliverable) and isinstance(parent, Objective):
            # Check if all deliverables in objective are complete
            if parent.deliverables:
                all_children_complete = all(
                    d.status == "completed" for d in parent.deliverables
                )

        # If all children are complete, mark parent as complete
        if all_children_complete and parent.status != "completed":
            parent.status = "completed"
            parent.updated_at = datetime.now()
            click.echo(
                f"  ✓ {type(parent).__name__} '{parent.name}' marked complete"
            )

            # Continue cascading only if parent is a deliverable
            if isinstance(parent, Deliverable):
                self._cascade_completion_local(parent)

    def complete_current_and_start_next(
        self,
    ) -> Tuple[Optional[Action], Optional[Action]]:
        """Complete the current action and start the next pending one.

        Returns:
            Tuple of (completed_action, next_action)
        """
        completed_action = self.complete_current_action()
        if not completed_action:
            return (None, None)

        next_action = self.start_next_action()
        return (completed_action, next_action)
