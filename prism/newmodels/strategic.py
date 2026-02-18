"""
Strategic item models for the Prism CLI.

Flat structure with UUID references for parent-child relationships.
"""
from typing import List, Optional

from pydantic import Field

from prism.newmodels.base import BaseItem, ItemStatus


class Phase(BaseItem):
    """Phase model - top-level strategic container.

    Valid children: Milestone
    """
    milestones: List['Milestone'] = Field(default_factory=list)

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


class Milestone(BaseItem):
    """Milestone model - groups objectives within a phase.

    Valid children: Objective
    """
    objectives: List['Objective'] = Field(default_factory=list)

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


class Objective(BaseItem):
    """Objective model - specific goals within a milestone.

    Valid children: Deliverable (execution item, stored separately)
    """
    deliverables: List['Deliverable'] = Field(default_factory=list)

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
