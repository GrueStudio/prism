from unittest.mock import patch, MagicMock
import uuid
from click.testing import CliRunner
from prism.cli import cli
from prism.models import Phase, Objective
from datetime import datetime

def test_cli_registers_strat_and_exec_groups():
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'strat' in result.output
    assert 'exec' in result.output

@patch('prism.commands.strat.Tracker')
def test_strat_add_phase(mock_tracker):
    runner = CliRunner()
    result = runner.invoke(cli, ['strat', 'add', '--phase', '--name', 'Test Phase', '--desc', 'A test phase'])
    assert result.exit_code == 0
    mock_tracker.return_value.add_item.assert_called_once_with(
        item_type='phase',
        name='Test Phase',
        description='A test phase',
        parent_path=None
    )
    assert "Phase 'Test Phase' created successfully." in result.output

@patch('prism.commands.strat.Tracker')
def test_strat_add_milestone(mock_tracker):
    runner = CliRunner()
    result = runner.invoke(cli, ['strat', 'add', '--milestone', '--name', 'Test Milestone', '--desc', 'A test milestone', '--parent-path', 'test-phase'])
    assert result.exit_code == 0
    mock_tracker.return_value.add_item.assert_called_once_with(
        item_type='milestone',
        name='Test Milestone',
        description='A test milestone',
        parent_path='test-phase'
    )
    assert "Milestone 'Test Milestone' created successfully." in result.output

@patch('prism.commands.strat.Tracker')
def test_strat_add_objective(mock_tracker):
    runner = CliRunner()
    result = runner.invoke(cli, ['strat', 'add', '--objective', '--name', 'Test Objective', '--desc', 'A test objective', '--parent-path', 'test-phase/test-milestone'])
    assert result.exit_code == 0
    mock_tracker.return_value.add_item.assert_called_once_with(
        item_type='objective',
        name='Test Objective',
        description='A test objective',
        parent_path='test-phase/test-milestone'
    )
    assert "Objective 'Test Objective' created successfully." in result.output

@patch('prism.commands.strat.Tracker')
def test_strat_add_no_item_type(mock_tracker):
    runner = CliRunner()
    result = runner.invoke(cli, ['strat', 'add', '--name', 'Test Item'])
    assert result.exit_code == 1 # Expecting an error exit code
    assert "Error: Please specify an item type to add." in result.output
    mock_tracker.return_value.add_item.assert_not_called()

@patch('prism.commands.strat.Tracker')
def test_strat_show(mock_tracker):
    mock_phase = Phase(
        id=uuid.uuid4(),
        name='Test Phase',
        description='A test phase',
        slug='test-phase',
        status='in-progress',
        created_at=datetime.now(),
        updated_at=datetime.now(),
        milestones=[]
    )
    mock_tracker.return_value.get_item_by_path.return_value = mock_phase

    runner = CliRunner()
    result = runner.invoke(cli, ['strat', 'show', '--path', 'test-phase'])
    assert result.exit_code == 0
    mock_tracker.return_value.get_item_by_path.assert_called_once_with('test-phase')
    assert "Name: Test Phase" in result.output
    assert "Description: A test phase" in result.output
    assert "Status: in-progress" in result.output
    assert "Type: Phase" in result.output

@patch('prism.commands.strat.Tracker')
def test_strat_add_validation_incomplete_exec_tree(mock_tracker):
    mock_tracker.return_value.is_exec_tree_complete.return_value = False
    
    # Mock get_item_by_path to return a valid Objective,
    # so the validation can proceed
    mock_objective = Objective(
        id=uuid.uuid4(),
        name='Parent Objective',
        description='A parent objective',
        slug='parent-obj',
        status='in-progress',
        created_at=datetime.now(),
        updated_at=datetime.now(),
        deliverables=[]
    )
    mock_tracker.return_value.get_item_by_path.return_value = mock_objective

    runner = CliRunner()
    result = runner.invoke(cli, ['strat', 'add', '--objective', '--name', 'New Objective', '--parent-path', 'parent-obj'])
    
    assert result.exit_code == 1 # Expecting an error exit code
    mock_tracker.return_value.is_exec_tree_complete.assert_called_once_with('parent-obj')
    mock_tracker.return_value.add_item.assert_not_called()
    assert "Error: Cannot add strategic item. Execution tree for 'parent-obj' is not complete or does not exist." in result.output