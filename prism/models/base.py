"""
Base item model for the Prism CLI.

Common base for all strategic and execution items.
"""

import re
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ItemStatus(str, Enum):
    """Valid status values for all items."""

    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class BaseItem(BaseModel):
    """
    Base model for all Prism items (strategic and execution).

    Common fields:
    - uuid: Unique identifier
    - name: Item name
    - description: Optional description
    - slug: URL-friendly identifier
    - status: Current status (stored as string, property returns ItemStatus enum)
    - parent_uuid: Reference to parent item
    - timestamps: created_at, updated_at
    - time_spent: Total time spent on this item (cascades from children)
    - child_uuids: List of child UUIDs in order (for preserving order)
    """

    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    slug: str
    status: str = "pending"
    parent_uuid: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    time_spent: Optional[timedelta] = None
    child_uuids: List[str] = Field(default_factory=list)

    def get_status(self) -> ItemStatus:
        """Get status as ItemStatus enum."""
        try:
            return ItemStatus(self.status)
        except ValueError:
            return ItemStatus.PENDING

    def set_status(self, value) -> None:
        """Set status from string or ItemStatus enum."""
        if isinstance(value, ItemStatus):
            self.status = value.value
        elif isinstance(value, str):
            self.status = value
        else:
            self.status = ItemStatus.PENDING.value

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validate slug format."""
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("Slug must be lowercase alphanumeric with hyphens")
        return v


# =============================================================================
# Execution Items (defined first to resolve forward references)
# =============================================================================


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


class Deliverable(BaseItem):
    """Deliverable model - concrete outputs within an objective.

    Valid children: Action
    """

    actions: List[Action] = Field(default_factory=list)

    def add_child(self, child: Action) -> None:
        """Add an action to this deliverable.

        Args:
            child: Action to add.
        """
        if child.uuid not in self.child_uuids:
            self.child_uuids.append(child.uuid)
        self.actions.append(child)


# =============================================================================
# Strategic Items
# =============================================================================


class Objective(BaseItem):
    """Objective model - specific goals within a milestone.

    Valid children: Deliverable (execution item, stored separately)
    """

    deliverables: List[Deliverable] = Field(default_factory=list)

    def add_child(self, child: Deliverable) -> None:
        """Add a deliverable to this objective.

        Args:
            child: Deliverable to add.
        """
        if child.uuid not in self.child_uuids:
            self.child_uuids.append(child.uuid)
        self.deliverables.append(child)


class Milestone(BaseItem):
    """Milestone model - groups objectives within a phase.

    Valid children: Objective
    """

    objectives: List[Objective] = Field(default_factory=list)

    def add_child(self, child: Objective) -> None:
        """Add an objective to this milestone.

        Args:
            child: Objective to add.
        """
        if child.uuid not in self.child_uuids:
            self.child_uuids.append(child.uuid)
        self.objectives.append(child)


class Phase(BaseItem):
    """Phase model - top-level strategic container.

    Valid children: Milestone
    """

    milestones: List[Milestone] = Field(default_factory=list)

    def add_child(self, child: Milestone) -> None:
        """Add a milestone to this phase.

        Args:
            child: Milestone to add.
        """
        if child.uuid not in self.child_uuids:
            self.child_uuids.append(child.uuid)
        self.milestones.append(child)
