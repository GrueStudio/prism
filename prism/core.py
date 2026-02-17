"""
Core business logic for the Prism CLI.
This class handles all business operations like adding, deleting, updating items.
"""
import json
import re  # Import re for slug generation
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import click

from prism.models import (
    Action,
    BaseItem,
    Deliverable,
    Milestone,
    Objective,
    Phase,
    ProjectData,
)
from prism.navigator import Navigator
from prism.data_store import DataStore
from prism.constants import SLUG_MAX_LENGTH
from prism.exceptions import (
    PrismError,
    ValidationError,
    NotFoundError,
    InvalidOperationError,
    DuplicateError,
)
from prism.constants import (
    SLUG_MAX_LENGTH,
    VALID_STATUSES,
    COMPLETED_STATUS,
    ARCHIVED_STATUS,
    DATE_FORMAT_ERROR,
    DEFAULT_STATUS,
    VALIDATION_INVALID_STATUS,
    get_slug_max_length,
    get_slug_word_limit,
    get_slug_filler_words,
)
from prism.utils import parse_date, validate_date_range


class Core:
    """
    Core class for business logic operations.
    Handles adding, deleting, updating items and other business logic.
    """
    
    def __init__(self, project_file: Optional[Path] = None):
        """
        Initialize the Core with a project file.
        
        Args:
            project_file: Path to the project file
        """
        self.data_store = DataStore(project_file)
        self.project_data = self.data_store.load_project_data()
        self.navigator = Navigator(self.project_data)

    def _save_project_data(self):
        """Save the project data to the data store."""
        self.data_store.save_project_data(self.project_data)

    def _generate_unique_slug(
        self, existing_items: List[BaseItem], base_name: str
    ) -> str:
        """Generate a unique slug for an item.
        
        Uses configurable word limit and filler word filtering.
        """
        # Get config values
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

    def add_item(
        self,
        item_type: str,
        name: str,
        description: Optional[str],
        parent_path: Optional[str],
        status: Optional[str] = None,
    ):
        """Add a new item to the project."""
        # Validate item_type
        if item_type not in [
            "phase",
            "milestone",
            "objective",
            "deliverable",
            "action",
        ]:
            raise ValidationError(
                f"Invalid item type: '{item_type}'. "
                f"Valid types are: phase, milestone, objective, deliverable, action."
            )

        # Determine the list of items to check for slug uniqueness
        items_to_check: List[BaseItem]
        if parent_path:
            parent_item = self.navigator.get_item_by_path(parent_path)
            if not parent_item:
                raise NotFoundError(
                    f"Parent item not found at path: '{parent_path}'. "
                    f"Please verify the path is correct and the parent item exists."
                )

            if item_type == "milestone" and isinstance(parent_item, Phase):
                items_to_check = parent_item.milestones
            elif item_type == "objective" and isinstance(parent_item, Milestone):
                items_to_check = parent_item.objectives
            elif item_type == "deliverable" and isinstance(parent_item, Objective):
                items_to_check = parent_item.deliverables
            elif item_type == "action" and isinstance(parent_item, Deliverable):
                items_to_check = parent_item.actions
            else:
                raise InvalidOperationError(
                    f"Cannot add {item_type} to parent of type {type(parent_item).__name__}. "
                    f"Valid parent-child relationships are: phase->milestone, milestone->objective, "
                    f"objective->deliverable, deliverable->action."
                )
        else:
            if item_type == "phase":
                items_to_check = self.project_data.phases
            else:
                raise ValueError(f"Cannot add {item_type} without a parent path. Only phases can be added at the top level.")

        slug = self._generate_unique_slug(items_to_check, name)

        new_item: BaseItem
        if item_type == "phase":
            new_item = Phase(name=name, description=description, slug=slug)
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
                    f"Invalid status: '{status}'. {VALIDATION_INVALID_STATUS}"
                )
            new_item.status = status
        else:
            new_item.status = DEFAULT_STATUS

        if parent_path:
            # Re-fetch parent_item as it might have been modified by adding slug
            parent_item = self.navigator.get_item_by_path(parent_path)
            if not parent_item:  # Should not happen if it was found before
                raise ValueError(f"Parent item not found at path: '{parent_path}'. Please verify the path is correct and the parent item exists.")

            if item_type == "milestone" and isinstance(parent_item, Phase):
                parent_item.milestones.append(new_item)
            elif item_type == "objective" and isinstance(parent_item, Milestone):
                parent_item.objectives.append(new_item)
            elif item_type == "deliverable" and isinstance(parent_item, Objective):
                parent_item.deliverables.append(new_item)
            elif item_type == "action" and isinstance(parent_item, Deliverable):
                parent_item.actions.append(new_item)
        else:
            if item_type == "phase":
                self.project_data.phases.append(new_item)

        self._save_project_data()

    def update_item(
        self,
        path: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        due_date: Optional[str] = None,
        status: Optional[str] = None,
    ):
        """Update an existing item."""
        item_to_update = self.navigator.get_item_by_path(path)
        if not item_to_update:
            raise NotFoundError(f"Item not found at path: '{path}'. Please verify the path is correct and the item exists.")

        if item_to_update.status in ["completed", "archived"]:
            raise InvalidOperationError(
                f"Cannot update item '{path}' because it is already in '{item_to_update.status}' status. "
                f"Items in 'completed' or 'archived' status cannot be modified to maintain historical accuracy."
            )

        updated = False
        if name is not None:
            item_to_update.name = name
            # Re-generate slug if name changes and it's not explicitly set
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

        if updated:
            item_to_update.updated_at = datetime.now()
            self._save_project_data()
        else:
            raise ValidationError(
                "No update parameters provided. Please specify at least one field to update: --name, --desc, or --due-date."
            )

    def _get_parent_items_for_slug_check(self, path: str) -> List[BaseItem]:
        """Helper to get the list of siblings for slug uniqueness check."""
        segments = path.split("/")
        if len(segments) == 1:  # Top-level phase
            return self.project_data.phases

        parent_path = "/".join(segments[:-1])
        parent_item = self.navigator.get_item_by_path(parent_path)

        if isinstance(parent_item, Phase):
            return parent_item.milestones
        elif isinstance(parent_item, Milestone):
            return parent_item.objectives
        elif isinstance(parent_item, Objective):
            return parent_item.deliverables
        elif isinstance(parent_item, Deliverable):
            return parent_item.actions
        return []

    def delete_item(self, path: str):
        """Delete an existing item."""
        # Find the item and its parent
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
                raise ValueError(f"Parent item not found at path: '{parent_path}'. Please verify the path is correct and the parent item exists.")

            # Determine the list of children to remove from
            target_list: Optional[List[BaseItem]] = None
            if isinstance(parent_item, Phase):
                target_list = parent_item.milestones
            elif isinstance(parent_item, Milestone):
                target_list = parent_item.objectives
            elif isinstance(parent_item, Objective):
                target_list = parent_item.deliverables
            elif isinstance(parent_item, Deliverable):
                target_list = parent_item.actions

            if target_list is not None:
                original_len = len(target_list)
                target_list[:] = [
                    item for item in target_list if item.slug != item_slug_to_delete
                ]

                if len(target_list) == original_len:
                    raise ValueError(
                        f"Item with slug '{item_slug_to_delete}' not found under parent '{parent_path}'."
                    )
            else:
                raise ValueError(
                    f"Cannot delete child from parent of type {type(parent_item).__name__}"
                )
        else:  # Top-level phase deletion
            original_len = len(self.project_data.phases)
            self.project_data.phases[:] = [
                phase
                for phase in self.project_data.phases
                if phase.slug != item_slug_to_delete
            ]
            if len(self.project_data.phases) == original_len:
                raise ValueError(f"Phase with slug '{item_slug_to_delete}' not found.")

        self._save_project_data()

    def is_exec_tree_complete(self, objective_path: str) -> bool:
        """
        Checks if the execution tree (deliverables and actions) for a given objective is complete.
        """
        objective = self.navigator.get_item_by_path(objective_path)
        if not isinstance(objective, Objective):
            return False  # Or raise an error, depending on desired strictness

        # Placeholder logic: An objective's exec tree is "complete" if it has at least one deliverable
        # In the future, this would check if all deliverables have actions, and if all actions are 'completed', etc.
        return len(objective.deliverables) > 0

    def get_current_action(self) -> Optional[Action]:
        """Gets the action currently referenced by the cursor."""
        if not self.project_data.cursor:
            return None
        item = self.navigator.get_item_by_path(self.project_data.cursor)
        if isinstance(item, Action):
            return item
        return None

    def _find_next_pending_action_in_deliverable(self, deliverable: Deliverable) -> Optional[Action]:
        """Find the next pending action within a specific deliverable."""
        for action in deliverable.actions:
            if action.status == "pending":
                return action
        return None

    def _find_next_pending_action_in_objective(self, objective: Objective) -> Optional[Action]:
        """Find the next pending action within an objective, prioritizing current deliverable."""
        # First, try to find pending actions in non-completed deliverables
        for deliverable in objective.deliverables:
            if deliverable.status != "completed":
                pending_action = self._find_next_pending_action_in_deliverable(deliverable)
                if pending_action:
                    return pending_action
        return None

    def _find_next_pending_action(self) -> Optional[Action]:
        """Find the next pending action across the current objective."""
        current_objective = self.navigator.get_current_objective()
        if not current_objective:
            return None
        
        return self._find_next_pending_action_in_objective(current_objective)

    def _start_action(self, action: Action) -> None:
        """Mark an action as in-progress and update the cursor."""
        action.status = "in-progress"
        action_path = self.navigator.get_item_path(action)
        self.project_data.cursor = action_path
        self._save_project_data()

    def start_next_action(self) -> Optional[Action]:
        """
        If there's an action in progress, returns it.
        Otherwise, finds the next pending action, sets it to 'in-progress', and updates the cursor.
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
            self.project_data.cursor = None
            self._save_project_data()

        return next_pending_action

    def complete_current_action(self) -> Optional[Action]:
        """Completes the current action without advancing to the next one."""
        current_action = self.get_current_action()
        if not current_action or current_action.status != "in-progress":
            return None

        current_action.status = "completed"
        current_action.updated_at = datetime.now()
        
        # Cascade completion up the tree
        self._cascade_completion(current_action)
        
        self._save_project_data()
        return current_action

    def _cascade_completion(self, item: BaseItem) -> None:
        """Cascade completion status up the tree when all children are complete.
        
        When all actions in a deliverable are complete, mark deliverable complete.
        When all deliverables in an objective are complete, mark objective complete.
        
        Does NOT cascade to milestones or phases to allow adding new children.
        
        Prints a notification when a parent item is marked complete.
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
            # Only cascade if deliverable has actions and all are complete
            if parent.actions:
                all_children_complete = all(a.status == "completed" for a in parent.actions)
        elif isinstance(item, Deliverable) and isinstance(parent, Objective):
            # Check if all deliverables in objective are complete
            if parent.deliverables:
                all_children_complete = all(d.status == "completed" for d in parent.deliverables)
        
        # If all children are complete, mark parent as complete and continue cascading
        # Only cascade up to objective level (not milestones or phases)
        if all_children_complete and parent.status != "completed":
            parent.status = "completed"
            parent.updated_at = datetime.now()
            click.echo(f"  ✓ {type(parent).__name__} '{parent.name}' marked complete")
            
            # Continue cascading only if parent is a deliverable (cascade to objective)
            if isinstance(parent, Deliverable):
                self._cascade_completion(parent)

    def complete_current_and_start_next(self) -> tuple[Optional[Action], Optional[Action]]:
        """Completes the current action and starts the next pending one.
        
        Returns:
            Tuple of (completed_action, next_action)
        """
        completed_action = self.complete_current_action()
        if not completed_action:
            return (None, None)
        
        next_action = self.start_next_action()
        return (completed_action, next_action)

    def add_exec_tree(self, tree_data: List[Dict[str, Any]], mode: str):
        """
        Adds an execution tree (objectives, deliverables, actions) from a list of dicts.
        """
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

            deliverable_slug = self._generate_unique_slug(
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

                action_slug = self._generate_unique_slug(
                    new_deliverable.actions, act_name
                )
                new_action = Action(
                    name=act_name, description=act_desc, slug=action_slug
                )
                new_deliverable.actions.append(new_action)

            current_objective.deliverables.append(new_deliverable)

        self._save_project_data()

    def get_status_summary(
        self, phase_path: Optional[str] = None, milestone_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a summary of project status.
        
        Args:
            phase_path: Optional path to filter by specific phase
            milestone_path: Optional path to filter by specific milestone
            
        Returns:
            Dictionary containing status summary
        """
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

        def _traverse(
            items: List[BaseItem],
            parent_path: str = "",
            parent_is_completed: bool = False,
        ):
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

        start_items: List[BaseItem] = []
        start_path = ""
        if milestone_path:
            milestone = self.navigator.get_item_by_path(milestone_path)
            if milestone and isinstance(milestone, Milestone):
                start_items = [milestone]
                start_path = milestone_path
            else:
                return summary  # Return empty if not found
        elif phase_path:
            phase = self.navigator.get_item_by_path(phase_path)
            if phase and isinstance(phase, Phase):
                start_items = [phase]
                start_path = phase_path
            else:
                return summary  # Return empty if not found
        else:
            start_items = self.project_data.phases

        _traverse(start_items, parent_path=start_path)
        return summary

    def get_current_strategic_items(self) -> Dict[str, Optional[BaseItem]]:
        """Returns the current phase, milestone, and objective based on the current action cursor."""
        current_action = self.get_current_action()
        if not current_action:
            # If no current action, return the current objective and its parents
            current_objective = self.navigator.get_current_objective()
            if not current_objective:
                return {"phase": None, "milestone": None, "objective": None}
            
            # Find the parent milestone and phase for the current objective
            for phase in self.project_data.phases:
                for milestone in phase.milestones:
                    if current_objective in milestone.objectives:
                        return {
                            "phase": phase,
                            "milestone": milestone,
                            "objective": current_objective
                        }
            return {"phase": None, "milestone": None, "objective": current_objective}
        
        # If there's a current action, trace back to find its parent items
        action_path = self.navigator.get_item_path(current_action)
        if not action_path:
            return {"phase": None, "milestone": None, "objective": None}
        
        path_segments = action_path.split('/')
        if len(path_segments) >= 3:  # At least phase/milestone/objective
            try:
                phase_path = path_segments[0]
                milestone_path = f"{path_segments[0]}/{path_segments[1]}"
                objective_path = f"{path_segments[0]}/{path_segments[1]}/{path_segments[2]}"
                
                return {
                    "phase": self.navigator.get_item_by_path(phase_path),
                    "milestone": self.navigator.get_item_by_path(milestone_path),
                    "objective": self.navigator.get_item_by_path(objective_path)
                }
            except (NotFoundError, KeyError, TypeError):
                # Log the exception for debugging but return None values to maintain functionality
                return {"phase": None, "milestone": None, "objective": None}
        
        return {"phase": None, "milestone": None, "objective": None}

    def calculate_completion_percentage(self, item: BaseItem) -> Dict[str, float]:
        """Calculates completion percentage for objectives and deliverables."""
        if isinstance(item, Objective):
            if len(item.deliverables) == 0:
                return {"overall": 0.0, "by_type": {"deliverables": 0.0}}
            
            completed_deliverables = sum(1 for d in item.deliverables if d.status == "completed")
            total_deliverables = len(item.deliverables)
            
            # Calculate completion for each deliverable's actions
            total_actions = 0
            completed_actions = 0
            
            for deliverable in item.deliverables:
                for action in deliverable.actions:
                    total_actions += 1
                    if action.status == "completed":
                        completed_actions += 1
            
            return {
                "overall": round((completed_deliverables / total_deliverables) * 100, 1) if total_deliverables > 0 else 0.0,
                "by_type": {
                    "deliverables": round((completed_deliverables / total_deliverables) * 100, 1) if total_deliverables > 0 else 0.0,
                    "actions": round((completed_actions / total_actions) * 100, 1) if total_actions > 0 else 0.0
                }
            }
        
        elif isinstance(item, Deliverable):
            if len(item.actions) == 0:
                return {"overall": 0.0}
            
            completed_actions = sum(1 for a in item.actions if a.status == "completed")
            total_actions = len(item.actions)
            
            return {
                "overall": round((completed_actions / total_actions) * 100, 1),
                "by_type": {"actions": round((completed_actions / total_actions) * 100, 1)}
            }
        
        return {"overall": 0.0}