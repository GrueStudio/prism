import json
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from prism.cli import cli
from prism.models import Deliverable, Milestone, Objective, Phase


def test_cli_registers_strat_and_exec_groups():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "strat" in result.output
    assert "exec" in result.output


@patch("prism.commands.strat.Core")
def test_strat_add_phase(mock_core):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["strat", "add", "--phase", "--name", "Test Phase", "--desc", "A test phase"],
    )
    assert result.exit_code == 0
    mock_core.return_value.add_item.assert_called_once_with(
        item_type="phase",
        name="Test Phase",
        description="A test phase",
        parent_path=None,
        status=None,
    )
    assert "Phase 'Test Phase' created successfully." in result.output


@patch("prism.commands.strat.Core")
def test_strat_add_milestone(mock_core):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "strat",
            "add",
            "--milestone",
            "--name",
            "Test Milestone",
            "--desc",
            "A test milestone",
            "--parent-path",
            "test-phase",
        ],
    )
    assert result.exit_code == 0
    mock_core.return_value.add_item.assert_called_once_with(
        item_type="milestone",
        name="Test Milestone",
        description="A test milestone",
        parent_path="test-phase",
        status=None,
    )
    assert "Milestone 'Test Milestone' created successfully." in result.output


@patch("prism.commands.strat.Core")
def test_strat_add_objective(mock_core):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "strat",
            "add",
            "--objective",
            "--name",
            "Test Objective",
            "--desc",
            "A test objective",
            "--parent-path",
            "test-phase/test-milestone",
        ],
    )
    assert result.exit_code == 0
    mock_core.return_value.add_item.assert_called_once_with(
        item_type="objective",
        name="Test Objective",
        description="A test objective",
        parent_path="test-phase/test-milestone",
        status=None,
    )
    assert "Objective 'Test Objective' created successfully." in result.output


@patch("prism.commands.strat.Core")
def test_strat_add_no_item_type(mock_core):
    runner = CliRunner()
    result = runner.invoke(cli, ["strat", "add", "--name", "Test Item"])
    assert result.exit_code == 1  # Expecting an error exit code
    assert "Error: Please specify an item type to add." in result.output
    mock_core.return_value.add_item.assert_not_called()


@patch("prism.commands.strat.Core")
def test_strat_show(mock_core):
    mock_milestone = Milestone(
        id=uuid.uuid4(),
        name="Test Milestone",
        description="A test milestone",
        slug="test-milestone",
        status="pending",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        objectives=[],
    )
    mock_phase = Phase(
        id=uuid.uuid4(),
        name="Test Phase",
        description="A test phase",
        slug="test-phase",
        status="in-progress",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        milestones=[mock_milestone],
    )
    # Set up the mock to return the mock_phase when navigator.get_item_by_path is called
    mock_core.return_value.navigator.get_item_by_path.return_value = mock_phase

    runner = CliRunner()
    result = runner.invoke(cli, ["strat", "show", "--path", "test-phase"])
    assert result.exit_code == 0
    mock_core.return_value.navigator.get_item_by_path.assert_called_once_with("test-phase")
    assert "Name: Test Phase" in result.output
    assert "Description: A test phase" in result.output
    assert "Status: in-progress" in result.output
    assert "Type: Phase" in result.output
    assert "Milestones:" in result.output
    assert "1. Test Milestone (test-milestone)" in result.output


@patch("prism.commands.strat.Core")
def test_strat_show_with_children(mock_core):
    """Test strat show displays child items correctly."""
    mock_milestone = Milestone(
        id=uuid.uuid4(),
        name="Milestone 1",
        description="First milestone",
        slug="milestone-1",
        status="completed",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        objectives=[],
    )
    mock_milestone2 = Milestone(
        id=uuid.uuid4(),
        name="Milestone 2",
        description="Second milestone",
        slug="milestone-2",
        status="pending",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        objectives=[],
    )
    mock_phase = Phase(
        id=uuid.uuid4(),
        name="Test Phase",
        description="A test phase",
        slug="test-phase",
        status="in-progress",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        milestones=[mock_milestone, mock_milestone2],
    )
    mock_core.return_value.navigator.get_item_by_path.return_value = mock_phase

    runner = CliRunner()
    result = runner.invoke(cli, ["strat", "show", "--path", "test-phase"])
    
    assert result.exit_code == 0
    assert "Milestones:" in result.output
    assert "1. Milestone 1 (milestone-1)" in result.output
    assert "2. Milestone 2 (milestone-2)" in result.output


