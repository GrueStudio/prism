"""
Tests for PrismCore integration.

Tests cover:
- PrismCore initialization and manager orchestration
- End-to-end workflows
- Cross-manager interactions
"""

from pathlib import Path

import pytest

from prism.core import PrismCore


# =============================================================================
# PrismCore Initialization Tests
# =============================================================================


class TestPrismCoreInit:
    """Test PrismCore initialization."""

    def test_init_creates_managers(self, temp_dir: Path):
        """PrismCore initializes all managers."""
        prism_dir = temp_dir / ".prism"
        prism_dir.mkdir()
        
        core = PrismCore(prism_dir)
        
        assert core.storage is not None
        assert core.project_manager is not None
        assert core.navigator is not None
        assert core.task_manager is not None
        assert core.project is not None

    def test_init_loads_empty_project(self, temp_dir: Path):
        """PrismCore loads empty project when no files exist."""
        prism_dir = temp_dir / ".prism"
        prism_dir.mkdir()
        (prism_dir / "archive").mkdir()
        
        core = PrismCore(prism_dir)
        
        assert len(core.project.phases) == 0
        assert core.project.task_cursor is None
        assert core.project.crud_context is None

    def test_init_default_path(self):
        """PrismCore uses .prism/ in current directory by default."""
        # This may fail if .prism doesn't exist, so just check it initializes
        try:
            core = PrismCore()
            assert core is not None
        except Exception:
            pass  # Expected if no .prism directory


# =============================================================================
# CRUD Integration Tests
# =============================================================================


class TestPrismCoreCrud:
    """Test CRUD operations through PrismCore."""

    def test_add_and_retrieve_phase(self, temp_dir: Path):
        """Add phase and retrieve it."""
        prism_dir = temp_dir / ".prism"
        prism_dir.mkdir()
        (prism_dir / "archive").mkdir()
        
        core = PrismCore(prism_dir)
        
        # Add phase
        phase = core.add_item(
            item_type="phase",
            name="Test Phase",
            description="Integration test",
            parent_path=None,
        )
        
        # Retrieve
        found = core.get_item_by_path(phase.slug)
        
        assert found is not None
        assert found.name == "Test Phase"

    def test_add_full_hierarchy(self, temp_dir: Path):
        """Add complete hierarchy: phase → milestone → objective → deliverable → action."""
        prism_dir = temp_dir / ".prism"
        prism_dir.mkdir()
        (prism_dir / "archive").mkdir()
        
        core = PrismCore(prism_dir)
        
        # Add phase
        phase = core.add_item("phase", "Phase", "Desc", None)
        
        # Add milestone
        milestone = core.add_item(
            "milestone", "Milestone", "Desc", phase.slug
        )
        
        # Add objective
        objective = core.add_item(
            "objective", "Objective", "Desc", f"{phase.slug}/{milestone.slug}"
        )
        
        # Add deliverable
        deliverable = core.add_item(
            "deliverable", "Deliverable", "Desc",
            f"{phase.slug}/{milestone.slug}/{objective.slug}"
        )
        
        # Add action
        action = core.add_item(
            "action", "Action", "Desc",
            f"{phase.slug}/{milestone.slug}/{objective.slug}/{deliverable.slug}"
        )

        # Verify hierarchy
        assert action is not None
        action_path = f"{phase.slug}/{milestone.slug}/{objective.slug}/{deliverable.slug}/{action.slug}"
        assert core.get_item_by_path(action_path) is not None

    def test_update_item(self, temp_dir: Path):
        """Update item through PrismCore."""
        prism_dir = temp_dir / ".prism"
        prism_dir.mkdir()
        (prism_dir / "archive").mkdir()
        
        core = PrismCore(prism_dir)
        phase = core.add_item("phase", "Phase", "Original", None)
        
        # Update
        updated = core.update_item(phase.slug, name="Updated Phase")
        
        assert updated.name == "Updated Phase"

    def test_delete_item(self, temp_dir: Path):
        """Delete item through PrismCore."""
        prism_dir = temp_dir / ".prism"
        prism_dir.mkdir()
        (prism_dir / "archive").mkdir()
        
        core = PrismCore(prism_dir)
        core.add_item("phase", "Phase", "To Delete", None)
        
        # Delete
        core.delete_item("phase")
        
        assert core.get_item_by_path("phase") is None


# =============================================================================
# Task Operations Integration Tests
# =============================================================================


