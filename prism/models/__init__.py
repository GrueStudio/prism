"""
Data models for the Prism CLI.

New model structure for .prism/ folder-based storage with UUID references.

Import models explicitly from their modules to avoid circular imports:
    from prism.models.base import BaseItem, ItemStatus
    from prism.models.strategic import Phase, Milestone, Objective
    from prism.models.execution import Deliverable, Action
    from prism.models.archived import ArchivedItem
    from prism.models.project import Project
    from prism.models.files import StrategicFile, ExecutionFile, etc.
"""

from .base import Action, Deliverable, Milestone, Objective, Phase

Phase.model_rebuild()
Milestone.model_rebuild()
Objective.model_rebuild()
Deliverable.model_rebuild()
Action.model_rebuild()
