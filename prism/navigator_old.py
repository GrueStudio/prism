"""
DEPRECATED: Old Prism Navigator using project.json storage.

This module is deprecated and will be removed in a future version.
Use prism.managers.NavigationManager with .prism/ folder-based storage instead.
"""
import warnings
warnings.warn(
    "Old Navigator (project.json storage) is deprecated. "
    "Use prism.managers.NavigationManager with .prism/ storage instead.",
    DeprecationWarning,
    stacklevel=2
)

"""
Navigation and path resolution for the Prism CLI.
This class handles all tree traversal, path resolution, and navigation logic.
"""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from prism.models_old import (
    Action,
    BaseItem,
    Deliverable,
    Milestone,
    Objective,
    Phase,
    ProjectData,
)


class Navigator:
    """
    Navigation class for tree navigation and path resolution operations.
    Handles all tree traversal, path resolution, and navigation logic.
    """
    
    def __init__(self, project_data: ProjectData):
        """
        Initialize the Navigator with project data.
        
        Args:
            project_data: The project data to operate on
        """
        self.project_data = project_data

    def _resolve_path_segment(
        self, items: List[BaseItem], segment: str
    ) -> Optional[BaseItem]:
        """
        Resolve a path segment to a specific item.
        
        Args:
            items: List of items to search in
            segment: The segment to resolve (either slug or index)
            
        Returns:
            The matching BaseItem or None if not found
        """
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
        """
        Get an item by its path.
        
        Args:
            path: The path to the item (e.g., "phase/milestone/objective/deliverable/action")
            
        Returns:
            The matching BaseItem or None if not found
        """
        if not path:
            return None
            
        try:
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
        except Exception:
            # Log the exception but return None to maintain functionality
            return None

    def get_item_path(self, item_to_find: BaseItem) -> Optional[str]:
        """
        Recursively find the path of a given item.
        
        Args:
            item_to_find: The item to find the path for
            
        Returns:
            The path string or None if not found
        """
        try:
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
        except Exception:
            # Log the exception but return None to maintain functionality
            return None

    def get_current_objective(self) -> Optional[Objective]:
        """
        Finds the most recently created objective that is not completed or archived.
        
        Returns:
            The current Objective or None if not found
        """
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