"""
Tests for the new simplified StorageManager.

These tests verify that StorageManager correctly handles read/write operations
for all file models using the new type-safe API with real model instances.
"""
import json
import tempfile
from pathlib import Path

import pytest

from prism.exceptions import StorageError
from prism.managers.storage_manager import StorageManager
from prism.models.base import Action, Deliverable, Milestone, Objective, Phase
from prism.models.files import (
    StrategicFile,
    ExecutionFile,
    ConfigFile,
    OrphansFile,
    ArchivedStrategicFile,
)
from prism.models.orphan import Orphan


@pytest.fixture
def temp_prism_dir():
    """Create a temporary .prism/ directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def storage_manager(temp_prism_dir):
    """Create a StorageManager instance with temp directory."""
    return StorageManager(prism_dir=temp_prism_dir)


class TestStorageManagerInitialization:
    """Test StorageManager initialization."""

    def test_storage_manager_creates_prism_dir(self, temp_prism_dir):
        """Test that StorageManager creates .prism/ directory."""
        nested_dir = temp_prism_dir / "nested" / "prism"
        storage = StorageManager(prism_dir=nested_dir)
        assert nested_dir.exists()
        assert (nested_dir / "archive").exists()

    def test_storage_manager_default_path(self, monkeypatch, tmp_path):
        """Test StorageManager uses .prism/ in current directory by default."""
        monkeypatch.chdir(tmp_path)
        storage = StorageManager()
        assert storage.prism_dir == Path(".prism")
        assert storage.prism_dir.exists()


class TestStrategicFileStorage:
    """Test StrategicFile read/write operations."""

    def test_load_strategic_when_file_does_not_exist(self, storage_manager):
        """Test loading strategic.json when file doesn't exist returns empty model."""
        result = storage_manager.load_strategic()
        assert isinstance(result, StrategicFile)
        assert result.phase is None
        assert result.milestone is None
        assert result.objective is None
        assert result.phase_index == 1

    def test_save_and_load_strategic(self, storage_manager):
        """Test saving and loading StrategicFile model with real model instances."""
        # Create real model instances
        phase = Phase(
            uuid="phase-uuid-1",
            name="Test Phase",
            slug="test-phase",
            description="A test phase",
            status="pending",
            child_uuids=["milestone-uuid-1"],
        )
        milestone = Milestone(
            uuid="milestone-uuid-1",
            name="Test Milestone",
            slug="test-milestone",
            description="A test milestone",
            status="pending",
            parent_uuid="phase-uuid-1",
            child_uuids=["objective-uuid-1"],
        )
        objective = Objective(
            uuid="objective-uuid-1",
            name="Test Objective",
            slug="test-objective",
            description="A test objective",
            status="pending",
            parent_uuid="milestone-uuid-1",
            child_uuids=[],
        )

        strategic = StrategicFile(
            phase=phase,
            milestone=milestone,
            objective=objective,
            phase_index=1,
            milestone_index=1,
            objective_index=1,
        )

        storage_manager.save_strategic(strategic)

        # Load and verify
        loaded = storage_manager.load_strategic()
        assert loaded.phase is not None
        assert isinstance(loaded.phase, Phase)
        assert loaded.phase.name == "Test Phase"
        assert loaded.milestone is not None
        assert isinstance(loaded.milestone, Milestone)
        assert loaded.milestone.name == "Test Milestone"
        assert loaded.objective is not None
        assert isinstance(loaded.objective, Objective)
        assert loaded.objective.name == "Test Objective"

    def test_save_strategic_creates_file(self, storage_manager, temp_prism_dir):
        """Test that save_strategic creates strategic.json."""
        strategic = StrategicFile()
        storage_manager.save_strategic(strategic)

        file_path = temp_prism_dir / "strategic.json"
        assert file_path.exists()

        # Verify content is valid JSON
        with open(file_path, "r") as f:
            data = json.load(f)
        assert isinstance(data, dict)


