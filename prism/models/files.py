"""
File models for the Prism CLI.

Models representing the structure of JSON files in the .prism/ directory.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from .base import Action, Deliverable, Milestone, Objective, Phase
from .bug import BugItem
from .config import BugType, ConfigFile
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


class BugsFile(BaseModel):
    """Model for bugs.json file.

    List of bug items.
    """

    bugs: List[BugItem] = Field(default_factory=list)


class CursorFile(BaseModel):
    """Model for cursor.json file.

    Tracks cursor positions in the project tree:
    - task_cursor: Current action being worked on (for task commands)
    - crud_context: Current working directory for CRUD operations
    """

    task_cursor: str | None = None
    crud_context: str | None = None
