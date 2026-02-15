import re  # Import re for slug generation
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from prism.models import (
    Action,
    BaseItem,
    Deliverable,
    Milestone,
    Objective,
    Phase,
    ProjectData,
)
from prism.data_store import DataStore


class Tracker:
    def __init__(self, project_file: Optional[Path] = None):
        self.data_store = DataStore(project_file)
        self.project_data = self.data_store.load_project_data()

    def _save_project_data(self):
        self.data_store.save_project_data(self.project_data)

    def _generate_unique_slug(
        self, existing_items: List[BaseItem], base_name: str
    ) -> str:
        base_slug = re.sub(r"[^a-z0-9]+", "-", base_name.lower()).strip("-")[:15]
        if not base_slug:
            base_slug = "item"

        existing_slugs = {item.slug for item in existing_items}

        slug = base_slug
        count = 1
        while slug in existing_slugs:
            slug = (
                f"{base_slug[: (15 - len(str(count)) - 1)]}-{count}"
                if len(base_slug) > (15 - len(str(count)) - 1)
                else f"{base_slug}-{count}"
            )
            count += 1
        return slug

    def get_status_summary(
        self, phase_path: Optional[str] = None, milestone_path: Optional[str] = None
    ) -> Dict[str, Any]:
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
            milestone = self.get_item_by_path(milestone_path)
            if milestone and isinstance(milestone, Milestone):
                start_items = [milestone]
                start_path = milestone_path
            else:
                return summary  # Return empty if not found
        elif phase_path:
            phase = self.get_item_by_path(phase_path)
            if phase and isinstance(phase, Phase):
                start_items = [phase]
                start_path = phase_path
            else:
                return summary  # Return empty if not found
        else:
            start_items = self.project_data.phases

        _traverse(start_items, parent_path=start_path)
        return summary

    def _resolve_path_segment(
        self, items: List[BaseItem], segment: str
    ) -> Optional[BaseItem]:
        # Try to match by slug
        for item in items:
            if item.slug == segment:
                return item

        # Try to match by index (e.g., "milestones/1")
        try:
            index = int(segment) - 1
            if 0 <= index < len(items):
                return items[index]
        except ValueError:
            pass  # Not an integer, continue

        return None

    def get_item_by_path(self, path: str) -> Optional[BaseItem]:
        segments = path.split("/")
        current_items: List[BaseItem] = list(self.project_data.phases)

        target_item: Optional[BaseItem] = None

        for i, segment in enumerate(segments):
            found_item = self._resolve_path_segment(current_items, segment)
            if not found_item:
                return None

            target_item = found_item

            if (
                i < len(segments) - 1
            ):  # If not the last segment, update current_items for next iteration
                if isinstance(found_item, Phase):
                    current_items = list(found_item.milestones)
                elif isinstance(found_item, Milestone):
                    current_items = list(found_item.objectives)
                elif isinstance(found_item, Objective):
                    current_items = list(found_item.deliverables)
                elif isinstance(found_item, Deliverable):
                    current_items = list(found_item.actions)
                else:
                    return None  # No children for this item type

        return target_item

    def add_item(
        self,
        item_type: str,
        name: str,
        description: Optional[str],
        parent_path: Optional[str],
        status: Optional[str] = None,
    ):
        # Validate item_type
        if item_type not in [
            "phase",
            "milestone",
            "objective",
            "deliverable",
            "action",
        ]:
            raise ValueError(f"Invalid item type: {item_type}")

        # Determine the list of items to check for slug uniqueness
        items_to_check: List[BaseItem]
        if parent_path:
            parent_item = self.get_item_by_path(parent_path)
            if not parent_item:
                raise ValueError(f"Parent item not found at path: {parent_path}")

            if item_type == "milestone" and isinstance(parent_item, Phase):
                items_to_check = parent_item.milestones
            elif item_type == "objective" and isinstance(parent_item, Milestone):
                items_to_check = parent_item.objectives
            elif item_type == "deliverable" and isinstance(parent_item, Objective):
                items_to_check = parent_item.deliverables
            elif item_type == "action" and isinstance(parent_item, Deliverable):
                items_to_check = parent_item.actions
            else:
                raise ValueError(
                    f"Cannot add {item_type} to parent of type {type(parent_item).__name__}"
                )
        else:
            if item_type == "phase":
                items_to_check = self.project_data.phases
            else:
                raise ValueError(f"Cannot add {item_type} without a parent path.")

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
            raise ValueError("Unsupported item type during instantiation.")

        # Enforce business rule: new items cannot be created as "completed" or "archived"
        if status in ["completed", "archived"]:
            new_item.status = "pending"
        elif status is not None:
            new_item.status = status
        else:
            new_item.status = "pending"  # Default to pending if no status is provided

        if parent_path:
            # Re-fetch parent_item as it might have been modified by adding slug
            parent_item = self.get_item_by_path(parent_path)
            if not parent_item:  # Should not happen if it was found before
                raise ValueError(f"Parent item not found at path: {parent_path}")

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
        item_to_update = self.get_item_by_path(path)
        if not item_to_update:
            raise ValueError(f"Item not found at path: {path}")

        if item_to_update.status in ["completed", "archived"]:
            raise ValueError(
                f"Cannot update item '{path}' because it is already in '{item_to_update.status}' status."
            )

        updated = False
        if name is not None:
            item_to_update.name = name
            # Re-generate slug if name changes and it's not explicitly set
            if not isinstance(
                item_to_update, Action
            ):  # Action slugs are derived from name but can't be changed by edit name
                item_to_update.slug = self._generate_unique_slug(
                    self._get_parent_items_for_slug_check(path), name
                )
            updated = True
        if description is not None:
            item_to_update.description = description
            updated = True
        if due_date is not None and isinstance(item_to_update, (Action, Deliverable)):
            try:
                item_to_update.due_date = datetime.strptime(due_date, "%Y-%m-%d")
                updated = True
            except ValueError:
                raise ValueError(
                    f"Invalid date format for due_date: {due_date}. Expected YYYY-MM-DD."
                )

        # Status update is not allowed from here as per deliverable
        # if status is not None:
        #     item_to_update.status = status
        #     updated = True

        if updated:
            item_to_update.updated_at = datetime.now()
            self._save_project_data()
        else:
            raise ValueError("No update parameters provided.")

    def _get_parent_items_for_slug_check(self, path: str) -> List[BaseItem]:
        # Helper to get the list of siblings for slug uniqueness check
        segments = path.split("/")
        if len(segments) == 1:  # Top-level phase
            return self.project_data.phases

        parent_path = "/".join(segments[:-1])
        parent_item = self.get_item_by_path(parent_path)

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
        # Find the item and its parent
        segments = path.split("/")
        if not segments:
            raise ValueError("Path cannot be empty.")

        item_to_delete = self.get_item_by_path(path)
        if not item_to_delete:
            raise ValueError(f"Item not found at path: {path}")

        if item_to_delete.status in ["completed", "archived"]:
            raise ValueError(
                f"Cannot delete item '{path}' because it is already in '{item_to_delete.status}' status."
            )

        item_slug_to_delete = segments[-1]
        parent_path = "/".join(segments[:-1]) if len(segments) > 1 else None

        if parent_path:
            parent_item = self.get_item_by_path(parent_path)
            if not parent_item:
                raise ValueError(f"Parent item not found at path: {parent_path}")

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
        For now, this is a placeholder and always returns True.
        """
        objective = self.get_item_by_path(objective_path)
        if not isinstance(objective, Objective):
            return False  # Or raise an error, depending on desired strictness

        # Placeholder logic: An objective's exec tree is "complete" if it has at least one deliverable
        # In the future, this would check if all deliverables have actions, and if all actions are 'completed', etc.
        return len(objective.deliverables) > 0

    def get_current_objective(self) -> Optional[Objective]:
        """Finds the most recently created objective that is not completed or archived."""
        current_objective = None
        for phase in self.project_data.phases:
            for milestone in phase.milestones:
                for objective in milestone.objectives:
                    if objective.status not in ["completed", "archived"]:
                        if (
                            current_objective is None
                            or objective.created_at > current_objective.created_at
                        ):
                            current_objective = objective
        return current_objective

    def get_item_path(self, item_to_find: BaseItem) -> Optional[str]:
        """Recursively finds the path of a given item."""

        def _traverse(items: List[BaseItem], current_path: str) -> Optional[str]:
            for item in items:
                path = f"{current_path}/{item.slug}" if current_path else item.slug
                if item is item_to_find:
                    return path

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
                    found_path = _traverse(children, path)
                    if found_path:
                        return found_path
            return None

        return _traverse(self.project_data.phases, "")

    def get_current_action(self) -> Optional[Action]:
        """Gets the action currently referenced by the cursor."""
        if not self.project_data.cursor:
            return None
        item = self.get_item_by_path(self.project_data.cursor)
        if isinstance(item, Action):
            return item
        return None

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
        current_objective = self.get_current_objective()
        if not current_objective:
            self.project_data.cursor = None
            self._save_project_data()
            return None

        next_pending_action = None
        for deliverable in current_objective.deliverables:
            if deliverable.status != "completed":
                for action in deliverable.actions:
                    if action.status == "pending":
                        next_pending_action = action
                        break
            if next_pending_action:
                break
        
        if next_pending_action:
            next_pending_action.status = "in-progress"
            action_path = self.get_item_path(next_pending_action)
            self.project_data.cursor = action_path
        else:
            self.project_data.cursor = None

        self._save_project_data()
        return next_pending_action
    
    def complete_current_action(self) -> Optional[Action]:
        """Completes the current action and advances the cursor by finding the next pending action."""
        current_action = self.get_current_action()
        if not current_action or current_action.status != "in-progress":
            return None  # Or raise an error if no action is in progress

        current_action.status = "completed"
        current_action.updated_at = datetime.now()
        
        # Now find the next action and update the cursor
        self.start_next_action()
        
        self._save_project_data()
        return current_action


    def add_exec_tree(self, tree_data: List[Dict[str, Any]], mode: str):
        """
        Adds an execution tree (objectives, deliverables, actions) from a list of dicts.
        The tree_data is expected to be a list of objective-like dictionaries with nested
        deliverables and actions, following the simplified structure.
        """
        current_objective = self.get_current_objective()
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
                raise ValueError("Deliverable name is required in addtree input.")

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
                    raise ValueError("Action name is required in addtree input.")

                action_slug = self._generate_unique_slug(
                    new_deliverable.actions, act_name
                )
                new_action = Action(
                    name=act_name, description=act_desc, slug=action_slug
                )
                new_deliverable.actions.append(new_action)

            current_objective.deliverables.append(new_deliverable)

        self._save_project_data()
