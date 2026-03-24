
import os
import shutil
from pathlib import Path
import pytest
from prism.managers.bug_manager import BugManager
from prism.models.bug import BugStatus

# Fixture to set up a test environment and a BugManager instance
@pytest.fixture
def bug_manager_env():
    test_dir = Path("test_prism_smart_update_pytest")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    from prism.managers.storage_manager import StorageManager
    storage = StorageManager(test_dir)
    
    from prism.models.config import BugType
    from prism.models.files import ConfigFile
    config = ConfigFile()
    config.bug_types.append(BugType(name="test", prefix="TEST"))
    storage.save_config(config)

    manager = BugManager(storage_manager=storage)
    
    yield manager
    
    shutil.rmtree(test_dir)

def test_transition_open_to_reproduced(bug_manager_env):
    manager = bug_manager_env
    bug = manager.add_bug("test", "Initial bug description.")
    steps = "1. Do this. 2. See error."
    
    updated_bug = manager.progress_bug_status(bug.bug_id, steps)
    
    assert updated_bug.status == BugStatus.REPRODUCED
    assert updated_bug.steps_to_reproduce == steps
    assert updated_bug.root_cause is None

def test_transition_reproduced_to_found(bug_manager_env):
    manager = bug_manager_env
    bug = manager.add_bug("test", "Initial bug description.")
    manager.progress_bug_status(bug.bug_id, "Steps.")
    
    cause = "Null pointer due to race condition."
    updated_bug = manager.progress_bug_status(bug.bug_id, cause)
    
    assert updated_bug.status == BugStatus.FOUND
    assert updated_bug.root_cause == cause

def test_transition_found_to_fixed(bug_manager_env):
    manager = bug_manager_env
    bug = manager.add_bug("test", "Initial bug description.")
    manager.progress_bug_status(bug.bug_id, "Steps.")
    manager.progress_bug_status(bug.bug_id, "Cause.")
    
    fix = "Added a lock to prevent race condition."
    updated_bug = manager.progress_bug_status(bug.bug_id, fix)
    
    assert updated_bug.status == BugStatus.FIXED
    assert updated_bug.fix_description == fix

def test_transition_fixed_to_implemented(bug_manager_env):
    manager = bug_manager_env
    bug = manager.add_bug("test", "Initial bug description.")
    manager.progress_bug_status(bug.bug_id, "Steps.")
    manager.progress_bug_status(bug.bug_id, "Cause.")
    manager.progress_bug_status(bug.bug_id, "Fix.")
    
    updated_bug = manager.progress_bug_status(bug.bug_id, "")
    
    assert updated_bug.status == BugStatus.IMPLEMENTED

def test_transition_terminal_state(bug_manager_env):
    manager = bug_manager_env
    bug = manager.add_bug("test", "Initial bug description.")
    manager.progress_bug_status(bug.bug_id, "Steps.")
    manager.progress_bug_status(bug.bug_id, "Cause.")
    manager.progress_bug_status(bug.bug_id, "Fix.")
    manager.progress_bug_status(bug.bug_id, "")
    
    with pytest.raises(ValueError, match="is in a terminal state"):
        manager.progress_bug_status(bug.bug_id, "Another update.")
