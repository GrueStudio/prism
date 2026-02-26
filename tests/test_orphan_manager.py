"""
Tests for OrphanManager.

Tests cover:
- Reading orphans
- Writing orphans
- Getting orphan by UUID and name
- Adding, removing, and updating orphans
"""

import json
import pytest

from prism.managers.orphan_manager import OrphanManager
from prism.managers.storage_manager import StorageManager
from prism.models.files import OrphansFile
from prism.models.orphan import Orphan


@pytest.fixture
def storage_manager(empty_prism_dir):
    """Fixture for a StorageManager."""
    return StorageManager(empty_prism_dir)


@pytest.fixture
def orphan_manager(storage_manager):
    """Fixture for an OrphanManager."""
    return OrphanManager(storage_manager)


class TestOrphanManager:
    """Test OrphanManager functionality."""

    def test_read_no_orphans(self, orphan_manager):
        """Test reading when no orphans file exists."""
        assert orphan_manager.read() == []

    def test_add_and_read_orphan(self, orphan_manager, storage_manager):
        """Test adding an orphan and then reading it."""
        orphan_manager.add(name="Test Orphan", description="This is a test.")
        orphans = orphan_manager.read()
        assert len(orphans) == 1
        assert orphans[0].name == "Test Orphan"

        # Verify file content
        orphans_file = storage_manager.prism_dir / "orphans.json"
        with open(orphans_file, "r") as f:
            data = json.load(f)
        assert len(data["orphans"]) == 1
        assert data["orphans"][0]["name"] == "Test Orphan"

    def test_get_by_uuid(self, orphan_manager):
        """Test getting an orphan by its UUID."""
        orphan = orphan_manager.add(name="Test", description="test")
        found_orphan = orphan_manager.get_by_uuid(orphan.uuid)
        assert found_orphan is not None
        assert found_orphan.uuid == orphan.uuid

    def test_get_by_name(self, orphan_manager):
        """Test getting an orphan by its name."""
        orphan_manager.add(name="Test Name", description="test")
        found_orphan = orphan_manager.get_by_name("Test Name")
        assert found_orphan is not None
        assert found_orphan.name == "Test Name"

    def test_remove_orphan(self, orphan_manager, storage_manager):
        """Test removing an orphan."""
        orphan = orphan_manager.add(name="To Be Removed", description="test")
        assert len(orphan_manager.read()) == 1

        removed = orphan_manager.remove(orphan.uuid)
        assert removed is True
        assert len(orphan_manager.read()) == 0

        # Verify file content
        orphans_file = storage_manager.prism_dir / "orphans.json"
        with open(orphans_file, "r") as f:
            data = json.load(f)
        assert len(data["orphans"]) == 0

    def test_update_orphan(self, orphan_manager, storage_manager):
        """Test updating an orphan."""
        orphan = orphan_manager.add(name="Original Name", description="Original desc")
        updated_orphan = orphan_manager.update(
            orphan.uuid, name="New Name", description="New desc"
        )
        assert updated_orphan is not None
        assert updated_orphan.name == "New Name"
        assert updated_orphan.description == "New desc"

        # Check that the change is persisted
        orphans = orphan_manager.read()
        assert orphans[0].name == "New Name"

        # Verify file content
        orphans_file = storage_manager.prism_dir / "orphans.json"
        with open(orphans_file, "r") as f:
            data = json.load(f)
        assert len(data["orphans"]) == 1
        assert data["orphans"][0]["name"] == "New Name"