class TestExecutionFileStorage:
    """Test ExecutionFile read/write operations."""

    def test_load_execution_when_file_does_not_exist(self, storage_manager):
        """Test loading execution.json when file doesn't exist returns empty model."""
        result = storage_manager.load_execution()
        assert isinstance(result, ExecutionFile)
        assert len(result.deliverables) == 0
        assert len(result.actions) == 0

    def test_save_and_load_execution(self, storage_manager):
        """Test saving and loading ExecutionFile model with real model instances."""
        deliverable = Deliverable(
            uuid="del-uuid-1",
            name="Test Deliverable",
            slug="test-deliverable",
            description="A test deliverable",
            status="pending",
            parent_uuid="obj-uuid-1",
            child_uuids=["act-uuid-1"],
        )
        action = Action(
            uuid="act-uuid-1",
            name="Test Action",
            slug="test-action",
            description="A test action",
            status="pending",
            parent_uuid="del-uuid-1",
            child_uuids=[],
        )

        execution = ExecutionFile(
            deliverables=[deliverable],
            actions=[action],
        )

        storage_manager.save_execution(execution)

        # Load and verify
        loaded = storage_manager.load_execution()
        assert len(loaded.deliverables) == 1
        assert len(loaded.actions) == 1
        assert isinstance(loaded.deliverables[0], Deliverable)
        assert isinstance(loaded.actions[0], Action)
        assert loaded.deliverables[0].name == "Test Deliverable"
        assert loaded.actions[0].name == "Test Action"

    def test_save_execution_creates_file(self, storage_manager, temp_prism_dir):
        """Test that save_execution creates execution.json."""
        execution = ExecutionFile()
        storage_manager.save_execution(execution)

        file_path = temp_prism_dir / "execution.json"
        assert file_path.exists()


class TestConfigFileStorage:
    """Test ConfigFile read/write operations."""

    def test_load_config_default(self, storage_manager):
        """Test loading config.json when file doesn't exist returns default config."""
        result = storage_manager.load_config()
        assert isinstance(result, ConfigFile)
        assert result.schema_version == "0.2.0"
        assert result.slug_max_length > 0

    def test_save_and_load_config(self, storage_manager):
        """Test saving and loading ConfigFile model."""
        config = ConfigFile(
            schema_version="0.2.0",
            slug_max_length=20,
            slug_word_limit=4,
        )

        storage_manager.save_config(config)

        # Load and verify
        loaded = storage_manager.load_config()
        assert loaded.slug_max_length == 20
        assert loaded.slug_word_limit == 4


class TestOrphansFileStorage:
    """Test OrphansFile read/write operations."""

    def test_load_orphans_when_file_does_not_exist(self, storage_manager):
        """Test loading orphans.json when file doesn't exist returns empty model."""
        result = storage_manager.load_orphans()
        assert isinstance(result, OrphansFile)
        assert len(result.orphans) == 0

    def test_save_and_load_orphans(self, storage_manager):
        """Test saving and loading OrphansFile model."""
        orphan = Orphan(
            uuid="orphan-uuid-1",
            name="Test Orphan",
            description="A test orphan idea",
        )

        orphans = OrphansFile(orphans=[orphan])
        storage_manager.save_orphans(orphans)

        # Load and verify
        loaded = storage_manager.load_orphans()
        assert len(loaded.orphans) == 1
        assert loaded.orphans[0].name == "Test Orphan"


class TestArchivedStrategicFileStorage:
    """Test ArchivedStrategicFile read/write operations."""

    def test_load_archived_strategic_when_file_does_not_exist(self, storage_manager):
        """Test loading archived strategic.json when file doesn't exist returns empty model."""
        result = storage_manager.load_archived_strategic()
        assert isinstance(result, ArchivedStrategicFile)
        assert len(result.phases) == 0
        assert len(result.milestones) == 0
        assert len(result.objectives) == 0

    def test_save_and_load_archived_strategic(self, storage_manager):
        """Test saving and loading ArchivedStrategicFile model with real instances."""
        archived = ArchivedStrategicFile(
            phases=[
                Phase(
                    uuid="archived-phase-uuid",
                    name="Archived Phase",
                    slug="archived-phase",
                    description="An archived phase",
                    status="completed",
                )
            ],
            milestones=[
                Milestone(
                    uuid="archived-milestone-uuid",
                    name="Archived Milestone",
                    slug="archived-milestone",
                    description="An archived milestone",
                    status="completed",
                    parent_uuid="archived-phase-uuid",
                )
            ],
            objectives=[
                Objective(
                    uuid="archived-objective-uuid",
                    name="Archived Objective",
                    slug="archived-objective",
                    description="An archived objective",
                    status="completed",
                    parent_uuid="archived-milestone-uuid",
                )
            ],
        )

        storage_manager.save_archived_strategic(archived)

        # Load and verify
        loaded = storage_manager.load_archived_strategic()
        assert len(loaded.phases) == 1
        assert len(loaded.milestones) == 1
        assert len(loaded.objectives) == 1
        assert isinstance(loaded.phases[0], Phase)
        assert loaded.phases[0].name == "Archived Phase"

    def test_save_archived_strategic_creates_file(self, storage_manager, temp_prism_dir):
        """Test that save_archived_strategic creates archive/strategic.json."""
        archived = ArchivedStrategicFile()
        storage_manager.save_archived_strategic(archived)

        file_path = temp_prism_dir / "archive" / "strategic.json"
        assert file_path.exists()


