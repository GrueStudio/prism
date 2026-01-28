from typing import List, Optional, Type, Tuple
from pathlib import Path

from prism.models import ProjectData, BaseItem, Phase, Milestone, Objective, Deliverable, Action, to_kebab_case, MAX_SLUG_SIZE
from prism.data_store import DataStore


class Tracker:
    """
    Manages the ProjectData, providing methods for adding, retrieving,
    and manipulating strategic and execution items.
    """
    def __init__(self, data_store: DataStore):
        self.data_store = data_store
        self.project_data = self.data_store.load_project_data()
        self.current_item_path: Optional[str] = None
        self.current_item: Optional[BaseItem] = None

    def _save_project_data(self):
        """Saves the current project_data state to the data store."""
        self.data_store.save_project_data(self.project_data)

    def _get_item_type_from_str(self, item_type_str: str) -> Type[BaseItem]:
        """Returns the Pydantic model class for a given item type string."""
        type_map = {
            "phase": Phase,
            "milestone": Milestone,
            "objective": Objective,
            "deliverable": Deliverable,
            "action": Action,
        }
        item_type_class = type_map.get(item_type_str.lower())
        if not item_type_class:
            raise ValueError(f"Unknown item type: {item_type_str}")
        return item_type_class

    def _generate_unique_slug(self, parent_items: List[BaseItem], base_name: str) -> str:
        """
        Generates a unique slug from a base name, ensuring it doesn't conflict
        with existing slugs in the provided list of parent items.
        """
        base_slug = to_kebab_case(base_name)
        if len(base_slug) == 0:
            raise ValueError("Cannot generate a slug from an empty or invalid base name.")

        existing_slugs = {item.slug for item in parent_items}

        if base_slug not in existing_slugs:
            return base_slug
        
        # If not unique, append a number
        i = 1
        while True:
            suffix = f"-{i}"
            # Ensure the combined slug (base_slug + suffix) doesn't exceed MAX_SLUG_SIZE
            # If base_slug is already MAX_SLUG_SIZE, we need to shorten base_slug
            if len(base_slug) + len(suffix) > MAX_SLUG_SIZE:
                # Truncate base_slug further to make space for the suffix, and ensure it doesn't end with '-'
                adjusted_base_slug = base_slug[:MAX_SLUG_SIZE - len(suffix)]
                if adjusted_base_slug.endswith('-'):
                    adjusted_base_slug = adjusted_base_slug.rstrip('-') # Make sure it's valid kebab-case before adding suffix
                new_slug = adjusted_base_slug + suffix
            else:
                new_slug = base_slug + suffix

            if new_slug not in existing_slugs:
                return new_slug
            i += 1


    def _resolve_path_segment(self, items: List[BaseItem], segment: str) -> Optional[BaseItem]:
        """
        Resolves a single path segment (slug or 1-based index) against a list of items.
        """
        # Try resolving by slug
        for item in items:
            if item.slug == segment:
                return item
        
        # Try resolving by 1-based index
        try:
            index = int(segment)
            if 1 <= index <= len(items):
                return items[index - 1]
        except ValueError:
            pass # Not a valid integer, continue to next check

        return None

    def get_item_by_path(self, path: str) -> Optional[BaseItem]:
        """
        Retrieves an item by its hierarchical path (e.g., "phase-slug.milestone-slug.1").
        """
        segments = path.split('.')
        current_items: List[BaseItem] = self.project_data.phases # Start with top-level phases
        found_item: Optional[BaseItem] = None

        for i, segment in enumerate(segments):

            resolved_item = self._resolve_path_segment(current_items, segment)
            if resolved_item:
                found_item = resolved_item
                # Determine the next list of items to search within
                if isinstance(found_item, Phase):
                    current_items = found_item.milestones
                elif isinstance(found_item, Milestone):
                    current_items = found_item.objectives
                elif isinstance(found_item, Objective):
                    current_items = found_item.deliverables
                elif isinstance(found_item, Deliverable):
                    current_items = found_item.actions
                else: # Action or unknown type, no further children
                    current_items = []
            else:
                # Segment not found at this level
                return None
        return found_item

    def _get_parent_and_siblings(self, item_path: str) -> Tuple[Optional[BaseItem], List[BaseItem], int]:
        """
        Retrieves the parent item, a list of its children (siblings of the item_path),
        and the index of the item_path's corresponding item within the siblings list.
        Returns (parent_item, siblings_list, item_index).
        If item_path refers to a top-level item, parent_item will be None.
        """
        segments = item_path.split('.')
        item_slug_or_index = segments[-1]
        
        if len(segments) == 1:
            # Top-level item (Phase)
            parent_item = None
            siblings = self.project_data.phases
            # Find the index of the item_slug_or_index in siblings
            for i, item in enumerate(siblings):
                if item.slug == item_slug_or_index:
                    return parent_item, siblings, i
            raise ValueError(f"Top-level item with slug or index '{item_slug_or_index}' not found.")
        
        parent_path = ".".join(segments[:-1])
        parent_item = self.get_item_by_path(parent_path)

        if not parent_item:
            raise ValueError(f"Parent item at path '{parent_path}' not found for item: {item_path}")

        siblings: List[BaseItem]
        if isinstance(parent_item, Phase):
            siblings = parent_item.milestones
        elif isinstance(parent_item, Milestone):
            siblings = parent_item.objectives
        elif isinstance(parent_item, Objective):
            siblings = parent_item.deliverables
        elif isinstance(parent_item, Deliverable):
            siblings = parent_item.actions
        else:
            raise TypeError(f"Parent item of unexpected type: {type(parent_item).__name__}")

        # Find the index of the item_slug_or_index in siblings
        for i, item in enumerate(siblings):
            if item.slug == item_slug_or_index:
                return parent_item, siblings, i
        
        # If not found by slug, try by 1-based index
        try:
            index = int(item_slug_or_index)
            if 1 <= index <= len(siblings):
                return parent_item, siblings, index - 1
        except ValueError:
            pass
        
        raise ValueError(f"Item with slug or index '{item_slug_or_index}' not found in parent path '{parent_path}'.")

    def _get_children(self, item: BaseItem) -> List[BaseItem]:
        """Helper to get children of a given item."""
        if isinstance(item, Phase):
            return item.milestones
        elif isinstance(item, Milestone):
            return item.objectives
        elif isinstance(item, Objective):
            return item.deliverables
        elif isinstance(item, Deliverable):
            return item.actions
        return []

    def _find_next_item_depth_first(self) -> Optional[Tuple[BaseItem, str]]:
        """
        Finds the next item in a depth-first traversal starting from the current_item.
        Returns a tuple of (next_item, next_item_path) or None if no next item.
        """
        if not self.current_item or not self.current_item_path:
            # If no current item, start from the very beginning (first phase)
            if self.project_data.phases:
                first_phase = self.project_data.phases[0]
                return first_phase, first_phase.slug
            return None

        current_item = self.current_item
        current_path = self.current_item_path

        # 1. Try to go deeper (children)
        children = self._get_children(current_item)
        if children:
            first_child = children[0]
            return first_child, f"{current_path}.{first_child.slug}"

        # 2. Try to go to the next sibling
        # Need to know parent and index among siblings
        
        # This handles top-level phases as well where parent_path_for_current_item would be empty
        parent_item, siblings, item_index = self._get_parent_and_siblings(current_path)

        if item_index < len(siblings) - 1:
            next_sibling = siblings[item_index + 1]
            parent_path_segments = current_path.split('.')[:-1]
            next_path = ".".join(parent_path_segments + [next_sibling.slug])
            return next_sibling, next_path

        # 3. No children and no next sibling, go up to parent's next sibling
        # This loop continues until a next item is found or we exhaust all parents
        temp_path = current_path
        while True:
            parent_segments = temp_path.split('.')[:-1]
            if not parent_segments:
                # We are at a top-level phase that was the last sibling, or there are no phases left
                return None
            
            parent_path = ".".join(parent_segments)
            parent_of_parent, parent_siblings, parent_index = self._get_parent_and_siblings(parent_path)

            if parent_index < len(parent_siblings) - 1:
                next_parent_sibling = parent_siblings[parent_index + 1]
                # Reconstruct the path for the next parent sibling
                next_item_path_segments = parent_path.split('.')[:-1] + [next_parent_sibling.slug]
                next_item_path = ".".join(next_item_path_segments)
                return next_parent_sibling, next_item_path
            
            temp_path = parent_path # Move up the hierarchy


    def _get_deepest_descendant(self, item: BaseItem, item_path: str) -> Tuple[BaseItem, str]:
        """
        Helper to find the deepest, rightmost descendant of an item.
        Used for finding the "previous" item in depth-first traversal.
        """
        current = item
        current_path = item_path
        
        while True:
            children = self._get_children(current)
            if not children:
                break
            last_child = children[-1]
            current = last_child
            current_path = f"{current_path}.{last_child.slug}"
        return current, current_path


    def _find_previous_item_depth_first(self) -> Optional[Tuple[BaseItem, str]]:
        """
        Finds the previous item in a depth-first traversal starting from the current_item.
        Returns a tuple of (previous_item, previous_item_path) or None if no previous item.
        """
        if not self.current_item or not self.current_item_path:
            return None # Cannot go back if no current item

        current_item = self.current_item
        current_path = self.current_item_path

        # 1. Try to go to the previous sibling's deepest descendant
        parent_item, siblings, item_index = self._get_parent_and_siblings(current_path)

        if item_index > 0:
            previous_sibling = siblings[item_index - 1]
            parent_path_segments = current_path.split('.')[:-1]
            previous_sibling_path = ".".join(parent_path_segments + [previous_sibling.slug])
            
            # The previous item is the deepest descendant of the previous sibling
            return self._get_deepest_descendant(previous_sibling, previous_sibling_path)
        
        # 2. If no previous sibling, the previous item is the parent
        if parent_item:
            parent_path = ".".join(current_path.split('.')[:-1])
            return parent_item, parent_path
        
        # 3. If no previous sibling and no parent (i.e., first top-level item)
        return None

    def add_item(
        self,
        parent_path: Optional[str],
        item_type_str: str,
        name: str,
        description: Optional[str] = None
    ) -> BaseItem:
        """
        Adds a new item (phase, milestone, objective, deliverable, action)
        to the project data.
        """
        item_class = self._get_item_type_from_str(item_type_str)
        new_item: BaseItem

        if item_type_str.lower() == "phase":
            if parent_path:
                raise ValueError("Phases cannot have parent items. They are top-level items.")
            # Phases are top-level items
            existing_phases = self.project_data.phases
            slug = self._generate_unique_slug(existing_phases, name)
            new_item = Phase(name=name, description=description, slug=slug)
            existing_phases.append(new_item)
            # If it's the first phase, make it current
            if len(existing_phases) == 1:
                new_item.current = True
        else:
            if not parent_path:
                raise ValueError(f"Parent path is required for {item_type_str}s.")
            
            parent_item = self.get_item_by_path(parent_path)
            if not parent_item:
                raise ValueError(f"Parent item at path '{parent_path}' not found.")

            target_list: List[BaseItem]
            if isinstance(parent_item, Phase) and item_type_str.lower() == "milestone":
                target_list = parent_item.milestones
            elif isinstance(parent_item, Milestone) and item_type_str.lower() == "objective":
                target_list = parent_item.objectives
            elif isinstance(parent_item, Objective) and item_type_str.lower() == "deliverable":
                target_list = parent_item.deliverables
            elif isinstance(parent_item, Deliverable) and item_type_str.lower() == "action":
                target_list = parent_item.actions
            else:
                raise ValueError(f"Cannot add {item_type_str} to parent type {type(parent_item).__name__}.")
            
            # Generate unique slug within the target list
            slug = self._generate_unique_slug(target_list, name)
            new_item = item_class(name=name, description=description, slug=slug)
            target_list.append(new_item)
        
        self._save_project_data()
        return new_item

    def set_current_item(self, path: str):
        """
        Sets the current item in the tracker based on the provided path.
        """
        item = self.get_item_by_path(path)
        if item:
            self.current_item_path = path
            self.current_item = item
        else:
            raise ValueError(f"No item found at path: {path}")

    def next_item(self) -> Optional[BaseItem]:
        """
        Moves the current item to the next item in a depth-first traversal.
        Returns the new current item, or None if at the end of the tree.
        """
        next_item_data = self._find_next_item_depth_first()
        if next_item_data:
            self.current_item, self.current_item_path = next_item_data
            return self.current_item
        else: # No next item found, reset current position
            self.current_item = None
            self.current_item_path = None
            return None

    def previous_item(self) -> Optional[BaseItem]:
        """
        Moves the current item to the previous item in a depth-first traversal.
        Returns the new current item, or None if at the beginning of the tree.
        """
        previous_item_data = self._find_previous_item_depth_first()
        if previous_item_data:
            self.current_item, self.current_item_path = previous_item_data
            return self.current_item
        else: # No previous item found, reset current position
            self.current_item = None
            self.current_item_path = None
            return None