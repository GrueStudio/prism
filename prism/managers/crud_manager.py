"""
CRUDManager for Prism CLI.

Handles all CRUD operations for strategic and execution items.
"""

import re
from datetime import datetime
from typing import List, Optional

import click

from prism.constants import (
    ARCHIVED_STATUS,
    COMPLETED_STATUS,
    DATE_FORMAT_ERROR,
    DEFAULT_STATUS,
    VALID_STATUSES,
    get_slug_max_length,
    get_slug_word_limit,
)
from prism.exceptions import InvalidOperationError, NotFoundError, ValidationError
from prism.managers.archive_manager import ArchiveManager
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


class CRUDManager:
    """
    Manages CRUD operations for Prism CLI.

    Handles:
    - Adding items (phases, milestones, objectives, deliverables, actions)
    - Updating items (name, description, due_date, status)
    - Deleting items
    - Auto-archive of completed strategic items
    """

    def __init__(
        self,
        project: Project,
        navigator: NavigationManager,
        archive_manager: ArchiveManager,
    ) -> None:
        """
        Initialize CRUDManager.

        Args:
            project: Project instance containing all items.
            navigator: NavigationManager instance for path resolution.
            archive_manager: ArchiveManager instance for archiving completed items.
        """
        self.project = project
        self.navigator = navigator
        self.archive_manager = archive_manager
        self._slug_max_length = get_slug_max_length()
        self._slug_word_limit = get_slug_word_limit()

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

            # Auto-archive completed strategic siblings before adding new item
            if item_type == "objective" and isinstance(parent_item, Milestone):
                self._archive_completed_strategic_siblings(parent_item, "objective")
            elif item_type == "milestone" and isinstance(parent_item, Phase):
                self._archive_completed_strategic_siblings(parent_item, "milestone")

            # Use add_child method which handles type validation
            parent_item.add_child(new_item)
        elif item_type == "phase":
            self.project.add_child(new_item)

        return new_item

    def _archive_completed_strategic_siblings(
        self, parent_item: BaseItem, item_type: str
    ) -> None:
        """Archive completed strategic siblings when adding a new item.

        Only archives items that are:
        - Marked as "completed"
        - Have complete execution trees (for objectives)

        Args:
            parent_item: Parent containing the siblings.
            item_type: Type of items to check ('objective' or 'milestone').
        """
        if not hasattr(parent_item, "children"):
            return

        for child in list(parent_item.children):
            if child.item_type == item_type and child.status == "completed":
                # For objectives, verify execution tree is complete
                if item_type == "objective":
                    if isinstance(
                        child, Objective
                    ) and not self._is_objective_exec_tree_complete(child):
                        continue  # Skip - has pending deliverables/actions

                # Archive this item
                self.archive_manager.archive_strategic_item(child, item_type)
                # Remove from parent's active children
                parent_item.children.remove(child)
                click.echo(f"  ✓ Archived completed {item_type} '{child.name}'")

    def _is_objective_exec_tree_complete(self, objective: Objective) -> bool:
        """Check if an objective's execution tree is complete.

        Args:
            objective: Objective to check.

        Returns:
            True if all deliverables and actions are complete (or empty).
        """
        if not objective.children:
            return True

        for deliverable in objective.children:
            if deliverable.status != "completed":
                return False
            for action in deliverable.children:
                if action.status != "completed":
                    return False

        return True

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

        if item_type == "phase":
            return self.project.phases

        raise ValueError(
            f"Cannot add {item_type} without a parent. "
            "Please specify a parent path or add a phase."
        )

    def _generate_unique_slug(self, existing_items: List[BaseItem], name: str) -> str:
        """Generate a unique slug from name.

        Args:
            existing_items: List of items to check for slug uniqueness.
            name: Name to generate slug from.

        Returns:
            Unique slug string.
        """
        # Generate base slug from name
        slug = self._slugify(name)
        base_slug = slug

        # Check for uniqueness
        existing_slugs = {item.slug for item in existing_items}
        counter = 1

        while slug in existing_slugs:
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    def _slugify(self, text: str) -> str:
        """Convert text to slug format.

        Args:
            text: Text to convert.

        Returns:
            Slug string (lowercase, alphanumeric + hyphens, max length enforced).
        """
        # Convert to lowercase and replace spaces/special chars with hyphens
        slug = text.lower()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        slug = re.sub(r"-+", "-", slug)
        slug = slug.strip("-")

        # Truncate to max length
        if len(slug) > self._slug_max_length:
            slug = slug[: self._slug_max_length]
            # Avoid ending with hyphen
            slug = slug.rstrip("-")

        return slug

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
            ValidationError: If item type or status is invalid.
        """
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
                    f"Invalid status: '{status}'. Status must be one of: {', '.join(VALID_STATUSES)}."
                )
            new_item.status = status
        else:
            new_item.status = DEFAULT_STATUS

        return new_item

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
            siblings = self._get_parent_items_for_slug_check(path)
            item_to_update.slug = self._generate_unique_slug(siblings, name)
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
                raise NotFoundError(f"Parent '{parent_path}' has no children list.")
        else:
            # Deleting a phase
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
