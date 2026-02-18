"""
Data models for the Prism CLI.

New model structure for .prism/ folder-based storage with UUID references.
"""

from .base import (
    ItemStatus,
    BaseItem,
)
from .strategic import (
    Phase,
    Milestone,
    Objective,
)
from .execution import (
    Deliverable,
    Action,
)
from .orphan import Orphan
from .files import (
    StrategicFile,
    ExecutionFile,
    OrphansFile,
    ConfigFile,
)

# Rebuild models to resolve forward references between strategic and execution
Phase.model_rebuild()
Milestone.model_rebuild()
Objective.model_rebuild()
Deliverable.model_rebuild()
Action.model_rebuild()

__all__ = [
    # Base
    "ItemStatus",
    "BaseItem",
    # Strategic items
    "Phase",
    "Milestone",
    "Objective",
    # Execution items
    "Deliverable",
    "Action",
    # Orphan
    "Orphan",
    # File models
    "StrategicFile",
    "ExecutionFile",
    "OrphansFile",
    "ConfigFile",
]