class TestArchivedExecutionTreeStorage:
    """Test archived execution tree read/write operations."""

    def test_load_archived_execution_tree_when_not_found(self, storage_manager):
        """Test loading archived execution tree when file doesn't exist returns None."""
        result = storage_manager.load_archived_execution_tree("non-existent-uuid")
        assert result is None

    def test_save_and_load_archived_execution_tree(self, storage_manager):
        """Test saving and loading archived execution tree with real instances."""
        execution = ExecutionFile(
            deliverables=[
                Deliverable(
                    uuid="archived-del-uuid",
                    name="Archived Deliverable",
                    slug="archived-deliverable",
                    description="An archived deliverable",
                    status="completed",
                )
            ],
            actions=[
                Action(
                    uuid="archived-act-uuid",
                    name="Archived Action",
                    slug="archived-action",
                    description="An archived action",
                    status="completed",
                )
            ],
        )

        objective_uuid = "test-objective-uuid"
        storage_manager.save_archived_execution_tree(objective_uuid, execution)

        # Load and verify
        loaded = storage_manager.load_archived_execution_tree(objective_uuid)
        assert loaded is not None
        assert len(loaded.deliverables) == 1
        assert len(loaded.actions) == 1
        assert isinstance(loaded.deliverables[0], Deliverable)
        assert isinstance(loaded.actions[0], Action)
        assert loaded.deliverables[0].name == "Archived Deliverable"

    def test_archive_current_execution_tree(self, storage_manager):
        """Test archiving current execution tree."""
        # First save some active execution data
        active_execution = ExecutionFile(
            deliverables=[
                Deliverable(
                    uuid="active-del-uuid",
                    name="Active Deliverable",
                    slug="active-deliverable",
                    description="An active deliverable",
                    status="completed",
                )
            ],
            actions=[],
        )
        storage_manager.save_execution(active_execution)

        # Archive it directly
        objective_uuid = "completed-objective-uuid"
        storage_manager.save_archived_execution_tree(objective_uuid, active_execution)

        # Verify it was archived
        archived = storage_manager.load_archived_execution_tree(objective_uuid)
        assert archived is not None
        assert len(archived.deliverables) == 1
        assert archived.deliverables[0].name == "Active Deliverable"


class TestAtomicWrite:
    """Test atomic write functionality."""

    def test_atomic_write_creates_file(self, storage_manager, temp_prism_dir):
        """Test that atomic write creates file."""
        data = {"test": "data"}
        file_path = temp_prism_dir / "test.json"
        storage_manager._atomic_write(file_path, data)

        assert file_path.exists()
        with open(file_path, "r") as f:
            loaded = json.load(f)
        assert loaded == data

    def test_atomic_write_no_temp_files_left(self, storage_manager, temp_prism_dir):
        """Test that atomic write doesn't leave temp files."""
        file_path = temp_prism_dir / "test.json"
        storage_manager._atomic_write(file_path, {"test": "data"})

        # Check no temp files remain
        temp_files = list(temp_prism_dir.glob(".tmp_prism_*.json"))
        assert len(temp_files) == 0


class TestStorageErrorHandling:
    """Test error handling in StorageManager."""

    def test_load_strategic_invalid_json_raises_storage_error(
        self, storage_manager, temp_prism_dir
    ):
        """Test that loading invalid JSON raises StorageError."""
        file_path = temp_prism_dir / "strategic.json"
        file_path.write_text("invalid json {{{")

        with pytest.raises(StorageError):
            storage_manager.load_strategic()

    def test_load_execution_invalid_json_raises_storage_error(
        self, storage_manager, temp_prism_dir
    ):
        """Test that loading invalid JSON raises StorageError."""
        file_path = temp_prism_dir / "execution.json"
        file_path.write_text("not valid json")

        with pytest.raises(StorageError):
            storage_manager.load_execution()

    def test_load_config_invalid_json_raises_storage_error(
        self, storage_manager, temp_prism_dir
    ):
        """Test that loading invalid JSON raises StorageError."""
        file_path = temp_prism_dir / "config.json"
        file_path.write_text("bad json")

        with pytest.raises(StorageError):
            storage_manager.load_config()
