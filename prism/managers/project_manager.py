"""
ProjectManager for Prism CLI.

Builds and manages the Project object by combining:
- Active items from StorageManager
- Archived item wrappers from ArchiveManager
"""

from typing import Any, Dict, List, Optional, Union

from prism.managers.archive_manager import ArchiveManager
from prism.managers.storage_manager import StorageManager
from prism.models.archived import ArchivedItem
from prism.models.base import (
    Action,
    BaseItem,
    Deliverable,
    ItemStatus,
    Milestone,
    Objective,
    Phase,
)
from prism.models.files import (
    CursorFile,
    ExecutionFile,
    StrategicFile,
)
from prism.models.project import Project


class ProjectManager:
    """
    Manages Project object lifecycle.

    Handles:
    - Loading project from storage (active + archived items)
    - Building hierarchical structure from flat storage
    - Building lookup maps for fast UUID access
    - Saving active items to storage

    Usage:
        storage = StorageManager()
        archive_mgr = ArchiveManager(storage)
        project_mgr = ProjectManager(storage, archive_mgr)

        # Load project
        project = project_mgr.load()

        # ... use project ...

        # Save changes
        project_mgr.save(project)
    """

    def __init__(
        self,
        storage: StorageManager,
        archive_manager: ArchiveManager,
    ) -> None:
        """
        Initialize ProjectManager.

        Args:
            storage: StorageManager for loading/saving active items.
            archive_manager: ArchiveManager for getting archived item wrappers.
        """
        self.storage = storage
        self.archive_manager = archive_manager
        self.project: Optional[Project] = None

    def load(self) -> Project:
        """
        Load project from storage and build hierarchical structure.

        Combines:
        - Active items: Full BaseItem instances from strategic.json/execution.json
        - Archived items: ArchivedItem wrappers (lazy-loading) from ArchiveManager

        Returns:
            Project object with all items and lookup maps built.
        """
        # Load active items from storage
        strategic = self.storage.load_strategic()
        execution = self.storage.load_execution()

        project = Project(strategic.phase_uuids)

        # Load cursors
        cursor_file = self.storage.load_cursor()
        project.task_cursor = cursor_file.task_cursor
        project.crud_context = cursor_file.crud_context

        def _load_strategic(item, parent, item_type):
            """Load strategic item and its children, then fill in archived siblings."""
            child_uuids = parent.child_uuids.copy()
            if item:
                if isinstance(parent, Project) and isinstance(item, Phase):
                    parent.add_child(item)
                else:
                    project.place_item(item)
                child_uuids.remove(item.uuid)

            # Fill in archived siblings from child_uuids
            for uuid in list(child_uuids):
                if item and uuid == item.uuid:
                    continue
                archived = self.archive_manager.get_archived_item(uuid, item_type)
                if archived:
                    parent.add_child(archived)

        # Load phase (and archived siblings)
        _load_strategic(strategic.phase, project, "phase")

        # Load milestone if phase exists
        if strategic.milestone and strategic.phase:
            _load_strategic(strategic.milestone, strategic.phase, "milestone")

        # Load objective if milestone exists
        if strategic.objective and strategic.milestone:
            _load_strategic(strategic.objective, strategic.milestone, "objective")

        # Load execution items
        for item in execution.deliverables + execution.actions:
            project.place_item(item)

        return project

    def save(self, project: Project) -> None:
        """
        Save active project items to storage.

        Serializes active items to StrategicFile and ExecutionFile format.
        Archived items are NOT saved here - they're managed by ArchiveManager.

        Args:
            project: Project object to save.
        """
        # Save cursors first (before any early exits)
        cursor_file = CursorFile(
            task_cursor=project.task_cursor,
            crud_context=project.crud_context,
        )
        self.storage.save_cursor(cursor_file)

        def find_active_strategic(
            children: List[BaseItem | ArchivedItem | None],
        ) -> BaseItem | None:
            for child in children:
                if isinstance(child, BaseItem) and child.get_status() in [
                    ItemStatus.PENDING,
                    ItemStatus.COMPLETED,
                ]:
                    return child
            return None

        strategic_file = StrategicFile(phase_uuids=project.child_uuids)

        phase = find_active_strategic(project.phases)
        if phase and isinstance(phase, Phase):
            strategic_file.phase = phase
        else:
            self.storage.save_strategic(strategic_file)
            return

        milestone = find_active_strategic(phase.children)
        if milestone and isinstance(milestone, Milestone):
            strategic_file.milestone = milestone
        else:
            self.storage.save_strategic(strategic_file)
            return

        objective = find_active_strategic(milestone.children)
        if objective and isinstance(objective, Objective):
            strategic_file.objective = objective
        else:
            self.storage.save_strategic(strategic_file)
            return

        self.storage.save_strategic(strategic_file)

        execution_file = ExecutionFile()

        for deliverable in objective.children:
            if isinstance(deliverable, Deliverable):
                execution_file.deliverables.append(deliverable)
            for action in deliverable.children:
                if isinstance(action, Action):
                    execution_file.actions.append(action)

        self.storage.save_execution(execution_file)