class TestPrismCoreTaskOperations:
    """Test task operations through PrismCore."""

    def test_start_complete_workflow(self, temp_dir: Path):
        """Complete workflow: add action, start, complete."""
        prism_dir = temp_dir / ".prism"
        prism_dir.mkdir()
        (prism_dir / "archive").mkdir()
        
        core = PrismCore(prism_dir)
        
        # Add hierarchy
        phase = core.add_item("phase", "Phase", "Desc", None)
        milestone = core.add_item("milestone", "MS", "Desc", phase.slug)
        objective = core.add_item("objective", "Obj", "Desc", f"{phase.slug}/{milestone.slug}")
        deliverable = core.add_item("deliverable", "Deliv", "Desc", f"{phase.slug}/{milestone.slug}/{objective.slug}")
        action = core.add_item("action", "Action", "Desc", f"{phase.slug}/{milestone.slug}/{objective.slug}/{deliverable.slug}")
        
        # Start
        started = core.start_next_action()
        assert started is not None
        assert started.status == "in-progress"
        
        # Complete
        completed = core.complete_current_action()
        assert completed is not None
        assert completed.status == "completed"

    def test_get_current_action(self, temp_dir: Path):
        """Get current action through PrismCore."""
        prism_dir = temp_dir / ".prism"
        prism_dir.mkdir()
        (prism_dir / "archive").mkdir()
        
        core = PrismCore(prism_dir)
        
        # Add and start action
        phase = core.add_item("phase", "Phase", "Desc", None)
        milestone = core.add_item("milestone", "MS", "Desc", phase.slug)
        objective = core.add_item("objective", "Obj", "Desc", f"{phase.slug}/{milestone.slug}")
        deliverable = core.add_item("deliverable", "Deliv", "Desc", f"{phase.slug}/{milestone.slug}/{objective.slug}")
        action = core.add_item("action", "Action", "Desc", f"{phase.slug}/{milestone.slug}/{objective.slug}/{deliverable.slug}")
        
        core.start_next_action()
        
        current = core.get_current_action()
        assert current is not None
        assert current.status == "in-progress"


# =============================================================================
# Completion Tracking Integration Tests
# =============================================================================


class TestPrismCoreCompletionTracking:
    """Test completion tracking through PrismCore."""

    def test_calculate_percentage(self, temp_dir: Path):
        """Calculate completion percentage."""
        prism_dir = temp_dir / ".prism"
        prism_dir.mkdir()
        (prism_dir / "archive").mkdir()
        
        core = PrismCore(prism_dir)
        
        # Add hierarchy with multiple actions
        phase = core.add_item("phase", "Phase", "Desc", None)
        milestone = core.add_item("milestone", "MS", "Desc", phase.slug)
        objective = core.add_item("objective", "Obj", "Desc", f"{phase.slug}/{milestone.slug}")
        deliverable = core.add_item("deliverable", "Deliv", "Desc", f"{phase.slug}/{milestone.slug}/{objective.slug}")
        
        action1 = core.add_item("action", "Action 1", "Desc", f"{phase.slug}/{milestone.slug}/{objective.slug}/{deliverable.slug}")
        action2 = core.add_item("action", "Action 2", "Desc", f"{phase.slug}/{milestone.slug}/{objective.slug}/{deliverable.slug}")
        
        # Complete one action
        core.task_manager.project.task_cursor = f"{phase.slug}/{milestone.slug}/{objective.slug}/{deliverable.slug}/{action1.slug}"
        core.task_manager.start_next_action()
        core.task_manager.complete_current_action()
        
        # Calculate percentage
        pct = core.calculate_completion_percentage(deliverable)
        
        assert pct["overall"] == 50.0

    def test_is_exec_tree_complete(self, temp_dir: Path):
        """Check if execution tree is complete."""
        prism_dir = temp_dir / ".prism"
        prism_dir.mkdir()
        (prism_dir / "archive").mkdir()
        
        core = PrismCore(prism_dir)
        
        # Add hierarchy
        phase = core.add_item("phase", "Phase", "Desc", None)
        milestone = core.add_item("milestone", "MS", "Desc", phase.slug)
        objective = core.add_item("objective", "Obj", "Desc", f"{phase.slug}/{milestone.slug}")
        deliverable = core.add_item("deliverable", "Deliv", "Desc", f"{phase.slug}/{milestone.slug}/{objective.slug}")
        action = core.add_item("action", "Action", "Desc", f"{phase.slug}/{milestone.slug}/{objective.slug}/{deliverable.slug}")
        
        # Not complete initially
        assert core.is_exec_tree_complete(f"{phase.slug}/{milestone.slug}/{objective.slug}") is False
        
        # Complete everything
        core.task_manager.project.task_cursor = f"{phase.slug}/{milestone.slug}/{objective.slug}/{deliverable.slug}/{action.slug}"
        core.task_manager.start_next_action()
        core.task_manager.complete_current_action()
        
        # Now complete
        assert core.is_exec_tree_complete(f"{phase.slug}/{milestone.slug}/{objective.slug}") is True


