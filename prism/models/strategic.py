"""
Strategic item models for the Prism CLI.

Flat structure with UUID references for parent-child relationships.
"""

from typing import List

from pydantic import Field

from prism.models.base import BaseItem


class Phase(BaseItem):
    """Phase model - top-level strategic container.

    Valid children: Milestone
    """

    milestones: List["Milestone"] = Field(default_factory=list)

    def add_child(self, child: "Milestone") -> None:
        """Add a milestone to this phase.

        Args:
            child: Milestone to add.
        """
        if child.uuid not in self.child_uuids:
            self.child_uuids.append(child.uuid)
        self.milestones.append(child)


class Milestone(BaseItem):
    """Milestone model - groups objectives within a phase.

    Valid children: Objective
    """

    objectives: List["Objective"] = Field(default_factory=list)

    def add_child(self, child: "Objective") -> None:
        """Add an objective to this milestone.

        Args:
            child: Objective to add.
        """
        if child.uuid not in self.child_uuids:
            self.child_uuids.append(child.uuid)
        self.objectives.append(child)


class Objective(BaseItem):
    """Objective model - specific goals within a milestone.

    Valid children: Deliverable (execution item, stored separately)
    """

    deliverables: List["Deliverable"] = Field(default_factory=list)

    def add_child(self, child: "Deliverable") -> None:
        """Add a deliverable to this objective.

        Args:
            child: Deliverable to add.
        """
        if child.uuid not in self.child_uuids:
            self.child_uuids.append(child.uuid)
        self.deliverables.append(child)
