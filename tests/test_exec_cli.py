import json
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from prism.cli import cli
from prism.models import Deliverable
from prism.exceptions import InvalidOperationError


@patch("prism.commands.exec.Core")
def test_exec_add_deliverable(mock_core):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "exec",
            "add",
            "--deliverable",
            "--name",
            "Test Deliverable",
            "--desc",
            "A test deliverable",
            "--parent-path",
            "test-phase/test-milestone/test-objective",
        ],
    )
    assert result.exit_code == 0
    mock_core.return_value.add_item.assert_called_once_with(
        item_type="deliverable",
        name="Test Deliverable",
        description="A test deliverable",
        parent_path="test-phase/test-milestone/test-objective",
        status=None,
    )
    assert "Deliverable 'Test Deliverable' created successfully." in result.output


@patch("prism.commands.exec.Core")
def test_exec_add_action(mock_core):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "exec",
            "add",
            "--action",
            "--name",
            "Test Action",
            "--desc",
            "A test action",
            "--parent-path",
            "test-phase/test-milestone/test-objective/test-deliverable",
        ],
    )
    assert result.exit_code == 0
    mock_core.return_value.add_item.assert_called_once_with(
        item_type="action",
        name="Test Action",
        description="A test action",
        parent_path="test-phase/test-milestone/test-objective/test-deliverable",
        status=None,
    )
    assert "Action 'Test Action' created successfully." in result.output


@patch("prism.commands.exec.Core")
def test_exec_add_no_item_type(mock_core):
    runner = CliRunner()
    result = runner.invoke(cli, ["exec", "add", "--name", "Test Item"])
    assert result.exit_code == 1  # Expecting an error exit code
    assert "Error: Please specify an item type to add." in result.output
    mock_core.return_value.add_item.assert_not_called()


@patch("prism.commands.exec.Core")
def test_exec_show(mock_core):
    mock_deliverable = Deliverable(
        id=uuid.uuid4(),
        name="Test Deliverable",
        description="A test deliverable",
        slug="test-deliv",
        status="in-progress",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        actions=[],
    )
    mock_core.return_value.navigator.get_item_by_path.return_value = mock_deliverable

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "exec",
            "show",
            "--path",
            "test-phase/test-milestone/test-objective/test-deliverable",
        ],
    )
    assert result.exit_code == 0
    mock_core.return_value.navigator.get_item_by_path.assert_called_once_with(
        "test-phase/test-milestone/test-objective/test-deliverable"
    )
    assert "Name: Test Deliverable" in result.output
    assert "Description: A test deliverable" in result.output
    assert "Status: in-progress" in result.output
    assert "Type: Deliverable" in result.output


@patch("prism.commands.exec.Core")
def test_exec_addtree(mock_core):
    runner = CliRunner()
    json_file_path = Path("tests/test_simplified_exec_tree.json")
    with open(json_file_path, "r") as f:
        expected_data = json.load(f)

    # Test with default mode (append)
    result = runner.invoke(cli, ["exec", "addtree", str(json_file_path)])
    assert result.exit_code == 0
    mock_core.return_value.add_exec_tree.assert_called_once_with(
        expected_data, "append"
    )
    assert "Execution tree added successfully in 'append' mode." in result.output
    mock_core.return_value.add_exec_tree.reset_mock()

    # Test with replace mode
    result = runner.invoke(
        cli, ["exec", "addtree", str(json_file_path), "--mode", "replace"]
    )
    assert result.exit_code == 0
    mock_core.return_value.add_exec_tree.assert_called_once_with(
        expected_data, "replace"
    )
    assert "Execution tree added successfully in 'replace' mode." in result.output
    mock_core.return_value.add_exec_tree.reset_mock()

    # Test with append mode explicitly
    result = runner.invoke(
        cli, ["exec", "addtree", str(json_file_path), "--mode", "append"]
    )
    assert result.exit_code == 0
    mock_core.return_value.add_exec_tree.assert_called_once_with(
        expected_data, "append"
    )
    assert "Execution tree added successfully in 'append' mode." in result.output
    mock_core.return_value.add_exec_tree.reset_mock()


@patch("prism.commands.exec.Core")
def test_exec_addtree_file_not_found(mock_core):
    runner = CliRunner()
    non_existent_file = "non_existent.json"
    result = runner.invoke(cli, ["exec", "addtree", non_existent_file])
    assert (
        result.exit_code == 2
    )  # click.Path(exists=True) exits with code 2 for non-existent files
    assert (
        "Error: Invalid value for 'JSON_FILE_PATH': File 'non_existent.json' does not exist."
        in result.output
    )
    mock_core.return_value.add_exec_tree.assert_not_called()


@patch("prism.commands.exec.Core")
def test_exec_addtree_invalid_json(mock_core):
    runner = CliRunner()
    invalid_json_file = "tests/invalid_exec_tree.json"
    Path(invalid_json_file).write_text("{invalid json}")
    result = runner.invoke(cli, ["exec", "addtree", invalid_json_file])
    assert result.exit_code == 1
    assert "Error: Invalid JSON format" in result.output
    mock_core.return_value.add_exec_tree.assert_not_called()
    Path(invalid_json_file).unlink()  # Clean up


