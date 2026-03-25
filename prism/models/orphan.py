"""
Orphan model for the Prism CLI.

Orphans are typeless ideas waiting to be adopted into the project structure.
"""

import re
import uuid
from typing import ClassVar

from pydantic import BaseModel, Field, field_validator

from prism.constants import (
    DEFAULT_ORPHAN_NAME_REGEX,
    DEFAULT_ORPHAN_DEFAULT_PRIORITY,
    DEFAULT_ORPHAN_PRIORITY_LABELS,
    DEFAULT_ORPHAN_PRIORITY_MAX,
    DEFAULT_ORPHAN_PRIORITY_MIN,
)


class Orphan(BaseModel):
    """Orphan model - typeless ideas waiting to be adopted.

    Minimal fields only. Orphans are deleted when adopted.
    Validation rules are stored as class variables and can be overridden by ConfigManager.
    """
    # Validation Rules (Class variables to avoid circular imports)
    NAME_REGEX: ClassVar[str] = DEFAULT_ORPHAN_NAME_REGEX
    DEFAULT_PRIORITY: ClassVar[int] = DEFAULT_ORPHAN_DEFAULT_PRIORITY
    PRIORITY_MIN: ClassVar[int] = DEFAULT_ORPHAN_PRIORITY_MIN
    PRIORITY_MAX: ClassVar[int] = DEFAULT_ORPHAN_PRIORITY_MAX
    PRIORITY_LABELS: ClassVar[dict[str, int]] = DEFAULT_ORPHAN_PRIORITY_LABELS

    id: int = Field(default=0)  # Auto-incremented numeric ID
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    priority: int | str = Field(default_factory=lambda: Orphan.DEFAULT_PRIORITY)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate orphan name against regex pattern."""
        if not v:
            raise ValueError("Name is required")

        if not re.match(cls.NAME_REGEX, v):
            raise ValueError(
                f"Name does not match required pattern: {cls.NAME_REGEX}. "
                "Name can only contain letters, numbers, spaces, hyphens, underscores, quotes."
            )
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate description is not empty."""
        if not v or not v.strip():
            raise ValueError("Description is required and cannot be empty")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: int | str) -> int:
        """Validate priority is within bounds."""
        if isinstance(v, str):
            if v in cls.PRIORITY_LABELS:
                v = cls.PRIORITY_LABELS[v]
            else:
                v = cls.DEFAULT_PRIORITY

        if v < cls.PRIORITY_MIN or v > cls.PRIORITY_MAX:
            raise ValueError(
                f"Priority must be between {cls.PRIORITY_MIN} and {cls.PRIORITY_MAX}, got {v}"
            )

        return v
