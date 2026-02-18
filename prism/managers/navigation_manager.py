"""
NavigationManager for path resolution and item lookup.

Handles all tree traversal, path resolution, and navigation logic.
Will replace Navigator class once migration is complete.
"""
from typing import Dict, List, Optional

from prism.newmodels import (
    Action,
    BaseItem,
    Deliverable,
    Milestone,
    Objective,
    Phase,
)
from prism.managers.project_manager import Project
from prism.exceptions import NavigationError


class NavigationManager:
    """
    Manages navigation and path resolution operations.

    Handles:
    - Path resolution to items
    - Item path discovery
    - Current objective/milestone/phase tracking
    - Tree traversal
    """

    def __init__(self, project: Project) -> None:
        """
        Initialize NavigationManager.

        Args:
            project: Project instance containing all items.
        """
        self.project = project

    def _resolve_path_segment(
        self, items: List[BaseItem], segment: str
    ) -> Optional[BaseItem]:
        """Resolve a path segment to a specific item.

        Args:
            items: List of items to search in.
            segment: Path segment to resolve (slug or index).

        Returns:
            Matching item or None if not found.
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
            pass  # Not an integer

        return None

    def get_item_by_path(self, path: str) -> Optional[BaseItem]:
        """Get an item by its path.

        Args:
            path: Path to the item (e.g., "phase/milestone/objective").

        Returns:
            The matching item or None if not found.

        Raises:
            NavigationError: If path resolution fails unexpectedly.
        """
        if not path:
            return None

        try:
            segments = path.split("/")
            current_items: List[BaseItem] = list(self.project.phases)

            target_item: Optional[BaseItem] = None

            for i, segment in enumerate(segments):
                found_item = self._resolve_path_segment(current_items, segment)
                if not found_item:
                    return None

                target_item = found_item

                if i < len(segments) - 1:
                    if isinstance(found_item, Phase):
                        current_items = list(found_item.milestones)
                    elif isinstance(found_item, Milestone):
                        current_items = list(found_item.objectives)
                    elif isinstance(found_item, Objective):
                        current_items = list(found_item.deliverables)
                    elif isinstance(found_item, Deliverable):
                        current_items = list(found_item.actions)
                    else:
                        return None

            return target_item
        except Exception as e:
            raise NavigationError(f"Failed to resolve path '{path}': {e}")

    def get_item_path(self, item_to_find: BaseItem) -> Optional[str]:
        """Get the path of an item.

        Args:
            item_to_find: Item to find path for.

        Returns:
            Path string or None if not found.

        Raises:
            NavigationError: If path discovery fails unexpectedly.
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

            return _traverse(self.project.phases, "")
        except Exception as e:
            raise NavigationError(f"Failed to find path for item: {e}")

    def get_current_objective(self) -> Optional[Objective]:
        """Get the current (most recent non-completed) objective.

        Returns:
            Current objective or None if not found.
        """
        current_objective = None
        for phase in self.project.phases:
            for milestone in phase.milestones:
                for objective in milestone.objectives:
                    if objective.status not in ["completed", "archived"]:
                        if (
                            current_objective is None
                            or objective.created_at > current_objective.created_at
                        ):
                            current_objective = objective
        return current_objective

    def get_current_milestone(self) -> Optional[Milestone]:
        """Get the current milestone containing the current objective.

        Returns:
            Current milestone or None if not found.
        """
        current_objective = self.get_current_objective()
        if not current_objective:
            return None

        for phase in self.project.phases:
            for milestone in phase.milestones:
                if current_objective in milestone.objectives:
                    return milestone
        return None

    def get_current_phase(self) -> Optional[Phase]:
        """Get the current phase containing the current objective.

        Returns:
            Current phase or None if not found.
        """
        current_objective = self.get_current_objective()
        if not current_objective:
            return None

        for phase in self.project.phases:
            for milestone in phase.milestones:
                if current_objective in milestone.objectives:
                    return phase
        return None

    def get_current_strategic_items(
        self,
    ) -> Dict[str, Optional[BaseItem]]:
        """Get current phase, milestone, and objective.

        Returns:
            Dictionary with 'phase', 'milestone', and 'objective' keys.
        """
        current_objective = self.get_current_objective()
        if not current_objective:
            return {"phase": None, "milestone": None, "objective": None}

        current_milestone = self.get_current_milestone()
        current_phase = self.get_current_phase()

        return {
            "phase": current_phase,
            "milestone": current_milestone,
            "objective": current_objective,
        }