@patch("prism.commands.exec.Core")
def test_exec_edit(mock_core):
    runner = CliRunner()
    path = "test-phase/test-milestone/test-objective/test-deliverable"
    new_name = "Updated Deliverable Name"
    new_description = "This is an updated deliverable description."
    new_due_date = "2024-12-31"  # Example date string

    result = runner.invoke(
        cli,
        [
            "exec",
            "edit",
            "--path",
            path,
            "--name",
            new_name,
            "--desc",
            new_description,
            "--due-date",
            new_due_date,
        ],
    )

    assert result.exit_code == 0
    mock_core.return_value.update_item.assert_called_once_with(
        path=path,
        name=new_name,
        description=new_description,
        due_date=new_due_date,  # due_date is included for exec items
        status=None,  # status is removed as per the deliverable
    )
    assert f"Item at '{path}' updated successfully." in result.output


@patch("prism.commands.exec.Core")
def test_exec_edit_from_file(mock_core):
    runner = CliRunner()
    path = "test-phase/test-milestone/test-objective/test-action"
    json_file_path = Path("tests/test_exec_edit_file.json")

    with open(json_file_path, "r") as f:
        update_data = json.load(f)

    result = runner.invoke(
        cli, ["exec", "edit", "--path", path, "--file", str(json_file_path)]
    )

    assert result.exit_code == 0
    mock_core.return_value.update_item.assert_called_once_with(
        path=path,
        name=update_data.get("name"),
        description=update_data.get("description"),
        due_date=update_data.get("due_date"),
        status=None,
    )
    assert f"Item at '{path}' updated successfully." in result.output


@patch("prism.commands.exec.Core")
def test_exec_delete(mock_core):
    runner = CliRunner()
    path = "test-phase/test-milestone/test-objective/test-action"

    result = runner.invoke(cli, ["exec", "delete", "--path", path])

    assert result.exit_code == 0
    mock_core.return_value.delete_item.assert_called_once_with(path=path)
    assert f"Item at '{path}' deleted successfully." in result.output


@patch("prism.commands.exec.Core")
def test_exec_delete_no_path(mock_core):
    runner = CliRunner()
    result = runner.invoke(cli, ["exec", "delete"])

    assert result.exit_code == 2  # Click exits with 2 for missing required options
    assert "Error: Missing option '--path'" in result.output
    mock_core.return_value.delete_item.assert_not_called()


@patch("prism.commands.exec.Core")
def test_exec_show_json_output(mock_core):
    # Use consistent datetime objects for both mock creation and assertion
    now = datetime.now()
    mock_deliverable = Deliverable(
        name="Test Deliverable",
        description="A test deliverable",
        slug="test-deliv",
        status="in-progress",
        created_at=now,
        updated_at=now,
        actions=[],
    )
    mock_core.return_value.navigator.get_item_by_path.return_value = mock_deliverable

    runner = CliRunner()
    result = runner.invoke(cli, ["exec", "show", "--path", "dummy/path", "--json"])

    assert result.exit_code == 0
    mock_core.return_value.navigator.get_item_by_path.assert_called_once_with("dummy/path")

    try:
        output_json = json.loads(result.output)
    except json.JSONDecodeError:
        assert False, "Output is not valid JSON"

    assert output_json["name"] == "Test Deliverable"
    assert output_json["description"] == "A test deliverable"
    assert output_json["slug"] == "test-deliv"
    assert output_json["status"] == "in-progress"
    assert output_json["created_at"] == now.isoformat()
    assert output_json["updated_at"] == now.isoformat()
    assert output_json["actions"] == []


@patch("prism.commands.exec.Core")
def test_exec_edit_completed_item_raises_error(mock_core):
    mock_deliverable = Deliverable(
        id=uuid.uuid4(),
        name="Completed Deliverable",
        description="A completed deliverable",
        slug="completed-deliv",
        status="completed",  # Set status to completed
        created_at=datetime.now(),
        updated_at=datetime.now(),
        actions=[],
    )
    mock_core.return_value.navigator.get_item_by_path.return_value = mock_deliverable
    mock_core.return_value.update_item.side_effect = InvalidOperationError(
        "Cannot update item 'dummy/path' because it is already in 'completed' status."
    )

    runner = CliRunner()
    result = runner.invoke(
        cli, ["exec", "edit", "--path", "dummy/path", "--name", "Attempt to Update"]
    )

    print(result.output)
    assert result.exit_code == 1
    assert (
        "Error: Cannot update item 'dummy/path' because it is already in 'completed' status."
        in result.output
    )

    mock_core.return_value.update_item.assert_called_once_with(
        path="dummy/path", name="Attempt to Update", status=None
    )


@patch("prism.commands.exec.Core")
def test_exec_delete_completed_item_raises_error(mock_core):
    mock_deliverable = Deliverable(
        id=uuid.uuid4(),
        name="Completed Deliverable",
        description="A completed deliverable",
        slug="completed-deliv",
        status="completed",  # Set status to completed
        created_at=datetime.now(),
        updated_at=datetime.now(),
        actions=[],
    )
    mock_core.return_value.navigator.get_item_by_path.return_value = mock_deliverable
    mock_core.return_value.delete_item.side_effect = InvalidOperationError(
        "Cannot delete item 'dummy/path' because it is already in 'completed' status."
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["exec", "delete", "--path", "dummy/path"])

    print(result.output)
    assert result.exit_code == 1
    assert (
        "Operation Error: Cannot delete item 'dummy/path' because it is already in 'completed' status."
        in result.output
    )

    mock_core.return_value.delete_item.assert_called_once_with(path="dummy/path")
