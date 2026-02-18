"""
Base item model for the Prism CLI.

Common base for all strategic and execution items.
"""
import re
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_serializer


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
    """
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    slug: str
    status: str = "pending"
    parent_uuid: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

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

    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validate slug format."""
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('Slug must be lowercase alphanumeric with hyphens')
        return v
