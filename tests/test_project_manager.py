"""
Tests for ProjectManager.

Tests cover:
- Loading project from storage (active + archived items)
- Building hierarchical structure from flat storage
- Saving project to storage
- Cursor loading/saving
"""

from pathlib import Path

import pytest

from prism.managers.archive_manager import ArchiveManager
from prism.managers.project_manager import ProjectManager
from prism.managers.storage_manager import StorageManager
from prism.models.archived import ArchivedItem
from prism.models.base import Phase
from prism.models.files import StrategicFile


class TestProjectManagerInit:
    """Test ProjectManager initialization."""

    def test_init(self, empty_prism_dir: Path):
        """ProjectManager initializes with storage and archive manager."""
        storage = StorageManager(empty_prism_dir)
        archive_mgr = ArchiveManager(storage)
        manager = ProjectManager(storage, archive_mgr)

        assert manager.storage == storage
        assert manager.archive_manager == archive_mgr
        assert manager.project is None


class TestProjectLoad:
    """Test project loading from storage."""

    def test_load_empty_project(self, empty_prism_dir: Path):
        """Load returns empty project when no files exist."""
        storage = StorageManager(empty_prism_dir)
        archive_mgr = ArchiveManager(storage)
        manager = ProjectManager(storage, archive_mgr)

        project = manager.load()

        assert len(project.phases) == 0
        assert project.task_cursor is None
        assert project.crud_context is None

    def test_load_project_with_strategic_only(
        self, empty_prism_dir: Path, strategic_file: StrategicFile
    ):
        """Load project from strategic.json."""
        storage = StorageManager(empty_prism_dir)
        archive_mgr = ArchiveManager(storage)
        manager = ProjectManager(storage, archive_mgr)

        # Save strategic file
        storage.save_strategic(strategic_file)

        # Load project
        project = manager.load()

        assert len(project.phases) == 1
        assert project.phases[0].name == strategic_file.phase.name

    def test_load_project_with_full_hierarchy(
        self, empty_prism_dir: Path, sample_project
    ):
        """Load project rebuilds full hierarchy from storage."""
        storage = StorageManager(empty_prism_dir)
        archive_mgr = ArchiveManager(storage)
        manager = ProjectManager(storage, archive_mgr)

        # Save project
        manager.save(sample_project)

        # Load project
        loaded = manager.load()

        # Verify hierarchy
        assert len(loaded.phases) == 1
        phase = loaded.phases[0]
        assert len(phase.children) == 1
        milestone = phase.children[0]
        assert len(milestone.children) == 1
        objective = milestone.children[0]
        assert len(objective.children) == 2

    def test_load_project_with_cursors(self, empty_prism_dir: Path, sample_project):
        """Load project restores task_cursor and crud_context."""
        storage = StorageManager(empty_prism_dir)
        archive_mgr = ArchiveManager(storage)
        manager = ProjectManager(storage, archive_mgr)

        # Set cursors
        sample_project.task_cursor = (
            "phase-1/milestone-1/objective-1/deliverable-1/action-1"
        )
        sample_project.crud_context = "phase-1/milestone-1/objective-1/deliverable-1"

        # Save and load
        manager.save(sample_project)
        loaded = manager.load()

        assert loaded.task_cursor == sample_project.task_cursor
        assert loaded.crud_context == sample_project.crud_context

    def test_load_project_with_archived_items(self, empty_prism_dir: Path, mock_data):
        """Load project includes archived items as ArchivedItem wrappers."""
        storage = StorageManager(empty_prism_dir)
        archive_mgr = ArchiveManager(storage)
        manager = ProjectManager(storage, archive_mgr)

        # Create and save active phase
        phase1 = mock_data.create_phase(
            name="Active", slug="active", uuid="active-uuid"
        )
        phase2 = mock_data.create_phase(
            name="Archived", slug="archived", uuid="archived-uuid"
        )

        # Archive phase2
        archive_mgr.archive_strategic_item(phase2, "phase")

        # Save phase1 in strategic
        from prism.models.files import StrategicFile

        strategic = StrategicFile(phase_uuids=["active-uuid", "archived-uuid"])
        strategic.phase = phase1
        storage.save_strategic(strategic)

        # Load project
        project = manager.load()

        # Should have both active and archived phases
        assert len(project.phases) == 2

        # Find archived phase
        archived_phase = None
        for p in project.phases:
            if isinstance(p, ArchivedItem):
                archived_phase = p
                break

        assert archived_phase is not None
        assert archived_phase.name == "Archived"


