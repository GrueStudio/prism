"""
ItemManager for CRUD operations on Prism items.

Handles adding, updating, and deleting strategic and execution items.
"""
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from prism.models import (
    Action,
    BaseItem,
    Deliverable,
    Milestone,
    Objective,
    Phase,
)
from prism.managers.project_manager import Project
from prism.managers.navigation_manager import NavigationManager
from prism.constants import (
    SLUG_MAX_LENGTH,
    VALID_STATUSES,
    COMPLETED_STATUS,
    ARCHIVED_STATUS,
    DEFAULT_STATUS,
    VALIDATION_INVALID_STATUS,
    DATE_FORMAT_ERROR,
    get_slug_max_length,
    get_slug_word_limit,
    get_slug_filler_words,
)
from prism.exceptions import (
    ValidationError,
    NotFoundError,
    InvalidOperationError,
)
from prism.utils import parse_date, validate_date_range


class ItemManager:
    """
    Manages CRUD operations for all Prism items.
    
    Handles:
    - Adding new items (phases, milestones, objectives, deliverables, actions)
    - Updating existing items
    - Deleting items
    - Slug generation with filler word filtering
    """

    def __init__(self, project: Project, navigator: NavigationManager) -> None:
        """
        Initialize ItemManager.

        Args:
            project: Project instance containing all items.
            navigator: NavigationManager instance for path resolution.
        """
        self.project = project
        self.navigator = navigator

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

    def _get_sibling_items(self, parent_path: Optional[str], item_type: str) -> List[BaseItem]:
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
                return parent_item.milestones
            elif item_type == "objective" and isinstance(parent_item, Milestone):
                return parent_item.objectives
            elif item_type == "deliverable" and isinstance(parent_item, Objective):
                return parent_item.deliverables
            elif item_type == "action" and isinstance(parent_item, Deliverable):
                return parent_item.actions
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
                    f"Invalid status: '{status}'. {VALIDATION_INVALID_STATUS}"
                )
            new_item.status = status
        else:
            new_item.status = DEFAULT_STATUS

        return new_item

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

        if isinstance(parent_item, Phase):
            return parent_item.milestones
        elif isinstance(parent_item, Milestone):
            return parent_item.objectives
        elif isinstance(parent_item, Objective):
            return parent_item.deliverables
        elif isinstance(parent_item, Deliverable):
            return parent_item.actions
        return []

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
                    f"Invalid status: '{status}'. {VALIDATION_INVALID_STATUS}"
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
                raise NotFoundError(f"Phase with slug '{item_slug_to_delete}' not found.")
