"""
Orphan model for the Prism CLI.

Orphans are typeless ideas waiting to be adopted into the project structure.
"""

import re
import uuid

from pydantic import BaseModel, Field, field_validator

from prism.constants import (
    get_orphan_default_priority,
    get_orphan_name_regex,
    get_orphan_priority_labels,
    get_orphan_priority_max,
    get_orphan_priority_min,
)


class Orphan(BaseModel):
    """Orphan model - typeless ideas waiting to be adopted.

    Minimal fields only. Orphans are deleted when adopted.
    """

    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    priority: int | str = Field(default_factory=get_orphan_default_priority)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate orphan name against regex pattern from config."""
        if not v:
            raise ValueError("Name is required")

        pattern = get_orphan_name_regex()
        if not re.match(pattern, v):
            raise ValueError(
                f"Name does not match required pattern: {pattern}. "
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
    def validate_priority(cls, v: int | str) -> int | str:
        """Validate priority is within bounds."""
        if isinstance(v, str):
            labels: dict[str, int] = get_orphan_priority_labels()
            if v in labels:
                v = labels[v]
            else:
                v = get_orphan_default_priority()

        min_val = get_orphan_priority_min()
        max_val = get_orphan_priority_max()

        if v < min_val or v > max_val:
            raise ValueError(
                f"Priority must be between {min_val} and {max_val}, got {v}"
            )

        return v
