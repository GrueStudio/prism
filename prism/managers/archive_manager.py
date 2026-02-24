"""
ArchiveManager for Prism CLI.

Handles all archive operations including:
- Creating lazy-loading ArchivedItem wrappers
- Archiving completed strategic items and execution trees
- Loading archived data on-demand via signals
"""

from typing import Dict, Optional

from prism.managers.storage_manager import StorageManager
from prism.models.archived import ArchivedItem, LoadState
from prism.models.base import Action, BaseItem, Deliverable, Milestone, Objective, Phase
from prism.models.files import ArchivedStrategicFile, ExecutionFile


class ArchiveManager:
    """
    Manages archive operations for Prism.

    Handles:
    - Creating lazy-loading ArchivedItem wrappers with signals connected
    - Archiving completed strategic items and execution trees
    - Loading archived data on-demand when signals fire

    Usage:
        archive_mgr = ArchiveManager(storage)

        # Create wrappers (ProjectManager)
        phase_wrapper = archive_mgr.create_archived_phase(position=0)

        # Archive completed items (TaskManager)
        archive_mgr.archive_strategic_item(objective, "objective", position=0)
        archive_mgr.archive_execution_tree(objective.uuid, objective)
    """

    def __init__(self, storage: StorageManager) -> None:
        """
        Initialize ArchiveManager.

        Args:
            storage: StorageManager for reading/writing archive files.
        """
        self.storage = storage
        self._cached_strategic: Optional[ArchivedStrategicFile] = None
        self._wrappers: Dict[str, ArchivedItem] = {}

    # =========================================================================
    # Public API: Create wrappers (for ProjectManager)
    # =========================================================================

    def get_archived_item(self, uuid: str, item_type: str) -> ArchivedItem:
        """
        Create ArchivedItem wrapper for archived objective.

        Objective data is loaded when accessed.

        Args:
            uuid: Optional UUID if known.

        Returns:
            ArchivedItem wrapper with signals connected.
        """
        if uuid in self._wrappers:
            return self._wrappers[uuid]

        wrapper = ArchivedItem(uuid=uuid, item_type=item_type)
        wrapper.request_load.connect(lambda: self._load_strategic_data(wrapper))
        wrapper.request_load_children.connect(lambda: self._load_exec_tree(wrapper))

        self._wrappers[uuid] = wrapper
        return wrapper

    # =========================================================================
    # Public API: Archive completed items (for TaskManager)
    # =========================================================================

    def archive_strategic_item(self, item: BaseItem, item_type: str) -> None:
        """
        Archive a completed strategic item.

        Appends to archive/strategic.json.

        Args:
            item: The completed BaseItem to archive.
            item_type: Type string ('phase', 'milestone', 'objective').
        """
        # Invalidate cache
        self._cached_strategic = None

        # Load existing archived items
        archived = self.storage.load_archived_strategic()

        def append_item(am, item):
            item.status = "archived"
            if isinstance(item, Phase):
                archived.phases.append(item)
                for milestone in item.children:
                    append_item(am, milestone)
            elif isinstance(item, Milestone):
                archived.milestones.append(item)
                for objective in item.children:
                    append_item(am, objective)
            elif isinstance(item, Objective):
                archived.objectives.append(item)
                am._archive_execution_tree(item)

        append_item(self, item)
        # Save
        self.storage.save_archived_strategic(archived)

    def _archive_execution_tree(self, objective: Objective) -> None:
        """
        Archive execution tree for completed objective.

        Creates archive/{objective_uuid}.exec.json.

        Args:
            objective_uuid: UUID of objective being archived.
            objective: The completed Objective with deliverables/actions.
        """
        # Serialize deliverables and actions
        deliverables = []
        actions = []
        for deliverable in objective.children:
            deliverable.status = "archived"
            deliverables.append(deliverable)
            for action in deliverable.children:
                action.status = "archived"
                actions.append(action)

        execution = ExecutionFile(
            deliverables=deliverables,
            actions=actions,
        )

        self.storage.save_archived_execution_tree(objective.uuid, execution)

    # =========================================================================
    # Internal: Signal handlers for lazy loading
    # =========================================================================

    def _get_archived_strategic(self) -> ArchivedStrategicFile:
        """Get cached archived strategic data, loading if needed."""
        if self._cached_strategic is None:
            self._cached_strategic = self.storage.load_archived_strategic()
        return self._cached_strategic

    def _place_item(self, item: BaseItem):
        # Loading an item with no ArchivedItem placeholder
        if item.uuid not in self._wrappers:
            wrapper = ArchivedItem(item.uuid, item_type=item.item_type)
            self._wrappers[item.uuid] = wrapper
            wrapper.mark_loaded(item)
            # If parent is tracked, add this item to the parent's children
            # Note: parent_uuid is None for top-level items (phases), which correctly
            # skips this block since they have no parent to add themselves to.
            if item.parent_uuid in self._wrappers:
                parent = self._wrappers[item.parent_uuid]
                parent.add_child(wrapper)

            # Check item_type directly on BaseItem, not through wrapper
            if isinstance(item, Objective):
                wrapper.request_load_children.connect(
                    lambda: self._load_exec_tree(wrapper)
                )
            return

        archived_item = self._wrappers[item.uuid]
        archived_item.mark_loaded(item)

    def _load_strategic_data(self, wrapper: ArchivedItem) -> None:
        """
        Load ArchivedStrategicFile and populate wrapper.

        Called when request_load signal fires. Loads all phases/milestones
        with children, objectives without children.

        Args:
            wrapper: The ArchivedItem requesting load.
        """
        if wrapper._load_state != LoadState.NOT_LOADED:
            return

        archived = self._get_archived_strategic()

        for item in archived.phases + archived.milestones + archived.objectives:
            self._place_item(item)

    def _load_exec_tree(self, wrapper: ArchivedItem) -> None:
        """
        Load ArchivedExecTree and populate wrapper.

        Called when request_load_children signal fires.
        Loads the execution tree for the objective.

        Args:
            wrapper: The ArchivedItem requesting load.
        """
        if wrapper._load_state == LoadState.CHILDREN_LOADED:
            return

        if wrapper.item_type != "objective":
            raise ValueError(
                f"archived children not loaded for non-objective {wrapper.uuid}"
            )

        archived = self.storage.load_archived_execution_tree(wrapper.uuid)

        if not archived:
            raise ValueError(f"archived execution tree not found for {wrapper.uuid}")

        for item in archived.deliverables + archived.actions:
            self._place_item(item)
