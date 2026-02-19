"""
Execution item models for the Prism CLI.

Flat structure with UUID references for parent-child relationships.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from prism.models.base import BaseItem


class Deliverable(BaseItem):
    """Deliverable model - concrete outputs within an objective.

    Valid children: Action
    """

    actions: List["Action"] = Field(default_factory=list)

    def add_child(self, child: "Action") -> None:
        """Add an action to this deliverable.

        Args:
            child: Action to add.
        """
        if child.uuid not in self.child_uuids:
            self.child_uuids.append(child.uuid)
        self.actions.append(child)


class Action(BaseItem):
    """Action model - individual tasks within a deliverable.

    Actions cannot have children.
    """

    due_date: Optional[datetime] = None

    def add_child(self, child: "Action") -> None:
        """Actions cannot have children.

        Raises:
            ValueError: Always raised since Actions cannot have children.
        """
        raise ValueError("Action cannot have children")
