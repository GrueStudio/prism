"""
Base item model for the Prism CLI.

Common base for all strategic and execution items.
"""

import re
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, PrivateAttr, field_validator


class ItemStatus(str, Enum):
    """Valid status values for all items."""

    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"
    PAUSED = "paused"


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
    
    Subclasses override _item_type to specify their type for validation.
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
    _children: List[Optional["BaseItem"]] = PrivateAttr()
    _item_type: str = PrivateAttr(default="base")

    def model_post_init(self, __context) -> None:
        """Initialize _children after model construction."""
        self._children = [None] * len(self.child_uuids)

    @property
    def item_type(self) -> str:
        """Get the item type."""
        return self._item_type

    def get_status(self) -> ItemStatus:
        """Get status as ItemStatus enum."""
        try:
            return ItemStatus(self.status)
        except ValueError:
            return ItemStatus.PENDING

    def set_status(self, value: ItemStatus | str | None = None) -> None:
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

    @property
    def children(self) -> List:
        """Get child items in order.

        This is a generic property that returns the appropriate child list
        for each item type. Subclasses override this to return their specific
        child type.

        Returns:
            List of child items (empty list for Action which cannot have children).
        """
        return self._children

    def add_child(self, child) -> None:
        """Add a child item to this item.

        Updates both the _children list and child_uuids list.
        If the child's UUID is already in child_uuids, replaces the None
        at that index with the child. Otherwise appends to both lists.

        Subclasses should override to add type validation before calling super().

        Args:
            child: Child item to add.
        """
        if child.uuid not in self.child_uuids:
            self.child_uuids.append(child.uuid)
            self._children.append(child)
        else:
            index = self.child_uuids.index(child.uuid)
            self._children[index] = child


# =============================================================================
# Execution Items (defined first to resolve forward references)
# =============================================================================


class Action(BaseItem):
    """Action model - individual tasks within a deliverable.

    Actions cannot have children.
    """

    due_date: Optional[datetime] = None
    _item_type: str = PrivateAttr(default="action")

    def add_child(self, child) -> None:
        """Actions cannot have children.

        Raises:
            ValueError: Always raised since Actions cannot have children.
        """
        raise ValueError("Action cannot have children")


class Deliverable(BaseItem):
    """Deliverable model - concrete outputs within an objective.

    Valid children: Action
    """

    _item_type: str = PrivateAttr(default="deliverable")

    def add_child(self, child) -> None:
        """Add an action to this deliverable.

        Args:
            child: Action to add.
        """
        if getattr(child, "item_type", None) != "action":
            raise ValueError("Deliverables can only have Actions as children")
        super().add_child(child)


# =============================================================================
# Strategic Items
# =============================================================================


class Objective(BaseItem):
    """Objective model - specific goals within a milestone.

    Valid children: Deliverable (execution item, stored separately)
    """

    _item_type: str = PrivateAttr(default="objective")

    def add_child(self, child) -> None:
        """Add a deliverable to this objective.

        Args:
            child: Deliverable to add.
        """
        if getattr(child, "item_type", None) != "deliverable":
            raise ValueError("Objectives can only have Deliverables as children")
        super().add_child(child)


class Milestone(BaseItem):
    """Milestone model - groups objectives within a phase.

    Valid children: Objective
    """

    _item_type: str = PrivateAttr(default="milestone")

    def add_child(self, child) -> None:
        """Add an objective to this milestone.

        Args:
            child: Objective to add.
        """
        if getattr(child, "item_type", None) != "objective":
            raise ValueError("Milestones can only have Objectives as children")
        super().add_child(child)


class Phase(BaseItem):
    """Phase model - top-level strategic container.

    Valid children: Milestone
    """

    _item_type: str = PrivateAttr(default="phase")

    def add_child(self, child) -> None:
        """Add a milestone to this phase.

        Args:
            child: Milestone to add.
        """
        if getattr(child, "item_type", None) != "milestone":
            raise ValueError("Phases can only have Milestones as children")
        super().add_child(child)
