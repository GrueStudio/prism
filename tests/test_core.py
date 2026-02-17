"""
Tests for the Core class in prism.core module.
"""

import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

import pytest

from prism.core import Core
from prism.models import ProjectData, Phase, Milestone, Objective, Deliverable, Action
from prism.exceptions import ValidationError, NotFoundError, InvalidOperationError


@pytest.fixture
def temp_project_file():
    """Create a temporary project file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        # Write empty project data
        json.dump({"phases": [], "cursor": None}, f)
        temp_path = Path(f.name)
    yield temp_path
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def core_with_data(temp_project_file):
    """Create a Core instance with test data."""
    core = Core(temp_project_file)
    
    # Add a test phase
    core.add_item("phase", "Test Phase", "A test phase", None)
    
    # Add a test milestone
    core.add_item("milestone", "Test Milestone", "A test milestone", "test-phase")
    
    # Add a test objective
    core.add_item("objective", "Test Objective", "A test objective", "test-phase/test-milestone")
    
    return core


class TestCoreInitialization:
    """Tests for Core class initialization."""

    def test_core_initializes_with_empty_project(self, temp_project_file):
        """Test that Core initializes with empty project data."""
        core = Core(temp_project_file)
        assert isinstance(core.project_data, ProjectData)
        assert len(core.project_data.phases) == 0
        assert core.project_data.cursor is None

    def test_core_initializes_with_default_project_file(self):
        """Test that Core uses default project.json when no file specified."""
        core = Core()
        assert core.data_store.project_file == Path("project.json")


class TestAddItem:
    """Tests for Core.add_item method."""

    def test_add_phase(self, temp_project_file):
        """Test adding a phase."""
        core = Core(temp_project_file)
        core.add_item("phase", "New Phase", "Description", None)
        
        assert len(core.project_data.phases) == 1
        assert core.project_data.phases[0].name == "New Phase"
        assert core.project_data.phases[0].slug == "new-phase"

    def test_add_milestone(self, core_with_data):
        """Test adding a milestone to a phase."""
        core_with_data.add_item("milestone", "New Milestone", "Description", "test-phase")
        
        phase = core_with_data.navigator.get_item_by_path("test-phase")
        assert len(phase.milestones) == 2
        assert phase.milestones[1].name == "New Milestone"

    def test_add_objective(self, core_with_data):
        """Test adding an objective to a milestone."""
        core_with_data.add_item("objective", "New Objective", "Description", "test-phase/test-milestone")
        
        milestone = core_with_data.navigator.get_item_by_path("test-phase/test-milestone")
        assert len(milestone.objectives) == 2

    def test_add_deliverable(self, core_with_data):
        """Test adding a deliverable to an objective."""
        # First add an objective
        core_with_data.add_item("objective", "Objective 2", "Desc", "test-phase/test-milestone")
        core_with_data.add_item("deliverable", "New Deliverable", "Description", "test-phase/test-milestone/objective-2")
        
        objective = core_with_data.navigator.get_item_by_path("test-phase/test-milestone/objective-2")
        assert len(objective.deliverables) == 1

    def test_add_action(self, core_with_data):
        """Test adding an action to a deliverable."""
        # Add objective and deliverable
        core_with_data.add_item("objective", "Objective 2", "Desc", "test-phase/test-milestone")
        core_with_data.add_item("deliverable", "Deliverable 1", "Desc", "test-phase/test-milestone/objective-2")
        core_with_data.add_item("action", "New Action", "Description", "test-phase/test-milestone/objective-2/deliverable-1")
        
        deliverable = core_with_data.navigator.get_item_by_path("test-phase/test-milestone/objective-2/deliverable-1")
        assert len(deliverable.actions) == 1

    def test_add_item_invalid_type(self, temp_project_file):
        """Test adding an item with invalid type raises error."""
        core = Core(temp_project_file)
        with pytest.raises(ValidationError, match="Invalid item type"):
            core.add_item("invalid", "Name", "Description", None)

    def test_add_item_without_parent(self, temp_project_file):
        """Test adding non-phase item without parent raises error."""
        core = Core(temp_project_file)
        with pytest.raises(ValueError, match="without a parent path"):
            core.add_item("milestone", "Name", "Description", None)

    def test_add_item_invalid_parent_child_relationship(self, core_with_data):
        """Test adding item to wrong parent type raises error."""
        with pytest.raises(InvalidOperationError, match="Cannot add"):
            core_with_data.add_item("milestone", "Name", "Description", "test-phase/test-milestone")

    def test_add_item_generates_unique_slug(self, temp_project_file):
        """Test that duplicate names get unique slugs."""
        core = Core(temp_project_file)
        core.add_item("phase", "Test Phase", "First", None)
        core.add_item("phase", "Test Phase", "Second", None)
        
        assert len(core.project_data.phases) == 2
        assert core.project_data.phases[0].slug == "test-phase"
        assert core.project_data.phases[1].slug == "test-phase-1"

    def test_add_item_status_defaults_to_pending(self, temp_project_file):
        """Test that new items default to pending status."""
        core = Core(temp_project_file)
        core.add_item("phase", "Test Phase", "Description", None)
        
        assert core.project_data.phases[0].status == "pending"

    def test_add_item_completed_status_resets_to_pending(self, temp_project_file):
        """Test that completed status on new items resets to pending."""
        core = Core(temp_project_file)
        core.add_item("phase", "Test Phase", "Description", None, status="completed")
        
        assert core.project_data.phases[0].status == "pending"


class TestUpdateItem:
    """Tests for Core.update_item method."""

    def test_update_item_name(self, core_with_data):
        """Test updating an item's name."""
        core_with_data.update_item("test-phase", name="Updated Phase")

        # Slug gets regenerated when name changes, so look up by new slug
        phase = core_with_data.navigator.get_item_by_path("updated-phase")
        assert phase.name == "Updated Phase"

    def test_update_item_description(self, core_with_data):
        """Test updating an item's description."""
        core_with_data.update_item("test-phase", description="Updated description")

        # Description update doesn't change slug
        phase = core_with_data.navigator.get_item_by_path("test-phase")
        assert phase.description == "Updated description"

    def test_update_item_regenerates_slug(self, core_with_data):
        """Test that updating name regenerates slug."""
        core_with_data.update_item("test-phase", name="Completely Different Name")

        # Slug is truncated to 15 chars: "completely-diff"
        phase = core_with_data.navigator.get_item_by_path("completely-diff")
        assert phase is not None
        assert phase.name == "Completely Different Name"

    def test_update_item_with_due_date_iso(self, core_with_data):
        """Test updating an action with ISO format due date."""
        # Add deliverable and action
        core_with_data.add_item("objective", "Objective 2", "Desc", "test-phase/test-milestone")
        core_with_data.add_item("deliverable", "Deliverable 1", "Desc", "test-phase/test-milestone/objective-2")
        core_with_data.add_item("action", "Action 1", "Desc", "test-phase/test-milestone/objective-2/deliverable-1")
        
        core_with_data.update_item("test-phase/test-milestone/objective-2/deliverable-1/action-1", due_date="2025-12-31")
        
        action = core_with_data.navigator.get_item_by_path("test-phase/test-milestone/objective-2/deliverable-1/action-1")
        assert action.due_date == datetime(2025, 12, 31)

    def test_update_item_with_due_date_european_format(self, core_with_data):
        """Test updating an action with European format due date."""
        core_with_data.add_item("objective", "Objective 2", "Desc", "test-phase/test-milestone")
        core_with_data.add_item("deliverable", "Deliverable 1", "Desc", "test-phase/test-milestone/objective-2")
        core_with_data.add_item("action", "Action 1", "Desc", "test-phase/test-milestone/objective-2/deliverable-1")
        
        core_with_data.update_item("test-phase/test-milestone/objective-2/deliverable-1/action-1", due_date="31/12/2025")
        
        action = core_with_data.navigator.get_item_by_path("test-phase/test-milestone/objective-2/deliverable-1/action-1")
        assert action.due_date == datetime(2025, 12, 31)

    def test_update_item_with_due_date_written_format(self, core_with_data):
        """Test updating an action with written format due date."""
        core_with_data.add_item("objective", "Objective 2", "Desc", "test-phase/test-milestone")
        core_with_data.add_item("deliverable", "Deliverable 1", "Desc", "test-phase/test-milestone/objective-2")
        core_with_data.add_item("action", "Action 1", "Desc", "test-phase/test-milestone/objective-2/deliverable-1")
        
        core_with_data.update_item("test-phase/test-milestone/objective-2/deliverable-1/action-1", due_date="December 31, 2025")
        
        action = core_with_data.navigator.get_item_by_path("test-phase/test-milestone/objective-2/deliverable-1/action-1")
        assert action.due_date == datetime(2025, 12, 31)

    def test_update_item_invalid_date_format(self, core_with_data):
        """Test updating with invalid date format raises error."""
        core_with_data.add_item("objective", "Objective 2", "Desc", "test-phase/test-milestone")
        core_with_data.add_item("deliverable", "Deliverable 1", "Desc", "test-phase/test-milestone/objective-2")
        core_with_data.add_item("action", "Action 1", "Desc", "test-phase/test-milestone/objective-2/deliverable-1")
        
        with pytest.raises(ValidationError, match="Invalid date format"):
            core_with_data.update_item("test-phase/test-milestone/objective-2/deliverable-1/action-1", due_date="invalid")

    def test_update_item_date_too_far_past(self, core_with_data):
        """Test updating with date too far in past raises error."""
        core_with_data.add_item("objective", "Objective 2", "Desc", "test-phase/test-milestone")
        core_with_data.add_item("deliverable", "Deliverable 1", "Desc", "test-phase/test-milestone/objective-2")
        core_with_data.add_item("action", "Action 1", "Desc", "test-phase/test-milestone/objective-2/deliverable-1")
        
        with pytest.raises(ValidationError, match="too far in the past"):
            core_with_data.update_item("test-phase/test-milestone/objective-2/deliverable-1/action-1", due_date="2020-01-01")

    def test_update_item_date_too_far_future(self, core_with_data):
        """Test updating with date too far in future raises error."""
        core_with_data.add_item("objective", "Objective 2", "Desc", "test-phase/test-milestone")
        core_with_data.add_item("deliverable", "Deliverable 1", "Desc", "test-phase/test-milestone/objective-2")
        core_with_data.add_item("action", "Action 1", "Desc", "test-phase/test-milestone/objective-2/deliverable-1")
        
        with pytest.raises(ValidationError, match="too far in the future"):
            core_with_data.update_item("test-phase/test-milestone/objective-2/deliverable-1/action-1", due_date="2050-01-01")

    def test_update_item_not_found(self, core_with_data):
        """Test updating non-existent item raises error."""
        with pytest.raises(NotFoundError, match="Item not found"):
            core_with_data.update_item("non-existent-path", name="New Name")

    def test_update_completed_item_raises_error(self, core_with_data):
        """Test updating completed item raises error."""
        phase = core_with_data.navigator.get_item_by_path("test-phase")
        phase.status = "completed"
        core_with_data._save_project_data()
        
        with pytest.raises(InvalidOperationError, match="completed"):
            core_with_data.update_item("test-phase", name="New Name")

    def test_update_item_no_parameters_raises_error(self, core_with_data):
        """Test updating with no parameters raises error."""
        with pytest.raises(ValidationError, match="No update parameters"):
            core_with_data.update_item("test-phase")


