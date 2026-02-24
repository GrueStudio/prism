"""
Tests for ArchiveManager.

Tests cover:
- Archiving strategic items (phase, milestone, objective)
- Archiving execution trees (deliverables, actions)
- Lazy loading of archived items
- Getting archived items by UUID
"""

from pathlib import Path

from prism.managers.archive_manager import ArchiveManager
from prism.managers.storage_manager import StorageManager
from prism.models.archived import ArchivedItem


class TestArchiveManagerInit:
    """Test ArchiveManager initialization."""

    def test_init(self, empty_prism_dir: Path):
        """ArchiveManager initializes with storage manager."""
        storage = StorageManager(empty_prism_dir)
        manager = ArchiveManager(storage)

        assert manager.storage == storage


class TestArchiveStrategicItem:
    """Test archiving strategic items."""

    def test_archive_phase(self, empty_prism_dir: Path, mock_data):
        """Archive a phase with all children."""
        storage = StorageManager(empty_prism_dir)
        manager = ArchiveManager(storage)

        # Create phase with hierarchy
        phase = mock_data.create_phase(name="Phase", slug="phase", uuid="phase-uuid")
        milestone = mock_data.create_milestone(
            name="Milestone",
            slug="milestone",
            parent_uuid=phase.uuid,
            uuid="milestone-uuid",
        )
        phase.add_child(milestone)

        # Archive
        manager.archive_strategic_item(phase, "phase")

        # Verify archived
        archived = manager.get_archived_item("phase-uuid", "phase")
        assert archived is not None
        assert archived.item_type == "phase"
        assert archived.name == "Phase"

    def test_archive_milestone(self, empty_prism_dir: Path, mock_data):
        """Archive a milestone with all children."""
        storage = StorageManager(empty_prism_dir)
        manager = ArchiveManager(storage)

        milestone = mock_data.create_milestone(
            name="Milestone", slug="milestone", uuid="milestone-uuid"
        )
        objective = mock_data.create_objective(
            name="Objective",
            slug="objective",
            parent_uuid=milestone.uuid,
            uuid="objective-uuid",
        )
        milestone.add_child(objective)

        # Archive
        manager.archive_strategic_item(milestone, "milestone")

        # Verify archived
        archived = manager.get_archived_item("milestone-uuid", "milestone")
        assert archived is not None
        assert archived.item_type == "milestone"

    def test_archive_objective(self, empty_prism_dir: Path, mock_data, sample_project):
        """Archive an objective with its execution tree."""
        storage = StorageManager(empty_prism_dir)
        manager = ArchiveManager(storage)

        # Get objective from sample project
        phase = sample_project.phases[0]
        milestone = phase.children[0]
        objective = milestone.children[0]

        # Archive
        manager.archive_strategic_item(objective, "objective")

        # Verify objective archived
        archived = manager.get_archived_item(objective.uuid, "objective")
        assert archived is not None
        assert archived.item_type == "objective"

        # Verify execution tree archived
        exec_tree = storage.load_archived_execution_tree(objective.uuid)
        assert exec_tree is not None
        assert len(exec_tree.deliverables) == 2
        assert len(exec_tree.actions) == 3

    def test_archive_updates_archived_strategic_file(
        self, empty_prism_dir: Path, mock_data
    ):
        """Archiving adds item to archive/strategic.json."""
        storage = StorageManager(empty_prism_dir)
        manager = ArchiveManager(storage)

        phase = mock_data.create_phase(name="Phase", slug="phase", uuid="phase-uuid")

        manager.archive_strategic_item(phase, "phase")

        # Load archived strategic file
        archived = storage.load_archived_strategic()
        assert len(archived.phases) == 1
        assert archived.phases[0].slug == "phase"


