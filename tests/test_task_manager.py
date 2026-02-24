"""
Tests for TaskManager.

Tests cover:
- Task operations (start, complete, next)
- Completion cascading
- Completion percentage calculations
- CRUD operations (add, update, delete)
- Slug generation
"""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from prism.exceptions import InvalidOperationError, NotFoundError, ValidationError
from prism.managers.navigation_manager import NavigationManager
from prism.managers.task_manager import TaskManager
from prism.models.base import Action, Deliverable, Objective


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def task_manager(sample_project):
    """Create TaskManager with sample project."""
    navigator = NavigationManager(sample_project)
    save_count = {"count": 0}
    
    def save_callback():
        save_count["count"] += 1
    
    manager = TaskManager(sample_project, navigator, save_callback)
    manager._save_count = save_count
    return manager


# =============================================================================
# Task Operations Tests
# =============================================================================


class TestGetCurrentAction:
    """Test get_current_action method."""

    def test_get_current_action_none_cursor(self, task_manager):
        """Get current action returns None when no cursor."""
        result = task_manager.get_current_action()
        assert result is None

    def test_get_current_action_not_action(self, task_manager):
        """Get current action returns None when cursor is not action."""
        task_manager.project.task_cursor = "phase-1/milestone-1/objective-1"
        
        result = task_manager.get_current_action()
        
        assert result is None

    def test_get_current_action_valid(self, task_manager):
        """Get current action returns action when cursor points to action."""
        task_manager.project.task_cursor = "phase-1/milestone-1/objective-1/deliverable-1/action-1"
        
        result = task_manager.get_current_action()
        
        assert result is not None
        assert result.name == "Action 1"


class TestStartNextAction:
    """Test start_next_action method."""

    def test_start_next_action_finds_pending(self, task_manager):
        """Start next action finds first pending action."""
        result = task_manager.start_next_action()
        
        assert result is not None
        assert result.status == "in-progress"
        assert task_manager.project.task_cursor is not None

    def test_start_next_action_returns_in_progress(self, task_manager):
        """Start next action returns existing in-progress action."""
        # Start an action
        task_manager.start_next_action()
        first_action = task_manager.get_current_action()
        
        # Start again should return same action
        result = task_manager.start_next_action()
        
        assert result is first_action

    def test_start_next_action_none_when_complete(self, task_manager):
        """Start next action returns None when all complete."""
        # Mark all actions complete
        phase = task_manager.project.phases[0]
        milestone = phase.children[0]
        objective = milestone.children[0]
        for deliverable in objective.children:
            for action in deliverable.children:
                action.status = "completed"
        
        result = task_manager.start_next_action()
        
        assert result is None
        assert task_manager.project.task_cursor is None

    def test_start_next_action_updates_cursor(self, task_manager):
        """Start next action updates task_cursor."""
        task_manager.start_next_action()
        
        assert task_manager.project.task_cursor is not None
        assert "action" in task_manager.project.task_cursor


class TestCompleteCurrentAction:
    """Test complete_current_action method."""

    def test_complete_current_action_none(self, task_manager):
        """Complete current action returns None when no action in progress."""
        result = task_manager.complete_current_action()
        assert result is None

    def test_complete_current_action_success(self, task_manager):
        """Complete current action marks action completed."""
        # Start action first
        task_manager.start_next_action()
        
        result = task_manager.complete_current_action()
        
        assert result is not None
        assert result.status == "completed"

    def test_complete_current_action_updates_timestamp(self, task_manager):
        """Complete current action updates updated_at."""
        task_manager.start_next_action()
        action = task_manager.get_current_action()
        before = action.updated_at
        
        task_manager.complete_current_action()
        
        assert action.updated_at > before

    def test_complete_current_action_triggers_save(self, task_manager):
        """Complete current action triggers save callback."""
        task_manager.start_next_action()
        before = task_manager._save_count["count"]
        
        task_manager.complete_current_action()
        
        assert task_manager._save_count["count"] > before