class TestDeleteItem:
    """Tests for Core.delete_item method."""

    def test_delete_phase(self, temp_project_file):
        """Test deleting a phase."""
        core = Core(temp_project_file)
        core.add_item("phase", "Phase to Delete", "Description", None)
        
        assert len(core.project_data.phases) == 1
        core.delete_item("phase-to-delete")
        assert len(core.project_data.phases) == 0

    def test_delete_action(self, core_with_data):
        """Test deleting an action."""
        core_with_data.add_item("objective", "Objective 2", "Desc", "test-phase/test-milestone")
        core_with_data.add_item("deliverable", "Deliverable 1", "Desc", "test-phase/test-milestone/objective-2")
        core_with_data.add_item("action", "Action to Delete", "Desc", "test-phase/test-milestone/objective-2/deliverable-1")

        deliverable = core_with_data.navigator.get_item_by_path("test-phase/test-milestone/objective-2/deliverable-1")
        assert len(deliverable.actions) == 1

        # Slug is truncated to 15 chars: "action-to-delet"
        core_with_data.delete_item("test-phase/test-milestone/objective-2/deliverable-1/action-to-delet")

        deliverable = core_with_data.navigator.get_item_by_path("test-phase/test-milestone/objective-2/deliverable-1")
        assert len(deliverable.actions) == 0

    def test_delete_completed_item_raises_error(self, core_with_data):
        """Test deleting completed item raises error."""
        phase = core_with_data.navigator.get_item_by_path("test-phase")
        phase.status = "completed"
        core_with_data._save_project_data()
        
        with pytest.raises(InvalidOperationError, match="completed"):
            core_with_data.delete_item("test-phase")

    def test_delete_nonexistent_item_raises_error(self, core_with_data):
        """Test deleting non-existent item raises error."""
        with pytest.raises(NotFoundError, match="Item not found"):
            core_with_data.delete_item("non-existent-path")


