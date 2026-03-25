"""
Tests for the BugManager class.
"""

import pytest
from pathlib import Path
from prism.managers.bug_manager import BugManager
from prism.managers.storage_manager import StorageManager
from prism.managers.config_manager import ConfigManager
from prism.models.bug import BugStatus
from prism.models.config import BugType


@pytest.fixture
def bug_manager(prism_dir: Path) -> BugManager:
    """Create a BugManager with a temporary prism directory."""
    storage = StorageManager(prism_dir)
    config_mgr = ConfigManager(storage=storage)
    
    # Add a test bug type
    config = storage.load_config()
    config.bug_types.append(BugType(name="Physics", prefix="PHYS", description="Physics bugs"))
    storage.save_config(config)
    config_mgr.reload()
    
    return BugManager(storage, config_mgr)


def test_add_bug(bug_manager):
    """Test adding a bug."""
    bug = bug_manager.add_bug("Physics", "Test bug description")
    
    assert bug.bug_id.startswith("PHYS")
    assert bug.description == "Test bug description"
    assert bug.status == BugStatus.OPEN
    
    # Verify persistence
    bugs = bug_manager.list_bugs()
    assert len(bugs) == 1
    assert bugs[0].bug_id == bug.bug_id


def test_add_bug_invalid_type(bug_manager):
    """Test adding a bug with an invalid type."""
    with pytest.raises(ValueError, match="Invalid bug type"):
        bug_manager.add_bug("Invalid", "Description")


def test_get_bug(bug_manager):
    """Test retrieving a bug by ID."""
    bug = bug_manager.add_bug("Physics", "Test bug")
    retrieved = bug_manager.get_bug(bug.bug_id)
    
    assert retrieved is not None
    assert retrieved.bug_id == bug.bug_id
    
    assert bug_manager.get_bug("NONEXISTENT") is None


def test_update_bug_fields(bug_manager):
    """Test updating bug fields (non-status)."""
    bug = bug_manager.add_bug("Physics", "Original description")
    
    updated = bug_manager.update_bug(
        bug.bug_id, 
        description="Updated description",
        steps_to_reproduce="Step 1, Step 2"
    )
    
    assert updated.description == "Updated description"
    assert updated.steps_to_reproduce == "Step 1, Step 2"
    
    # Verify persistence
    retrieved = bug_manager.get_bug(bug.bug_id)
    assert retrieved.description == "Updated description"


def test_update_bug_status(bug_manager):
    """Test updating bug status with validation."""
    bug = bug_manager.add_bug("Physics", "Test bug")
    assert bug.status == BugStatus.OPEN
    
    # Valid transition: open -> reproduced
    updated = bug_manager.update_bug(bug.bug_id, status=BugStatus.REPRODUCED)
    assert updated.status == BugStatus.REPRODUCED
    
    # Invalid transition: reproduced -> fixed (must go to found first)
    with pytest.raises(ValueError, match="Invalid status transition"):
        bug_manager.update_bug(bug.bug_id, status=BugStatus.FIXED)


def test_delete_bug(bug_manager):
    """Test deleting a bug."""
    bug = bug_manager.add_bug("Physics", "To be deleted")
    assert len(bug_manager.list_bugs()) == 1
    
    success = bug_manager.delete_bug(bug.bug_id)
    assert success is True
    assert len(bug_manager.list_bugs()) == 0
    
    # Delete nonexistent
    assert bug_manager.delete_bug("NONEXISTENT") is False


def test_bug_id_generation_uniqueness(bug_manager):
    """Test that bug IDs are unique and incremented."""
    bug1 = bug_manager.add_bug("Physics", "Bug 1")
    bug2 = bug_manager.add_bug("Physics", "Bug 2")
    
    assert bug1.bug_id != bug2.bug_id
    
    # Example format: PHYS240326_01, PHYS240326_02
    counter1 = int(bug1.bug_id.split("_")[-1])
    counter2 = int(bug2.bug_id.split("_")[-1])
    assert counter2 == counter1 + 1