class TestCompleteCurrentAndStartNext:
    """Test complete_current_and_start_next method."""

    def test_complete_and_start_next_success(self, task_manager):
        """Complete and start next returns both actions."""
        task_manager.start_next_action()
        
        completed, next_action = task_manager.complete_current_and_start_next()
        
        assert completed is not None
        assert completed.status == "completed"
        # Next action might be None if all complete or might be another action

    def test_complete_and_start_next_none_when_not_started(self, task_manager):
        """Complete and start next returns (None, None) when not started."""
        completed, next_action = task_manager.complete_current_and_start_next()
        
        assert completed is None
        assert next_action is None


# =============================================================================
# Completion Cascading Tests
# =============================================================================


class TestCascadeCompletion:
    """Test completion cascading up the tree."""

    def test_cascade_completes_deliverable_when_all_actions_done(
        self, task_manager, mock_data
    ):
        """Cascade marks deliverable complete when all actions complete."""
        # Start and complete all actions in deliverable-1
        task_manager.project.task_cursor = (
            "phase-1/milestone-1/objective-1/deliverable-1/action-1"
        )
        task_manager.start_next_action()
        task_manager.complete_current_action()

        task_manager.project.task_cursor = (
            "phase-1/milestone-1/objective-1/deliverable-1/action-2"
        )
        task_manager.start_next_action()
        task_manager.complete_current_action()

        # Deliverable should be complete
        phase = task_manager.project.phases[0]
        milestone = phase.children[0]
        objective = milestone.children[0]
        deliverable = objective.children[0]

        assert deliverable.status == "completed"

    def test_cascade_completes_objective_when_all_deliverables_done(
        self, task_manager
    ):
        """Cascade marks objective complete when all deliverables complete."""
        # Complete all actions in all deliverables
        phase = task_manager.project.phases[0]
        milestone = phase.children[0]
        objective = milestone.children[0]
        
        for deliverable in objective.children:
            for action in deliverable.children:
                action.status = "completed"
                action.updated_at = datetime.now()
            deliverable.status = "completed"
        
        # Manually trigger cascade on last deliverable
        task_manager._cascade_completion(deliverable)
        
        assert objective.status == "completed"

    def test_cascade_stops_at_objective(self, task_manager):
        """Cascade does not propagate to milestone or phase."""
        # Complete everything
        phase = task_manager.project.phases[0]
        milestone = phase.children[0]
        objective = milestone.children[0]
        
        for deliverable in objective.children:
            for action in deliverable.children:
                action.status = "completed"
            deliverable.status = "completed"
        objective.status = "completed"
        
        # Trigger cascade
        task_manager._cascade_completion(objective)
        
        # Milestone and phase should NOT be completed
        assert milestone.status != "completed"
        assert phase.status != "completed"


# =============================================================================
# Completion Percentage Tests
# =============================================================================


class TestCalculateCompletionPercentage:
    """Test completion percentage calculations."""

    def test_percentage_deliverable_partial(self, task_manager):
        """Calculate percentage for partially complete deliverable."""
        phase = task_manager.project.phases[0]
        milestone = phase.children[0]
        objective = milestone.children[0]
        deliverable = objective.children[0]
        
        # 1 of 2 actions complete
        deliverable.children[0].status = "completed"
        
        result = task_manager.calculate_completion_percentage(deliverable)
        
        assert result["overall"] == 50.0

    def test_percentage_deliverable_complete(self, task_manager):
        """Calculate percentage for complete deliverable."""
        phase = task_manager.project.phases[0]
        milestone = phase.children[0]
        objective = milestone.children[0]
        deliverable = objective.children[0]
        
        for action in deliverable.children:
            action.status = "completed"
        
        result = task_manager.calculate_completion_percentage(deliverable)
        
        assert result["overall"] == 100.0

    def test_percentage_objective_partial(self, task_manager):
        """Calculate percentage for partially complete objective."""
        phase = task_manager.project.phases[0]
        milestone = phase.children[0]
        objective = milestone.children[0]
        
        # Complete first deliverable
        for action in objective.children[0].children:
            action.status = "completed"
        objective.children[0].status = "completed"
        
        result = task_manager.calculate_completion_percentage(objective)
        
        # 1 of 2 deliverables complete = 50%
        assert result["overall"] == 50.0

    def test_percentage_empty_item(self, task_manager, mock_data):
        """Calculate percentage for item with no children."""
        empty_deliv = mock_data.create_deliverable(slug="empty")
        
        result = task_manager.calculate_completion_percentage(empty_deliv)
        
        assert result["overall"] == 0.0