class TestGetCurrentAction:
    """Tests for Core.get_current_action and related cursor methods."""

    def test_get_current_action_none_when_no_cursor(self, temp_project_file):
        """Test that get_current_action returns None when no cursor."""
        core = Core(temp_project_file)
        assert core.get_current_action() is None

    def test_start_next_action_finds_pending_action(self, core_with_data):
        """Test that start_next_action finds and starts first pending action."""
        # Add objective with deliverable and action
        core_with_data.add_item("objective", "Objective 2", "Desc", "test-phase/test-milestone")
        core_with_data.add_item("deliverable", "Deliverable 1", "Desc", "test-phase/test-milestone/objective-2")
        core_with_data.add_item("action", "Action 1", "Desc", "test-phase/test-milestone/objective-2/deliverable-1")
        
        action = core_with_data.start_next_action()
        
        assert action is not None
        assert action.name == "Action 1"
        assert action.status == "in-progress"
        assert core_with_data.project_data.cursor is not None

    def test_complete_current_action(self, core_with_data):
        """Test completing the current action."""
        core_with_data.add_item("objective", "Objective 2", "Desc", "test-phase/test-milestone")
        core_with_data.add_item("deliverable", "Deliverable 1", "Desc", "test-phase/test-milestone/objective-2")
        core_with_data.add_item("action", "Action 1", "Desc", "test-phase/test-milestone/objective-2/deliverable-1")
        
        # Start the action
        core_with_data.start_next_action()
        
        # Complete it
        completed = core_with_data.complete_current_action()
        
        assert completed is not None
        assert completed.status == "completed"


