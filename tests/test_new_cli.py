"""
Tests for the new CRUD CLI commands.

Uses mocks to avoid modifying actual project data.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from prism.cli import cli as newcli
from prism.core import PrismCore
from prism.models import Phase, Milestone, Objective, Deliverable, Action


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_core():
    """Create a mock PrismCore for testing."""
    core = Mock(spec=PrismCore)
    
    # Create mock items
    phase = Phase(
        uuid="phase-uuid",
        name="Test Phase",
        slug="test-phase",
        status="pending"
    )
    milestone = Milestone(
        uuid="milestone-uuid",
        name="Test Milestone",
        slug="test-milestone",
        status="pending",
        parent_uuid="phase-uuid"
    )
    objective = Objective(
        uuid="objective-uuid",
        name="Test Objective",
        slug="test-objective",
        status="pending",
        parent_uuid="milestone-uuid"
    )
    deliverable = Deliverable(
        uuid="deliverable-uuid",
        name="Test Deliverable",
        slug="test-deliverable",
        status="pending",
        parent_uuid="objective-uuid"
    )
    action = Action(
        uuid="action-uuid",
        name="Test Action",
        slug="test-action",
        status="pending",
        parent_uuid="deliverable-uuid"
    )
    
    # Build hierarchy
    phase.milestones.append(milestone)
    milestone.objectives.append(objective)
    objective.deliverables.append(deliverable)
    deliverable.actions.append(action)
    
    # Setup mock project
    core.project = Mock()
    core.project.phases = [phase]
    core.project.get_by_uuid = Mock(side_effect=lambda uuid: {
        "phase-uuid": phase,
        "milestone-uuid": milestone,
        "objective-uuid": objective,
        "deliverable-uuid": deliverable,
        "action-uuid": action,
    }.get(uuid))
    
    # Setup mock navigator
    core.navigator = Mock()
    core.navigator.get_current_phase = Mock(return_value=phase)
    core.navigator.get_current_milestone = Mock(return_value=milestone)
    core.navigator.get_current_objective = Mock(return_value=objective)
    core.navigator.get_item_by_path = Mock(side_effect=lambda path: {
        "1": phase,
        "1/1": milestone,
        "1/1/1": objective,
        "1/1/1/1": deliverable,
        "1/1/1/1/1": action,
        "test-phase": phase,
        "test-phase/test-milestone": milestone,
        "test-phase/test-milestone/test-objective": objective,
        "objective-uuid/test-deliverable": deliverable,
        "1/1/1/test-deliverable": deliverable,
    }.get(path))
    core.navigator.get_item_path = Mock(side_effect=lambda item: {
        "phase-uuid": "1",
        "milestone-uuid": "1/1",
        "objective-uuid": "1/1/1",
        "deliverable-uuid": "1/1/1/1",
        "action-uuid": "1/1/1/1/1",
    }.get(getattr(item, 'uuid', None), "unknown"))
    
    # Setup mock methods
    core.add_item = Mock()
    core.update_item = Mock()
    core.delete_item = Mock()
    core.is_exec_tree_complete = Mock(return_value=True)
    
    # Setup mock task manager
    core.task_manager = Mock()
    core.task_manager.start_next_action = Mock(return_value=None)
    core.task_manager.complete_current_action = Mock(return_value=None)
    core.task_manager.complete_current_and_start_next = Mock(return_value=(None, None))
    
    return core


class TestCrudShow:
    """Tests for crud show command."""
    
    def test_show_with_path(self, runner, mock_core):
        """Test showing an item by path."""
        with patch('prism.commands.crud.PrismCore', return_value=mock_core):
            result = runner.invoke(newcli, ['crud', 'show', '1/1/1'])
            
            assert result.exit_code == 0
            assert 'Test Objective' in result.output
            assert 'Type: Objective' in result.output
    
    def test_show_with_uuid(self, runner, mock_core):
        """Test showing an item by UUID."""
        with patch('prism.commands.crud.PrismCore', return_value=mock_core):
            result = runner.invoke(newcli, ['crud', 'show', '-u', 'objective-uuid'])
            
            assert result.exit_code == 0
            assert 'Test Objective' in result.output
    
    def test_show_no_path_defaults_to_phase(self, runner, mock_core):
        """Test showing with no path defaults to current phase."""
        with patch('prism.commands.crud.PrismCore', return_value=mock_core):
            result = runner.invoke(newcli, ['crud', 'show'])
            
            assert result.exit_code == 0
            assert 'Test Phase' in result.output
            assert 'Type: Phase' in result.output
    
    def test_show_json_output(self, runner, mock_core):
        """Test showing an item in JSON format."""
        with patch('prism.commands.crud.PrismCore', return_value=mock_core):
            result = runner.invoke(newcli, ['crud', 'show', '1/1/1', '-j'])
            
            assert result.exit_code == 0
            assert '"name": "Test Objective"' in result.output
            assert '"type"' not in result.output  # JSON uses snake_case
    
    def test_show_not_found(self, runner, mock_core):
        """Test showing a non-existent item."""
        mock_core.navigator.get_item_by_path = Mock(return_value=None)
        
        with patch('prism.commands.crud.PrismCore', return_value=mock_core):
            result = runner.invoke(newcli, ['crud', 'show', '999'])
            
            assert result.exit_code == 1
            assert 'not found' in result.output


class TestCrudEdit:
    """Tests for crud edit command."""
    
    def test_edit_requires_path(self, runner, mock_core):
        """Test that edit requires a path (safety feature)."""
        with patch('prism.commands.crud.PrismCore', return_value=mock_core):
            result = runner.invoke(newcli, ['crud', 'edit', '-n', 'New Name'])
            
            assert result.exit_code == 1
            assert 'Path required' in result.output
    
    def test_edit_with_path(self, runner, mock_core):
        """Test editing an item by path."""
        with patch('prism.commands.crud.PrismCore', return_value=mock_core):
            result = runner.invoke(newcli, ['crud', 'edit', '1/1/1', '-n', 'New Name'])
            
            assert result.exit_code == 0
            assert 'updated successfully' in result.output
            mock_core.update_item.assert_called_once()
    
    def test_edit_with_uuid(self, runner, mock_core):
        """Test editing an item by UUID."""
        with patch('prism.commands.crud.PrismCore', return_value=mock_core):
            result = runner.invoke(newcli, ['crud', 'edit', '-u', 'objective-uuid', '-s', 'completed'])
            
            assert result.exit_code == 0
            assert 'updated successfully' in result.output
    
    def test_edit_no_changes(self, runner, mock_core):
        """Test editing without specifying changes."""
        with patch('prism.commands.crud.PrismCore', return_value=mock_core):
            result = runner.invoke(newcli, ['crud', 'edit', '1/1/1'])
            
            assert result.exit_code == 1
            assert 'No update parameters' in result.output


class TestCrudDelete:
    """Tests for crud delete command."""
    
    def test_delete_requires_path(self, runner, mock_core):
        """Test that delete requires a path (safety feature)."""
        with patch('prism.commands.crud.PrismCore', return_value=mock_core):
            # Use --yes to skip confirmation, then check path error
            result = runner.invoke(newcli, ['crud', 'delete', '--yes'])
            
            assert result.exit_code == 1
            assert 'Path required' in result.output
    
    def test_delete_with_path(self, runner, mock_core):
        """Test deleting an item by path."""
        with patch('prism.commands.crud.PrismCore', return_value=mock_core):
            # Use --yes to skip confirmation prompt
            result = runner.invoke(newcli, ['crud', 'delete', '1/1/1', '--yes'])
            
            assert result.exit_code == 0
            assert 'deleted successfully' in result.output
            mock_core.delete_item.assert_called_once()


class TestCrudAdd:
    """Tests for crud add command."""
    
    def test_add_phase(self, runner, mock_core):
        """Test adding a phase."""
        with patch('prism.commands.crud.PrismCore', return_value=mock_core):
            result = runner.invoke(newcli, ['crud', 'add', '-t', 'phase', '-n', 'New Phase'])
            
            assert result.exit_code == 0
            assert 'created successfully' in result.output
            mock_core.add_item.assert_called_once()
    
    def test_add_action_infers_parent(self, runner, mock_core):
        """Test adding an action with inferred parent."""
        with patch('prism.commands.crud.PrismCore', return_value=mock_core):
            result = runner.invoke(newcli, ['crud', 'add', '-t', 'action', '-n', 'New Action'])
            
            assert result.exit_code == 0
            assert 'created successfully' in result.output
            mock_core.add_item.assert_called_once()
    
    def test_add_requires_parent_for_milestone(self, runner, mock_core):
        """Test that milestone requires parent if no context."""
        mock_core.navigator.get_current_phase = Mock(return_value=None)
        
        with patch('prism.commands.crud.PrismCore', return_value=mock_core):
            result = runner.invoke(newcli, ['crud', 'add', '-t', 'milestone', '-n', 'New Milestone'])
            
            assert result.exit_code == 1
            assert 'Cannot add milestone without a parent' in result.output


class TestTaskCommands:
    """Tests for task commands."""
    
    def test_task_start(self, runner, mock_core):
        """Test task start command."""
        mock_action = Mock()
        mock_action.name = "Test Action"
        mock_core.task_manager.start_next_action = Mock(return_value=mock_action)
        
        with patch('prism.commands.task.PrismCore', return_value=mock_core):
            result = runner.invoke(newcli, ['task', 'start'])
            
            assert result.exit_code == 0
            assert 'Test Action' in result.output
    
    def test_task_start_no_tasks(self, runner, mock_core):
        """Test task start with no pending tasks."""
        mock_core.task_manager.start_next_action = Mock(return_value=None)
        
        with patch('prism.commands.task.PrismCore', return_value=mock_core):
            result = runner.invoke(newcli, ['task', 'start'])
            
            assert result.exit_code == 0
            assert 'No pending tasks' in result.output
    
    def test_task_done(self, runner, mock_core):
        """Test task done command."""
        mock_action = Mock()
        mock_action.name = "Test Action"
        mock_core.task_manager.complete_current_action = Mock(return_value=mock_action)
        
        with patch('prism.commands.task.PrismCore', return_value=mock_core):
            result = runner.invoke(newcli, ['task', 'done'])
            
            assert result.exit_code == 0
            assert 'Test Action' in result.output
    
    def test_task_next(self, runner, mock_core):
        """Test task next command."""
        completed = Mock()
        completed.name = "Completed Task"
        next_action = Mock()
        next_action.name = "Next Task"
        mock_core.task_manager.complete_current_and_start_next = Mock(return_value=(completed, next_action))
        
        with patch('prism.commands.task.PrismCore', return_value=mock_core):
            result = runner.invoke(newcli, ['task', 'next'])
            
            assert result.exit_code == 0
            assert 'Completed Task' in result.output
            assert 'Next Task' in result.output


class TestConfigCommands:
    """Tests for config command stubs."""
    
    def test_config_show(self, runner):
        """Test config show command (stub)."""
        result = runner.invoke(newcli, ['config', 'show'])
        
        assert result.exit_code == 0
        assert 'TODO' in result.output
    
    def test_config_set(self, runner):
        """Test config set command (stub)."""
        result = runner.invoke(newcli, ['config', 'set', 'key', 'value'])
        
        assert result.exit_code == 0
        assert 'TODO' in result.output
    
    def test_config_get(self, runner):
        """Test config get command (stub)."""
        result = runner.invoke(newcli, ['config', 'get', 'key'])
        
        assert result.exit_code == 0
        assert 'TODO' in result.output


class TestOrphanCommands:
    """Tests for orphan command stubs."""
    
    def test_orphan_list(self, runner):
        """Test orphan list command (stub)."""
        result = runner.invoke(newcli, ['orphan', 'list'])
        
        assert result.exit_code == 0
        assert 'TODO' in result.output
    
    def test_orphan_add(self, runner):
        """Test orphan add command (stub)."""
        result = runner.invoke(newcli, ['orphan', 'add', '-n', 'Test Idea'])
        
        assert result.exit_code == 0
        assert 'TODO' in result.output
    
    def test_orphan_adopt(self, runner):
        """Test orphan adopt command (stub)."""
        result = runner.invoke(newcli, ['orphan', 'adopt', '1', '-t', 'phase'])
        
        assert result.exit_code == 0
        assert 'TODO' in result.output
    
    def test_orphan_delete(self, runner):
        """Test orphan delete command (stub)."""
        result = runner.invoke(newcli, ['orphan', 'delete', '1', '--yes'])
        
        assert result.exit_code == 0
        assert 'TODO' in result.output
