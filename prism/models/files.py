"""
File models for the Prism CLI.

Models representing the structure of JSON files in the .prism/ directory.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from prism.constants import (
    DEFAULT_DATE_FORMATS,
    DEFAULT_DATE_MAX_YEARS_FUTURE,
    DEFAULT_DATE_MAX_YEARS_PAST,
    DEFAULT_PERCENTAGE_ROUND_PRECISION,
    DEFAULT_SLUG_FILLER_WORDS,
    DEFAULT_SLUG_MAX_LENGTH,
    DEFAULT_SLUG_REGEX_PATTERN,
    DEFAULT_SLUG_WORD_LIMIT,
    DEFAULT_STATUS_HEADER_WIDTH,
)

from .base import Action, Deliverable, Milestone, Objective, Phase
from .orphan import Orphan


class StrategicFile(BaseModel):
    """Model for strategic.json file.

    Contains the current active path: one phase, one milestone, one objective.
    The index fields track the position for path resolution (e.g., phase[1], milestone[1]).
    Indices are 1-based to match CLI path notation.
    """

    phase: Optional[Phase] = None
    milestone: Optional[Milestone] = None
    objective: Optional[Objective] = None

    phase_uuids: List[str] = Field(default_factory=list)


class ArchivedStrategicFile(BaseModel):
    """Model for archive/strategic.json file.

    Contains archived strategic items grouped by type.
    """

    phases: List[Phase] = Field(default_factory=list)
    milestones: List[Milestone] = Field(default_factory=list)
    objectives: List[Objective] = Field(default_factory=list)


class ExecutionFile(BaseModel):
    """Model for execution.json file.

    Flat list of all execution items with parent_uuid references.
    """

    deliverables: List[Deliverable] = Field(default_factory=list)
    actions: List[Action] = Field(default_factory=list)


class OrphansFile(BaseModel):
    """Model for orphans.json file.

    List of orphan ideas.
    """

    orphans: List[Orphan] = Field(default_factory=list)


class ConfigFile(BaseModel):
    """Model for config.json file.

    Project settings and configuration.
    """

    schema_version: str = "0.2.0"

    # Slug settings
    slug_max_length: int = DEFAULT_SLUG_MAX_LENGTH
    slug_regex_pattern: str = DEFAULT_SLUG_REGEX_PATTERN
    slug_word_limit: int = DEFAULT_SLUG_WORD_LIMIT
    slug_filler_words: List[str] = Field(
        default_factory=lambda: list(DEFAULT_SLUG_FILLER_WORDS)
    )

    # Date settings
    date_formats: List[str] = Field(default_factory=lambda: list(DEFAULT_DATE_FORMATS))
    date_max_years_future: int = DEFAULT_DATE_MAX_YEARS_FUTURE
    date_max_years_past: int = DEFAULT_DATE_MAX_YEARS_PAST

    # Display settings
    status_header_width: int = DEFAULT_STATUS_HEADER_WIDTH
    percentage_round_precision: int = DEFAULT_PERCENTAGE_ROUND_PRECISION

    # Orphan settings
    orphan_name_regex: str = r"^[a-zA-Z0-9\s\-_'\"]+$"
    orphan_default_priority: int = 0
    orphan_priority_min: int = -100
    orphan_priority_max: int = 100
    orphan_priority_labels: dict[str, int] = Field(
        default_factory=lambda: {
            "low": -10,
            "medium": 0,
            "high": 10,
            "critical": 50,
        }
    )


class CursorFile(BaseModel):
    """Model for cursor.json file.

    Tracks cursor positions in the project tree:
    - task_cursor: Current action being worked on (for task commands)
    - crud_context: Current working directory for CRUD operations
    """

    task_cursor: str | None = None
    crud_context: str | None = None
