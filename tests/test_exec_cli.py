from unittest.mock import patch, MagicMock
import uuid
import json
from pathlib import Path
from click.testing import CliRunner
from prism.cli import cli
from prism.models import Deliverable
from datetime import datetime

@patch('prism.commands.exec.Tracker')
def test_exec_add_deliverable(mock_tracker):
    runner = CliRunner()
    result = runner.invoke(cli, ['exec', 'add', '--deliverable', '--name', 'Test Deliverable', '--desc', 'A test deliverable', '--parent-path', 'test-phase/test-milestone/test-objective'])
    assert result.exit_code == 0
    mock_tracker.return_value.add_item.assert_called_once_with(
        item_type='deliverable',
        name='Test Deliverable',
        description='A test deliverable',
        parent_path='test-phase/test-milestone/test-objective'
    )
    assert "Deliverable 'Test Deliverable' created successfully." in result.output

@patch('prism.commands.exec.Tracker')
def test_exec_add_action(mock_tracker):
    runner = CliRunner()
    result = runner.invoke(cli, ['exec', 'add', '--action', '--name', 'Test Action', '--desc', 'A test action', '--parent-path', 'test-phase/test-milestone/test-objective/test-deliverable'])
    assert result.exit_code == 0
    mock_tracker.return_value.add_item.assert_called_once_with(
        item_type='action',
        name='Test Action',
        description='A test action',
        parent_path='test-phase/test-milestone/test-objective/test-deliverable'
    )
    assert "Action 'Test Action' created successfully." in result.output

@patch('prism.commands.exec.Tracker')
def test_exec_add_no_item_type(mock_tracker):
    runner = CliRunner()
    result = runner.invoke(cli, ['exec', 'add', '--name', 'Test Item'])
    assert result.exit_code == 1 # Expecting an error exit code
    assert "Error: Please specify an item type to add." in result.output
    mock_tracker.return_value.add_item.assert_not_called()

@patch('prism.commands.exec.Tracker')
def test_exec_show(mock_tracker):
    mock_deliverable = Deliverable(
        id=uuid.uuid4(),
        name='Test Deliverable',
        description='A test deliverable',
        slug='test-deliv',
        status='in-progress',
        created_at=datetime.now(),
        updated_at=datetime.now(),
        actions=[]
    )
    mock_tracker.return_value.get_item_by_path.return_value = mock_deliverable

    runner = CliRunner()
    result = runner.invoke(cli, ['exec', 'show', '--path', 'test-phase/test-milestone/test-objective/test-deliverable'])
    assert result.exit_code == 0
    mock_tracker.return_value.get_item_by_path.assert_called_once_with('test-phase/test-milestone/test-objective/test-deliverable')
    assert "Name: Test Deliverable" in result.output
    assert "Description: A test deliverable" in result.output
    assert "Status: in-progress" in result.output
    assert "Type: Deliverable" in result.output

@patch('prism.commands.exec.Tracker')
def test_exec_addtree(mock_tracker):
    runner = CliRunner()
    json_file_path = Path('tests/test_exec_tree.json')
    with open(json_file_path, 'r') as f:
        expected_data = json.load(f)

    # Test with default mode (append)
    result = runner.invoke(cli, ['exec', 'addtree', str(json_file_path)])
    assert result.exit_code == 0
    mock_tracker.return_value.add_exec_tree.assert_called_once_with(expected_data, 'append')
    assert "Execution tree added successfully in 'append' mode." in result.output
    mock_tracker.return_value.add_exec_tree.reset_mock()

    # Test with replace mode
    result = runner.invoke(cli, ['exec', 'addtree', str(json_file_path), '--mode', 'replace'])
    assert result.exit_code == 0
    mock_tracker.return_value.add_exec_tree.assert_called_once_with(expected_data, 'replace')
    assert "Execution tree added successfully in 'replace' mode." in result.output
    mock_tracker.return_value.add_exec_tree.reset_mock()

    # Test with append mode explicitly
    result = runner.invoke(cli, ['exec', 'addtree', str(json_file_path), '--mode', 'append'])
    assert result.exit_code == 0
    mock_tracker.return_value.add_exec_tree.assert_called_once_with(expected_data, 'append')
    assert "Execution tree added successfully in 'append' mode." in result.output
    mock_tracker.return_value.add_exec_tree.reset_mock()

@patch('prism.commands.exec.Tracker')
def test_exec_addtree_file_not_found(mock_tracker):
    runner = CliRunner()
    non_existent_file = "non_existent.json"
    result = runner.invoke(cli, ['exec', 'addtree', non_existent_file])
    assert result.exit_code == 2 # click.Path(exists=True) exits with code 2 for non-existent files
    assert "Error: Invalid value for 'JSON_FILE_PATH': File 'non_existent.json' does not exist." in result.output
    mock_tracker.return_value.add_exec_tree.assert_not_called()

@patch('prism.commands.exec.Tracker')
def test_exec_addtree_invalid_json(mock_tracker):
    runner = CliRunner()
    invalid_json_file = "tests/invalid_exec_tree.json"
    Path(invalid_json_file).write_text("{invalid json}")
    result = runner.invoke(cli, ['exec', 'addtree', invalid_json_file])
    assert result.exit_code == 1
    assert "Error: Invalid JSON format" in result.output
    mock_tracker.return_value.add_exec_tree.assert_not_called()
    Path(invalid_json_file).unlink() # Clean up
