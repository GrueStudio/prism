"""
Project model for the Prism CLI.

In-memory project data with hierarchical structure.
Built from flat storage on load.
Flattened back to storage on save.

Archived items are represented as ArchivedItem wrappers for lazy loading.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union

from prism.models.base import Phase, Milestone, Objective, Deliverable, Action
from prism.models.archived import ArchivedItem


@dataclass
class Project:
    """
    In-memory project data with hierarchical structure.

    Built from flat storage on load.
    Flattened back to storage on save.

    Archived items are represented as ArchivedItem wrappers for lazy loading.
    """
    phases: List[Union[Phase, ArchivedItem]] = field(default_factory=list)
    cursor: Optional[str] = None

    # Lookup maps for fast access (includes both real and archived items)
    _phase_map: Dict[str, Union[Phase, ArchivedItem]] = field(default_factory=dict)
    _milestone_map: Dict[str, Union[Milestone, ArchivedItem]] = field(default_factory=dict)
    _objective_map: Dict[str, Union[Objective, ArchivedItem]] = field(default_factory=dict)
    _deliverable_map: Dict[str, Union[Deliverable, ArchivedItem]] = field(default_factory=dict)
    _action_map: Dict[str, Union[Action, ArchivedItem]] = field(default_factory=dict)

    def build_maps(self) -> None:
        """Build lookup maps from hierarchical structure."""
        self._phase_map.clear()
        self._milestone_map.clear()
        self._objective_map.clear()
        self._deliverable_map.clear()
        self._action_map.clear()

        for phase in self.phases:
            self._phase_map[phase.uuid] = phase
            # Handle both Phase objects and ArchivedItem wrappers
            milestones = phase.milestones if isinstance(phase, Phase) else phase.children
            for milestone in milestones:
                self._milestone_map[milestone.uuid] = milestone
                # Handle both Milestone objects and ArchivedItem wrappers
                objectives = milestone.objectives if isinstance(milestone, Milestone) else milestone.children
                for objective in objectives:
                    self._objective_map[objective.uuid] = objective
                    # Handle both Objective objects and ArchivedItem wrappers
                    deliverables = objective.deliverables if isinstance(objective, Objective) else objective.get_deliverables()
                    for deliverable in deliverables:
                        self._deliverable_map[deliverable.uuid] = deliverable
                        # Handle both Deliverable objects and ArchivedItem wrappers
                        actions = deliverable.actions if isinstance(deliverable, Deliverable) else deliverable.get_actions()
                        for action in actions:
                            self._action_map[action.uuid] = action

    def get_by_uuid(self, uuid: str):
        """Get any item by UUID (real or archived)."""
        return (
            self._phase_map.get(uuid)
            or self._milestone_map.get(uuid)
            or self._objective_map.get(uuid)
            or self._deliverable_map.get(uuid)
            or self._action_map.get(uuid)
        )
