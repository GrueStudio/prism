"""
Tests for the bug CLI commands.
"""

import pytest
from click.testing import CliRunner
from pathlib import Path
from prism.cli import cli
from prism.managers.storage_manager import StorageManager
from prism.models.config import BugType


@pytest.fixture
def runner():
    """CLI runner fixture."""
    return CliRunner()


@pytest.fixture
def isolated_prism(runner, temp_dir):
    """Run tests in an isolated directory with a initialized .prism/ folder."""
    with runner.isolated_filesystem(temp_dir=temp_dir):
        # Initialize storage and config
        storage = StorageManager(Path(".prism"))
        config = storage.load_config()
        config.bug_types.append(BugType(name="Physics", prefix="PHYS", description="Physics bugs"))
        storage.save_config(config)
        yield storage


def test_bug_add_command(runner, isolated_prism):
    """Test 'prism bug add' command."""
    result = runner.invoke(cli, ["bug", "add", "-t", "Physics", "-d", "Test bug"])
    assert result.exit_code == 0
    assert "Successfully added bug: PHYS" in result.output
    
    # Verify it exists in storage
    bugs = isolated_prism.load_bugs().bugs
    assert len(bugs) == 1
    assert bugs[0].description == "Test bug"


def test_bug_add_invalid_type(runner, isolated_prism):
    """Test 'prism bug add' with invalid type."""
    result = runner.invoke(cli, ["bug", "add", "-t", "Invalid", "-d", "Test bug"])
    assert result.exit_code == 0  # Command completes but shows error
    assert "Error: Invalid bug type: 'Invalid'" in result.output


def test_bug_show_command(runner, isolated_prism):
    """Test 'prism bug show' command."""
    # First add a bug
    runner.invoke(cli, ["bug", "add", "-t", "Physics", "-d", "Test bug"])
    bugs = isolated_prism.load_bugs().bugs
    bug_id = bugs[0].bug_id
    
    result = runner.invoke(cli, ["bug", "show", bug_id])
    assert result.exit_code == 0
    assert f"Bug: {bug_id}" in result.output
    assert "Type:        Physics (PHYS)" in result.output
    assert "Status:      open" in result.output
    assert "Description: Test bug" in result.output


def test_bug_edit_command(runner, isolated_prism):
    """Test 'prism bug edit' command."""
    # First add a bug
    runner.invoke(cli, ["bug", "add", "-t", "Physics", "-d", "Old description"])
    bugs = isolated_prism.load_bugs().bugs
    bug_id = bugs[0].bug_id
    
    # Edit description
    result = runner.invoke(cli, ["bug", "edit", bug_id, "-d", "New description"])
    assert result.exit_code == 0
    assert f"Successfully updated bug: {bug_id}" in result.output
    
    # Verify update
    result = runner.invoke(cli, ["bug", "show", bug_id])
    assert "Description: New description" in result.output


def test_bug_delete_command(runner, isolated_prism):
    """Test 'prism bug delete' command."""
    # First add a bug
    runner.invoke(cli, ["bug", "add", "-t", "Physics", "-d", "To be deleted"])
    bugs = isolated_prism.load_bugs().bugs
    bug_id = bugs[0].bug_id
    
    # Delete with confirmation skip
    result = runner.invoke(cli, ["bug", "delete", bug_id, "-y"])
    assert result.exit_code == 0
    assert f"Successfully deleted bug: {bug_id}" in result.output
    
    # Verify it's gone
    bugs_after = isolated_prism.load_bugs().bugs
    assert len(bugs_after) == 0
