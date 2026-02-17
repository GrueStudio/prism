"""
Tests for the StorageManager class in prism.storage_manager module.
"""
import json
import shutil
import tempfile
from pathlib import Path

import pytest

from prism.storage_manager import StorageManager
from prism.newmodels import (
    StrategicFile,
    ExecutionFile,
    OrphansFile,
    ConfigFile,
    Phase,
    Milestone,
    Objective,
    Deliverable,
    Action,
    Orphan,
    ItemStatus,
)


@pytest.fixture
def temp_prism_dir():
    """Create a temporary .prism/ directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def storage_manager(temp_prism_dir):
    """Create a StorageManager instance with test directory."""
    return StorageManager(temp_prism_dir)


class TestStorageManagerInitialization:
    """Tests for StorageManager class initialization."""

    def test_storage_manager_creates_prism_dir(self, temp_prism_dir):
        """Test that StorageManager creates the .prism/ directory."""
        # The fixture already creates the dir, but test that manager ensures it
        manager = StorageManager(temp_prism_dir)
        assert manager.prism_dir.exists()
        assert manager.prism_dir.is_dir()

    def test_storage_manager_default_path(self):
        """Test that StorageManager uses default .prism/ path."""
        manager = StorageManager()
        assert manager.prism_dir == Path(".prism")
        # Clean up - use rmtree since directory now contains archive subdirectory
        if Path(".prism").exists():
            shutil.rmtree(".prism")

    def test_storage_manager_initializes_with_existing_dir(self, temp_prism_dir):
        """Test that StorageManager works with existing directory."""
        # Create some files in the temp directory
        test_file = temp_prism_dir / "test.txt"
        test_file.write_text("test content")

        manager = StorageManager(temp_prism_dir)
        assert test_file.exists()


class TestAtomicWrite:
    """Tests for atomic write functionality."""

    def test_atomic_write_creates_file(self, storage_manager, temp_prism_dir):
        """Test that atomic write creates a new file."""
        test_data = {"key": "value"}
        file_path = temp_prism_dir / "test.json"

        storage_manager._atomic_write(file_path, test_data)

        assert file_path.exists()
        with open(file_path, 'r') as f:
            content = json.load(f)
        assert content == test_data

    def test_atomic_write_overwrites_existing_file(self, storage_manager, temp_prism_dir):
        """Test that atomic write overwrites existing file."""
        file_path = temp_prism_dir / "test.json"

        # Write initial data
        storage_manager._atomic_write(file_path, {"initial": "data"})

        # Overwrite with new data
        new_data = {"updated": "data"}
        storage_manager._atomic_write(file_path, new_data)

        with open(file_path, 'r') as f:
            content = json.load(f)
        assert content == new_data

    def test_atomic_write_no_temp_files_left(self, storage_manager, temp_prism_dir):
        """Test that atomic write cleans up temp files on success."""
        file_path = temp_prism_dir / "test.json"
        test_data = {"key": "value"}

        storage_manager._atomic_write(file_path, test_data)

        # Check no temp files remain
        temp_files = list(temp_prism_dir.glob(".tmp_prism_*.json"))
        assert len(temp_files) == 0


class TestStrategicStorage:
    """Tests for strategic.json storage operations."""

    def test_load_strategic_empty(self, storage_manager):
        """Test loading strategic data when file doesn't exist."""
        result = storage_manager.load_strategic()

        assert isinstance(result, StrategicFile)
        assert len(result.items) == 0

    def test_save_and_load_strategic(self, storage_manager):
        """Test saving and loading strategic data."""
        # Create strategic data with a phase
        strategic_data = StrategicFile(items=[
            {
                "uuid": "test-uuid-1",
                "name": "Test Phase",
                "description": "A test phase",
                "slug": "test-phase",
                "status": "pending",
                "parent_uuid": None,
                "children": []
            }
        ])

        storage_manager.save_strategic(strategic_data)

        # Load and verify
        loaded = storage_manager.load_strategic()
        assert len(loaded.items) == 1
        assert loaded.items[0]["name"] == "Test Phase"
        assert loaded.items[0]["uuid"] == "test-uuid-1"

    def test_save_strategic_creates_file(self, storage_manager, temp_prism_dir):
        """Test that save_strategic creates strategic.json."""
        strategic_data = StrategicFile()
        storage_manager.save_strategic(strategic_data)

        file_path = temp_prism_dir / "strategic.json"
        assert file_path.exists()


