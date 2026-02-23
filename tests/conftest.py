"""
Test fixtures for the Prism CLI test suite.

Provides:
- Temporary directory fixtures (isolated from project .prism/)
- Mock data builders for creating test items
- Helper functions for common test operations
"""

import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Generator, Optional

import pytest

from prism.models.base import (
    Action,
    Deliverable,
    Milestone,
    Objective,
    Phase,
)
from prism.models.files import (
    ConfigFile,
    CursorFile,
    ExecutionFile,
    StrategicFile,
)
from prism.models.project import Project


# =============================================================================
# Temporary Directory Fixtures
# =============================================================================


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test isolation.
    
    Ensures tests don't modify the project's actual .prism/ directory.
    """
    temp_path = Path(tempfile.mkdtemp(prefix="prism_test_"))
    yield temp_path
    # Cleanup
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def prism_dir(temp_dir: Path) -> Generator[Path, None, None]:
    """Create a temporary .prism/ directory structure.
    
    Returns the path to the .prism/ directory.
    """
    prism_path = temp_dir / ".prism"
    prism_path.mkdir(parents=True)
    (prism_path / "archive").mkdir()
    yield prism_path


@pytest.fixture
def empty_prism_dir(temp_dir: Path) -> Generator[Path, None, None]:
    """Create an empty .prism/ directory (no files)."""
    prism_path = temp_dir / ".prism"
    prism_path.mkdir(parents=True)
    (prism_path / "archive").mkdir()
    yield prism_path


# =============================================================================
# Mock Data Builders
# =============================================================================


class MockDataBuilder:
    """Helper class for building mock Prism items for testing."""

    @staticmethod
    def create_phase(
        name: str = "Test Phase",
        description: str = "Test description",
        slug: str = "test-phase",
        status: str = "pending",
        uuid: Optional[str] = None,
    ) -> Phase:
        """Create a mock Phase for testing."""
        phase = Phase(name=name, description=description, slug=slug)
        phase.status = status
        if uuid:
            phase.uuid = uuid
        return phase

    @staticmethod
    def create_milestone(
        name: str = "Test Milestone",
        description: str = "Test description",
        slug: str = "test-milestone",
        status: str = "pending",
        parent_uuid: Optional[str] = None,
        uuid: Optional[str] = None,
    ) -> Milestone:
        """Create a mock Milestone for testing."""
        milestone = Milestone(name=name, description=description, slug=slug)
        milestone.status = status
        if parent_uuid:
            milestone.parent_uuid = parent_uuid
        if uuid:
            milestone.uuid = uuid
        return milestone

    @staticmethod
    def create_objective(
        name: str = "Test Objective",
        description: str = "Test description",
        slug: str = "test-objective",
        status: str = "pending",
        parent_uuid: Optional[str] = None,
        uuid: Optional[str] = None,
    ) -> Objective:
        """Create a mock Objective for testing."""
        objective = Objective(name=name, description=description, slug=slug)
        objective.status = status
        if parent_uuid:
            objective.parent_uuid = parent_uuid
        if uuid:
            objective.uuid = uuid
        return objective

    @staticmethod
    def create_deliverable(
        name: str = "Test Deliverable",
        description: str = "Test description",
        slug: str = "test-deliverable",
        status: str = "pending",
        parent_uuid: Optional[str] = None,
        uuid: Optional[str] = None,
        due_date: Optional[datetime] = None,
    ) -> Deliverable:
        """Create a mock Deliverable for testing."""
        deliverable = Deliverable(name=name, description=description, slug=slug)
        deliverable.status = status
        if parent_uuid:
            deliverable.parent_uuid = parent_uuid
        if uuid:
            deliverable.uuid = uuid
        if due_date:
            deliverable.due_date = due_date
        return deliverable

    @staticmethod
    def create_action(
        name: str = "Test Action",
        description: str = "Test description",
        slug: str = "test-action",
        status: str = "pending",
        parent_uuid: Optional[str] = None,
        uuid: Optional[str] = None,
        due_date: Optional[datetime] = None,
    ) -> Action:
        """Create a mock Action for testing."""
        action = Action(name=name, description=description, slug=slug)
        action.status = status
        if parent_uuid:
            action.parent_uuid = parent_uuid
        if uuid:
            action.uuid = uuid
        if due_date:
            action.due_date = due_date
        return action


@pytest.fixture
def mock_data() -> MockDataBuilder:
    """Provide mock data builder for test item creation."""
    return MockDataBuilder()


# =============================================================================
# Project Structure Fixtures
# =============================================================================


@pytest.fixture
def sample_project(mock_data: MockDataBuilder) -> Project:
    """Create a sample project with a full hierarchy for testing.

    Structure:
        Phase 1
        └── Milestone 1
            └── Objective 1
                ├── Deliverable 1
                │   ├── Action 1
                │   └── Action 2
                └── Deliverable 2
                    └── Action 3
    """
    project = Project([])

    # Create phase
    phase = mock_data.create_phase(
        name="Phase 1", slug="phase-1", uuid="phase-1-uuid"
    )
    project.add_child(phase)

    # Create milestone
    milestone = mock_data.create_milestone(
        name="Milestone 1",
        slug="milestone-1",
        parent_uuid=phase.uuid,
        uuid="milestone-1-uuid",
    )
    project.place_item(milestone)

    # Create objective
    objective = mock_data.create_objective(
        name="Objective 1",
        slug="objective-1",
        parent_uuid=milestone.uuid,
        uuid="objective-1-uuid",
    )
    project.place_item(objective)

    # Create deliverables
    deliv1 = mock_data.create_deliverable(
        name="Deliverable 1",
        slug="deliverable-1",
        parent_uuid=objective.uuid,
        uuid="deliverable-1-uuid",
    )
    deliv2 = mock_data.create_deliverable(
        name="Deliverable 2",
        slug="deliverable-2",
        parent_uuid=objective.uuid,
        uuid="deliverable-2-uuid",
    )
    project.place_item(deliv1)
    project.place_item(deliv2)

    # Create actions
    action1 = mock_data.create_action(
        name="Action 1",
        slug="action-1",
        parent_uuid=deliv1.uuid,
        uuid="action-1-uuid",
    )
    action2 = mock_data.create_action(
        name="Action 2",
        slug="action-2",
        parent_uuid=deliv1.uuid,
        uuid="action-2-uuid",
    )
    action3 = mock_data.create_action(
        name="Action 3",
        slug="action-3",
        parent_uuid=deliv2.uuid,
        uuid="action-3-uuid",
    )
    project.place_item(action1)
    project.place_item(action2)
    project.place_item(action3)

    return project


@pytest.fixture
def empty_project() -> Project:
    """Create an empty project with no items."""
    return Project([])


# =============================================================================
# File Model Fixtures
# =============================================================================


@pytest.fixture
def strategic_file(sample_project: Project) -> StrategicFile:
    """Create a StrategicFile from sample project."""
    phase = sample_project.phases[0]
    milestone = phase.children[0]
    objective = milestone.children[0]
    
    return StrategicFile(
        phase=phase,
        milestone=milestone,
        objective=objective,
        phase_uuids=sample_project.child_uuids,
    )


@pytest.fixture
def execution_file(sample_project: Project) -> ExecutionFile:
    """Create an ExecutionFile from sample project."""
    phase = sample_project.phases[0]
    milestone = phase.children[0]
    objective = milestone.children[0]
    
    deliverables = []
    actions = []
    
    for deliv in objective.children:
        deliverables.append(deliv)
        for action in deliv.children:
            actions.append(action)
    
    return ExecutionFile(deliverables=deliverables, actions=actions)


@pytest.fixture
def cursor_file() -> CursorFile:
    """Create a default CursorFile."""
    return CursorFile(task_cursor=None, crud_context=None)


@pytest.fixture
def config_file() -> ConfigFile:
    """Create a default ConfigFile."""
    return ConfigFile()


# =============================================================================
# Helper Functions
# =============================================================================


def count_items(project: Project) -> dict:
    """Count items by type in a project.
    
    Returns:
        Dict with counts for each item type.
    """
    counts = {
        "Phase": 0,
        "Milestone": 0,
        "Objective": 0,
        "Deliverable": 0,
        "Action": 0,
    }
    
    def traverse(items):
        for item in items:
            item_type = type(item).__name__
            if item_type in counts:
                counts[item_type] += 1
            if hasattr(item, "children") and item.children:
                traverse(item.children)
    
    traverse(project.phases)
    return counts


def get_item_by_slug(project: Project, slug: str):
    """Find an item by its slug in the project tree.
    
    Returns:
        The item if found, None otherwise.
    """
    def traverse(items):
        for item in items:
            if hasattr(item, "slug") and item.slug == slug:
                return item
            if hasattr(item, "children") and item.children:
                result = traverse(item.children)
                if result:
                    return result
        return None
    
    return traverse(project.phases)


def build_path(project: Project, slugs: list) -> str:
    """Build a path string from a list of slugs.
    
    Args:
        project: Project to search in.
        slugs: List of slugs forming the path.
    
    Returns:
        Path string (e.g., "phase-1/milestone-1/objective-1").
    """
    return "/".join(slugs)


@pytest.fixture
def helpers():
    """Provide helper functions for tests."""
    return {
        "count_items": count_items,
        "get_item_by_slug": get_item_by_slug,
        "build_path": build_path,
    }
