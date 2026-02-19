import pytest
from click.testing import CliRunner
from prism.cli import cli
from prism.models_old import ProjectData, Phase, Milestone, Objective, Deliverable, Action
from prism.core_old import Core
from unittest.mock import patch, MagicMock


@patch("prism.commands.task_old.Core")
def test_task_start_with_pending_task(mock_core_class):
    """Test 'prism task start' when there is a pending task."""
    runner = CliRunner()

    # Setup mock data
    action1 = Action(name="Action 1", slug="action-1", status="pending")
    deliverable1 = Deliverable(name="Deliverable 1", slug="deliverable-1", actions=[action1])
    objective1 = Objective(name="Objective 1", slug="objective-1", deliverables=[deliverable1])
    milestone1 = Milestone(name="Milestone 1", slug="milestone-1", objectives=[objective1])
    phase1 = Phase(name="Phase 1", slug="phase-1", milestones=[milestone1])
    project_data = ProjectData(phases=[phase1])

    # Configure the mock
    mock_core_instance = mock_core_class.return_value
    mock_core_instance.start_next_action.return_value = action1

    # Run the command
    result = runner.invoke(cli, ["task", "start"])

    # Assertions
    assert result.exit_code == 0
    assert "Currently working on: Action 1" in result.output
    mock_core_instance.start_next_action.assert_called_once()

@patch("prism.commands.task_old.Core")
def test_task_start_no_pending_tasks(mock_core_class):
    """Test 'prism task start' when there are no pending tasks."""
    runner = CliRunner()
    
    # Configure the mock to return None, simulating no pending tasks
    mock_core_instance = mock_core_class.return_value
    mock_core_instance.start_next_action.return_value = None
    
    # Run the command
    result = runner.invoke(cli, ["task", "start"])
    
    # Assertions
    assert result.exit_code == 0
    assert "No pending tasks found." in result.output
    mock_core_instance.start_next_action.assert_called_once()

@patch("prism.commands.task_old.Core")
def test_task_done_with_in_progress_task(mock_core_class):
    """Test 'prism task done' when there is a task in progress."""
    runner = CliRunner()

    # Setup mock data for current action
    current_action = Action(name="Current Task", slug="current-task", status="in-progress")

    # Configure the mock
    mock_core_instance = mock_core_class.return_value
    mock_core_instance.complete_current_action.return_value = current_action

    # Run the command
    result = runner.invoke(cli, ["task", "done"])

    # Assertions
    assert result.exit_code == 0
    assert "Completed task: Current Task" in result.output
    mock_core_instance.complete_current_action.assert_called_once()

@patch("prism.commands.task_old.Core")
def test_task_done_no_in_progress_task(mock_core_class):
    """Test 'prism task done' when there is no task in progress."""
    runner = CliRunner()

    # Configure the mock to return None, simulating no task in progress
    mock_core_instance = mock_core_class.return_value
    mock_core_instance.complete_current_action.return_value = None

    # Run the command
    result = runner.invoke(cli, ["task", "done"])

    # Assertions
    assert result.exit_code == 0
    assert "No task in progress." in result.output
    mock_core_instance.complete_current_action.assert_called_once()
    mock_core_instance.get_current_action.assert_not_called()

@patch("prism.commands.task_old.Core")
def test_task_next_with_in_progress_task(mock_core_class):
    """Test 'prism task next' when there is a task in progress."""
    runner = CliRunner()

    # Setup mock data for completed and next actions
    completed_action = Action(name="Completed Task", slug="completed-task", status="completed")
    next_action = Action(name="Next New Task", slug="next-new-task", status="in-progress")

    # Configure the mock
    mock_core_instance = mock_core_class.return_value
    mock_core_instance.complete_current_and_start_next.return_value = (completed_action, next_action)

    # Run the command
    result = runner.invoke(cli, ["task", "next"])

    # Assertions
    assert result.exit_code == 0
    assert "Completed task: Completed Task" in result.output
    assert "Started next task: Next New Task" in result.output
    mock_core_instance.complete_current_and_start_next.assert_called_once()

@patch("prism.commands.task_old.Core")
def test_task_next_no_in_progress_task(mock_core_class):
    """Test 'prism task next' when there is no task in progress."""
    runner = CliRunner()

    # Configure the mock to return (None, None), simulating no task in progress to complete
    mock_core_instance = mock_core_class.return_value
    mock_core_instance.complete_current_and_start_next.return_value = (None, None)

    # Run the command
    result = runner.invoke(cli, ["task", "next"])

    # Assertions
    assert result.exit_code == 0
    assert "No task in progress to complete." in result.output
    mock_core_instance.complete_current_and_start_next.assert_called_once()

@patch("prism.commands.task_old.Core")
def test_task_workflow(mock_core_class):
    """Test the full workflow: start, next, done."""
    runner = CliRunner()

    # Setup mock data for multiple actions
    action1 = Action(name="Action 1", slug="action-1", status="pending")
    action2 = Action(name="Action 2", slug="action-2", status="pending")
    action3 = Action(name="Action 3", slug="action-3", status="pending")

    # Configure the mock
    mock_core_instance = mock_core_class.return_value

    # --- Step 1: Start the first task ---
    mock_core_instance.start_next_action.return_value = action1
    result = runner.invoke(cli, ["task", "start"])
    assert result.exit_code == 0
    assert "Currently working on: Action 1" in result.output
    mock_core_instance.start_next_action.assert_called_once()
    mock_core_instance.start_next_action.reset_mock()

    # --- Step 2: Complete current and start next (Action 2) ---
    mock_core_instance.complete_current_and_start_next.return_value = (action1, action2)
    result = runner.invoke(cli, ["task", "next"])
    assert result.exit_code == 0
    assert "Completed task: Action 1" in result.output
    assert "Started next task: Action 2" in result.output
    mock_core_instance.complete_current_and_start_next.assert_called_once()
    mock_core_instance.complete_current_and_start_next.reset_mock()

    # --- Step 3: Complete current (Action 2) using 'done' (doesn't start next) ---
    mock_core_instance.complete_current_action.return_value = action2
    result = runner.invoke(cli, ["task", "done"])
    assert result.exit_code == 0
    assert "Completed task: Action 2" in result.output
    mock_core_instance.complete_current_action.assert_called_once()
    mock_core_instance.complete_current_action.reset_mock()

    # --- Step 4: Complete current (Action 3) using 'done', no more tasks ---
    mock_core_instance.complete_current_action.return_value = action3
    result = runner.invoke(cli, ["task", "done"])
    assert result.exit_code == 0
    assert "Completed task: Action 3" in result.output
    mock_core_instance.complete_current_action.assert_called_once()