@patch("prism.commands.strat.Core")
def test_strat_show_no_children(mock_core):
    """Test strat show displays 'no children' message."""
    mock_phase = Phase(
        id=uuid.uuid4(),
        name="Empty Phase",
        description="A phase with no milestones",
        slug="empty-phase",
        status="pending",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        milestones=[],
    )
    mock_core.return_value.navigator.get_item_by_path.return_value = mock_phase

    runner = CliRunner()
    result = runner.invoke(cli, ["strat", "show", "--path", "empty-phase"])
    
    assert result.exit_code == 0
    assert "No milestones." in result.output


@patch("prism.commands.strat.Core")
def test_strat_show_json_with_children(mock_core):
    """Test strat show JSON output includes children."""
    mock_deliverable = Deliverable(
        id=uuid.uuid4(),
        name="Test Deliverable",
        description="A test deliverable",
        slug="test-del",
        status="pending",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        actions=[],
    )
    mock_objective = Objective(
        id=uuid.uuid4(),
        name="Test Objective",
        description="A test objective",
        slug="test-obj",
        status="pending",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        deliverables=[mock_deliverable],
    )
    mock_core.return_value.navigator.get_item_by_path.return_value = mock_objective

    runner = CliRunner()
    result = runner.invoke(cli, ["strat", "show", "--path", "test-obj", "--json"])
    
    assert result.exit_code == 0
    import json as json_module
    output_data = json_module.loads(result.output)
    assert "deliverables" in output_data
    assert len(output_data["deliverables"]) == 1
    assert output_data["deliverables"][0]["name"] == "Test Deliverable"
    assert output_data["deliverables"][0]["slug"] == "test-del"


@patch("prism.commands.strat.Core")
def test_strat_add_validation_incomplete_exec_tree(mock_core):
    mock_core.return_value.is_exec_tree_complete.return_value = False

    # Mock get_item_by_path to return a valid Objective,
    # so the validation can proceed
    mock_objective = Objective(
        id=uuid.uuid4(),
        name="Parent Objective",
        description="A parent objective",
        slug="parent-obj",
        status="in-progress",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        deliverables=[],
    )
    mock_core.return_value.navigator.get_item_by_path.return_value = mock_objective

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "strat",
            "add",
            "--objective",
            "--name",
            "New Objective",
            "--parent-path",
            "parent-obj",
        ],
    )

    assert result.exit_code == 1  # Expecting an error exit code
    mock_core.return_value.is_exec_tree_complete.assert_called_once_with(
        "parent-obj"
    )
    mock_core.return_value.add_item.assert_not_called()
    assert (
        "Error: Cannot add strategic item. Execution tree for 'parent-obj' is not complete or does not exist."
        in result.output
    )


@patch("prism.commands.strat.Core")
def test_strat_edit(mock_core):
    runner = CliRunner()
    path = "test-phase/test-milestone"
    new_name = "Updated Milestone Name"
    new_description = "This is an updated description."

    result = runner.invoke(
        cli,
        [
            "strat",
            "edit",
            "--path",
            path,
            "--name",
            new_name,
            "--desc",
            new_description,
        ],
    )

    assert result.exit_code == 0
    mock_core.return_value.update_item.assert_called_once_with(
        path=path,
        name=new_name,
        description=new_description,
        status=None,  # status is removed as per the deliverable
    )
    assert f"Item at '{path}' updated successfully." in result.output