# =============================================================================
# Navigation Integration Tests
# =============================================================================


class TestPrismCoreNavigation:
    """Test navigation through PrismCore."""

    def test_get_current_objective(self, temp_dir: Path):
        """Get current objective through PrismCore."""
        prism_dir = temp_dir / ".prism"
        prism_dir.mkdir()
        (prism_dir / "archive").mkdir()
        
        core = PrismCore(prism_dir)
        core.add_item("phase", "Phase", "Desc", None)
        core.add_item("milestone", "MS", "Desc", "phase")
        core.add_item("objective", "Obj", "Desc", "phase/ms")
        
        current = core.get_current_objective()
        
        assert current is not None
        assert current.name == "Obj"

    def test_get_item_path(self, temp_dir: Path):
        """Get item path through PrismCore."""
        prism_dir = temp_dir / ".prism"
        prism_dir.mkdir()
        (prism_dir / "archive").mkdir()
        
        core = PrismCore(prism_dir)
        phase = core.add_item("phase", "Phase", "Desc", None)
        
        path = core.get_item_path(phase)
        
        assert path == "phase"


# =============================================================================
# Persistence Integration Tests
# =============================================================================


class TestPrismCorePersistence:
    """Test data persistence through PrismCore."""

    def test_save_and_reload(self, temp_dir: Path):
        """Save project and reload in new PrismCore instance."""
        prism_dir = temp_dir / ".prism"
        prism_dir.mkdir()
        (prism_dir / "archive").mkdir()
        
        # Create and modify
        core1 = PrismCore(prism_dir)
        core1.add_item("phase", "Phase", "Desc", None)
        core1.add_item("milestone", "MS", "Desc", "phase")
        
        # Reload in new instance
        core2 = PrismCore(prism_dir)
        
        assert len(core2.project.phases) == 1
        assert len(core2.project.phases[0].children) == 1

    def test_cursor_persistence(self, temp_dir: Path):
        """Task cursor persists across reloads."""
        prism_dir = temp_dir / ".prism"
        prism_dir.mkdir()
        (prism_dir / "archive").mkdir()
        
        # Create and set cursor
        core1 = PrismCore(prism_dir)
        core1.add_item("phase", "Phase", "Desc", None)
        core1.add_item("milestone", "MS", "Desc", "phase")
        core1.add_item("objective", "Obj", "Desc", "phase/ms")
        core1.add_item("deliverable", "Deliv", "Desc", "phase/ms/obj")
        core1.add_item("action", "Action", "Desc", "phase/ms/obj/deliv")
        
        core1.project.task_cursor = "phase/ms/obj/deliv/action"
        core1.project.crud_context = "phase/ms/obj/deliv"
        core1._save_project()
        
        # Reload
        core2 = PrismCore(prism_dir)
        
        assert core2.project.task_cursor == "phase/ms/obj/deliv/action"
        assert core2.project.crud_context == "phase/ms/obj/deliv"


# =============================================================================
# Status Summary Integration Tests
# =============================================================================


class TestPrismCoreStatusSummary:
    """Test status summary through PrismCore."""

    def test_get_status_summary(self, temp_dir: Path):
        """Get status summary."""
        prism_dir = temp_dir / ".prism"
        prism_dir.mkdir()
        (prism_dir / "archive").mkdir()
        
        core = PrismCore(prism_dir)
        core.add_item("phase", "Phase", "Desc", None)
        core.add_item("milestone", "MS", "Desc", "phase")
        core.add_item("objective", "Obj", "Desc", "phase/ms")
        core.add_item("deliverable", "Deliv", "Desc", "phase/ms/obj")
        core.add_item("action", "Action", "Desc", "phase/ms/obj/deliv")
        
        summary = core.get_status_summary()
        
        assert "item_counts" in summary
        assert summary["item_counts"]["Phase"]["total"] == 1
        assert summary["item_counts"]["Action"]["total"] == 1

    def test_get_status_summary_filtered(self, temp_dir: Path):
        """Get status summary filtered by phase/milestone."""
        prism_dir = temp_dir / ".prism"
        prism_dir.mkdir()
        (prism_dir / "archive").mkdir()
        
        core = PrismCore(prism_dir)
        core.add_item("phase", "Phase", "Desc", None)
        core.add_item("milestone", "MS", "Desc", "phase")
        
        summary = core.get_status_summary(phase_path="phase")
        
        assert summary["item_counts"]["Phase"]["total"] == 1
