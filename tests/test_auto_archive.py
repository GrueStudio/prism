"""
Tests for the auto-archive functionality with event-driven architecture.
"""
import json
import tempfile
from pathlib import Path

import pytest

from prism.core import PrismCore
from prism.managers import StorageManager, get_event_bus


@pytest.fixture
def temp_prism_dir():
    """Create a temporary .prism/ directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture(autouse=True)
def reset_event_bus():
    """Reset event bus before each test."""
    bus = get_event_bus()
    bus.clear()
    yield
    bus.clear()


class TestAutoArchiveFlow:
    """Test auto-archive functionality with event-driven architecture."""

    def test_auto_archive_on_objective_completion(self, temp_prism_dir):
        """Test that completing an objective triggers auto-archive."""
        # Create PrismCore with temp directory
        core = PrismCore(prism_dir=temp_prism_dir, auto_archive_enabled=True)

        # Create a simple objective with one deliverable and one action
        # Note: slugs are truncated to 15 chars max
        core.add_item("phase", "Test Phase", "A test phase", None)
        core.add_item("milestone", "Test Milestone", "A test milestone", "test-phase")
        core.add_item("objective", "Test Objective", "A test objective", "test-phase/test-milestone")
        # Note: "Test Deliverable" -> slug truncated to 15 chars: "test-deliverabl"
        core.add_item("deliverable", "Test Deliverable", "A test deliverable", "test-phase/test-milestone/test-objective")
        # Note: "Test Action" -> slug "test-action"
        core.add_item("action", "Test Action", "A test action", "test-phase/test-milestone/test-objective/test-deliverabl")

        # Fetch fresh objects from navigator (local refs may be stale)
        objective = core.navigator.get_item_by_path("test-phase/test-milestone/test-objective")
        assert objective is not None
        from prism.models import Objective, Deliverable
        assert isinstance(objective, Objective)
        assert len(objective.deliverables) == 1
        
        deliverable = objective.deliverables[0]
        assert isinstance(deliverable, Deliverable)
        assert len(deliverable.actions) == 1

        # Start and complete the action
        action = core.start_next_action()
        assert action is not None
        assert action.status == "in-progress"

        # Complete the action - this should cascade and trigger auto-archive
        completed = core.complete_current_action()
        assert completed is not None
        assert completed.status == "completed"

        # Verify objective is now complete
        objective = core.navigator.get_item_by_path("test-phase/test-milestone/test-objective")
        assert objective.status == "completed"

        # Verify archive files were created
        archive_dir = temp_prism_dir / "archive"
        assert archive_dir.exists()

        # Check strategic archive exists (single file with all archived items)
        strategic_archive = archive_dir / "strategic.json"
        assert strategic_archive.exists()
        
        # Verify archive content
        with open(strategic_archive, 'r') as f:
            strategic_data = json.load(f)
        assert "items" in strategic_data
        assert len(strategic_data["items"]) == 1
        assert strategic_data["items"][0]["name"] == "Test Objective"
        assert strategic_data["items"][0]["status"] == "completed"

        # Check execution archive exists (per-objective file)
        execution_archives = list(archive_dir.glob("objective-*.exec.json"))
        assert len(execution_archives) == 1

        with open(execution_archives[0], 'r') as f:
            execution_data = json.load(f)
        assert execution_data["objective_slug"] == "test-objective"
        assert len(execution_data["deliverables"]) == 1
        assert len(execution_data["actions"]) == 1

    def test_auto_archive_disabled(self, temp_prism_dir):
        """Test that auto-archive can be disabled."""
        # Create PrismCore with auto-archive disabled
        core = PrismCore(prism_dir=temp_prism_dir, auto_archive_enabled=False)

        # Create test structure
        core.add_item("phase", "Test Phase", "A test phase", None)
        core.add_item("milestone", "Test Milestone", "A test milestone", "test-phase")
        core.add_item("objective", "Test Objective", "A test objective", "test-phase/test-milestone")
        core.add_item("deliverable", "Test Deliverable", "A test deliverable", "test-phase/test-milestone/test-objective")
        core.add_item("action", "Test Action", "A test action", "test-phase/test-milestone/test-objective/test-deliverabl")

        # Start and complete the action
        core.start_next_action()
        core.complete_current_action()

        # Verify NO archive files were created
        archive_dir = temp_prism_dir / "archive"
        strategic_archives = list(archive_dir.glob("strategic-*.json"))
        execution_archives = list(archive_dir.glob("objective-*.exec.json"))

        # Archives should not exist when auto-archive is disabled
        # (Note: archive dir might exist from StorageManager init, but should be empty)
        assert len(strategic_archives) == 0
        assert len(execution_archives) == 0
