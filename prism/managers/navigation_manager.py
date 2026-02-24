"""
NavigationManager for path resolution and item navigation.

Handles all tree traversal, path resolution, navigation logic, and special token resolution.
"""

from typing import Dict, List, Optional

from prism.exceptions import NavigationError
from prism.models.archived import ArchivedItem
from prism.models.base import (
    Action,
    BaseItem,
    Deliverable,
    Milestone,
    Objective,
    Phase,
)
from prism.models.project import Project


# Special navigation tokens
SPECIAL_TOKENS = {
    # Up/parent navigation
    ":u": "up",
    ":up": "up",
    ":parent": "up",
    # Current - short forms
    ":cp": "current_phase",
    ":cm": "current_milestone",
    ":co": "current_objective",
    ":cd": "current_deliverable",
    ":ca": "current_action",
    # Current - long forms
    ":currentp": "current_phase",
    ":currentm": "current_milestone",
    ":currento": "current_objective",
    ":currentd": "current_deliverable",
    ":currenta": "current_action",
    ":current-phase": "current_phase",
    ":current-milestone": "current_milestone",
    ":current-objective": "current_objective",
    ":current-deliverable": "current_deliverable",
    ":current-action": "current_action",
    # Last - short forms
    ":lp": "last_phase",
    ":lm": "last_milestone",
    ":lo": "last_objective",
    ":ld": "last_deliverable",
    ":la": "last_action",
    # Last - medium forms
    ":lastp": "last_phase",
    ":lastm": "last_milestone",
    ":lasto": "last_objective",
    ":lastd": "last_deliverable",
    ":lasta": "last_action",
    # Last - long forms
    ":last-phase": "last_phase",
    ":last-milestone": "last_milestone",
    ":last-objective": "last_objective",
    ":last-deliverable": "last_deliverable",
    ":last-action": "last_action",
    # Next - short forms (deliverable and action only - strategic items don't have "next")
    ":nd": "next_deliverable",
    ":na": "next_action",
    # Next - medium forms
    ":nextd": "next_deliverable",
    ":nexta": "next_action",
    # Next - long forms
    ":next-deliverable": "next_deliverable",
    ":next-action": "next_action",
}

# Type shortcuts for last/next commands
TYPE_SHORTCUTS = {
    "p": "phase",
    "phase": "phase",
    "m": "milestone",
    "milestone": "milestone",
    "o": "objective",
    "objective": "objective",
    "d": "deliverable",
    "deliverable": "deliverable",
    "a": "action",
    "action": "action",
}