@patch("prism.commands.strat.Core")
def test_strat_edit_from_file(mock_core):
    runner = CliRunner()
    path = "test-phase/test-objective"
    json_file_path = Path("tests/test_strat_edit_file.json")

    with open(json_file_path, "r") as f:
        update_data = json.load(f)

    result = runner.invoke(
        cli, ["strat", "edit", "--path", path, "--file", str(json_file_path)]
    )

    assert result.exit_code == 0
    mock_core.return_value.update_item.assert_called_once_with(
        path=path,
        name=update_data.get("name"),
        description=update_data.get("description"),
        status=None,  # status is removed as per the deliverable
    )
    assert f"Item at '{path}' updated successfully." in result.output


@patch("prism.commands.strat.Core")
def test_strat_delete(mock_core):
    runner = CliRunner()
    path = "test-phase/test-objective"

    result = runner.invoke(cli, ["strat", "delete", "--path", path])

    assert result.exit_code == 0
    mock_core.return_value.delete_item.assert_called_once_with(path=path)
    assert f"Item at '{path}' deleted successfully." in result.output


@patch("prism.commands.strat.Core")
def test_strat_delete_no_path(mock_core):
    runner = CliRunner()
    result = runner.invoke(cli, ["strat", "delete"])

    assert result.exit_code == 2  # Click exits with 2 for missing required options
    assert "Error: Missing option '--path'" in result.output
    mock_core.return_value.delete_item.assert_not_called()


@patch("prism.commands.strat.Core")
def test_strat_show_json_output(mock_core):
    mock_phase_data = Phase(
        name="Test Phase",
        description="A test phase",
        slug="test-phase",
        status="in-progress",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        milestones=[],
    )
    mock_core.return_value.navigator.get_item_by_path.return_value = mock_phase_data

    runner = CliRunner()
    result = runner.invoke(cli, ["strat", "show", "--path", "test-phase", "--json"])
    print(result.output)

    assert result.exit_code == 0
    mock_core.assert_called_once()  # Ensure Tracker class was instantiated
    mock_core.return_value.navigator.get_item_by_path.assert_called_once_with("test-phase")

    try:
        output_json = json.loads(result.output)

        assert output_json["name"] == mock_phase_data.name
        assert output_json["description"] == mock_phase_data.description
        assert output_json["slug"] == mock_phase_data.slug
        assert output_json["status"] == mock_phase_data.status
        assert output_json["created_at"] == mock_phase_data.created_at.isoformat()
        assert output_json["updated_at"] == mock_phase_data.updated_at.isoformat()
        assert output_json["milestones"] == []  # Empty milestones list
    except json.JSONDecodeError:
        pytest.fail("Output is not valid JSON.")


@patch("prism.commands.strat.Core")
def test_strat_edit_completed_item_raises_error(mock_core):
    mock_phase = Phase(
        id=uuid.uuid4(),
        name="Completed Phase",
        description="A completed phase",
        slug="completed-phase",
        status="completed",  # Set status to completed
        created_at=datetime.now(),
        updated_at=datetime.now(),
        milestones=[],
    )
    mock_core.return_value.get_item_by_path.return_value = mock_phase
    # The Tracker.update_item method itself will raise the ValueError
    # when the item_to_update.status is 'completed' or 'archived'.
    # We are mocking the Tracker class directly, so we need to ensure
    # the side_effect correctly simulates the behavior of the real method.
    mock_core.return_value.update_item.side_effect = ValueError(
        "Cannot update item 'dummy/path' because it is already in 'completed' status."
    )

    runner = CliRunner()
    result = runner.invoke(
        cli, ["strat", "edit", "--path", "dummy/path", "--name", "Attempt to Update"]
    )

    assert result.exit_code == 1
    assert (
        "Error: Cannot update item 'dummy/path' because it is already in 'completed' status."
        in result.output
    )

    mock_core.return_value.update_item.assert_called_once_with(
        path="dummy/path", name="Attempt to Update", status=None
    )
