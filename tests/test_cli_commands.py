"""
Tests for Prism CLI commands.

Tests cover:
- crud commands (add, show, edit, delete, nav)
- task commands (start, done, next)
- status command
- CLI error handling

Uses Click's CliRunner with isolated temporary .prism/ directory.
"""

import json
from pathlib import Path

import pytest

from prism.cli import cli
from prism.core import PrismCore
from prism.managers.archive_manager import ArchiveManager
from prism.managers.project_manager import ProjectManager
from prism.managers.storage_manager import StorageManager

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_prism_dir(temp_dir: Path, sample_project):
    """Create a temporary .prism/ directory with sample project data."""
    prism_dir = temp_dir / ".prism"
    prism_dir.mkdir()
    (prism_dir / "archive").mkdir()

    # Save sample project using ProjectManager
    storage = StorageManager(prism_dir)
    archive_mgr = ArchiveManager(storage)
    project_mgr = ProjectManager(storage, archive_mgr)
    project_mgr.save(sample_project)

    return prism_dir


@pytest.fixture
def runner(temp_prism_dir, monkeypatch):
    """Create CliRunner with PrismCore patched to use temp directory.

    Uses monkeypatch to inject the temp directory for all PrismCore instances.
    """
    from click.testing import CliRunner

    from prism.core import PrismCore

    original_init = PrismCore.__init__

    def patched_init(self, prism_dir=None, **kwargs):
        # Always use temp_prism_dir
        original_init(self, prism_dir=temp_prism_dir, **kwargs)

    monkeypatch.setattr(PrismCore, "__init__", patched_init)

    yield CliRunner()


# =============================================================================
# CRUD Command Tests
# =============================================================================


