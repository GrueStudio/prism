"""
Tests for ArchiveManager.

Tests cover:
- Creating lazy-loading ArchivedItem wrappers
- Archiving completed strategic items and execution trees
- Signal-based lazy loading on property access
- Cache management
"""
import tempfile
from pathlib import Path

import pytest

from prism.managers.archive_manager import ArchiveManager
from prism.managers.storage_manager import StorageManager
from prism.models.archived import ArchivedItem, LoadState
from prism.models.base import Action, Deliverable, Milestone, Objective, Phase
from prism.models.files import ArchivedStrategicFile, ExecutionFile


@pytest.fixture
def temp_prism_dir():
    """Create a temporary .prism/ directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def storage_manager(temp_prism_dir):
    """Create a StorageManager instance with temp directory."""
    return StorageManager(prism_dir=temp_prism_dir)


@pytest.fixture
def archive_manager(storage_manager):
    """Create an ArchiveManager instance."""
    return ArchiveManager(storage=storage_manager)


class TestArchiveManagerInitialization:
    """Test ArchiveManager initialization."""

    def test_archive_manager_initializes_with_storage(self, storage_manager):
        """Test ArchiveManager initializes with StorageManager."""
        archive_mgr = ArchiveManager(storage_manager)
        assert archive_mgr.storage is storage_manager

    def test_archive_manager_cache_starts_empty(self, archive_manager):
        """Test ArchiveManager cache is empty on initialization."""
        assert archive_manager._cached_strategic is None
        assert len(archive_manager._wrappers) == 0


class TestCreateArchivedWrappers:
    """Test creating ArchivedItem wrappers."""

    def test_create_archived_phase_returns_wrapper(self, archive_manager):
        """Test creating archived phase wrapper."""
        wrapper = archive_manager.create_archived_phase(position=0)

        assert isinstance(wrapper, ArchivedItem)
        assert wrapper._load_state == LoadState.NOT_LOADED
        assert wrapper._load_context.get("position") == 0

    def test_create_archived_milestone_returns_wrapper(self, archive_manager):
        """Test creating archived milestone wrapper."""
        parent_uuid = "phase-uuid-1"
        wrapper = archive_manager.create_archived_milestone(
            parent_uuid=parent_uuid, position=0
        )

        assert isinstance(wrapper, ArchivedItem)
        assert wrapper._load_state == LoadState.NOT_LOADED
        assert wrapper._load_context.get("parent_uuid") == parent_uuid
        assert wrapper._load_context.get("position") == 0

    def test_create_archived_objective_returns_wrapper(self, archive_manager):
        """Test creating archived objective wrapper."""
        parent_uuid = "milestone-uuid-1"
        wrapper = archive_manager.create_archived_objective(
            parent_uuid=parent_uuid, position=0
        )

        assert isinstance(wrapper, ArchivedItem)
        assert wrapper._load_state == LoadState.NOT_LOADED
        assert wrapper._load_context.get("parent_uuid") == parent_uuid
        assert wrapper._load_context.get("position") == 0

    def test_create_wrapper_returns_cached_instance(self, archive_manager):
        """Test that creating wrapper with same key returns cached instance."""
        wrapper1 = archive_manager.create_archived_phase(position=0)
        wrapper2 = archive_manager.create_archived_phase(position=0)

        assert wrapper1 is wrapper2

    def test_signals_are_connected(self, archive_manager):
        """Test that signals are connected on wrapper creation."""
        wrapper = archive_manager.create_archived_phase(position=0)

        # Check that callbacks are connected to signals
        assert len(wrapper.request_load.get_connections()) > 0
        assert len(wrapper.request_load_children.get_connections()) > 0


class TestArchiveStrategicItem:
    """Test archiving strategic items."""

    def test_archive_phase(self, archive_manager, storage_manager):
        """Test archiving a phase."""
        phase = Phase(
            uuid="phase-uuid-1",
            name="Test Phase",
            slug="test-phase",
            description="A test phase",
            status="completed",
        )

        archive_manager.archive_strategic_item(phase, "phase", position=0)

        # Verify file was created
        archived = storage_manager.load_archived_strategic()
        assert len(archived.phases) == 1
        assert isinstance(archived.phases[0], Phase)
        assert archived.phases[0].uuid == "phase-uuid-1"
        assert archived.phases[0].name == "Test Phase"

    def test_archive_milestone(self, archive_manager, storage_manager):
        """Test archiving a milestone."""
        milestone = Milestone(
            uuid="milestone-uuid-1",
            name="Test Milestone",
            slug="test-milestone",
            description="A test milestone",
            status="completed",
            parent_uuid="phase-uuid-1",
        )

        archive_manager.archive_strategic_item(milestone, "milestone", position=0)

        # Verify file was created
        archived = storage_manager.load_archived_strategic()
        assert len(archived.milestones) == 1
        assert isinstance(archived.milestones[0], Milestone)
        assert archived.milestones[0].uuid == "milestone-uuid-1"
        assert archived.milestones[0].parent_uuid == "phase-uuid-1"

    def test_archive_objective(self, archive_manager, storage_manager):
        """Test archiving an objective."""
        objective = Objective(
            uuid="objective-uuid-1",
            name="Test Objective",
            slug="test-objective",
            description="A test objective",
            status="completed",
            parent_uuid="milestone-uuid-1",
        )

        archive_manager.archive_strategic_item(objective, "objective", position=0)

        # Verify file was created
        archived = storage_manager.load_archived_strategic()
        assert len(archived.objectives) == 1
        assert isinstance(archived.objectives[0], Objective)
        assert archived.objectives[0].uuid == "objective-uuid-1"

    def test_archive_multiple_items(self, archive_manager, storage_manager):
        """Test archiving multiple items."""
        phase1 = Phase(uuid="phase-1", name="Phase 1", slug="phase-1", status="completed")
        phase2 = Phase(uuid="phase-2", name="Phase 2", slug="phase-2", status="completed")

        archive_manager.archive_strategic_item(phase1, "phase", position=0)
        archive_manager.archive_strategic_item(phase2, "phase", position=1)

        # Verify both items archived
        archived = storage_manager.load_archived_strategic()
        assert len(archived.phases) == 2
        assert archived.phases[0].uuid == "phase-1"
        assert archived.phases[1].uuid == "phase-2"

    def test_archive_invalidates_cache(self, archive_manager):
        """Test that archiving invalidates the strategic cache."""
        # Set cache
        archive_manager._cached_strategic = ArchivedStrategicFile()

        # Archive item
        phase = Phase(uuid="phase-1", name="Phase 1", slug="phase-1", status="completed")
        archive_manager.archive_strategic_item(phase, "phase", position=0)

        # Cache should be cleared
        assert archive_manager._cached_strategic is None


class TestArchiveExecutionTree:
    """Test archiving execution trees."""

    def test_archive_execution_tree(self, archive_manager, storage_manager):
        """Test archiving an execution tree."""
        deliverable = Deliverable(
            uuid="del-uuid-1",
            name="Test Deliverable",
            slug="test-deliverable",
            status="completed",
        )
        action = Action(
            uuid="act-uuid-1",
            name="Test Action",
            slug="test-action",
            status="completed",
        )
        deliverable.add_child(action)

        objective = Objective(
            uuid="obj-uuid-1",
            name="Test Objective",
            slug="test-objective",
            status="completed",
        )
        objective.add_child(deliverable)

        archive_manager.archive_execution_tree("obj-uuid-1", objective)

        # Verify file was created
        archived = storage_manager.load_archived_execution_tree("obj-uuid-1")
        assert archived is not None
        assert len(archived.deliverables) == 1
        assert len(archived.actions) == 1
        assert isinstance(archived.deliverables[0], Deliverable)
        assert isinstance(archived.actions[0], Action)
        assert archived.deliverables[0].uuid == "del-uuid-1"
        assert archived.actions[0].uuid == "act-uuid-1"

    def test_archive_execution_tree_multiple_deliverables(
        self, archive_manager, storage_manager
    ):
        """Test archiving execution tree with multiple deliverables."""
        objective = Objective(
            uuid="obj-uuid-1",
            name="Test Objective",
            slug="test-objective",
            status="completed",
        )

        for i in range(3):
            deliverable = Deliverable(
                uuid=f"del-uuid-{i}",
                name=f"Deliverable {i}",
                slug=f"deliverable-{i}",
                status="completed",
            )
            action = Action(
                uuid=f"act-uuid-{i}",
                name=f"Action {i}",
                slug=f"action-{i}",
                status="completed",
            )
            deliverable.add_child(action)
            objective.add_child(deliverable)

        archive_manager.archive_execution_tree("obj-uuid-1", objective)

        # Verify all items archived
        archived = storage_manager.load_archived_execution_tree("obj-uuid-1")
        assert len(archived.deliverables) == 3
        assert len(archived.actions) == 3


class TestLazyLoading:
    """Test signal-based lazy loading."""

    def test_wrapper_starts_unloaded(self, archive_manager):
        """Test that wrapper starts in NOT_LOADED state."""
        wrapper = archive_manager.create_archived_phase(position=0)
        assert wrapper._load_state == LoadState.NOT_LOADED

    def test_accessing_name_triggers_load(self, archive_manager, storage_manager):
        """Test that accessing name property triggers load."""
        # First archive a phase
        phase = Phase(
            uuid="phase-uuid-1",
            name="Test Phase",
            slug="test-phase",
            status="completed",
        )
        archive_manager.archive_strategic_item(phase, "phase", position=0)

        # Clear cache to force reload
        archive_manager.clear_cache()

        # Create wrapper
        wrapper = archive_manager.create_archived_phase(position=0)
        assert wrapper._load_state == LoadState.NOT_LOADED

        # Access name - should trigger load
        name = wrapper.name
        assert name == "Test Phase"
        # Phases load children too, so state should be CHILDREN_LOADED
        assert wrapper._load_state == LoadState.CHILDREN_LOADED

    def test_accessing_uuid_triggers_load(self, archive_manager, storage_manager):
        """Test that accessing uuid property triggers load."""
        # Archive a phase
        phase = Phase(
            uuid="phase-uuid-1",
            name="Test Phase",
            slug="test-phase",
            status="completed",
        )
        archive_manager.archive_strategic_item(phase, "phase", position=0)
        archive_manager.clear_cache()

        # Create and access
        wrapper = archive_manager.create_archived_phase(position=0)
        uuid = wrapper.uuid

        assert uuid == "phase-uuid-1"
        # Phases load children too
        assert wrapper._load_state == LoadState.CHILDREN_LOADED

    def test_accessing_children_triggers_load(self, archive_manager, storage_manager):
        """Test that accessing children property triggers children load."""
        # Archive phase with milestone
        phase = Phase(
            uuid="phase-uuid-1",
            name="Test Phase",
            slug="test-phase",
            status="completed",
        )
        milestone = Milestone(
            uuid="milestone-uuid-1",
            name="Test Milestone",
            slug="test-milestone",
            status="completed",
            parent_uuid="phase-uuid-1",
        )
        archive_manager.archive_strategic_item(phase, "phase", position=0)
        archive_manager.archive_strategic_item(milestone, "milestone", position=0)
        archive_manager.clear_cache()

        # Create phase wrapper
        wrapper = archive_manager.create_archived_phase(position=0)

        # Access children - should load milestones
        children = wrapper.children

        assert len(children) == 1
        assert children[0].item_type == "milestone"
        assert wrapper._load_state == LoadState.CHILDREN_LOADED


class TestClearCache:
    """Test cache clearing."""

    def test_clear_cache_clears_strategic_cache(self, archive_manager):
        """Test that clear_cache clears strategic cache."""
        archive_manager._cached_strategic = ArchivedStrategicFile()
        archive_manager.clear_cache()
        assert archive_manager._cached_strategic is None

    def test_clear_cache_clears_wrappers_cache(self, archive_manager):
        """Test that clear_cache clears wrappers cache."""
        wrapper = archive_manager.create_archived_phase(position=0)
        archive_manager.clear_cache()
        assert len(archive_manager._wrappers) == 0

    def test_clear_cache_allows_fresh_wrapper_creation(self, archive_manager):
        """Test that after clear_cache, new wrappers can be created."""
        wrapper1 = archive_manager.create_archived_phase(position=0)
        archive_manager.clear_cache()
        wrapper2 = archive_manager.create_archived_phase(position=0)

        # Should be different instances
        assert wrapper1 is not wrapper2


class TestCreateBaseItem:
    """Test _create_base_item helper method."""

    def test_create_phase_from_dict(self, archive_manager):
        """Test creating Phase from dict."""
        item_data = {
            "uuid": "phase-uuid",
            "name": "Test Phase",
            "slug": "test-phase",
            "status": "completed",
        }

        item = archive_manager._create_base_item(item_data, "phase")

        assert isinstance(item, Phase)
        assert item.uuid == "phase-uuid"
        assert item.name == "Test Phase"

    def test_create_milestone_from_dict(self, archive_manager):
        """Test creating Milestone from dict."""
        item_data = {
            "uuid": "milestone-uuid",
            "name": "Test Milestone",
            "slug": "test-milestone",
            "status": "completed",
            "parent_uuid": "phase-uuid",
        }

        item = archive_manager._create_base_item(item_data, "milestone")

        assert isinstance(item, Milestone)
        assert item.parent_uuid == "phase-uuid"

    def test_create_objective_from_dict(self, archive_manager):
        """Test creating Objective from dict."""
        item_data = {
            "uuid": "objective-uuid",
            "name": "Test Objective",
            "slug": "test-objective",
            "status": "completed",
            "parent_uuid": "milestone-uuid",
        }

        item = archive_manager._create_base_item(item_data, "objective")

        assert isinstance(item, Objective)

    def test_create_deliverable_from_dict(self, archive_manager):
        """Test creating Deliverable from dict."""
        item_data = {
            "uuid": "deliverable-uuid",
            "name": "Test Deliverable",
            "slug": "test-deliverable",
            "status": "completed",
            "parent_uuid": "objective-uuid",
        }

        item = archive_manager._create_base_item(item_data, "deliverable")

        assert isinstance(item, Deliverable)

    def test_create_action_from_dict(self, archive_manager):
        """Test creating Action from dict."""
        from datetime import datetime, timedelta

        item_data = {
            "uuid": "action-uuid",
            "name": "Test Action",
            "slug": "test-action",
            "status": "completed",
            "parent_uuid": "deliverable-uuid",
            "due_date": "2024-01-01T00:00:00",
            "time_spent": 3600,  # seconds
        }

        item = archive_manager._create_base_item(item_data, "action")

        assert isinstance(item, Action)
        assert item.due_date == datetime(2024, 1, 1)
        assert item.time_spent == timedelta(hours=1)

    def test_create_invalid_type_returns_none(self, archive_manager):
        """Test that invalid type returns None."""
        item = archive_manager._create_base_item({}, "invalid_type")
        assert item is None
