"""
Tests for StorageManager.

Tests cover:
- Directory creation
- Atomic writes
- All file operations (strategic, execution, cursor, config, archived)
- Error handling
"""

import json
from pathlib import Path

import pytest

from prism.exceptions import StorageError
from prism.managers.storage_manager import StorageManager
from prism.models.files import (
    ArchivedStrategicFile,
    ConfigFile,
    CursorFile,
    ExecutionFile,
    StrategicFile,
)


class TestStorageManagerInit:
    """Test StorageManager initialization."""

    def test_init_creates_prism_dir(self, temp_dir: Path):
        """StorageManager creates .prism/ directory on init."""
        prism_path = temp_dir / ".prism"
        assert not prism_path.exists()
        
        StorageManager(prism_path)
        assert prism_path.exists()
        assert (prism_path / "archive").exists()

    def test_init_default_path(self):
        """StorageManager uses .prism/ in current dir by default."""
        manager = StorageManager()
        assert manager.prism_dir == Path(".prism")

    def test_init_custom_path(self, temp_dir: Path):
        """StorageManager uses custom path when provided."""
        custom_path = temp_dir / "custom_prism"
        manager = StorageManager(custom_path)
        assert manager.prism_dir == custom_path


class TestStrategicFileOperations:
    """Test strategic.json operations."""

    def test_load_strategic_empty(self, empty_prism_dir: Path):
        """Load strategic.json returns empty StrategicFile when file doesn't exist."""
        manager = StorageManager(empty_prism_dir)
        result = manager.load_strategic()
        
        assert isinstance(result, StrategicFile)
        assert result.phase is None
        assert result.milestone is None
        assert result.objective is None

    def test_save_and_load_strategic(
        self, empty_prism_dir: Path, strategic_file: StrategicFile
    ):
        """Save and load strategic.json preserves data."""
        manager = StorageManager(empty_prism_dir)
        
        # Save
        manager.save_strategic(strategic_file)
        
        # Load
        result = manager.load_strategic()
        
        assert result.phase is not None
        assert result.phase.name == strategic_file.phase.name
        assert result.milestone is not None
        assert result.objective is not None

    def test_strategic_file_persists_correctly(self, empty_prism_dir: Path):
        """Strategic file is saved with correct JSON structure."""
        manager = StorageManager(empty_prism_dir)
        strategic = StrategicFile(phase_uuids=["uuid-1", "uuid-2"])
        
        manager.save_strategic(strategic)
        
        # Read raw JSON
        file_path = empty_prism_dir / "strategic.json"
        with open(file_path, "r") as f:
            data = json.load(f)
        
        assert "phase_uuids" in data
        assert data["phase_uuids"] == ["uuid-1", "uuid-2"]


class TestExecutionFileOperations:
    """Test execution.json operations."""

    def test_load_execution_empty(self, empty_prism_dir: Path):
        """Load execution.json returns empty ExecutionFile when file doesn't exist."""
        manager = StorageManager(empty_prism_dir)
        result = manager.load_execution()
        
        assert isinstance(result, ExecutionFile)
        assert len(result.deliverables) == 0
        assert len(result.actions) == 0

    def test_save_and_load_execution(
        self, empty_prism_dir: Path, execution_file: ExecutionFile
    ):
        """Save and load execution.json preserves data."""
        manager = StorageManager(empty_prism_dir)
        
        # Save
        manager.save_execution(execution_file)
        
        # Load
        result = manager.load_execution()
        
        assert len(result.deliverables) == len(execution_file.deliverables)
        assert len(result.actions) == len(execution_file.actions)


class TestCursorFileOperations:
    """Test cursor.json operations."""

    def test_load_cursor_empty(self, empty_prism_dir: Path):
        """Load cursor.json returns empty CursorFile when file doesn't exist."""
        manager = StorageManager(empty_prism_dir)
        result = manager.load_cursor()
        
        assert isinstance(result, CursorFile)
        assert result.task_cursor is None
        assert result.crud_context is None

    def test_save_and_load_cursor(self, empty_prism_dir: Path):
        """Save and load cursor.json preserves data."""
        manager = StorageManager(empty_prism_dir)
        cursor = CursorFile(
            task_cursor="phase-1/milestone-1/objective-1/deliverable-1/action-1",
            crud_context="phase-1/milestone-1/objective-1/deliverable-1",
        )
        
        # Save
        manager.save_cursor(cursor)
        
        # Load
        result = manager.load_cursor()
        
        assert result.task_cursor == cursor.task_cursor
        assert result.crud_context == cursor.crud_context

    def test_cursor_file_persists_correctly(self, empty_prism_dir: Path):
        """Cursor file is saved with correct JSON structure."""
        manager = StorageManager(empty_prism_dir)
        cursor = CursorFile(task_cursor="test-path", crud_context="test-context")
        
        manager.save_cursor(cursor)
        
        # Read raw JSON
        file_path = empty_prism_dir / "cursor.json"
        with open(file_path, "r") as f:
            data = json.load(f)
        
        assert data["task_cursor"] == "test-path"
        assert data["crud_context"] == "test-context"


