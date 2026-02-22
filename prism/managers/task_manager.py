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
from typing import Any, Callable, Dict, List, Optional, Tuple

import click

from prism.constants import (
    ARCHIVED_STATUS,
    COMPLETED_STATUS,
    DATE_FORMAT_ERROR,
    DEFAULT_STATUS,
    PERCENTAGE_ROUND_PRECISION,
    VALID_STATUSES,
    get_slug_filler_words,
    get_slug_max_length,
    get_slug_word_limit,
)
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
    Milestone,
    Objective,
    Phase,
)
from prism.models.project import Project
from prism.utils import parse_date, validate_date_range


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
        self._round_precision = PERCENTAGE_ROUND_PRECISION

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
        for deliverable in objective.children:
            if deliverable.status != "completed":
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

    def _start_action(self, action: Action) -> None:
        """Mark an action as in-progress and update the task cursor.

        Args:
            action: Action to start.
        """
        action.status = "in-progress"
        action_path = self.navigator.get_item_path(action)
        self.project.task_cursor = action_path
        self._save_callback()

    def start_next_action(self) -> Optional[Action]:
        """Start the next pending action.

        If there's an action in progress, returns it.
        Otherwise, finds the next pending action, sets it to 'in-progress',
        and updates the task cursor.

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
            self.project.task_cursor = None
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

        # Cascade completion up the tree
        self._cascade_completion(current_action)

        self._save_callback()
        return current_action

    def _cascade_completion(self, item: BaseItem) -> None:
        """Cascade completion status up the tree when all children are complete.

        When all actions in a deliverable are complete, mark deliverable complete.
        When all deliverables in an objective are complete, mark objective complete.

        Does NOT cascade to milestones or phases to allow adding new children.

        Prints a notification when a parent item is marked complete.

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
            if parent.children:
                all_children_complete = all(
                    a.status == "completed" for a in parent.children
                )
        elif isinstance(item, Deliverable) and isinstance(parent, Objective):
            # Check if all deliverables in objective are complete
            if parent.children:
                all_children_complete = all(
                    d.status == "completed" for d in parent.children
                )

        # If all children are complete, mark parent as complete and continue cascading
        # Only cascade up to objective level (not milestones or phases)
        if all_children_complete and parent.status != "completed":
            parent.status = "completed"
            parent.updated_at = datetime.now()
            click.echo(f"  ✓ {type(parent).__name__} '{parent.name}' marked complete")

            # Continue cascading only if parent is a deliverable (cascade to objective)
            if isinstance(parent, Deliverable):
                self._cascade_completion(parent)

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
                1 for d in item.children if d.status == "completed"
            )
            total_deliverables = len(item.children)

            # Calculate completion for each deliverable's actions
            total_actions = 0
            completed_actions = 0

            for deliverable in item.children:
                for action in deliverable.children:
                    total_actions += 1
                    if action.status == "completed":
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

            completed_actions = sum(1 for a in item.children if a.status == "completed")
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
            True if all deliverables and actions are complete.
        """
        if not objective.children:
            return False

        for deliverable in objective.children:
            if deliverable.status != "completed":
                return False
            for action in deliverable.children:
                if action.status != "completed":
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
            completed_del = sum(1 for d in item.children if d.status == "completed")
            total_act = sum(len(d.children) for d in item.children)
            completed_act = sum(
                sum(1 for a in d.children if a.status == "completed")
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
            completed = sum(1 for a in item.children if a.status == "completed")
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
        max_length = get_slug_max_length()
        word_limit = get_slug_word_limit()
        filler_words = set(get_slug_filler_words())

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
        if status in [COMPLETED_STATUS, ARCHIVED_STATUS]:
            new_item.status = DEFAULT_STATUS
        elif status is not None:
            # Validate status against allowed values
            if status not in VALID_STATUSES:
                raise ValidationError(
                    f"Invalid status: '{status}'. Status must be one of: {', '.join(VALID_STATUSES)}."
                )
            new_item.status = status
        else:
            new_item.status = DEFAULT_STATUS

        return new_item

    # =========================================================================
    # CRUD Operations - Add
    # =========================================================================

    def add_item(
        self,
        item_type: str,
        name: str,
        description: Optional[str],
        parent_path: Optional[str],
        status: Optional[str] = None,
    ) -> BaseItem:
        """Add a new item to the project.

        Args:
            item_type: Type of item to add.
            name: Item name.
            description: Item description.
            parent_path: Path to parent item, or None for phases.
            status: Optional item status.

        Returns:
            The newly created item.

        Raises:
            ValidationError: If item type or status is invalid.
            NotFoundError: If parent item not found.
            InvalidOperationError: If parent-child relationship is invalid.
        """
        # Get sibling items for slug generation
        items_to_check = self._get_sibling_items(parent_path, item_type)

        # Generate unique slug
        slug = self._generate_unique_slug(items_to_check, name)

        # Create the new item
        new_item = self._create_item(item_type, name, description, slug, status)

        # Add to parent or project
        if parent_path:
            parent_item = self.navigator.get_item_by_path(parent_path)
            if not parent_item:
                raise NotFoundError(
                    f"Parent item not found at path: '{parent_path}'. "
                    f"Please verify the path is correct and the parent item exists."
                )

            # Set parent_uuid on the new item
            new_item.parent_uuid = parent_item.uuid

            # Use add_child method which handles type validation
            parent_item.add_child(new_item)
        else:
            if item_type == "phase":
                self.project.phases.append(new_item)

        # Rebuild lookup maps
        self.project.build_maps()

        return new_item

    def _get_parent_items_for_slug_check(self, path: str) -> List[BaseItem]:
        """Helper to get the list of siblings for slug uniqueness check.

        Args:
            path: Path to the item.

        Returns:
            List of sibling items.
        """
        segments = path.split("/")
        if len(segments) == 1:  # Top-level phase
            return self.project.phases

        parent_path = "/".join(segments[:-1])
        parent_item = self.navigator.get_item_by_path(parent_path)

        if parent_item:
            return parent_item.children
        return []

    # =========================================================================
    # CRUD Operations - Update
    # =========================================================================

    def update_item(
        self,
        path: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        due_date: Optional[str] = None,
        status: Optional[str] = None,
    ) -> BaseItem:
        """Update an existing item.

        Args:
            path: Path to the item to update.
            name: Optional new name.
            description: Optional new description.
            due_date: Optional new due date (for actions/deliverables).
            status: Optional new status.

        Returns:
            The updated item.

        Raises:
            NotFoundError: If item not found.
            InvalidOperationError: If item is completed/archived.
            ValidationError: If no update parameters or invalid date format.
        """
        item_to_update = self.navigator.get_item_by_path(path)
        if not item_to_update:
            raise NotFoundError(
                f"Item not found at path: '{path}'. "
                f"Please verify the path is correct and the item exists."
            )

        if item_to_update.status in ["completed", "archived"]:
            raise InvalidOperationError(
                f"Cannot update item '{path}' because it is already in '{item_to_update.status}' status. "
                f"Items in 'completed' or 'archived' status cannot be modified to maintain historical accuracy."
            )

        updated = False
        if name is not None:
            item_to_update.name = name
            # Re-generate slug if name changes
            item_to_update.slug = self._generate_unique_slug(
                self._get_parent_items_for_slug_check(path), name
            )
            updated = True
        if description is not None:
            item_to_update.description = description
            updated = True
        if due_date is not None and isinstance(item_to_update, (Action, Deliverable)):
            parsed_date = parse_date(due_date)
            if parsed_date is None:
                raise ValidationError(DATE_FORMAT_ERROR)

            is_valid, error_msg = validate_date_range(parsed_date)
            if not is_valid:
                raise ValidationError(error_msg)

            item_to_update.due_date = parsed_date
            updated = True
        if status is not None:
            if status not in VALID_STATUSES:
                raise ValidationError(
                    f"Invalid status: '{status}'. Status must be one of: {', '.join(VALID_STATUSES)}."
                )
            item_to_update.status = status
            updated = True

        if updated:
            item_to_update.updated_at = datetime.now()
        else:
            raise ValidationError(
                "No update parameters provided. "
                "Please specify at least one field to update: --name, --desc, --due-date, or --status."
            )

        return item_to_update

    # =========================================================================
    # CRUD Operations - Delete
    # =========================================================================

    def delete_item(self, path: str) -> None:
        """Delete an existing item.

        Args:
            path: Path to the item to delete.

        Raises:
            ValueError: If path is empty.
            NotFoundError: If item not found.
            InvalidOperationError: If item is completed/archived.
        """
        segments = path.split("/")
        if not segments:
            raise ValueError("Path cannot be empty.")

        item_to_delete = self.navigator.get_item_by_path(path)
        if not item_to_delete:
            raise NotFoundError(f"Item not found at path: {path}")

        if item_to_delete.status in ["completed", "archived"]:
            raise InvalidOperationError(
                f"Cannot delete item '{path}' because it is already in '{item_to_delete.status}' status. "
                f"Items in 'completed' or 'archived' status cannot be deleted for record-keeping purposes."
            )

        item_slug_to_delete = segments[-1]
        parent_path = "/".join(segments[:-1]) if len(segments) > 1 else None

        if parent_path:
            parent_item = self.navigator.get_item_by_path(parent_path)
            if not parent_item:
                raise NotFoundError(
                    f"Parent item not found at path: '{parent_path}'. "
                    f"Please verify the path is correct and the parent item exists."
                )

            # Remove from parent's children list
            target_list: Optional[List[BaseItem]] = parent_item.children

            if target_list is not None:
                original_len = len(target_list)
                target_list[:] = [
                    item for item in target_list if item.slug != item_slug_to_delete
                ]

                if len(target_list) == original_len:
                    raise NotFoundError(
                        f"Item with slug '{item_slug_to_delete}' not found under parent '{parent_path}'."
                    )
            else:
                raise InvalidOperationError(
                    f"Cannot delete child from parent of type {type(parent_item).__name__}"
                )
        else:  # Top-level phase deletion
            original_len = len(self.project.phases)
            self.project.phases[:] = [
                phase
                for phase in self.project.phases
                if phase.slug != item_slug_to_delete
            ]
            if len(self.project.phases) == original_len:
                raise NotFoundError(
                    f"Phase with slug '{item_slug_to_delete}' not found."
                )