class TestExecutionStorage:
    """Tests for execution.json storage operations."""

    def test_load_execution_empty(self, storage_manager):
        """Test loading execution data when file doesn't exist."""
        result = storage_manager.load_execution()

        assert isinstance(result, ExecutionFile)
        assert len(result.deliverables) == 0
        assert len(result.actions) == 0

    def test_save_and_load_execution(self, storage_manager):
        """Test saving and loading execution data."""
        execution_data = ExecutionFile(
            deliverables=[
                {
                    "uuid": "del-uuid-1",
                    "name": "Test Deliverable",
                    "slug": "test-deliverable",
                    "status": "pending",
                    "parent_uuid": "obj-uuid-1",
                    "children": []
                }
            ],
            actions=[
                {
                    "uuid": "act-uuid-1",
                    "name": "Test Action",
                    "slug": "test-action",
                    "status": "pending",
                    "parent_uuid": "del-uuid-1"
                }
            ]
        )

        storage_manager.save_execution(execution_data)

        # Load and verify
        loaded = storage_manager.load_execution()
        assert len(loaded.deliverables) == 1
        assert len(loaded.actions) == 1
        assert loaded.deliverables[0]["name"] == "Test Deliverable"
        assert loaded.actions[0]["name"] == "Test Action"

    def test_save_execution_creates_file(self, storage_manager, temp_prism_dir):
        """Test that save_execution creates execution.json."""
        execution_data = ExecutionFile()
        storage_manager.save_execution(execution_data)

        file_path = temp_prism_dir / "execution.json"
        assert file_path.exists()


class TestConfigStorage:
    """Tests for config.json storage operations."""

    def test_load_config_default(self, storage_manager):
        """Test loading config returns defaults when file doesn't exist."""
        result = storage_manager.load_config()

        assert isinstance(result, ConfigFile)
        assert result.schema_version == "0.2.0"
        assert result.slug_max_length == 15
        assert result.percentage_round_precision == 1

    def test_save_and_load_config(self, storage_manager):
        """Test saving and loading config data."""
        config_data = ConfigFile(
            schema_version="0.3.0",
            slug_max_length=20,
            status_header_width=30
        )

        storage_manager.save_config(config_data)

        # Load and verify
        loaded = storage_manager.load_config()
        assert loaded.schema_version == "0.3.0"
        assert loaded.slug_max_length == 20
        assert loaded.status_header_width == 30

    def test_save_config_creates_file(self, storage_manager, temp_prism_dir):
        """Test that save_config creates config.json."""
        config_data = ConfigFile()
        storage_manager.save_config(config_data)

        file_path = temp_prism_dir / "config.json"
        assert file_path.exists()


class TestOrphansStorage:
    """Tests for orphans.json storage operations."""

    def test_load_orphans_empty(self, storage_manager):
        """Test loading orphans when file doesn't exist."""
        result = storage_manager.load_orphans()

        assert isinstance(result, OrphansFile)
        assert len(result.orphans) == 0

    def test_save_and_load_orphans(self, storage_manager):
        """Test saving and loading orphans data."""
        orphans_data = OrphansFile(
            orphans=[
                Orphan(
                    uuid="orphan-uuid-1",
                    name="Test Idea",
                    description="A test orphan idea"
                )
            ]
        )

        storage_manager.save_orphans(orphans_data)

        # Load and verify
        loaded = storage_manager.load_orphans()
        assert len(loaded.orphans) == 1
        assert loaded.orphans[0].name == "Test Idea"

    def test_save_orphans_creates_file(self, storage_manager, temp_prism_dir):
        """Test that save_orphans creates orphans.json."""
        orphans_data = OrphansFile()
        storage_manager.save_orphans(orphans_data)

        file_path = temp_prism_dir / "orphans.json"
        assert file_path.exists()