class TestConfigFileOperations:
    """Test config.json operations."""

    def test_load_config_empty(self, empty_prism_dir: Path):
        """Load config.json returns empty ConfigFile when file doesn't exist."""
        manager = StorageManager(empty_prism_dir)
        result = manager.load_config()
        
        assert isinstance(result, ConfigFile)
        assert result.schema_version == "0.2.0"

    def test_save_and_load_config(self, empty_prism_dir: Path):
        """Save and load config.json preserves data."""
        manager = StorageManager(empty_prism_dir)
        config = ConfigFile(
            slug_max_length=20,
            slug_word_limit=5,
            status_header_width=30,
        )
        
        # Save
        manager.save_config(config)
        
        # Load
        result = manager.load_config()
        
        assert result.slug_max_length == 20
        assert result.slug_word_limit == 5
        assert result.status_header_width == 30


class TestArchivedStrategicFileOperations:
    """Test archive/strategic.json operations."""

    def test_load_archived_strategic_empty(self, empty_prism_dir: Path):
        """Load archived strategic.json returns empty when file doesn't exist."""
        manager = StorageManager(empty_prism_dir)
        result = manager.load_archived_strategic()
        
        assert isinstance(result, ArchivedStrategicFile)
        assert len(result.phases) == 0
        assert len(result.milestones) == 0
        assert len(result.objectives) == 0

    def test_save_and_load_archived_strategic(self, empty_prism_dir: Path, mock_data):
        """Save and load archived strategic.json preserves data."""
        manager = StorageManager(empty_prism_dir)
        
        # Create archived items
        archived = ArchivedStrategicFile(
            phases=[mock_data.create_phase(name="Archived Phase", slug="archived-phase")],
            milestones=[mock_data.create_milestone(name="Archived Milestone", slug="archived-milestone")],
            objectives=[mock_data.create_objective(name="Archived Objective", slug="archived-objective")],
        )
        
        # Save
        manager.save_archived_strategic(archived)
        
        # Load
        result = manager.load_archived_strategic()
        
        assert len(result.phases) == 1
        assert result.phases[0].name == "Archived Phase"
        assert len(result.milestones) == 1
        assert len(result.objectives) == 1


class TestArchivedExecutionTreeOperations:
    """Test archived execution tree operations."""

    def test_load_archived_execution_empty(self, empty_prism_dir: Path):
        """Load archived execution tree returns None when file doesn't exist."""
        manager = StorageManager(empty_prism_dir)
        result = manager.load_archived_execution_tree("test-uuid")
        
        assert result is None

    def test_save_and_load_archived_execution(
        self, empty_prism_dir: Path, execution_file: ExecutionFile
    ):
        """Save and load archived execution tree preserves data."""
        manager = StorageManager(empty_prism_dir)
        objective_uuid = "test-objective-uuid"
        
        # Save
        manager.save_archived_execution_tree(objective_uuid, execution_file)
        
        # Load
        result = manager.load_archived_execution_tree(objective_uuid)
        
        assert result is not None
        assert len(result.deliverables) == len(execution_file.deliverables)
        assert len(result.actions) == len(execution_file.actions)

    def test_archived_execution_file_naming(self, empty_prism_dir: Path):
        """Archived execution files use correct naming convention."""
        manager = StorageManager(empty_prism_dir)
        objective_uuid = "abc-123-xyz"
        execution = ExecutionFile()
        
        manager.save_archived_execution_tree(objective_uuid, execution)
        
        # Check file exists with correct name
        file_path = empty_prism_dir / "archive" / f"{objective_uuid}.exec.json"
        assert file_path.exists()


class TestAtomicWrites:
    """Test atomic write operations."""

    def test_atomic_write_creates_file(self, empty_prism_dir: Path):
        """Atomic write successfully creates file."""
        manager = StorageManager(empty_prism_dir)
        data = {"test": "data"}
        file_path = empty_prism_dir / "test.json"
        
        manager._atomic_write(file_path, data)
        
        assert file_path.exists()
        with open(file_path, "r") as f:
            loaded = json.load(f)
        assert loaded == data

    def test_atomic_write_overwrites(self, empty_prism_dir: Path):
        """Atomic write overwrites existing file."""
        manager = StorageManager(empty_prism_dir)
        file_path = empty_prism_dir / "test.json"
        
        # Write initial data
        manager._atomic_write(file_path, {"initial": "data"})
        
        # Overwrite
        manager._atomic_write(file_path, {"updated": "data"})
        
        with open(file_path, "r") as f:
            loaded = json.load(f)
        assert loaded == {"updated": "data"}

    def test_atomic_write_no_temp_files_left(self, empty_prism_dir: Path):
        """Atomic write doesn't leave temp files on success."""
        manager = StorageManager(empty_prism_dir)
        data = {"test": "data"}
        file_path = empty_prism_dir / "test.json"
        
        manager._atomic_write(file_path, data)
        
        # Check no temp files remain
        temp_files = list(empty_prism_dir.glob(".tmp_prism_*.json"))
        assert len(temp_files) == 0


class TestStorageErrors:
    """Test error handling in StorageManager."""

    def test_invalid_json_raises_storage_error(self, empty_prism_dir: Path):
        """Loading invalid JSON raises StorageError."""
        manager = StorageManager(empty_prism_dir)
        
        # Write invalid JSON
        file_path = empty_prism_dir / "strategic.json"
        with open(file_path, "w") as f:
            f.write("not valid json {{{")
        
        with pytest.raises(StorageError):
            manager.load_strategic()

    def test_write_to_invalid_path_raises(self, temp_dir: Path):
        """Writing to invalid path raises StorageError."""
        # Use a path that doesn't exist and can't be created
        invalid_path = temp_dir / "nonexistent" / "strategic.json"
        manager = StorageManager(temp_dir / ".prism")
        
        with pytest.raises(StorageError):
            manager._atomic_write(invalid_path, {"test": "data"})
