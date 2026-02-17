"""
Strategic item models for the Prism CLI.

Flat structure with UUID references for parent-child relationships.
"""
import re
import uuid
from datetime import datetime
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


class BaseStrategicItem(BaseModel):
    """Base model for all strategic items."""
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    slug: str
    status: ItemStatus = ItemStatus.PENDING
    parent_uuid: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    children: List[str] = Field(default_factory=list)  # List of child UUIDs

    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validate slug format."""
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('Slug must be lowercase alphanumeric with hyphens')
        return v

    def add_child(self, child_uuid: str) -> None:
        """Add a child UUID to the children list.
        
        Args:
            child_uuid: UUID of the child item to add.
        """
        if child_uuid not in self.children:
            self.children.append(child_uuid)

    def remove_child(self, child_uuid: str) -> None:
        """Remove a child UUID from the children list.
        
        Args:
            child_uuid: UUID of the child item to remove.
        """
        if child_uuid in self.children:
            self.children.remove(child_uuid)


class Phase(BaseStrategicItem):
    """Phase model - top-level strategic container.

    Valid children: Milestone
    """

    def add_child(self, child_uuid: str, child_type: str) -> None:
        """Add a milestone UUID to this phase.
        
        Args:
            child_uuid: UUID of the milestone to add.
            child_type: Type of child (must be 'milestone').
            
        Raises:
            ValueError: If child_type is not 'milestone'.
        """
        if child_type != 'milestone':
            raise ValueError(f"Phase can only contain milestones, not {child_type}")
        super().add_child(child_uuid)


class Milestone(BaseStrategicItem):
    """Milestone model - groups objectives within a phase.

    Valid children: Objective
    """

    def add_child(self, child_uuid: str, child_type: str) -> None:
        """Add an objective UUID to this milestone.
        
        Args:
            child_uuid: UUID of the objective to add.
            child_type: Type of child (must be 'objective').
            
        Raises:
            ValueError: If child_type is not 'objective'.
        """
        if child_type != 'objective':
            raise ValueError(f"Milestone can only contain objectives, not {child_type}")
        super().add_child(child_uuid)


class Objective(BaseStrategicItem):
    """Objective model - specific goals within a milestone.

    Valid children: Deliverable (execution item, stored separately)
    """

    def add_child(self, child_uuid: str, child_type: str) -> None:
        """Add a deliverable UUID to this objective.
        
        Args:
            child_uuid: UUID of the deliverable to add.
            child_type: Type of child (must be 'deliverable').
            
        Raises:
            ValueError: If child_type is not 'deliverable'.
        """
        if child_type != 'deliverable':
            raise ValueError(f"Objective can only contain deliverables, not {child_type}")
        super().add_child(child_uuid)