class TestIntegration:
    """Integration tests for StorageManager."""

    def test_save_all_load_all(self, storage_manager):
        """Test saving and loading all file types together."""
        # Create all data types
        strategic = StrategicFile(items=[
            {
                "uuid": "phase-uuid",
                "name": "Alpha Phase",
                "slug": "alpha",
                "status": "pending",
                "parent_uuid": None,
                "children": []
            }
        ])
        execution = ExecutionFile(
            deliverables=[
                {
                    "uuid": "del-uuid",
                    "name": "Test Deliverable",
                    "slug": "test-deliverable",
                    "status": "pending",
                    "parent_uuid": "obj-uuid",
                    "children": []
                }
            ],
            actions=[]
        )
        config = ConfigFile(slug_max_length=20)
        orphans = OrphansFile(
            orphans=[
                {
                    "uuid": "orphan-uuid",
                    "name": "Future Feature",
                    "description": "Something for later"
                }
            ]
        )

        # Save all
        storage_manager.save_strategic(strategic)
        storage_manager.save_execution(execution)
        storage_manager.save_config(config)
        storage_manager.save_orphans(orphans)

        # Load all and verify
        loaded_strategic = storage_manager.load_strategic()
        loaded_execution = storage_manager.load_execution()
        loaded_config = storage_manager.load_config()
        loaded_orphans = storage_manager.load_orphans()

        assert len(loaded_strategic.items) == 1
        assert len(loaded_execution.deliverables) == 1
        assert loaded_config.slug_max_length == 20
        assert len(loaded_orphans.orphans) == 1

    def test_multiple_saves_same_file(self, storage_manager):
        """Test that multiple saves to the same file work correctly."""
        config1 = ConfigFile(schema_version="1.0.0")
        config2 = ConfigFile(schema_version="2.0.0")
        config3 = ConfigFile(schema_version="3.0.0")

        storage_manager.save_config(config1)
        storage_manager.save_config(config2)
        storage_manager.save_config(config3)

        loaded = storage_manager.load_config()
        assert loaded.schema_version == "3.0.0"


class TestErrorHandling:
    """Tests for error handling."""

    def test_load_strategic_invalid_json(self, storage_manager, temp_prism_dir):
        """Test loading strategic with invalid JSON raises exception."""
        file_path = temp_prism_dir / "strategic.json"
        file_path.write_text("{invalid json}")

        with pytest.raises(Exception, match="Error loading strategic data"):
            storage_manager.load_strategic()

    def test_load_execution_invalid_json(self, storage_manager, temp_prism_dir):
        """Test loading execution with invalid JSON raises exception."""
        file_path = temp_prism_dir / "execution.json"
        file_path.write_text("{invalid json}")

        with pytest.raises(Exception, match="Error loading execution data"):
            storage_manager.load_execution()

    def test_load_config_invalid_json(self, storage_manager, temp_prism_dir):
        """Test loading config with invalid JSON raises exception."""
        file_path = temp_prism_dir / "config.json"
        file_path.write_text("{invalid json}")

        with pytest.raises(Exception, match="Error loading config"):
            storage_manager.load_config()

    def test_load_orphans_invalid_json(self, storage_manager, temp_prism_dir):
        """Test loading orphans with invalid JSON raises exception."""
        file_path = temp_prism_dir / "orphans.json"
        file_path.write_text("{invalid json}")

        with pytest.raises(Exception, match="Error loading orphans data"):
            storage_manager.load_orphans()