class TestProjectSave:
    """Test project saving to storage."""

    def test_save_empty_project(self, empty_prism_dir: Path):
        """Save empty project creates minimal strategic file."""
        storage = StorageManager(empty_prism_dir)
        archive_mgr = ArchiveManager(storage)
        manager = ProjectManager(storage, archive_mgr)

        project = manager.load()
        manager.save(project)

        # Strategic file should exist
        assert (empty_prism_dir / "strategic.json").exists()

    def test_save_project_with_hierarchy(self, empty_prism_dir: Path, sample_project):
        """Save project writes strategic.json and execution.json."""
        storage = StorageManager(empty_prism_dir)
        archive_mgr = ArchiveManager(storage)
        manager = ProjectManager(storage, archive_mgr)

        manager.save(sample_project)

        # Check files exist
        assert (empty_prism_dir / "strategic.json").exists()
        assert (empty_prism_dir / "execution.json").exists()

        # Verify content
        strategic = storage.load_strategic()
        execution = storage.load_execution()

        assert strategic.phase is not None
        assert strategic.milestone is not None
        assert strategic.objective is not None
        assert len(execution.deliverables) == 2
        assert len(execution.actions) == 3

    def test_save_project_preserves_cursors(
        self, empty_prism_dir: Path, sample_project
    ):
        """Save project writes cursors to cursor.json."""
        storage = StorageManager(empty_prism_dir)
        archive_mgr = ArchiveManager(storage)
        manager = ProjectManager(storage, archive_mgr)

        sample_project.task_cursor = "test/action/path"
        sample_project.crud_context = "test/context/path"

        manager.save(sample_project)

        # Verify cursors saved
        cursor = storage.load_cursor()
        assert cursor.task_cursor == "test/action/path"
        assert cursor.crud_context == "test/context/path"

    def test_save_early_exit_for_missing_strategic(
        self, empty_prism_dir: Path, empty_project
    ):
        """Save handles project with no active strategic items."""
        storage = StorageManager(empty_prism_dir)
        archive_mgr = ArchiveManager(storage)
        manager = ProjectManager(storage, archive_mgr)

        # Save should not raise
        manager.save(empty_project)

        # Strategic file should exist (empty)
        assert (empty_prism_dir / "strategic.json").exists()


class TestProjectBuildMaps:
    """Test project UUID lookup map building."""

    def test_build_maps_creates_lookup(self, sample_project):
        """build_maps creates UUID to item lookup."""
        # Get a known UUID
        phase = sample_project.phases[0]
        phase_uuid = phase.uuid

        # Lookup should work
        found = sample_project.get_item(phase_uuid)
        assert found is phase

    def test_build_maps_includes_all_items(self, sample_project):
        """build_maps includes all items in lookup."""

        # Count items in map
        map_count = len(sample_project._id_map)

        # Should have: 1 phase + 1 milestone + 1 objective + 2 deliverables + 3 actions = 8
        assert map_count == 8


class TestProjectPlaceItem:
    """Test placing items in project hierarchy."""

    def test_place_item_adds_to_parent(self, sample_project):
        """place_item adds item to correct parent."""
        from prism.models.base import Action

        # Create new action
        action = Action(
            name="New Action",
            description="Test",
            slug="new-action",
            parent_uuid="deliverable-1-uuid",
        )

        # Place in project
        sample_project.place_item(action)

        # Find deliverable
        phase = sample_project.phases[0]
        milestone = phase.children[0]
        objective = milestone.children[0]
        deliverable = objective.children[0]

        # Action should be added
        assert action in deliverable.children

    def test_place_item_updates_map(self, sample_project):
        """place_item adds item to UUID map."""
        from prism.models.base import Action

        action = Action(
            name="New Action",
            description="Test",
            slug="new-action",
            parent_uuid="deliverable-1-uuid",
        )

        sample_project.place_item(action)

        assert sample_project.get_item(action.uuid) is action
