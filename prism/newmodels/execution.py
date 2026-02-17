"""
Execution item models for the Prism CLI.

Flat structure with UUID references for parent-child relationships.
"""
import re
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from .strategic import ItemStatus


class BaseExecutionItem(BaseModel):
    """Base model for all execution items."""
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    slug: str
    status: ItemStatus = ItemStatus.PENDING
    parent_uuid: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validate slug format."""
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('Slug must be lowercase alphanumeric with hyphens')
        return v


class Deliverable(BaseExecutionItem):
    """Deliverable model - concrete outputs within an objective.

    Valid children: Action
    """
    children: list[str] = Field(default_factory=list)  # List of action UUIDs

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
        if child_uuid not in self.children:
            self.children.append(child_uuid)

    def remove_child(self, child_uuid: str) -> None:
        """Remove an action UUID from this deliverable.
        
        Args:
            child_uuid: UUID of the action to remove.
        """
        if child_uuid in self.children:
            self.children.remove(child_uuid)


class Action(BaseExecutionItem):
    """Action model - individual tasks within a deliverable."""
    time_spent: Optional[float] = None  # Hours spent
    due_date: Optional[datetime] = None