class TestIsExecTreeComplete:
    """Test execution tree completion check."""

    def test_exec_tree_complete(self, task_manager):
        """Is exec tree complete returns True when all done."""
        phase = task_manager.project.phases[0]
        milestone = phase.children[0]
        objective = milestone.children[0]
        
        for deliverable in objective.children:
            for action in deliverable.children:
                action.status = "completed"
            deliverable.status = "completed"
        
        result = task_manager.is_exec_tree_complete(objective)
        
        assert result is True

    def test_exec_tree_incomplete(self, task_manager):
        """Is exec tree complete returns False when not all done."""
        phase = task_manager.project.phases[0]
        milestone = phase.children[0]
        objective = milestone.children[0]
        
        result = task_manager.is_exec_tree_complete(objective)
        
        assert result is False


# =============================================================================
# CRUD - Add Item Tests
# =============================================================================


class TestAddItem:
    """Test add_item method."""

    def test_add_phase(self, task_manager, mock_data):
        """Add phase to project."""
        result = task_manager.add_item(
            item_type="phase",
            name="New Phase",
            description="Test phase",
            parent_path=None,
        )
        
        assert result is not None
        assert result.name == "New Phase"
        assert result.slug == "new-phase"
        assert len(task_manager.project.phases) == 2

    def test_add_milestone(self, task_manager):
        """Add milestone to phase."""
        result = task_manager.add_item(
            item_type="milestone",
            name="New Milestone",
            description="Test milestone",
            parent_path="phase-1",
        )
        
        assert result is not None
        assert result.name == "New Milestone"
        assert len(task_manager.project.phases[0].children) == 2

    def test_add_action(self, task_manager):
        """Add action to deliverable."""
        result = task_manager.add_item(
            item_type="action",
            name="New Action",
            description="Test action",
            parent_path="phase-1/milestone-1/objective-1/deliverable-1",
        )
        
        assert result is not None
        assert result.name == "New Action"

    def test_add_item_invalid_parent_type(self, task_manager):
        """Add item raises error for invalid parent type."""
        with pytest.raises(InvalidOperationError):
            task_manager.add_item(
                item_type="action",
                name="Bad Action",
                description="Test",
                parent_path="phase-1",  # Actions need deliverable parent
            )

    def test_add_item_parent_not_found(self, task_manager):
        """Add item raises error when parent not found."""
        with pytest.raises(NotFoundError):
            task_manager.add_item(
                item_type="milestone",
                name="Bad Milestone",
                description="Test",
                parent_path="nonexistent-path",
            )


# =============================================================================
# CRUD - Update Item Tests
# =============================================================================


class TestUpdateItem:
    """Test update_item method."""

    def test_update_name(self, task_manager):
        """Update item name."""
        result = task_manager.update_item(
            path="phase-1",
            name="Updated Phase",
        )
        
        assert result.name == "Updated Phase"
        assert result.slug != "phase-1"  # Slug regenerated

    def test_update_description(self, task_manager):
        """Update item description."""
        result = task_manager.update_item(
            path="phase-1",
            description="New description",
        )
        
        assert result.description == "New description"

    def test_update_status(self, task_manager):
        """Update item status."""
        result = task_manager.update_item(
            path="phase-1",
            status="in-progress",
        )
        
        assert result.status == "in-progress"

    def test_update_due_date(self, task_manager):
        """Update action due date."""
        result = task_manager.update_item(
            path="phase-1/milestone-1/objective-1/deliverable-1/action-1",
            due_date="2025-12-31",
        )
        
        assert result.due_date is not None
        assert result.due_date.year == 2025

    def test_update_completed_item_raises(self, task_manager):
        """Update raises error for completed item."""
        # First complete the item
        phase = task_manager.project.phases[0]
        phase.status = "completed"
        
        with pytest.raises(InvalidOperationError):
            task_manager.update_item(
                path="phase-1",
                name="Cannot Update",
            )

    def test_update_no_params_raises(self, task_manager):
        """Update raises error when no params provided."""
        with pytest.raises(ValidationError):
            task_manager.update_item(path="phase-1")