class TestIsExecTreeComplete:
    """Tests for Core.is_exec_tree_complete method."""

    def test_exec_tree_complete_with_deliverables(self, core_with_data):
        """Test that exec tree is complete when it has deliverables."""
        core_with_data.add_item("objective", "Objective 2", "Desc", "test-phase/test-milestone")
        
        assert core_with_data.is_exec_tree_complete("test-phase/test-milestone/objective-2") is False
        
        core_with_data.add_item("deliverable", "Deliverable 1", "Desc", "test-phase/test-milestone/objective-2")
        
        assert core_with_data.is_exec_tree_complete("test-phase/test-milestone/objective-2") is True


class TestCalculateCompletionPercentage:
    """Tests for Core.calculate_completion_percentage method."""

    def test_completion_percentage_empty_objective(self, core_with_data):
        """Test completion percentage for objective with no deliverables."""
        objective = core_with_data.navigator.get_item_by_path("test-phase/test-milestone/test-objective")
        result = core_with_data.calculate_completion_percentage(objective)
        
        assert result["overall"] == 0.0

    def test_completion_percentage_objective_with_deliverables(self, core_with_data):
        """Test completion percentage for objective with deliverables."""
        core_with_data.add_item("objective", "Objective 2", "Desc", "test-phase/test-milestone")
        core_with_data.add_item("deliverable", "Deliverable 1", "Desc", "test-phase/test-milestone/objective-2")
        core_with_data.add_item("deliverable", "Deliverable 2", "Desc", "test-phase/test-milestone/objective-2")
        
        # Mark one deliverable as completed
        del1 = core_with_data.navigator.get_item_by_path("test-phase/test-milestone/objective-2/deliverable-1")
        del1.status = "completed"
        core_with_data._save_project_data()
        
        objective = core_with_data.navigator.get_item_by_path("test-phase/test-milestone/objective-2")
        result = core_with_data.calculate_completion_percentage(objective)
        
        assert result["overall"] == 50.0

    def test_completion_percentage_deliverable_with_actions(self, core_with_data):
        """Test completion percentage for deliverable with actions."""
        core_with_data.add_item("objective", "Objective 2", "Desc", "test-phase/test-milestone")
        core_with_data.add_item("deliverable", "Deliverable 1", "Desc", "test-phase/test-milestone/objective-2")
        core_with_data.add_item("action", "Action 1", "Desc", "test-phase/test-milestone/objective-2/deliverable-1")
        core_with_data.add_item("action", "Action 2", "Desc", "test-phase/test-milestone/objective-2/deliverable-1")

        # Mark one action as completed (don't update name as it changes the slug)
        action = core_with_data.navigator.get_item_by_path("test-phase/test-milestone/objective-2/deliverable-1/action-1")
        action.status = "completed"
        core_with_data._save_project_data()

        deliverable = core_with_data.navigator.get_item_by_path("test-phase/test-milestone/objective-2/deliverable-1")
        result = core_with_data.calculate_completion_percentage(deliverable)

        assert result["overall"] == 50.0