class TestArchiveExecutionTree:
    """Test archiving execution trees."""

    def test_archive_execution_tree(self, empty_prism_dir: Path, mock_data):
        """Archive deliverables and actions under an objective."""
        storage = StorageManager(empty_prism_dir)
        manager = ArchiveManager(storage)

        objective = mock_data.create_objective(uuid="obj-uuid")
        deliv = mock_data.create_deliverable(
            name="Deliverable",
            slug="deliv",
            parent_uuid=objective.uuid,
            uuid="deliv-uuid",
        )
        action = mock_data.create_action(
            name="Action", slug="action", parent_uuid=deliv.uuid, uuid="action-uuid"
        )
        deliv.add_child(action)
        objective.add_child(deliv)

        # Archive objective (which archives execution tree)
        manager.archive_strategic_item(objective, "objective")

        # Verify archived
        exec_tree = storage.load_archived_execution_tree(objective.uuid)
        assert exec_tree is not None
        assert len(exec_tree.deliverables) == 1
        assert len(exec_tree.actions) == 1


class TestGetArchivedItem:
    """Test retrieving archived items."""

    def test_get_archived_phase(self, empty_prism_dir: Path, mock_data):
        """Get archived phase by UUID."""
        storage = StorageManager(empty_prism_dir)
        manager = ArchiveManager(storage)

        phase = mock_data.create_phase(name="Phase", slug="phase", uuid="phase-uuid")
        manager.archive_strategic_item(phase, "phase")

        archived = manager.get_archived_item("phase-uuid", "phase")
        assert archived is not None
        assert isinstance(archived, ArchivedItem)
        assert archived.name == "Phase"

    def test_get_archived_milestone(self, empty_prism_dir: Path, mock_data):
        """Get archived milestone by UUID."""
        storage = StorageManager(empty_prism_dir)
        manager = ArchiveManager(storage)

        milestone = mock_data.create_milestone(uuid="ms-uuid")
        manager.archive_strategic_item(milestone, "milestone")

        archived = manager.get_archived_item("ms-uuid", "milestone")
        assert archived is not None
        assert archived.item_type == "milestone"

    def test_get_archived_objective(self, empty_prism_dir: Path, mock_data):
        """Get archived objective by UUID."""
        storage = StorageManager(empty_prism_dir)
        manager = ArchiveManager(storage)

        objective = mock_data.create_objective(uuid="obj-uuid")
        manager.archive_strategic_item(objective, "objective")

        archived = manager.get_archived_item("obj-uuid", "objective")
        assert archived is not None
        assert archived.item_type == "objective"

    def test_get_nonexistent_archived_item(self, empty_prism_dir: Path):
        """Get archived item returns wrapper for nonexistent UUID (lazy loading)."""
        storage = StorageManager(empty_prism_dir)
        manager = ArchiveManager(storage)

        # Returns a wrapper (lazy loading), but accessing properties will fail
        # or return None since the item doesn't exist in archive
        archived = manager.get_archived_item("nonexistent-uuid", "phase")
        assert archived is not None
        assert archived.uuid == "nonexistent-uuid"
        assert archived.item_type == "phase"


