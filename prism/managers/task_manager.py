"""
TaskManager for task operations and CRUD in the Prism CLI.

Handles:
- Task operations (start, complete, next)
- Completion cascading up the tree
- Completion percentage calculations
- CRUD operations (add, update, delete items)
- Slug generation with filler word filtering
"""

import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, NamedTuple

from prism.managers.config_manager import get_config_manager
from prism.exceptions import (
    InvalidOperationError,
    NotFoundError,
    ValidationError,
)
from prism.managers.navigation_manager import NavigationManager
from prism.models.base import (
    Action,
    BaseItem,
    Deliverable,
    ItemStatus,
    Milestone,
    Objective,
    Phase,
)
from prism.models.project import Project


class StatusChangeEvent(NamedTuple):
    """Represents a status change that occurred during an operation."""
    item: BaseItem
    old_status: ItemStatus
    new_status: ItemStatus
    cascaded: bool = False


class TaskManager:
    """
    Manages task operations and CRUD for the Prism CLI.

    Handles:
    - Getting current action from cursor
    - Finding next pending action
    - Starting actions (mark as in-progress)
    - Completing actions with cascade
    - Adding, updating, deleting items
    - Slug generation
    - Completion percentage calculations
    """

    def __init__(
        self,
        project: Project,
        navigator: NavigationManager,
        save_callback: Callable[[], None],
    ) -> None:
        """
        Initialize TaskManager.

        Args:
            project: Project instance containing all items.
            navigator: NavigationManager instance for path resolution.
            save_callback: Callback function to save project data.
        """
        self.project = project
        self.navigator = navigator
        self._save_callback = save_callback
        
        config = get_config_manager()
        self._round_precision = config.PERCENTAGE_ROUND_PRECISION

    # =========================================================================
    # Task Operations
    # =========================================================================

    def get_current_action(self) -> Optional[Action]:
        """Get the action currently referenced by the task cursor.

        Returns:
            Current action or None if no task cursor.
        """
        if not self.project.task_cursor:
            return None
        item = self.navigator.get_item_by_path(self.project.task_cursor)
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
        for action in deliverable.children:
            if action.status == ItemStatus.PENDING:
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
        for deliverable in objective.children:
            if deliverable.status != ItemStatus.COMPLETED:
                pending_action = self._find_next_pending_action_in_deliverable(
                    deliverable
                )
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

    def _start_action(self, action: Action) -> List[StatusChangeEvent]:
        """Mark an action as in-progress and update the task cursor.

        Enforces single active task by pausing any currently in-progress action.

        Args:
            action: Action to start.

        Returns:
            List of status change events.
        """
        events = []
        
        # Check if another action is currently in progress and pause it
        current_action = self.get_current_action()
        if current_action and current_action.uuid != action.uuid:
            if current_action.status == ItemStatus.IN_PROGRESS:
                old_status = current_action.status
                current_action.set_status(ItemStatus.PAUSED)
                events.append(StatusChangeEvent(current_action, old_status, ItemStatus.PAUSED))

        # Start the new action
        if action.status != ItemStatus.IN_PROGRESS:
            old_status = action.status
            action.set_status(ItemStatus.IN_PROGRESS)
            events.append(StatusChangeEvent(action, old_status, ItemStatus.IN_PROGRESS))
            
            # Cascade in-progress up the tree
            events.extend(self._cascade_in_progress(action))

        action_path = self.navigator.get_item_path(action)
        self.project.task_cursor = action_path
        self._save_callback()
        
        return events

    def start_action_by_path(self, path: str) -> Tuple[Action, List[StatusChangeEvent]]:
        """Start a specific action or deliverable's first action by path.

        Args:
            path: Path to the action or deliverable.

        Returns:
            Tuple of (started_action, list of status change events).

        Raises:
            NotFoundError: If item at path not found.
            InvalidOperationError: If item is not an action or deliverable.
        """
        item = self.navigator.resolve_to_item(path)
        if not item:
            raise NotFoundError(f"Item not found at path: {path}")

        action_to_start = None
        if isinstance(item, Action):
            action_to_start = item
        elif isinstance(item, Deliverable):
            # Start first pending action in deliverable
            action_to_start = self._find_next_pending_action_in_deliverable(item)
            if not action_to_start and item.children:
                # Fallback to first action if none pending
                action_to_start = item.children[0]
        
        if not action_to_start:
            raise InvalidOperationError(
                f"Cannot start item at '{path}'. It must be an action or a deliverable with actions."
            )

        events = self._start_action(action_to_start)
        return action_to_start, events

    def start_next_action(self, path: Optional[str] = None) -> Tuple[Optional[Action], List[StatusChangeEvent]]:
        """Start the next pending action, or a specific action if path provided.

        If a path is provided, starts that specific action.
        If there's an action in progress or paused, and no path provided, returns/resumes it.
        Otherwise, finds the next pending action, sets it to 'in-progress',
        and updates the task cursor.

        Args:
            path: Optional path to a specific action to start.

        Returns:
            Tuple of (started_action, list of status change events).
        """
        if path:
            return self.start_action_by_path(path)

        # Check if there's an action currently in progress or paused
        current_action = self.get_current_action()
        if current_action and current_action.status in {
            ItemStatus.IN_PROGRESS,
            ItemStatus.PAUSED,
        }:
            events = []
            if current_action.status == ItemStatus.PAUSED:
                events = self._start_action(current_action)
            return current_action, events

        # If no action in progress, find the next pending one
        next_pending_action = self._find_next_pending_action()

        if next_pending_action:
            events = self._start_action(next_pending_action)
            return next_pending_action, events
        else:
            self.project.task_cursor = None
            self._save_callback()
            return None, []

    def complete_current_action(self) -> Tuple[Optional[Action], List[StatusChangeEvent]]:
        """Complete the current action without advancing to the next one.

        Returns:
            Tuple of (completed_action, list of status change events).
        """
        current_action = self.get_current_action()
        if not current_action or current_action.status != ItemStatus.IN_PROGRESS:
            return None, []

        events = []
        old_status = current_action.status
        current_action.set_status(ItemStatus.COMPLETED)
        events.append(StatusChangeEvent(current_action, old_status, ItemStatus.COMPLETED))

        # Cascade completion up the tree
        events.extend(self._cascade_completion(current_action))

        # Always clear the task cursor when an action is completed, 
        # unless it's immediately replaced by a 'next' command (handled there)
        self.project.task_cursor = None

        # If we just completed the task, check if we should pause the parent 
        # deliverable if it still has pending work but no active task
        parent = self.navigator.get_parent(current_action)
        if isinstance(parent, Deliverable) and parent.status == ItemStatus.IN_PROGRESS:
            # Only pause if there's no auto-advance happening (which would resume it)
            # and there are still pending items
            pending_sibling = self._find_next_pending_action_in_deliverable(parent)
            if pending_sibling:
                old_p_status = parent.status
                parent.set_status(ItemStatus.PAUSED)
                events.append(StatusChangeEvent(parent, old_p_status, ItemStatus.PAUSED, cascaded=True))

        self._save_callback()
        return current_action, events

    def pause_current_action(self) -> Tuple[Optional[Action], List[StatusChangeEvent]]:
        """Pause the current action.

        Returns:
            Tuple of (paused_action, list of status change events).
        """
        current_action = self.get_current_action()
        if not current_action or current_action.status != ItemStatus.IN_PROGRESS:
            return None, []

        old_status = current_action.status
        current_action.set_status(ItemStatus.PAUSED)
        
        events = [StatusChangeEvent(current_action, old_status, ItemStatus.PAUSED)]
        
        # Also pause the parent deliverable
        parent = self.navigator.get_parent(current_action)
        if isinstance(parent, Deliverable) and parent.status == ItemStatus.IN_PROGRESS:
            old_p_status = parent.status
            parent.set_status(ItemStatus.PAUSED)
            events.append(StatusChangeEvent(parent, old_p_status, ItemStatus.PAUSED, cascaded=True))

        self._save_callback()
        return current_action, events

    def _cascade_completion(self, item: BaseItem) -> List[StatusChangeEvent]:
        """Cascade completion status up the tree when all children are complete.

        Args:
            item: The completed item.

        Returns:
            List of status change events.
        """
        events = []
        parent = self.navigator.get_parent(item)
        if not parent:
            return events

        # Check if all children are terminal (completed, archived, or cancelled)
        all_children_terminal = False
        if parent.children:
            all_children_terminal = all(
                a.status in {ItemStatus.COMPLETED, ItemStatus.ARCHIVED, ItemStatus.CANCELLED}
                for a in parent.children
            )
        else:
            all_children_terminal = True

        # If all children are terminal, mark parent as complete and continue cascading
        if all_children_terminal and parent.status != ItemStatus.COMPLETED:
            old_status = parent.status
            parent.set_status(ItemStatus.COMPLETED)
            events.append(StatusChangeEvent(parent, old_status, ItemStatus.COMPLETED, cascaded=True))

            # Continue cascading up the tree recursively
            events.extend(self._cascade_completion(parent))

        return events

    def _cascade_in_progress(self, item: BaseItem) -> List[StatusChangeEvent]:
        """Cascade in-progress status up the tree.

        Args:
            item: The item that became in-progress.

        Returns:
            List of status change events.
        """
        events = []
        parent = self.navigator.get_parent(item)
        if not parent:
            return events

        # Only cascade up to Phase level
        if parent.status != ItemStatus.IN_PROGRESS:
            old_status = parent.status
            parent.set_status(ItemStatus.IN_PROGRESS)
            events.append(StatusChangeEvent(parent, old_status, ItemStatus.IN_PROGRESS, cascaded=True))
            
            if not isinstance(parent, Phase):
                events.extend(self._cascade_in_progress(parent))
                
        return events
        return events

    def cascade_status_to_in_progress(self, item: BaseItem) -> List[StatusChangeEvent]:
        """External entry point for cascading in-progress status."""
        events = self._cascade_in_progress(item)
        if events:
            self._save_callback()
        return events

    def complete_current_and_start_next(
        self,
        next_path: Optional[str] = None,
        reset: bool = False,
    ) -> Tuple[Optional[Action], Optional[Action], List[StatusChangeEvent]]:
        """Complete the current action and start the next pending one.

        Args:
            next_path: Optional path to the specific next action to start.
            reset: If True, reset to the first action of the current deliverable.

        Returns:
            Tuple of (completed_action, next_action, list of status change events)
        """
        completed_action, comp_events = self.complete_current_action()
        if not completed_action:
            return None, None, []

        all_events = list(comp_events)

        # If explicit next_path provided, use it
        if next_path:
            next_action, start_events = self.start_next_action(path=next_path)
            all_events.extend(start_events)
            return completed_action, next_action, all_events

        # If reset requested, find the first action of the current deliverable
        if reset:
            deliverable = self.navigator.get_parent(completed_action)
            if isinstance(deliverable, Deliverable) and deliverable.children:
                first_action = deliverable.children[0]
                start_events = self._start_action(first_action)
                all_events.extend(start_events)
                return completed_action, first_action, all_events

        # Default sequential behavior
        # Check if deliverable boundary was reached
        deliverable = self.navigator.get_parent(completed_action)
        if isinstance(deliverable, Deliverable) and deliverable.status == ItemStatus.COMPLETED:
            # Deliverable boundary reached, do not auto-start next action
            # The cursor was already cleared in complete_current_action
            return completed_action, None, all_events

        next_action, start_events = self.start_next_action()
        all_events.extend(start_events)
        return completed_action, next_action, all_events

    # =========================================================================
    # Completion Tracking
    # =========================================================================

    def calculate_completion_percentage(self, item: BaseItem) -> Dict[str, Any]:
        """Calculate completion percentage for objectives and deliverables.

        Args:
            item: Item to calculate percentage for.

        Returns:
            Dictionary with 'overall' percentage and 'by_type' breakdown.
        """
        if isinstance(item, Objective):
            if len(item.children) == 0:
                return {"overall": 0.0, "by_type": {"deliverables": 0.0}}

            completed_deliverables = sum(
                1 for d in item.children if d.status == ItemStatus.COMPLETED
            )
            total_deliverables = len(item.children)

            # Calculate completion for each deliverable's actions
            total_actions = 0
            completed_actions = 0

            for deliverable in item.children:
                for action in deliverable.children:
                    total_actions += 1
                    if action.status == ItemStatus.COMPLETED:
                        completed_actions += 1

            return {
                "overall": round(
                    (completed_deliverables / total_deliverables) * 100,
                    self._round_precision,
                )
                if total_deliverables > 0
                else 0.0,
                "by_type": {
                    "deliverables": round(
                        (completed_deliverables / total_deliverables) * 100,
                        self._round_precision,
                    )
                    if total_deliverables > 0
                    else 0.0,
                    "actions": round(
                        (completed_actions / total_actions) * 100,
                        self._round_precision,
                    )
                    if total_actions > 0
                    else 0.0,
                },
            }

        elif isinstance(item, Deliverable):
            if len(item.children) == 0:
                return {"overall": 0.0}

            completed_actions = sum(1 for a in item.children if a.status == ItemStatus.COMPLETED)
            total_actions = len(item.children)

            return {
                "overall": round(
                    (completed_actions / total_actions) * 100, self._round_precision
                ),
                "by_type": {
                    "actions": round(
                        (completed_actions / total_actions) * 100, self._round_precision
                    )
                },
            }

        return {"overall": 0.0}

    def is_exec_tree_complete(self, objective: Objective) -> bool:
        """Check if an execution tree (deliverables and actions) is complete.

        Args:
            objective: Objective to check.

        Returns:
            True if all deliverables and actions are complete (or empty).
        """
        if not objective.children:
            return True  # Empty tree is considered complete (ready for new items)

        for deliverable in objective.children:
            if deliverable.status != ItemStatus.COMPLETED:
                return False
            for action in deliverable.children:
                if action.status != ItemStatus.COMPLETED:
                    return False

        return True

    def get_completion_stats(self, item: BaseItem) -> Dict[str, int]:
        """Get completion statistics for an item.

        Args:
            item: Item to get stats for.

        Returns:
            Dictionary with total, completed, and pending counts.
        """
        if isinstance(item, Objective):
            total_del = len(item.children)
            completed_del = sum(1 for d in item.children if d.status == ItemStatus.COMPLETED)
            total_act = sum(len(d.children) for d in item.children)
            completed_act = sum(
                sum(1 for a in d.children if a.status == ItemStatus.COMPLETED)
                for d in item.children
            )
            return {
                "deliverables_total": total_del,
                "deliverables_completed": completed_del,
                "deliverables_pending": total_del - completed_del,
                "actions_total": total_act,
                "actions_completed": completed_act,
                "actions_pending": total_act - completed_act,
            }
        elif isinstance(item, Deliverable):
            total = len(item.children)
            completed = sum(1 for a in item.children if a.status == ItemStatus.COMPLETED)
            return {
                "actions_total": total,
                "actions_completed": completed,
                "actions_pending": total - completed,
            }
        return {}

    # =========================================================================
    # CRUD Operations - Slug Generation
    # =========================================================================

    def _generate_unique_slug(
        self, existing_items: List[BaseItem], base_name: str
    ) -> str:
        """Generate a unique slug for an item.

        Uses configurable word limit and filler word filtering.

        Args:
            existing_items: List of existing sibling items for slug uniqueness check.
            base_name: Base name to generate slug from.

        Returns:
            Unique slug string.
        """
        config = get_config_manager()
        max_length = config.SLUG_MAX_LENGTH
        word_limit = config.SLUG_WORD_LIMIT
        filler_words = set(config.SLUG_FILLER_WORDS)

        # Split name into words, convert to lowercase
        words = base_name.lower().split()

        # Filter out filler words and take first N words
        filtered_words = [w for w in words if w not in filler_words][:word_limit]

        # If all words were filtered out, use original words
        if not filtered_words:
            filtered_words = words[:word_limit]

        # Join with hyphens and remove non-alphanumeric chars
        base_slug = "-".join(filtered_words)
        base_slug = re.sub(r"[^a-z0-9\-]+", "-", base_slug).strip("-")

        # Truncate to max length
        base_slug = base_slug[:max_length]

        if not base_slug:
            base_slug = "item"

        existing_slugs = {item.slug for item in existing_items}

        slug = base_slug
        count = 1
        while slug in existing_slugs:
            slug = (
                f"{base_slug[: (max_length - len(str(count)) - 1)]}-{count}"
                if len(base_slug) > (max_length - len(str(count)) - 1)
                else f"{base_slug}-{count}"
            )
            count += 1
        return slug

    def _get_sibling_items(
        self, parent_path: Optional[str], item_type: str
    ) -> List[BaseItem]:
        """Get list of sibling items for slug uniqueness check.

        Args:
            parent_path: Path to parent item, or None for top-level phases.
            item_type: Type of item being added.

        Returns:
            List of sibling items.

        Raises:
            NotFoundError: If parent item not found.
            InvalidOperationError: If parent-child relationship is invalid.
            ValueError: If adding non-phase item without parent.
        """
        if parent_path:
            parent_item = self.navigator.get_item_by_path(parent_path)
            if not parent_item:
                raise NotFoundError(
                    f"Parent item not found at path: '{parent_path}'. "
                    f"Please verify the path is correct and the parent item exists."
                )

            if item_type == "milestone" and isinstance(parent_item, Phase):
                return parent_item.children
            elif item_type == "objective" and isinstance(parent_item, Milestone):
                return parent_item.children
            elif item_type == "deliverable" and isinstance(parent_item, Objective):
                return parent_item.children
            elif item_type == "action" and isinstance(parent_item, Deliverable):
                return parent_item.children
            else:
                raise InvalidOperationError(
                    f"Cannot add {item_type} to parent of type {type(parent_item).__name__}. "
                    f"Valid parent-child relationships are: phase->milestone, milestone->objective, "
                    f"objective->deliverable, deliverable->action."
                )
        else:
            if item_type == "phase":
                return self.project.phases
            else:
                raise ValueError(
                    f"Cannot add {item_type} without a parent path. "
                    f"Only phases can be added at the top level."
                )

    def _create_item(
        self,
        item_type: str,
        name: str,
        description: Optional[str],
        slug: str,
        status: Optional[str] = None,
    ) -> BaseItem:
        """Create a new item instance.

        Args:
            item_type: Type of item to create.
            name: Item name.
            description: Item description.
            slug: Item slug.
            status: Optional item status.

        Returns:
            New item instance.

        Raises:
            ValidationError: If item type is invalid or status is invalid.
        """
        # Validate item_type
        valid_types = ["phase", "milestone", "objective", "deliverable", "action"]
        if item_type not in valid_types:
            raise ValidationError(
                f"Invalid item type: '{item_type}'. "
                f"Valid types are: {', '.join(valid_types)}."
            )

        # Create the item
        if item_type == "phase":
            new_item: BaseItem = Phase(name=name, description=description, slug=slug)
        elif item_type == "milestone":
            new_item = Milestone(name=name, description=description, slug=slug)
        elif item_type == "objective":
            new_item = Objective(name=name, description=description, slug=slug)
        elif item_type == "deliverable":
            new_item = Deliverable(name=name, description=description, slug=slug)
        elif item_type == "action":
            new_item = Action(name=name, description=description, slug=slug)
        else:
            raise ValidationError("Unsupported item type during instantiation.")

        # Enforce business rule: new items cannot be created as "completed" or "archived"
        if status in [ItemStatus.COMPLETED, ItemStatus.ARCHIVED]:
            raise ValidationError(
                f"Cannot create new item with status '{status.value if isinstance(status, ItemStatus) else status}'. "
                f"New items must start in 'pending' status."
            )
        elif status is not None:
            # Validate status against allowed values
            valid_values = [s.value for s in ItemStatus]
            if status not in valid_values:
                raise ValidationError(
                    f"Invalid status: '{status}'. Status must be one of: {', '.join(valid_values)}."
                )
            new_item.status = status
        else:
            new_item.status = ItemStatus.PENDING

        return new_item