# =============================================================================
# CRUD - Delete Item Tests
# =============================================================================


class TestDeleteItem:
    """Test delete_item method."""

    def test_delete_action(self, task_manager):
        """Delete action from deliverable."""
        task_manager.delete_item(
            path="phase-1/milestone-1/objective-1/deliverable-1/action-1"
        )
        
        phase = task_manager.project.phases[0]
        milestone = phase.children[0]
        objective = milestone.children[0]
        deliverable = objective.children[0]
        
        assert len(deliverable.children) == 1

    def test_delete_phase(self, task_manager):
        """Delete phase from project."""
        # Add a second phase first
        task_manager.add_item(
            item_type="phase",
            name="Phase 2",
            description="To be deleted",
            parent_path=None,
        )
        
        task_manager.delete_item(path="phase-2")
        
        assert len(task_manager.project.phases) == 1

    def test_delete_completed_item_raises(self, task_manager):
        """Delete raises error for completed item."""
        phase = task_manager.project.phases[0]
        phase.status = "completed"
        
        with pytest.raises(InvalidOperationError):
            task_manager.delete_item(path="phase-1")

    def test_delete_not_found_raises(self, task_manager):
        """Delete raises error when item not found."""
        with pytest.raises(NotFoundError):
            task_manager.delete_item(path="nonexistent/item")


# =============================================================================
# Slug Generation Tests
# =============================================================================


class TestGenerateUniqueSlug:
    """Test slug generation."""

    def test_generate_slug_basic(self, task_manager):
        """Generate basic slug from name."""
        slug = task_manager._generate_unique_slug([], "My Test Item")
        
        assert slug == "my-test-item"

    def test_generate_slug_filters_filler_words(self, task_manager):
        """Generate slug filters out filler words."""
        slug = task_manager._generate_unique_slug([], "The Quick And Easy Test")
        
        # "and", "the" should be filtered
        assert "and" not in slug
        assert "the" not in slug

    def test_generate_slug_handles_duplicates(self, task_manager, mock_data):
        """Generate slug adds number for duplicates."""
        existing = [
            mock_data.create_deliverable(slug="test-item"),
        ]
        
        slug = task_manager._generate_unique_slug(existing, "Test Item")
        
        assert slug == "test-item-1"

    def test_generate_slug_truncates(self, task_manager):
        """Generate slug truncates to max length."""
        long_name = "This Is A Very Long Name That Should Be Truncated Because It Exceeds The Maximum Slug Length"
        slug = task_manager._generate_unique_slug([], long_name)
        
        assert len(slug) <= 15  # Default max length


# =============================================================================
# Integration Tests
# =============================================================================


class TestTaskManagerIntegration:
    """Integration tests for TaskManager workflows."""

    def test_full_workflow(self, task_manager):
        """Test complete workflow: add, start, complete, cascade."""
        # Add new action
        action = task_manager.add_item(
            item_type="action",
            name="Test Action",
            description="Integration test",
            parent_path="phase-1/milestone-1/objective-1/deliverable-1",
        )
        
        # Start action
        task_manager.project.task_cursor = (
            "phase-1/milestone-1/objective-1/deliverable-1/" + action.slug
        )
        started = task_manager.start_next_action()
        assert started.status == "in-progress"
        
        # Complete action
        completed = task_manager.complete_current_action()
        assert completed.status == "completed"

    def test_slug_uniqueness_across_operations(self, task_manager):
        """Test slugs remain unique across add/update operations."""
        # Add item
        item1 = task_manager.add_item(
            item_type="action",
            name="Same Name",
            description="First",
            parent_path="phase-1/milestone-1/objective-1/deliverable-1",
        )
        
        # Add another with same name
        item2 = task_manager.add_item(
            item_type="action",
            name="Same Name",
            description="Second",
            parent_path="phase-1/milestone-1/objective-1/deliverable-1",
        )
        
        assert item1.slug != item2.slug