class TestArchiveStorage:
    """Tests for archive folder functionality."""

    def test_archive_strategic(self, storage_manager, temp_prism_dir):
        """Test archiving a strategic item."""
        item_data = {
            "uuid": "test-uuid-123",
            "name": "Archived Phase",
            "slug": "archived-phase",
            "status": "completed"
        }

        storage_manager.archive_strategic("test-uuid-123", item_data)

        # Verify archive file was created
        archive_path = temp_prism_dir / "archive" / "strategic-test-uuid-123.json"
        assert archive_path.exists()

        # Verify content
        with open(archive_path, 'r') as f:
            content = json.load(f)
        assert content["uuid"] == "test-uuid-123"
        assert content["name"] == "Archived Phase"

    def test_archive_execution_tree(self, storage_manager, temp_prism_dir):
        """Test archiving an execution tree."""
        tree_data = {
            "deliverables": [
                {
                    "uuid": "del-uuid",
                    "name": "Completed Deliverable",
                    "slug": "completed-deliverable"
                }
            ],
            "actions": [
                {
                    "uuid": "act-uuid",
                    "name": "Completed Action",
                    "slug": "completed-action"
                }
            ]
        }

        storage_manager.archive_execution_tree("my-objective", tree_data)

        # Verify archive file was created
        archive_path = temp_prism_dir / "archive" / "objective-my-objective.exec.json"
        assert archive_path.exists()

        # Verify content
        with open(archive_path, 'r') as f:
            content = json.load(f)
        assert len(content["deliverables"]) == 1
        assert len(content["actions"]) == 1

    def test_load_archived_strategic(self, storage_manager, temp_prism_dir):
        """Test loading an archived strategic item."""
        item_data = {
            "uuid": "load-test-uuid",
            "name": "Loaded Phase",
            "slug": "loaded-phase"
        }

        # First archive the item
        storage_manager.archive_strategic("load-test-uuid", item_data)

        # Then load it back
        loaded = storage_manager.load_archived_strategic("load-test-uuid")
        assert loaded is not None
        assert loaded["uuid"] == "load-test-uuid"
        assert loaded["name"] == "Loaded Phase"

    def test_load_archived_strategic_not_found(self, storage_manager):
        """Test loading a non-existent archived strategic item."""
        loaded = storage_manager.load_archived_strategic("non-existent-uuid")
        assert loaded is None

    def test_load_archived_execution_tree(self, storage_manager, temp_prism_dir):
        """Test loading an archived execution tree."""
        tree_data = {
            "deliverables": [],
            "actions": []
        }

        # First archive the tree
        storage_manager.archive_execution_tree("test-obj", tree_data)

        # Then load it back
        loaded = storage_manager.load_archived_execution_tree("test-obj")
        assert loaded is not None
        assert "deliverables" in loaded
        assert "actions" in loaded

    def test_load_archived_execution_tree_not_found(self, storage_manager):
        """Test loading a non-existent archived execution tree."""
        loaded = storage_manager.load_archived_execution_tree("non-existent")
        assert loaded is None

    def test_list_archived_strategic(self, storage_manager, temp_prism_dir):
        """Test listing all archived strategic items."""
        # Archive multiple items
        storage_manager.archive_strategic("uuid-1", {"uuid": "uuid-1", "name": "Item 1"})
        storage_manager.archive_strategic("uuid-2", {"uuid": "uuid-2", "name": "Item 2"})
        storage_manager.archive_strategic("uuid-3", {"uuid": "uuid-3", "name": "Item 3"})

        archived = storage_manager.list_archived_strategic()
        assert len(archived) == 3
        assert "uuid-1" in archived
        assert "uuid-2" in archived
        assert "uuid-3" in archived

    def test_list_archived_execution_trees(self, storage_manager, temp_prism_dir):
        """Test listing all archived execution trees."""
        # Archive multiple trees
        storage_manager.archive_execution_tree("obj-1", {"deliverables": [], "actions": []})
        storage_manager.archive_execution_tree("obj-2", {"deliverables": [], "actions": []})

        archived = storage_manager.list_archived_execution_trees()
        assert len(archived) == 2
        assert "obj-1" in archived
        assert "obj-2" in archived

    def test_archive_dir_created(self, temp_prism_dir):
        """Test that archive directory is created on initialization."""
        manager = StorageManager(temp_prism_dir)
        archive_path = temp_prism_dir / "archive"
        assert archive_path.exists()
        assert archive_path.is_dir()