class TestGetStatusSummary:
    """Tests for Core.get_status_summary method."""

    def test_status_summary_counts_items(self, core_with_data):
        """Test that status summary correctly counts items."""
        summary = core_with_data.get_status_summary()

        assert summary["item_counts"]["Phase"]["total"] >= 1
        assert summary["item_counts"]["Milestone"]["total"] >= 1
        assert summary["item_counts"]["Objective"]["total"] >= 1

    def test_status_summary_overdue_actions(self, core_with_data):
        """Test that status summary identifies overdue actions."""
        core_with_data.add_item("objective", "Objective 2", "Desc", "test-phase/test-milestone")
        core_with_data.add_item("deliverable", "Deliverable 1", "Desc", "test-phase/test-milestone/objective-2")
        core_with_data.add_item("action", "Overdue Action", "Desc", "test-phase/test-milestone/objective-2/deliverable-1")

        # Set a past due date
        action = core_with_data.navigator.get_item_by_path("test-phase/test-milestone/objective-2/deliverable-1/overdue-action")
        action.due_date = datetime(2020, 1, 1)
        core_with_data._save_project_data()

        summary = core_with_data.get_status_summary()

        assert len(summary["overdue_actions"]) >= 1


class TestCascadeCompletion:
    """Tests for cascading completion functionality."""

    def test_cascade_action_to_deliverable(self, temp_project_file):
        """Test that completing all actions marks deliverable as complete."""
        core = Core(temp_project_file)
        
        # Create structure: phase -> milestone -> objective -> deliverable -> 2 actions
        core.add_item("phase", "Test Phase", "Desc", None)
        core.add_item("milestone", "Test Milestone", "Desc", "test-phase")
        core.add_item("objective", "Test Objective", "Desc", "test-phase/test-milestone")
        core.add_item("deliverable", "Test Deliverable", "Desc", "test-phase/test-milestone/test-objective")
        core.add_item("action", "Action 1", "Desc", "test-phase/test-milestone/test-objective/1")
        core.add_item("action", "Action 2", "Desc", "test-phase/test-milestone/test-objective/1")
        
        # Start and complete first action
        core.start_next_action()
        core.complete_current_action()
        
        # Deliverable should NOT be complete yet (1 of 2 actions complete)
        deliverable = core.navigator.get_item_by_path("test-phase/test-milestone/test-objective/1")
        assert deliverable.status != "completed"
        
        # Start and complete second action
        core.start_next_action()
        core.complete_current_action()
        
        # Now deliverable should be complete
        deliverable = core.navigator.get_item_by_path("test-phase/test-milestone/test-objective/1")
        assert deliverable.status == "completed"

    def test_cascade_deliverable_to_objective(self, temp_project_file):
        """Test that completing all deliverables marks objective as complete."""
        core = Core(temp_project_file)
        
        # Create structure with 2 deliverables, each with 1 action
        core.add_item("phase", "Test Phase", "Desc", None)
        core.add_item("milestone", "Test Milestone", "Desc", "test-phase")
        core.add_item("objective", "Test Objective", "Desc", "test-phase/test-milestone")
        core.add_item("deliverable", "Deliverable 1", "Desc", "test-phase/test-milestone/test-objective")
        core.add_item("deliverable", "Deliverable 2", "Desc", "test-phase/test-milestone/test-objective")
        core.add_item("action", "Action 1", "Desc", "test-phase/test-milestone/test-objective/deliverable-1")
        core.add_item("action", "Action 2", "Desc", "test-phase/test-milestone/test-objective/deliverable-2")
        
        # Complete all actions (which cascades to deliverables)
        core.start_next_action()
        core.complete_current_action()
        core.start_next_action()
        core.complete_current_action()
        
        # Objective should now be complete (all deliverables complete)
        objective = core.navigator.get_item_by_path("test-phase/test-milestone/test-objective")
        assert objective.status == "completed"

    def test_partial_completion_no_cascade(self, temp_project_file):
        """Test that partial completion doesn't cascade."""
        core = Core(temp_project_file)
        
        # Create structure with 2 actions
        core.add_item("phase", "Test Phase", "Desc", None)
        core.add_item("milestone", "Test Milestone", "Desc", "test-phase")
        core.add_item("objective", "Test Objective", "Desc", "test-phase/test-milestone")
        core.add_item("deliverable", "Test Deliverable", "Desc", "test-phase/test-milestone/test-objective")
        core.add_item("action", "Action 1", "Desc", "test-phase/test-milestone/test-objective/1")
        core.add_item("action", "Action 2", "Desc", "test-phase/test-milestone/test-objective/1")
        
        # Complete only first action
        core.start_next_action()
        core.complete_current_action()
        
        # Nothing should be marked complete (only 1 of 2 actions)
        deliverable = core.navigator.get_item_by_path("test-phase/test-milestone/test-objective/1")
        assert deliverable.status != "completed"
        
        objective = core.navigator.get_item_by_path("test-phase/test-milestone/test-objective")
        assert objective.status != "completed"
