"""
ProjectManager for building and managing project structure.

Builds hierarchical structure from flat storage on demand.
Uses ArchivedItem wrappers from ArchiveManager for lazy-loading archived items.
"""

from typing import Dict, Optional

from prism.managers.archive_manager import ArchiveManager
from prism.managers.storage_manager import StorageManager
from prism.models.archived import ArchivedItem
from prism.models.base import (
    Action,
    Deliverable,
    Milestone,
    Objective,
    Phase,
)
from prism.models.files import ExecutionFile, StrategicFile
from prism.models.project import Project


class ProjectManager:
    """
    Manages project structure building and persistence.

    Builds hierarchical structure from flat storage.
    Flattens hierarchy back to storage on save.
    """

    def __init__(self, storage: StorageManager) -> None:
        """
        Initialize ProjectManager.

        Args:
            storage: StorageManager for persistence.
        """
        self.storage = storage
        self.archive_manager = ArchiveManager(storage)
        self.project = Project()

    def load(self) -> Project:
        """
        Load project from storage and build hierarchical structure.

        Loads active items as full objects.
        Loads archived items as ArchivedItem wrappers for lazy loading.
        Preserves order using child_uuids.

        Returns:
            Project with hierarchical structure.
        """
        strategic = self.storage.load_strategic()
        execution = self.storage.load_execution()

        self.project = Project()

        # Build all items (active + archived) in a single dict
        all_items: Dict[str, object] = {}

        # Load active phase
        if strategic.phase:
            phase = Phase(
                uuid=strategic.phase["uuid"],
                name=strategic.phase["name"],
                description=strategic.phase.get("description"),
                slug=strategic.phase["slug"],
                status=strategic.phase.get("status", "pending"),
                parent_uuid=None,
                child_uuids=strategic.phase.get("child_uuids", []),
            )
            all_items[phase.uuid] = phase
            self.project.phases.append(phase)

        # Load active milestone
        if strategic.milestone:
            milestone = Milestone(
                uuid=strategic.milestone["uuid"],
                name=strategic.milestone["name"],
                description=strategic.milestone.get("description"),
                slug=strategic.milestone["slug"],
                status=strategic.milestone.get("status", "pending"),
                parent_uuid=strategic.milestone.get("parent_uuid"),
                child_uuids=strategic.milestone.get("child_uuids", []),
            )
            all_items[milestone.uuid] = milestone

        # Load active objective
        if strategic.objective:
            objective = Objective(
                uuid=strategic.objective["uuid"],
                name=strategic.objective["name"],
                description=strategic.objective.get("description"),
                slug=strategic.objective["slug"],
                status=strategic.objective.get("status", "pending"),
                parent_uuid=strategic.objective.get("parent_uuid"),
                child_uuids=strategic.objective.get("child_uuids", []),
            )
            all_items[objective.uuid] = objective

        # Load active execution items
        for del_data in execution.deliverables:
            deliverable = Deliverable(
                uuid=del_data["uuid"],
                name=del_data["name"],
                description=del_data.get("description"),
                slug=del_data["slug"],
                status=del_data.get("status", "pending"),
                parent_uuid=del_data.get("parent_uuid"),
                child_uuids=del_data.get("child_uuids", []),
            )
            all_items[deliverable.uuid] = deliverable

        for act_data in execution.actions:
            action = Action(
                uuid=act_data["uuid"],
                name=act_data["name"],
                description=act_data.get("description"),
                slug=act_data["slug"],
                status=act_data.get("status", "pending"),
                parent_uuid=act_data.get("parent_uuid"),
                due_date=act_data.get("due_date"),
                time_spent=act_data.get("time_spent"),
            )
            all_items[action.uuid] = action

        # Load archived items as ArchivedItem wrappers
        archived = self.storage.load_all_archived_strategic()

        # Create archived phase wrappers
        for i, phase_data in enumerate(archived["phases"]):
            archived_phase = ArchivedItem(
                uuid=phase_data["uuid"],
                name=phase_data["name"],
                slug=phase_data["slug"],
                item_type="phase",
                status=phase_data.get("status", "archived"),
                parent_uuid=None,
                description=phase_data.get("description"),
                position=phase_data.get("position", i),
                storage=self.storage,
            )
            all_items[archived_phase.uuid] = archived_phase
            self.project.phases.append(archived_phase)

        # Create archived milestone wrappers
        for i, milestone_data in enumerate(archived["milestones"]):
            archived_milestone = ArchivedItem(
                uuid=milestone_data["uuid"],
                name=milestone_data["name"],
                slug=milestone_data["slug"],
                item_type="milestone",
                status=milestone_data.get("status", "archived"),
                parent_uuid=milestone_data.get("parent_uuid"),
                description=milestone_data.get("description"),
                position=milestone_data.get("position", i),
                storage=self.storage,
            )
            all_items[archived_milestone.uuid] = archived_milestone

        # Create archived objective wrappers
        for i, objective_data in enumerate(archived["objectives"]):
            archived_objective = ArchivedItem(
                uuid=objective_data["uuid"],
                name=objective_data["name"],
                slug=objective_data["slug"],
                item_type="objective",
                status=objective_data.get("status", "archived"),
                parent_uuid=objective_data.get("parent_uuid"),
                description=objective_data.get("description"),
                position=objective_data.get("position", i),
                storage=self.storage,
            )
            all_items[archived_objective.uuid] = archived_objective

        # Build hierarchy using child_uuids for ordering
        for uuid, item in all_items.items():
            if isinstance(item, (Phase, Milestone, Objective, Deliverable)):
                # Real objects: build children from child_uuids
                self._build_children(item, all_items)
            # ArchivedItem children are loaded lazily

        self.project.build_maps()
        self.project.cursor = None
        return self.project

    def _build_children(self, parent, all_items: Dict[str, object]) -> None:
        """Build children list for a parent item using child_uuids for ordering.

        Active items are shown first, then archived items.
        """
        if not hasattr(parent, "child_uuids") or not parent.child_uuids:
            return

        active_children = []
        archived_children = []

        for child_uuid in parent.child_uuids:
            if child_uuid in all_items:
                child = all_items[child_uuid]
                # Handle both real objects and ArchivedItem wrappers
                child_type = (
                    child.item_type
                    if hasattr(child, "item_type")
                    else type(child).__name__.lower()
                )

                # Determine if this is an active or archived child
                is_archived = isinstance(child, ArchivedItem) or child_type.startswith(
                    "archived"
                )

                if isinstance(parent, Phase) and (
                    isinstance(child, Milestone) or child_type == "milestone"
                ):
                    if is_archived:
                        archived_children.append(child)
                    else:
                        active_children.append(child)
                elif isinstance(parent, Milestone) and (
                    isinstance(child, Objective) or child_type == "objective"
                ):
                    if is_archived:
                        archived_children.append(child)
                    else:
                        active_children.append(child)
                elif isinstance(parent, Objective) and (
                    isinstance(child, Deliverable) or child_type == "deliverable"
                ):
                    if is_archived:
                        archived_children.append(child)
                    else:
                        active_children.append(child)
                elif isinstance(parent, Deliverable) and (
                    isinstance(child, Action) or child_type == "action"
                ):
                    if is_archived:
                        archived_children.append(child)
                    else:
                        active_children.append(child)

        # Add active children first, then archived children
        all_children = active_children + archived_children
        for child in all_children:
            if isinstance(parent, Phase):
                parent.milestones.append(child)
            elif isinstance(parent, Milestone):
                parent.objectives.append(child)
            elif isinstance(parent, Objective):
                parent.deliverables.append(child)
            elif isinstance(parent, Deliverable):
                parent.actions.append(child)

    def save(self, project: Project) -> None:
        """
        Save project to storage by flattening hierarchy.

        Args:
            project: Project with hierarchical structure.
        """
        strategic_items = []
        execution_deliverables = []
        execution_actions = []

        def traverse_phase(phase: Phase, parent_uuid: Optional[str] = None) -> None:
            strategic_items.append(
                {
                    "uuid": phase.uuid,
                    "type": "phase",
                    "name": phase.name,
                    "description": phase.description,
                    "slug": phase.slug,
                    "status": phase.status,
                    "parent_uuid": parent_uuid,
                }
            )
            for milestone in phase.milestones:
                traverse_milestone(milestone, phase.uuid)

        def traverse_milestone(milestone: Milestone, parent_uuid: str) -> None:
            strategic_items.append(
                {
                    "uuid": milestone.uuid,
                    "type": "milestone",
                    "name": milestone.name,
                    "description": milestone.description,
                    "slug": milestone.slug,
                    "status": milestone.status,
                    "parent_uuid": parent_uuid,
                }
            )
            for objective in milestone.objectives:
                traverse_objective(objective, milestone.uuid)

        def traverse_objective(objective: Objective, parent_uuid: str) -> None:
            strategic_items.append(
                {
                    "uuid": objective.uuid,
                    "type": "objective",
                    "name": objective.name,
                    "description": objective.description,
                    "slug": objective.slug,
                    "status": objective.status,
                    "parent_uuid": parent_uuid,
                }
            )
            for deliverable in objective.deliverables:
                traverse_deliverable(deliverable, objective.uuid)

        def traverse_deliverable(deliverable: Deliverable, parent_uuid: str) -> None:
            execution_deliverables.append(
                {
                    "uuid": deliverable.uuid,
                    "name": deliverable.name,
                    "description": deliverable.description,
                    "slug": deliverable.slug,
                    "status": deliverable.status,
                    "parent_uuid": parent_uuid,
                }
            )
            for action in deliverable.actions:
                traverse_action(action, deliverable.uuid)

        def traverse_action(action: Action, parent_uuid: str) -> None:
            execution_actions.append(
                {
                    "uuid": action.uuid,
                    "name": action.name,
                    "description": action.description,
                    "slug": action.slug,
                    "status": action.status,
                    "parent_uuid": parent_uuid,
                    "due_date": action.due_date.isoformat()
                    if action.due_date
                    else None,
                    "time_spent": action.time_spent,
                }
            )

        # Traverse all phases
        for phase in project.phases:
            traverse_phase(phase)

        # Save to storage
        self.storage.save_strategic(StrategicFile(items=strategic_items))
        self.storage.save_execution(
            ExecutionFile(
                deliverables=execution_deliverables,
                actions=execution_actions,
            )
        )