class TestLazyLoading:
    """Test lazy loading of archived item children."""

    def test_archived_phase_lazy_loads_milestones(
        self, empty_prism_dir: Path, mock_data
    ):
        """Archived phase lazy-loads milestone children."""
        storage = StorageManager(empty_prism_dir)
        manager = ArchiveManager(storage)

        phase = mock_data.create_phase(name="Phase", slug="phase", uuid="phase-uuid")
        milestone = mock_data.create_milestone(
            name="Milestone", slug="milestone", parent_uuid=phase.uuid, uuid="ms-uuid"
        )
        phase.add_child(milestone)

        manager.archive_strategic_item(phase, "phase")

        # Get archived phase
        archived = manager.get_archived_item("phase-uuid", "phase")

        # Access children (triggers lazy loading)
        children = archived.children
        assert len(children) == 1
        assert children[0].item_type == "milestone"

    def test_archived_milestone_lazy_loads_objectives(
        self, empty_prism_dir: Path, mock_data
    ):
        """Archived milestone lazy-loads objective children."""
        storage = StorageManager(empty_prism_dir)
        manager = ArchiveManager(storage)

        milestone = mock_data.create_milestone(uuid="ms-uuid")
        objective = mock_data.create_objective(
            name="Objective", slug="obj", parent_uuid=milestone.uuid, uuid="obj-uuid"
        )
        milestone.add_child(objective)

        manager.archive_strategic_item(milestone, "milestone")

        archived = manager.get_archived_item("ms-uuid", "milestone")
        children = archived.children

        assert len(children) == 1
        assert children[0].item_type == "objective"

    def test_archived_objective_lazy_loads_deliverables(
        self, empty_prism_dir: Path, mock_data
    ):
        """Archived objective lazy-loads deliverables from execution tree."""
        storage = StorageManager(empty_prism_dir)
        manager = ArchiveManager(storage)

        objective = mock_data.create_objective(uuid="obj-uuid")
        deliv = mock_data.create_deliverable(
            name="Deliverable",
            slug="deliv",
            parent_uuid=objective.uuid,
            uuid="deliv-uuid",
        )
        objective.add_child(deliv)

        manager.archive_strategic_item(objective, "objective")

        archived = manager.get_archived_item("obj-uuid", "objective")
        deliverables = archived.children

        assert len(deliverables) == 1
        assert deliverables[0].item_type == "deliverable"

    def test_archived_deliverable_lazy_loads_actions(
        self, empty_prism_dir: Path, mock_data
    ):
        """Archived deliverable lazy-loads actions from execution tree."""
        storage = StorageManager(empty_prism_dir)
        manager = ArchiveManager(storage)

        objective = mock_data.create_objective(uuid="obj-uuid")
        deliv = mock_data.create_deliverable(
            name="Deliverable",
            slug="deliv",
            parent_uuid=objective.uuid,
            uuid="deliv-uuid",
        )
        action = mock_data.create_action(
            name="Action", slug="action", parent_uuid=deliv.uuid, uuid="action-uuid"
        )
        deliv.add_child(action)
        objective.add_child(deliv)

        manager.archive_strategic_item(objective, "objective")

        # Get archived deliverable through objective
        archived_obj = manager.get_archived_item("obj-uuid", "objective")
        deliverables = archived_obj.children

        assert len(deliverables) == 1
        actions = deliverables[0].children

        assert len(actions) == 1
        assert actions[0].item_type == "action"


class TestArchivedItemProperties:
    """Test ArchivedItem wrapper properties."""

    def test_archived_item_wraps_base_item(self, empty_prism_dir: Path, mock_data):
        """ArchivedItem correctly wraps a BaseItem."""
        storage = StorageManager(empty_prism_dir)
        manager = ArchiveManager(storage)

        phase = mock_data.create_phase(
            name="Test Phase",
            description="Test desc",
            slug="test-phase",
            uuid="phase-uuid",
        )
        manager.archive_strategic_item(phase, "phase")

        archived = manager.get_archived_item("phase-uuid", "phase")

        assert archived.uuid == "phase-uuid"
        assert archived.name == "Test Phase"
        assert archived.description == "Test desc"
        assert archived.slug == "test-phase"
        assert archived.item_type == "phase"

    def test_archived_item_status(self, empty_prism_dir: Path, mock_data):
        """ArchivedItem returns 'archived' status."""
        storage = StorageManager(empty_prism_dir)
        manager = ArchiveManager(storage)

        phase = mock_data.create_phase(slug="phase", uuid="phase-uuid")
        manager.archive_strategic_item(phase, "phase")

        archived = manager.get_archived_item("phase-uuid", "phase")
        assert archived.status == "archived"

    def test_archived_item_children_property(self, empty_prism_dir: Path, mock_data):
        """ArchivedItem children property triggers lazy loading."""
        storage = StorageManager(empty_prism_dir)
        manager = ArchiveManager(storage)

        milestone = mock_data.create_milestone(uuid="ms-uuid")
        objective = mock_data.create_objective(
            name="Obj", slug="obj", parent_uuid=milestone.uuid, uuid="obj-uuid"
        )
        milestone.add_child(objective)

        manager.archive_strategic_item(milestone, "milestone")

        archived = manager.get_archived_item("ms-uuid", "milestone")

        # Access via property
        children = archived.children
        assert len(children) == 1