class NavigationManager:
    """
    Manages navigation and path resolution operations.

    Handles:
    - Path resolution to items
    - Item path discovery
    - Current objective/milestone/phase tracking
    - Tree traversal
    - Special token resolution (:back, :lasto, :nextd, etc.)
    - CRUD context management
    """

    def __init__(self, project: Project) -> None:
        """
        Initialize NavigationManager.

        Args:
            project: Project instance containing all items.
        """
        self.project = project

    def _resolve_path_segment(self, items: list, segment: str) -> Optional[object]:
        """Resolve a path segment to a specific item.

        Args:
            items: List of items to search in (can include ArchivedItem wrappers).
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

    def get_item_by_path(self, path: str) -> Optional[object]:
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
            current_items: list = list(self.project.phases)

            target_item: Optional[object] = None

            for i, segment in enumerate(segments):
                found_item = self._resolve_path_segment(current_items, segment)
                if not found_item:
                    return None

                target_item = found_item

                if i < len(segments) - 1:
                    # Get children - all items now use .children property
                    current_items = list(found_item.children)

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

                    if item.children:
                        found_path = _traverse(item.children, path)
                        if found_path:
                            return found_path
                return None

            return _traverse(self.project.phases, "")
        except Exception as e:
            raise NavigationError(f"Failed to find path for item: {e}")

    def get_current_objective(self) -> Optional[Objective]:
        """Get the current objective (most recent non-archived objective).

        Completed objectives are included - they're still current until a new one starts.
        Only archived objectives are excluded (old completed items moved to archive).

        Returns:
            Current objective or None if not found.
        """
        current_objective = None
        for phase in self.project.phases:
            for milestone in phase.children:
                for objective in milestone.children:
                    # Only exclude archived objectives, not completed ones
                    if objective.status != "archived":
                        if (
                            current_objective is None
                            or objective.created_at > current_objective.created_at
                        ):
                            current_objective = objective
        return current_objective

    def get_current_milestone(self) -> Optional[Milestone]:
        """Get the current milestone (most recent non-archived milestone).

        Completed milestones are included - they're still current until a new one starts.
        Only archived milestones are excluded (old completed items moved to archive).

        Returns:
            Current milestone or None if not found.
        """
        current_milestone = None
        for phase in self.project.phases:
            for milestone in phase.children:
                # Only exclude archived milestones, not completed ones
                if milestone.status != "archived":
                    if (
                        current_milestone is None
                        or milestone.created_at > current_milestone.created_at
                    ):
                        current_milestone = milestone
        return current_milestone

    def get_current_phase(self) -> Optional[Phase]:
        """Get the current phase (most recent non-archived phase).

        Completed phases are included - they're still current until a new one starts.
        Only archived phases are excluded (old completed items moved to archive).

        Returns:
            Current phase or None if not found.
        """
        current_phase = None
        for phase in self.project.phases:
            # Only exclude archived phases, not completed ones
            if phase.status != "archived":
                if (
                    current_phase is None
                    or phase.created_at > current_phase.created_at
                ):
                    current_phase = phase
        return current_phase

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

    # =========================================================================
    # Cursor-based navigation
    # =========================================================================

    def get_current_position(self) -> Optional[BaseItem]:
        """Get item at current task_cursor position.

        Returns:
            Item at task_cursor or None if not set.
        """
        if not self.project.task_cursor:
            return None
        return self.get_item_by_path(self.project.task_cursor)

    def get_crud_context(self) -> Optional[str]:
        """Get current CRUD context (deliverable-level path).

        CRUD context must not be 'behind' task_cursor in depth-first traversal order.
        If task_cursor is at 2/2/2/2/2, crud_context cannot be at 1/*, 2/1/*, 2/2/1/*, etc.

        Returns:
            - crud_context if explicitly set (validated to not be behind task_cursor)
            - Otherwise, parent deliverable path from task_cursor
            - None if neither available
        """
        # Use explicit crud_context if set
        if self.project.crud_context:
            # Validate it's not behind task_cursor in depth-first order
            if self.project.task_cursor:
                if self._is_path_behind(self.project.crud_context, self.project.task_cursor):
                    # crud_context is behind task_cursor, reset it
                    self.project.crud_context = None
                else:
                    return self.project.crud_context
            else:
                return self.project.crud_context

        # Infer from task_cursor (get parent deliverable)
        if self.project.task_cursor:
            parts = self.project.task_cursor.split("/")
            if len(parts) >= 4:
                # Return path up to deliverable level
                return "/".join(parts[:-1])
            # task_cursor is at strategic level, use it as context
            return self.project.task_cursor

        return None

    def _is_path_behind(self, path1: str, path2: str) -> bool:
        """Check if path1 comes before path2 in depth-first traversal order.

        Examples (path1 behind path2 = True):
            "1/1/1" behind "2/1/1" = True
            "2/1/1" behind "2/2/1" = True
            "2/2/1" behind "2/2/2" = True
            "2/2/2/1" behind "2/2/2/2" = True

        Args:
            path1: First path to compare.
            path2: Second path to compare.

        Returns:
            True if path1 comes before path2 in depth-first order.
        """
        parts1 = path1.split("/")
        parts2 = path2.split("/")

        for i in range(min(len(parts1), len(parts2))):
            try:
                num1 = int(parts1[i])
                num2 = int(parts2[i])
            except ValueError:
                # If not a number, compare as strings
                if parts1[i] < parts2[i]:
                    return True
                elif parts1[i] > parts2[i]:
                    return False
                continue

            if num1 < num2:
                return True
            elif num1 > num2:
                return False

        # path1 is a prefix of path2 (path1 is ancestor of path2)
        # Ancestor is NOT behind descendant in depth-first order
        if len(parts1) < len(parts2):
            return False

        # path2 is a prefix of path1 (path2 is ancestor of path1)
        # Descendant IS behind ancestor in depth-first order
        if len(parts1) > len(parts2):
            return True

        # Paths are equal
        return False

    def set_crud_context(self, path: str) -> bool:
        """Set CRUD context to a specific path.

        CRUD context must not be 'behind' task_cursor in depth-first traversal order.
        If task_cursor is at 2/2/2/2/2, crud_context cannot be set to 1/*, 2/1/*, etc.

        Args:
            path: Path to set as CRUD context.

        Returns:
            True if path is valid and context was set, False otherwise.
        """
        item = self.get_item_by_path(path)
        if not item:
            return False

        # Validate: crud_context must not be behind task_cursor in depth-first order
        if self.project.task_cursor:
            if self._is_path_behind(path, self.project.task_cursor):
                # Path is behind task_cursor, reject it
                return False

        self.project.crud_context = path
        return True

    # =========================================================================
    # Special token resolution
    # =========================================================================

    def resolve_special_token(self, token: str) -> Optional[str]:
        """Resolve special navigation token to a path.

        Args:
            token: Special token like :up, :lasto, :nextd, :co, etc.

        Returns:
            Resolved path string, or None if token invalid or target not found.
        """
        if not token.startswith(":"):
            return None

        # Look up token in special tokens map
        token_type = SPECIAL_TOKENS.get(token)
        if not token_type:
            return None

        # Handle :up/:parent
        if token_type == "up":
            return self._resolve_up()

        # Handle :current_* tokens
        if token_type.startswith("current_"):
            item_type = token_type[8:]  # Extract type after "current_"
            return self._resolve_current_of_type(item_type)

        # Handle :last_* tokens
        if token_type.startswith("last_"):
            item_type = token_type[5:]  # Extract type after "last_"
            return self._find_last_of_type(item_type)

        # Handle :next_* tokens
        if token_type.startswith("next_"):
            item_type = token_type[5:]  # Extract type after "next_"
            return self._find_next_of_type(item_type)

        return None

    def _resolve_up(self) -> Optional[str]:
        """Resolve :up/:parent token to parent path.

        Returns:
            Parent path or None if at root.
        """
        # Try crud_context first
        context = self.get_crud_context()
        if context:
            parts = context.split("/")
            if len(parts) > 1:
                return "/".join(parts[:-1])
            return None

        # Fall back to task_cursor
        if self.project.task_cursor:
            parts = self.project.task_cursor.split("/")
            if len(parts) > 1:
                return "/".join(parts[:-1])
            return None

        return None

    def _resolve_current_of_type(self, item_type: str) -> Optional[str]:
        """Resolve :current_* token to path of current item of that type.

        Uses existing get_current_*() methods for strategic items.
        For deliverable/action, extracts from task_cursor.

        Args:
            item_type: Type of item to find (phase, milestone, objective, deliverable, action).

        Returns:
            Path to current item or None if not found.
        """
        # Normalize type shortcut
        item_type = TYPE_SHORTCUTS.get(item_type, item_type)

        if item_type == "phase":
            current = self.get_current_phase()
            return self.get_item_path(current) if current else None

        if item_type == "milestone":
            current = self.get_current_milestone()
            return self.get_item_path(current) if current else None

        if item_type == "objective":
            current = self.get_current_objective()
            return self.get_item_path(current) if current else None

        if item_type == "deliverable":
            # Extract deliverable from task_cursor or crud_context
            context = self.get_crud_context() or self.project.task_cursor
            if not context:
                return None
            parts = context.split("/")
            if len(parts) >= 4:
                # Return path up to deliverable level
                return "/".join(parts[:4])
            return None

        if item_type == "action":
            # Action is the task_cursor itself (if it's an action)
            if not self.project.task_cursor:
                return None
            parts = self.project.task_cursor.split("/")
            if len(parts) >= 5:
                return self.project.task_cursor
            return None

        return None

    def _find_last_of_type(self, item_type: str) -> Optional[str]:
        """Find last (most recently created) non-completed item of given type.

        Args:
            item_type: Type of item to find (phase, milestone, objective, deliverable, action).

        Returns:
            Path to last item or None if not found.
        """
        # Normalize type
        item_type = TYPE_SHORTCUTS.get(item_type, item_type)
        if item_type not in TYPE_SHORTCUTS.values():
            return None

        if item_type == "phase":
            # Find last non-completed phase
            for phase in reversed(self.project.phases):
                if isinstance(phase, BaseItem) and phase.status != "completed":
                    return self.get_item_path(phase)
            return None

        # For other types, traverse tree and collect all items of that type
        items = self._collect_all_items_of_type(item_type)

        # Return last non-completed item
        for item in reversed(items):
            if item.status != "completed":
                return self.get_item_path(item)

        return None

    def _find_next_of_type(self, item_type: str) -> Optional[str]:
        """Find next item of given type after current position.

        Only supports deliverable and action types.
        Strategic items (phase, milestone, objective) don't have "next" navigation.

        Args:
            item_type: Type of item to find (deliverable or action).

        Returns:
            Path to next item or None if not found.
        """
        # Normalize type
        item_type = TYPE_SHORTCUTS.get(item_type, item_type)

        # Only deliverable and action support :next navigation
        if item_type not in ("deliverable", "action"):
            return None

        # Get current position
        current_path = self.get_crud_context() or self.project.task_cursor
        if not current_path:
            # No current position, return first item of type
            items = self._collect_all_items_of_type(item_type)
            if items:
                return self.get_item_path(items[0])
            return None

        # Collect all items of type
        items = self._collect_all_items_of_type(item_type)

        # Find current item's index and return next
        current_item = self.get_item_by_path(current_path)
        if not current_item:
            return None

        found_current = False
        for item in items:
            if found_current:
                return self.get_item_path(item)
            if item is current_item:
                found_current = True

        return None

    def _collect_all_items_of_type(self, item_type: str) -> List[BaseItem]:
        """Collect all items of a given type from the project tree.

        Args:
            item_type: Type of item to collect.

        Returns:
            List of items in traversal order.
        """
        items = []

        def _traverse(current_items: List):
            for item in current_items:
                if not isinstance(item, BaseItem):
                    continue

                item_name = type(item).__name__.lower()
                if item_name == item_type:
                    items.append(item)

                if item.children:
                    _traverse(item.children)

        _traverse(self.project.phases)
        return items

    # =========================================================================
    # Path resolution (combines special tokens + normal paths)
    # =========================================================================

    def resolve_path(self, path: Optional[str] = None) -> Optional[str]:
        """Resolve any path: special tokens, relative, or absolute.

        Args:
            path: Path string, special token, or None for current position.

        Returns:
            Resolved absolute path, or None for current position.
        """
        # None or empty = current position
        if path is None or path == "":
            return self.get_crud_context()

        # Check for special token
        if path.startswith(":"):
            return self.resolve_special_token(path)

        # Absolute path (starts with /)
        if path.startswith("/"):
            return path[1:]

        # Relative path - resolve from CRUD context
        context = self.get_crud_context()
        if context:
            return f"{context}/{path}"

        return path

    def resolve_to_item(self, path: Optional[str] = None) -> Optional[BaseItem]:
        """Resolve path to an actual item.

        Args:
            path: Path string, special token, or None for current position.

        Returns:
            Resolved item or None if not found.
        """
        resolved_path = self.resolve_path(path)
        if not resolved_path:
            return None
        return self.get_item_by_path(resolved_path)