class TestCrudAddCommand:
    """Test crud add command."""

    def test_add_phase(self, runner):
        """Add phase via CLI."""
        result = runner.invoke(
            cli,
            ["crud", "add", "-t", "phase", "-n", "New Phase", "-d", "Test"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "created successfully" in result.output

    def test_add_milestone(self, runner):
        """Add milestone via CLI."""
        result = runner.invoke(
            cli,
            ["crud", "add", "-t", "milestone", "-n", "New Milestone", "-p", "phase-1"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "created successfully" in result.output

    def test_add_action(self, runner):
        """Add action via CLI."""
        result = runner.invoke(
            cli,
            [
                "crud",
                "add",
                "-t",
                "action",
                "-n",
                "New Action",
                "-p",
                "phase-1/milestone-1/objective-1/deliverable-1",
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "created successfully" in result.output

    def test_add_with_nav_flag(self, runner):
        """Add with --nav flag navigates to created item."""
        result = runner.invoke(
            cli,
            [
                "crud",
                "add",
                "-t",
                "action",
                "-n",
                "Nav Test",
                "-p",
                "phase-1/milestone-1/objective-1/deliverable-1",
                "--nav",
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "navigating to" in result.output.lower()

    def test_add_missing_name(self, runner):
        """Add fails without name."""
        result = runner.invoke(
            cli,
            ["crud", "add", "-t", "phase"],
            catch_exceptions=False,
        )

        assert result.exit_code != 0


class TestCrudShowCommand:
    """Test crud show command."""

    def test_show_by_path(self, runner):
        """Show item by path."""
        result = runner.invoke(
            cli,
            ["crud", "show", "phase-1"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Phase 1" in result.output

    def test_show_current_position(self, runner):
        """Show without path shows current position."""
        # First set a context
        core = PrismCore()
        core.project.crud_context = "phase-1"
        core._save_project()

        result = runner.invoke(
            cli,
            ["crud", "show"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0

    def test_show_json_output(self, runner):
        """Show with --json outputs JSON."""
        result = runner.invoke(
            cli,
            ["crud", "show", "phase-1", "--json"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "name" in data or "slug" in data

    def test_show_not_found(self, runner):
        """Show fails for nonexistent path."""
        result = runner.invoke(
            cli,
            ["crud", "show", "nonexistent"],
            catch_exceptions=False,
        )

        assert result.exit_code != 0
        assert "not found" in result.output.lower()


class TestCrudEditCommand:
    """Test crud edit command."""

    def test_edit_name(self, runner):
        """Edit item name."""
        result = runner.invoke(
            cli,
            ["crud", "edit", "phase-1", "-n", "Updated Phase"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "updated successfully" in result.output.lower()

    def test_edit_status(self, runner):
        """Edit item status."""
        result = runner.invoke(
            cli,
            ["crud", "edit", "phase-1", "-s", "in-progress"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0

    def test_edit_no_params(self, runner):
        """Edit fails without update params."""
        result = runner.invoke(
            cli,
            ["crud", "edit", "phase-1"],
            catch_exceptions=False,
        )

        assert result.exit_code != 0


class TestCrudDeleteCommand:
    """Test crud delete command."""

    def test_delete_action(self, runner):
        """Delete action via CLI."""
        result = runner.invoke(
            cli,
            [
                "crud",
                "delete",
                "phase-1/milestone-1/objective-1/deliverable-1/action-1",
            ],
            input="y\n",  # Confirm deletion
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "deleted successfully" in result.output.lower()

    def test_delete_requires_confirmation(self, runner):
        """Delete requires confirmation."""
        result = runner.invoke(
            cli,
            [
                "crud",
                "delete",
                "phase-1/milestone-1/objective-1/deliverable-1/action-1",
            ],
            input="n\n",  # Decline
            catch_exceptions=False,
        )

        # Click's confirmation should abort on 'n'
        assert result.exit_code != 0 or "Aborted" in result.output


class TestCrudNavCommand:
    """Test crud nav command."""

    def test_nav_show_current(self, runner):
        """Nav without args shows current position."""
        result = runner.invoke(
            cli,
            ["crud", "nav"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0

    def test_nav_to_path(self, runner):
        """Nav to specific path."""
        result = runner.invoke(
            cli,
            ["crud", "nav", "phase-1/milestone-1/objective-1"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Navigated to" in result.output

    def test_nav_up_token(self, runner):
        """Nav with :up token."""
        # First set a position
        core = PrismCore()
        core.project.task_cursor = (
            "phase-1/milestone-1/objective-1/deliverable-1/action-1"
        )
        core._save_project()

        result = runner.invoke(
            cli,
            ["crud", "nav", ":u"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0

    def test_nav_current_token(self, runner):
        """Nav with :co (current objective) token."""
        result = runner.invoke(
            cli,
            ["crud", "nav", ":co"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Navigated to" in result.output

    def test_nav_behind_task_cursor(self, temp_dir, monkeypatch):
        """Nav to ancestor is allowed even when task_cursor is deep."""
        from click.testing import CliRunner

        from prism.core import PrismCore

        # Create clean temp directory (not pre-populated like runner fixture)
        prism_dir = temp_dir / ".prism"
        prism_dir.mkdir()
        (prism_dir / "archive").mkdir()

        # Patch PrismCore to use our clean temp dir
        original_init = PrismCore.__init__

        def patched_init(self, prism_dir_arg=None, **kwargs):
            original_init(self, prism_dir=prism_dir, **kwargs)

        monkeypatch.setattr(PrismCore, "__init__", patched_init)

        # Create project structure
        core = PrismCore()
        core.add_item("phase", "Phase", "Desc", None)
        core.add_item("milestone", "MS", "Desc", "phase")
        core.add_item("objective", "Obj", "Desc", "phase/ms")
        core.add_item("deliverable", "Deliv", "Desc", "phase/ms/obj")
        core.add_item("action", "Action", "Desc", "phase/ms/obj/deliv")

        # Set task cursor deep in tree
        core.project.task_cursor = "phase/ms/obj/deliv/action"
        core.project.crud_context = None  # Clear crud context
        core._save_project()

        # Nav to ancestor should be allowed (use absolute path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["crud", "nav", "/phase"],
            catch_exceptions=False,
        )

        # Ancestor nav should succeed
        assert result.exit_code == 0


# =============================================================================
# Task Command Tests
# =============================================================================


class TestTaskStartCommand:
    """Test task start command."""

    def test_start_finds_pending(self, runner):
        """Task start finds pending action."""
        result = runner.invoke(
            cli,
            ["task", "start"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "working on" in result.output.lower() or "No pending" in result.output

    def test_start_shows_current(self, runner):
        """Task start shows current in-progress action."""
        # Start an action first
        core = PrismCore()
        core.task_manager.start_next_action()

        result = runner.invoke(
            cli,
            ["task", "start"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Currently working on" in result.output


class TestTaskDoneCommand:
    """Test task done command."""

    def test_done_completes_action(self, runner):
        """Task done completes current action."""
        # Start an action first
        core = PrismCore()
        core.task_manager.start_next_action()

        result = runner.invoke(
            cli,
            ["task", "done"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Completed" in result.output

    def test_done_no_action(self, runner):
        """Task done reports when no action in progress."""
        result = runner.invoke(
            cli,
            ["task", "done"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "No task in progress" in result.output


class TestTaskNextCommand:
    """Test task next command."""

    def test_next_completes_and_starts(self, runner):
        """Task next completes current and starts next."""
        # Start an action first
        core = PrismCore()
        core.task_manager.start_next_action()

        result = runner.invoke(
            cli,
            ["task", "next"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Completed" in result.output


# =============================================================================
# Status Command Tests
# =============================================================================


class TestStatusCommand:
    """Test status command."""

    def test_status_shows_summary(self, runner):
        """Status shows project summary."""
        result = runner.invoke(
            cli,
            ["status"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Project Status" in result.output

    def test_status_json_output(self, runner):
        """Status with --json outputs structured data."""
        result = runner.invoke(
            cli,
            ["status", "--json"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "current_strategic_focus" in data
        assert "execution_tree" in data

    def test_status_current_deliverable(self, runner):
        """Status with --current-deliverable shows focused view."""
        result = runner.invoke(
            cli,
            ["status", "--current-deliverable"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0


# =============================================================================
# Orphan Command Tests
# =============================================================================


class TestOrphanListCommand:
    """Test orphan list command."""

    def test_list_no_orphans(self, runner):
        """List shows message when no orphans exist."""
        result = runner.invoke(
            cli,
            ["orphan", "list"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "No orphan ideas found" in result.output

    def test_list_with_orphans(self, temp_prism_dir, monkeypatch):
        """List shows orphan ideas."""
        from click.testing import CliRunner

        from prism.core import PrismCore
        from prism.managers.orphan_manager import OrphanManager

        # Add an orphan to the temp directory
        core = PrismCore(prism_dir=temp_prism_dir)
        core.add_orphan(name="Test Orphan", description="A test orphan")

        # Patch PrismCore to use temp directory for CLI command
        original_init = PrismCore.__init__

        def patched_init(self, prism_dir=None, **kwargs):
            original_init(self, prism_dir=temp_prism_dir, **kwargs)

        monkeypatch.setattr(PrismCore, "__init__", patched_init)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["orphan", "list"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Orphan Ideas" in result.output
        assert "Test Orphan" in result.output

    def test_list_json_output(self, temp_prism_dir, monkeypatch):
        """List with --json outputs JSON array."""
        from click.testing import CliRunner

        from prism.core import PrismCore

        # Add an orphan to the temp directory
        core = PrismCore(prism_dir=temp_prism_dir)
        core.add_orphan(name="JSON Test", description="Test")

        # Patch PrismCore to use temp directory for CLI command
        original_init = PrismCore.__init__

        def patched_init(self, prism_dir=None, **kwargs):
            original_init(self, prism_dir=temp_prism_dir, **kwargs)

        monkeypatch.setattr(PrismCore, "__init__", patched_init)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["orphan", "list", "--json"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "name" in data[0]


class TestOrphanShowCommand:
    """Test orphan show command."""

    def test_show_by_name(self, temp_prism_dir, monkeypatch):
        """Show orphan by name."""
        from click.testing import CliRunner

        from prism.core import PrismCore

        # Add an orphan to the temp directory
        core = PrismCore(prism_dir=temp_prism_dir)
        core.add_orphan(name="Show Test", description="Testing show command")

        # Patch PrismCore to use temp directory for CLI command
        original_init = PrismCore.__init__

        def patched_init(self, prism_dir=None, **kwargs):
            original_init(self, prism_dir=temp_prism_dir, **kwargs)

        monkeypatch.setattr(PrismCore, "__init__", patched_init)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["orphan", "show", "Show Test"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Show Test" in result.output
        assert "ID:" in result.output

    def test_show_by_uuid(self, temp_prism_dir, monkeypatch):
        """Show orphan by UUID."""
        from click.testing import CliRunner

        from prism.core import PrismCore

        # Add an orphan to the temp directory
        core = PrismCore(prism_dir=temp_prism_dir)
        orphan = core.add_orphan(name="UUID Test", description="Testing UUID lookup")

        # Patch PrismCore to use temp directory for CLI command
        original_init = PrismCore.__init__

        def patched_init(self, prism_dir=None, **kwargs):
            original_init(self, prism_dir=temp_prism_dir, **kwargs)

        monkeypatch.setattr(PrismCore, "__init__", patched_init)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["orphan", "show", orphan.uuid],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "UUID Test" in result.output

    def test_show_by_id(self, temp_prism_dir, monkeypatch):
        """Show orphan by numeric ID."""
        from click.testing import CliRunner

        from prism.core import PrismCore

        # Add an orphan to the temp directory
        core = PrismCore(prism_dir=temp_prism_dir)
        orphan = core.add_orphan(name="ID Test", description="Testing ID lookup")

        # Patch PrismCore to use temp directory for CLI command
        original_init = PrismCore.__init__

        def patched_init(self, prism_dir=None, **kwargs):
            original_init(self, prism_dir=temp_prism_dir, **kwargs)

        monkeypatch.setattr(PrismCore, "__init__", patched_init)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["orphan", "show", str(orphan.id)],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "ID Test" in result.output
        assert f"ID: {orphan.id}" in result.output

    def test_show_json_output(self, temp_prism_dir, monkeypatch):
        """Show with --json outputs JSON object."""
        from click.testing import CliRunner

        from prism.core import PrismCore

        # Add an orphan to the temp directory
        core = PrismCore(prism_dir=temp_prism_dir)
        core.add_orphan(name="JSON Show Test", description="Test")

        # Patch PrismCore to use temp directory for CLI command
        original_init = PrismCore.__init__

        def patched_init(self, prism_dir=None, **kwargs):
            original_init(self, prism_dir=temp_prism_dir, **kwargs)

        monkeypatch.setattr(PrismCore, "__init__", patched_init)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["orphan", "show", "JSON Show Test", "--json"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "name" in data
        assert "uuid" in data

    def test_show_not_found(self, runner):
        """Show fails for nonexistent orphan."""
        result = runner.invoke(
            cli,
            ["orphan", "show", "nonexistent"],
            catch_exceptions=False,
        )

        assert result.exit_code != 0
        assert "not found" in result.output.lower()


class TestOrphanAddCommand:
    """Test orphan add command."""

    def test_add_orphan_minimal(self, temp_prism_dir, monkeypatch):
        """Add orphan with minimal required fields."""
        from click.testing import CliRunner

        from prism.core import PrismCore

        # Patch PrismCore to use temp directory
        original_init = PrismCore.__init__

        def patched_init(self, prism_dir=None, **kwargs):
            original_init(self, prism_dir=temp_prism_dir, **kwargs)

        monkeypatch.setattr(PrismCore, "__init__", patched_init)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["orphan", "add", "-n", "New Orphan", "-d", "A new idea"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "added successfully" in result.output.lower()
        assert "UUID:" in result.output

        # Verify orphan was persisted
        core = PrismCore(prism_dir=temp_prism_dir)
        orphans = core.list_orphans()
        assert len(orphans) == 1
        assert orphans[0].name == "New Orphan"

    def test_add_orphan_with_priority(self, temp_prism_dir, monkeypatch):
        """Add orphan with custom priority."""
        from click.testing import CliRunner

        from prism.core import PrismCore

        original_init = PrismCore.__init__

        def patched_init(self, prism_dir=None, **kwargs):
            original_init(self, prism_dir=temp_prism_dir, **kwargs)

        monkeypatch.setattr(PrismCore, "__init__", patched_init)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["orphan", "add", "-n", "High Priority", "-d", "Important", "-p", "5"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Verify priority was set
        core = PrismCore(prism_dir=temp_prism_dir)
        orphans = core.list_orphans()
        assert orphans[0].priority == 5

    def test_add_orphan_default_priority(self, temp_prism_dir, monkeypatch):
        """Add orphan uses default priority when not specified."""
        from click.testing import CliRunner

        from prism.core import PrismCore

        original_init = PrismCore.__init__

        def patched_init(self, prism_dir=None, **kwargs):
            original_init(self, prism_dir=temp_prism_dir, **kwargs)

        monkeypatch.setattr(PrismCore, "__init__", patched_init)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["orphan", "add", "-n", "Default Priority", "-d", "Test"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        core = PrismCore(prism_dir=temp_prism_dir)
        orphans = core.list_orphans()
        assert orphans[0].priority == 0

    def test_add_orphan_missing_name(self, runner):
        """Add fails without required name."""
        result = runner.invoke(
            cli,
            ["orphan", "add", "-d", "No name"],
            catch_exceptions=False,
        )

        assert result.exit_code != 0
        assert "Missing option" in result.output or "Error" in result.output


class TestOrphanDeleteCommand:
    """Test orphan delete command."""

    def test_delete_by_id(self, temp_prism_dir, monkeypatch):
        """Delete orphan by numeric ID."""
        from click.testing import CliRunner

        from prism.core import PrismCore

        # Add an orphan first
        core = PrismCore(prism_dir=temp_prism_dir)
        orphan = core.add_orphan(name="To Delete", description="Will be deleted")

        # Patch PrismCore to use temp directory
        original_init = PrismCore.__init__

        def patched_init(self, prism_dir=None, **kwargs):
            original_init(self, prism_dir=temp_prism_dir, **kwargs)

        monkeypatch.setattr(PrismCore, "__init__", patched_init)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["orphan", "delete", str(orphan.id), "--yes"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "deleted successfully" in result.output.lower()

        # Verify orphan was removed
        core = PrismCore(prism_dir=temp_prism_dir)
        orphans = core.list_orphans()
        assert len(orphans) == 0

    def test_delete_by_uuid(self, temp_prism_dir, monkeypatch):
        """Delete orphan by UUID."""
        from click.testing import CliRunner

        from prism.core import PrismCore

        core = PrismCore(prism_dir=temp_prism_dir)
        orphan = core.add_orphan(name="UUID Delete", description="Test")

        original_init = PrismCore.__init__

        def patched_init(self, prism_dir=None, **kwargs):
            original_init(self, prism_dir=temp_prism_dir, **kwargs)

        monkeypatch.setattr(PrismCore, "__init__", patched_init)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["orphan", "delete", orphan.uuid, "--yes"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "deleted successfully" in result.output.lower()

    def test_delete_by_name(self, temp_prism_dir, monkeypatch):
        """Delete orphan by name."""
        from click.testing import CliRunner

        from prism.core import PrismCore

        core = PrismCore(prism_dir=temp_prism_dir)
        core.add_orphan(name="Name Delete Test", description="Test")

        original_init = PrismCore.__init__

        def patched_init(self, prism_dir=None, **kwargs):
            original_init(self, prism_dir=temp_prism_dir, **kwargs)

        monkeypatch.setattr(PrismCore, "__init__", patched_init)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["orphan", "delete", "Name Delete Test", "--yes"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "deleted successfully" in result.output.lower()

    def test_delete_not_found(self, temp_prism_dir, monkeypatch):
        """Delete fails for nonexistent orphan."""
        from click.testing import CliRunner

        from prism.core import PrismCore

        # Patch PrismCore to use temp directory
        original_init = PrismCore.__init__

        def patched_init(self, prism_dir=None, **kwargs):
            original_init(self, prism_dir=temp_prism_dir, **kwargs)

        monkeypatch.setattr(PrismCore, "__init__", patched_init)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["orphan", "delete", "nonexistent", "--yes"],
            catch_exceptions=False,
        )

        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_delete_with_confirmation(self, temp_prism_dir, monkeypatch):
        """Delete with interactive confirmation."""
        from click.testing import CliRunner

        from prism.core import PrismCore

        core = PrismCore(prism_dir=temp_prism_dir)
        orphan = core.add_orphan(name="Confirm Delete", description="Test")

        original_init = PrismCore.__init__

        def patched_init(self, prism_dir=None, **kwargs):
            original_init(self, prism_dir=temp_prism_dir, **kwargs)

        monkeypatch.setattr(PrismCore, "__init__", patched_init)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["orphan", "delete", str(orphan.id)],
            input="y\n",  # Confirm
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "deleted successfully" in result.output.lower()

    def test_delete_declined(self, temp_prism_dir, monkeypatch):
        """Delete aborted when user declines confirmation."""
        from click.testing import CliRunner

        from prism.core import PrismCore

        core = PrismCore(prism_dir=temp_prism_dir)
        orphan = core.add_orphan(name="Not Deleted", description="Test")

        original_init = PrismCore.__init__

        def patched_init(self, prism_dir=None, **kwargs):
            original_init(self, prism_dir=temp_prism_dir, **kwargs)

        monkeypatch.setattr(PrismCore, "__init__", patched_init)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["orphan", "delete", str(orphan.id)],
            input="n\n",  # Decline
            catch_exceptions=False,
        )

        # Click's confirmation should abort on 'n'
        assert result.exit_code != 0 or "Aborted" in result.output


class TestOrphanAdoptCommand:
    """Test orphan adopt command."""

    def test_adopt_as_phase(self, empty_prism_dir, monkeypatch):
        """Adopt orphan as a phase."""
        from click.testing import CliRunner

        from prism.core import PrismCore

        # Use empty prism directory (no sample data)
        core = PrismCore(prism_dir=empty_prism_dir)
        orphan = core.add_orphan(name="Adopt as Phase", description="Will become a phase")

        # Patch PrismCore to use empty directory
        original_init = PrismCore.__init__

        def patched_init(self, prism_dir=None, **kwargs):
            original_init(self, prism_dir=empty_prism_dir, **kwargs)

        monkeypatch.setattr(PrismCore, "__init__", patched_init)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["orphan", "adopt", str(orphan.id), "-t", "phase", "--yes"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Adopted" in result.output
        assert "phase" in result.output.lower()

        # Reload core to get updated data from disk
        core = PrismCore(prism_dir=empty_prism_dir)

        # Verify orphan was removed
        orphans = core.list_orphans()
        assert len(orphans) == 0

        # Verify phase was created
        phases = core.project.phases
        assert len(phases) == 1
        assert phases[0].name == "Adopt as Phase"

    def test_adopt_not_found(self, empty_prism_dir, monkeypatch):
        """Adopt fails for nonexistent orphan."""
        from click.testing import CliRunner

        from prism.core import PrismCore

        original_init = PrismCore.__init__

        def patched_init(self, prism_dir=None, **kwargs):
            original_init(self, prism_dir=empty_prism_dir, **kwargs)

        monkeypatch.setattr(PrismCore, "__init__", patched_init)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["orphan", "adopt", "nonexistent", "-t", "phase", "--yes"],
            catch_exceptions=False,
        )

        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_adopt_with_confirmation(self, empty_prism_dir, monkeypatch):
        """Adopt with interactive confirmation."""
        from click.testing import CliRunner

        from prism.core import PrismCore

        core = PrismCore(prism_dir=empty_prism_dir)
        orphan = core.add_orphan(name="Confirm Adopt", description="Test")

        original_init = PrismCore.__init__

        def patched_init(self, prism_dir=None, **kwargs):
            original_init(self, prism_dir=empty_prism_dir, **kwargs)

        monkeypatch.setattr(PrismCore, "__init__", patched_init)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["orphan", "adopt", str(orphan.id), "-t", "phase"],
            input="y\n",  # Confirm
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Adopted" in result.output

    def test_adopt_declined(self, empty_prism_dir, monkeypatch):
        """Adopt aborted when user declines confirmation."""
        from click.testing import CliRunner

        from prism.core import PrismCore

        core = PrismCore(prism_dir=empty_prism_dir)
        orphan = core.add_orphan(name="Not Adopted", description="Test")

        original_init = PrismCore.__init__

        def patched_init(self, prism_dir=None, **kwargs):
            original_init(self, prism_dir=empty_prism_dir, **kwargs)

        monkeypatch.setattr(PrismCore, "__init__", patched_init)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["orphan", "adopt", str(orphan.id), "-t", "phase"],
            input="n\n",  # Decline
            catch_exceptions=False,
        )

        # Click's confirmation should abort on 'n'
        assert result.exit_code != 0 or "Aborted" in result.output


# =============================================================================
# CLI Error Handling Tests
# =============================================================================


class TestCliErrorHandling:
    """Test CLI error handling."""

    def test_invalid_command(self, runner):
        """Invalid command shows help."""
        result = runner.invoke(
            cli,
            ["invalid-command"],
            catch_exceptions=False,
        )

        assert result.exit_code != 0

    def test_missing_required_option(self, runner):
        """Missing required option shows error."""
        result = runner.invoke(
            cli,
            ["crud", "add", "-t", "phase"],  # Missing -n
            catch_exceptions=False,
        )

        assert result.exit_code != 0

    def test_invalid_item_type(self, runner):
        """Invalid item type shows error."""
        result = runner.invoke(
            cli,
            ["crud", "add", "-t", "invalid", "-n", "Test"],
            catch_exceptions=False,
        )

        assert result.exit_code != 0
        assert "Invalid value" in result.output
