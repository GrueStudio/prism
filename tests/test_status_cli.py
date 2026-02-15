from unittest.mock import patch
from click.testing import CliRunner
from prism.cli import cli
from prism.tracker import Tracker
from pathlib import Path
import json
from datetime import datetime, timedelta

def setup_test_project(tmp_path):
    """Helper function to set up a test project.json with specific data."""
    project_file = tmp_path / "project.json"
    
    # Create a project structure with known states
    # Phase -> Milestone -> Objective -> Deliverable -> Action
    
    yesterday = datetime.now() - timedelta(days=1)
    
    project_data = {
        "phases": [
            {
                "name": "Test Phase 1",
                "status": "completed",
                "milestones": [
                    {
                        "name": "Test Milestone 1.1",
                        "status": "completed",
                        "objectives": [
                            {
                                "name": "Test Objective 1.1.1",
                                "status": "completed",
                                "deliverables": [
                                    {
                                        "name": "Completed Deliverable",
                                        "status": "completed",
                                        "actions": [
                                            {"name": "Completed Action", "status": "completed"}
                                        ]
                                    },
                                    {
                                        "name": "Orphaned Deliverable",
                                        "status": "pending", # Orphan because parent objective is complete
                                        "actions": []
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "name": "Test Phase 2",
                "status": "pending",
                "milestones": [
                    {
                        "name": "Test Milestone 2.1",
                        "status": "pending",
                        "objectives": [
                            {
                                "name": "Test Objective 2.1.1",
                                "status": "pending",
                                "deliverables": [
                                    {
                                        "name": "Deliverable with Overdue Action",
                                        "status": "in-progress",
                                        "actions": [
                                            {
                                                "name": "Overdue Action", 
                                                "status": "pending",
                                                "due_date": yesterday.isoformat()
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }

    with patch.object(Tracker, '_load_project_data', return_value=project_data):
        with patch.object(Tracker, '_save_project_data', return_value=None):
            tracker = Tracker(project_file=project_file)
            # The add_exec_tree logic can be complex, so we'll mock the data loading directly for this test
            # This ensures we are testing the `status` command's output based on a known data state.
            
            # Since we're mocking _load_project_data, we can't use add_exec_tree.
            # We'll need to create a project.json file manually.
            
            # We can't easily create a full project.json with all the required fields (like slug, id, etc)
            # without re-implementing a lot of the tracker logic here.
            
            # The best approach is to use the existing tracker logic to create the project,
            # then modify it to fit the test case.
            
            # Let's use a simplified approach: we will mock get_status_summary
            # to return a predictable dictionary, and test the CLI output formatting.
            pass


@patch('prism.commands.status.Tracker')
def test_status_command_output(mock_tracker, tmp_path):
    """Test the output formatting of the 'status' command."""

    yesterday = datetime.now() - timedelta(days=1)

    # Configure the mock to have the new methods
    mock_tracker.return_value.get_current_strategic_items.return_value = {
        "phase": None,
        "milestone": None,
        "objective": None
    }
    mock_tracker.return_value.get_current_action.return_value = None
    mock_tracker.return_value.calculate_completion_percentage.return_value = {"overall": 0.0}
    mock_tracker.return_value.get_item_path.return_value = None

    mock_summary = {
        "item_counts": {
            "Phase": {"pending": 1, "completed": 1, "total": 2},
            "Milestone": {"pending": 1, "completed": 1, "total": 2},
            "Objective": {"pending": 1, "completed": 1, "total": 2},
            "Deliverable": {"pending": 2, "completed": 1, "total": 3},
            "Action": {"pending": 1, "completed": 1, "total": 2},
        },
        "overdue_actions": [
            {"path": "test-phase-2/test-milesto/test-object/deliverable/overdue-ac", "due_date": yesterday.isoformat()}
        ],
        "orphaned_items": [
            {"path": "test-phase-1/test-milesto/test-object/orphaned-de", "type": "Deliverable"}
        ],
    }

    mock_tracker.return_value.get_status_summary.return_value = mock_summary

    runner = CliRunner()
    result = runner.invoke(cli, ['status'])

    assert result.exit_code == 0

    # Check for titles
    assert "Project Status Summary" in result.output
    assert "Item Counts:" in result.output
    assert "Overdue Actions:" in result.output
    assert "Orphaned Items:" in result.output

    # Check item counts
    assert "Phases: 1 completed / 2 total" in result.output
    assert "Milestones: 1 completed / 2 total" in result.output
    assert "Objectives: 1 completed / 2 total" in result.output
    assert "Deliverables: 1 completed / 3 total" in result.output
    assert "Actions: 1 completed / 2 total" in result.output

    # Check overdue actions
    assert "Path: test-phase-2/test-milesto/test-object/deliverable/overdue-ac" in result.output
    assert f"(Due: {yesterday.strftime('%Y-%m-%d')})" in result.output

    # Check orphaned items
    assert "Path: test-phase-1/test-milesto/test-object/orphaned-de" in result.output
    assert "(Type: Deliverable)" in result.output

@patch('prism.commands.status.Tracker')
def test_status_command_no_issues(mock_tracker):
    """Test the output when there are no overdue or orphaned items."""
    
    mock_summary = {
        "item_counts": {
            "Phase": {"pending": 2, "completed": 0, "total": 2},
            "Milestone": {"pending": 2, "completed": 0, "total": 2},
            "Objective": {"pending": 0, "completed": 0, "total": 0},
            "Deliverable": {"pending": 0, "completed": 0, "total": 0},
            "Action": {"pending": 0, "completed": 0, "total": 0},
        },
        "overdue_actions": [],
        "orphaned_items": [],
    }
    
    mock_tracker.return_value.get_status_summary.return_value = mock_summary
    
    runner = CliRunner()
    result = runner.invoke(cli, ['status'])
    
    assert result.exit_code == 0
    
    assert "No overdue actions." in result.output
    assert "No orphaned items found." in result.output

@patch('prism.commands.status.Tracker')
def test_status_command_with_phase_filter(mock_tracker):
    """Test the 'status' command with a --phase filter."""
    
    mock_summary = {
        "item_counts": {
            "Phase": {"pending": 1, "completed": 0, "total": 1},
            "Milestone": {"pending": 1, "completed": 0, "total": 1},
            "Objective": {"pending": 1, "completed": 0, "total": 1},
            "Deliverable": {"pending": 1, "completed": 0, "total": 1},
            "Action": {"pending": 1, "completed": 0, "total": 1},
        },
        "overdue_actions": [],
        "orphaned_items": [],
    }
    mock_tracker.return_value.get_status_summary.return_value = mock_summary
    
    runner = CliRunner()
    result = runner.invoke(cli, ['status', '--phase', 'test-phase-2'])
    
    assert result.exit_code == 0
    mock_tracker.return_value.get_status_summary.assert_called_once_with(phase_path='test-phase-2', milestone_path=None)
    
    assert "Project Status Summary for Phase 'test-phase-2'" in result.output
    assert "Phases: 0 completed / 1 total" in result.output
    assert "Milestones: 0 completed / 1 total" in result.output

@patch('prism.commands.status.Tracker')
def test_status_command_with_milestone_filter(mock_tracker):
    """Test the 'status' command with a --milestone filter."""
    
    mock_summary = {
        "item_counts": {
            "Milestone": {"pending": 0, "completed": 1, "total": 1},
            "Objective": {"pending": 0, "completed": 1, "total": 1},
            "Deliverable": {"pending": 1, "completed": 1, "total": 2},
            "Action": {"pending": 0, "completed": 1, "total": 1},
        },
        "overdue_actions": [],
        "orphaned_items": [{"path": "test-phase-1/test-milestone-1/test-objective-1/orphaned-deliverable", "type": "Deliverable"}],
    }
    mock_tracker.return_value.get_status_summary.return_value = mock_summary
    
    runner = CliRunner()
    result = runner.invoke(cli, ['status', '--milestone', 'test-phase-1/test-milestone-1'])
    
    assert result.exit_code == 0
    mock_tracker.return_value.get_status_summary.assert_called_once_with(phase_path=None, milestone_path='test-phase-1/test-milestone-1')
    
    assert "Project Status Summary for Milestone 'test-phase-1/test-milestone-1'" in result.output
    assert "Milestones: 1 completed / 1 total" in result.output
    assert "Orphaned Items:" in result.output
    assert "Path: test-phase-1/test-milestone-1/test-objective-1/orphaned-deliverable" in result.output
