"""
Execution item models for the Prism CLI.

Flat structure with UUID references for parent-child relationships.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import Field

from prism.newmodels.base import BaseItem, ItemStatus


class Deliverable(BaseItem):
    """Deliverable model - concrete outputs within an objective.

    Valid children: Action
    """
    actions: List['Action'] = Field(default_factory=list)

    def add_child(self, child_uuid: str, child_type: str) -> None:
        """Add an action UUID to this deliverable.

        Args:
            child_uuid: UUID of the action to add.
            child_type: Type of child (must be 'action').

        Raises:
            ValueError: If child_type is not 'action'.
        """
        if child_type != 'action':
            raise ValueError(f"Deliverable can only contain actions, not {child_type}")


class Action(BaseItem):
    """Action model - individual tasks within a deliverable.

    Actions cannot have children.
    """
    due_date: Optional[datetime] = None

    def add_child(self, child_uuid: str, child_type: str) -> None:
        """Actions cannot have children.

        Raises:
            ValueError: Always raised since Actions cannot have children.
        """
        raise ValueError(f"Action cannot have children, got {child_type}")
