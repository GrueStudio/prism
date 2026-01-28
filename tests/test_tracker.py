import pytest
from pathlib import Path
import tempfile
import json
from unittest.mock import MagicMock

from prism.tracker import Tracker
from prism.data_store import DataStore
from prism.models import (
    MAX_SLUG_SIZE,
    Action,
    BaseItem,
    Deliverable,
    Milestone,
    Objective,
    Phase,
    ProjectData,
    to_kebab_case,
)


@pytest.fixture
def mock_data_store():
    """Provides a mock DataStore that doesn't interact with files."""
    mock_store = MagicMock(spec=DataStore)
    mock_store.load_project_data.return_value = ProjectData()  # Start with empty data
    return mock_store


@pytest.fixture
def tracker(mock_data_store):
    """Provides a Tracker instance with a mock DataStore."""
    return Tracker(mock_data_store)


@pytest.fixture
def populated_tracker(tracker):
    """Provides a Tracker instance with some sample data with slugs conforming to MAX_SLUG_SIZE=10."""
    # Define names and their expected slugs
    phase_name_1 = "Main Phase"  # slug: main-phase
    milestone_name_1 = "Data Model"  # slug: data-model
    milestone_name_2 = "Data Stor"  # slug: data-stor
    objective_name_1 = "Base Item"  # slug: base-item
    deliverable_name_1 = "Slug Logic"  # slug: slug-logic
    action_name_1_1 = "Write Test"  # slug: write-test
    action_name_1_2 = "Impl Code"  # slug: impl-code

    # Add a phase
    tracker.add_item(None, "phase", phase_name_1, "The first development phase")

    # Add milestones
    tracker.add_item(
        to_kebab_case(phase_name_1),
        "milestone",
        milestone_name_1,
        "Define all Pydantic models",
    )
    tracker.add_item(
        to_kebab_case(phase_name_1),
        "milestone",
        milestone_name_2,
        "Implement JSON persistence",
    )

    # Add objective
    tracker.add_item(
        f"{to_kebab_case(phase_name_1)}.{to_kebab_case(milestone_name_1)}",
        "objective",
        objective_name_1,
        "Implement base model",
    )

    # Add deliverable
    tracker.add_item(
        f"{to_kebab_case(phase_name_1)}.{to_kebab_case(milestone_name_1)}.{to_kebab_case(objective_name_1)}",
        "deliverable",
        deliverable_name_1,
        "Add slug generation",
    )

    # Add actions
    tracker.add_item(
        f"{to_kebab_case(phase_name_1)}.{to_kebab_case(milestone_name_1)}.{to_kebab_case(objective_name_1)}.{to_kebab_case(deliverable_name_1)}",
        "action",
        action_name_1_1,
        "Write slug tests",
    )
    tracker.add_item(
        f"{to_kebab_case(phase_name_1)}.{to_kebab_case(milestone_name_1)}.{to_kebab_case(objective_name_1)}.{to_kebab_case(deliverable_name_1)}",
        "action",
        action_name_1_2,
        "Implement slug code",
    )

    # Set status for one action for specific test cases if needed later
    # tracker.project_data.phases[0].milestones[0].objectives[0].deliverables[0].actions[0].status = "completed"

    tracker.data_store.save_project_data.reset_mock()  # Clear save calls from setup
    return tracker


def test_tracker_initialization(mock_data_store):
    """Test that Tracker initializes correctly and loads project data."""
    tracker = Tracker(mock_data_store)
    mock_data_store.load_project_data.assert_called_once()
    assert isinstance(tracker.project_data, ProjectData)


def test_save_project_data_calls_data_store(tracker, mock_data_store):
    """Test that _save_project_data calls the data store's save method."""
    tracker._save_project_data()
    mock_data_store.save_project_data.assert_called_once_with(tracker.project_data)


def test_get_item_type_from_str(tracker):
    """Test _get_item_type_from_str utility."""
    assert tracker._get_item_type_from_str("phase") == Phase
    assert tracker._get_item_type_from_str("Milestone") == Milestone
    assert tracker._get_item_type_from_str("ACTION") == Action
    with pytest.raises(ValueError, match="Unknown item type"):
        tracker._get_item_type_from_str("unknown")


def test_generate_unique_slug_no_conflict(tracker):
    """Test slug generation when no conflict exists."""
    item_list = [Phase(name="Existing Phase", slug="exist-phas")]
    slug = tracker._generate_unique_slug(item_list, "New Phase")
    assert slug == "new-phase"


def test_generate_unique_slug_with_conflict(tracker):
    """Test slug generation when a conflict exists, should append number."""
    item_list = []
    
    # First unique slug for "Existing Phase"
    slug_initial = tracker._generate_unique_slug(item_list, "Existing Phase")
    assert slug_initial == "existing-p"
    item_list.append(Phase(name="Existing Phase Original", slug=slug_initial)) # Add the generated one
    
    # Now try to generate a slug that conflicts
    slug1 = tracker._generate_unique_slug(item_list, "Existing Phase")
    assert slug1 == "existing-1" # Corrected expectation
    
    item_list.append(Phase(name="Another Existing Phase", slug=slug1))
    slug2 = tracker._generate_unique_slug(item_list, "Existing Phase")
    assert slug2 == "existing-2" # Corrected expectation


def test_generate_unique_slug_with_long_name_and_conflict(tracker):
    """Test slug generation with truncation and conflict."""
    long_name = "Very Very Long Phase Name"
    item_list = [Phase(name=long_name, slug=to_kebab_case(long_name))]
    assert (
        item_list[0].slug == "very-very"
    )  # Corrected truncated slug, no trailing hyphen

    slug = tracker._generate_unique_slug(item_list, long_name)
    assert slug == "very-ver-1"  # truncated base slug + suffix


def test_generate_unique_slug_from_invalid_name_raises_error(tracker):
    """Test that generating a slug from an invalid name raises an error."""
    with pytest.raises(
        ValueError, match="Cannot generate a slug from an empty or invalid base name."
    ):
        tracker._generate_unique_slug([], "!@#")
    with pytest.raises(
        ValueError, match="Cannot generate a slug from an empty or invalid base name."
    ):
        tracker._generate_unique_slug([], "")


def test_resolve_path_segment_by_slug(tracker):
    """Test resolving a segment by slug."""
    phase = Phase(name="Test Phase")
    milestone = Milestone(name="Test Milestone")
    items = [phase, milestone]
    assert tracker._resolve_path_segment(items, "test-phase") == phase
    assert tracker._resolve_path_segment(items, "test-miles") == milestone


def test_resolve_path_segment_by_index(tracker):
    """Test resolving a segment by 1-based index."""
    phase = Phase(name="Test Phase")
    milestone = Milestone(name="Test Milestone")
    items = [phase, milestone]
    assert tracker._resolve_path_segment(items, "1") == phase
    assert tracker._resolve_path_segment(items, "2") == milestone


def test_resolve_path_segment_not_found(tracker):
    """Test resolving a segment that does not exist."""
    phase = Phase(name="Test Phase")
    items = [phase]
    assert tracker._resolve_path_segment(items, "non-exist") is None
    assert tracker._resolve_path_segment(items, "2") is None  # Index out of bounds
    assert (
        tracker._resolve_path_segment(items, "0") is None
    )  # 0 is not a valid 1-based index


def test_get_item_by_path_phase(populated_tracker):
    """Test retrieving a top-level phase by slug."""
    phase = populated_tracker.get_item_by_path("main-phase")
    assert phase is not None
    assert phase.name == "Main Phase"
    assert isinstance(phase, Phase)


def test_get_item_by_path_milestone(populated_tracker):
    """Test retrieving a milestone by full path."""
    milestone = populated_tracker.get_item_by_path("main-phase.data-model")
    assert milestone is not None
    assert milestone.name == "Data Model"
    assert isinstance(milestone, Milestone)


def test_get_item_by_path_objective(populated_tracker):
    """Test retrieving an objective by full path."""
    objective = populated_tracker.get_item_by_path("main-phase.data-model.base-item")
    assert objective is not None
    assert objective.name == "Base Item"
    assert isinstance(objective, Objective)


def test_get_item_by_path_deliverable(populated_tracker):
    """Test retrieving a deliverable by full path."""
    deliverable = populated_tracker.get_item_by_path(
        "main-phase.data-model.base-item.slug-logic"
    )
    assert deliverable is not None
    assert deliverable.name == "Slug Logic"
    assert isinstance(deliverable, Deliverable)


def test_get_item_by_path_action(populated_tracker):
    """Test retrieving an action by full path."""
    action = populated_tracker.get_item_by_path(
        "main-phase.data-model.base-item.slug-logic.write-test"
    )
    assert action is not None
    assert action.name == "Write Test"
    assert isinstance(action, Action)


def test_get_item_by_path_with_index(populated_tracker):
    """Test retrieving items using index in path."""
    # Assuming "Main Phase" is the first phase, "Data Model" is first milestone
    milestone = populated_tracker.get_item_by_path("1.1")
    assert milestone is not None
    assert milestone.name == "Data Model"

    # 1st phase, 1st milestone, 1st objective, 1st deliverable, 2nd action
    action = populated_tracker.get_item_by_path(
        f"{to_kebab_case('Main Phase')}.{to_kebab_case('Data Model')}.{to_kebab_case('Base Item')}.{to_kebab_case('Slug Logic')}.2"
    )
    assert action is not None
    assert action.name == "Impl Code"


def test_get_item_by_path_not_found(populated_tracker):
    """Test retrieving a non-existent item by path."""
    assert populated_tracker.get_item_by_path("non-existent-phase") is None
    assert (
        populated_tracker.get_item_by_path("main-phase.non-existent-milestone") is None
    )
    assert (
        populated_tracker.get_item_by_path(
            "main-phase.data-model.non-existent-objective"
        )
        is None
    )
    assert (
        populated_tracker.get_item_by_path(
            "main-phase.data-model.base-item.non-existent-deliverable"
        )
        is None
    )
    assert (
        populated_tracker.get_item_by_path(
            "main-phase.data-model.base-item.slug-logic.non-existent-action"
        )
        is None
    )
    assert populated_tracker.get_item_by_path("main-phase.999") is None  # Invalid index


def test_add_phase(tracker, mock_data_store):
    """Test adding a new phase."""
    new_phase = tracker.add_item(None, "phase", "New Phase", "A brand new phase")
    assert isinstance(new_phase, Phase)
    assert new_phase.name == "New Phase"
    assert new_phase.slug == "new-phase"
    assert len(tracker.project_data.phases) == 1
    assert tracker.project_data.phases[0] == new_phase
    mock_data_store.save_project_data.assert_called_once()
    assert new_phase.current is True  # Should be current if first phase


def test_add_second_phase_not_current(tracker, mock_data_store):
    """Test adding a second phase, which should not be current."""
    tracker.add_item(None, "phase", "First Phase")
    mock_data_store.save_project_data.reset_mock()
    second_phase = tracker.add_item(None, "phase", "Second Phase")
    assert second_phase.current is False
    assert len(tracker.project_data.phases) == 2
    mock_data_store.save_project_data.assert_called_once()


def test_add_milestone(populated_tracker, mock_data_store):
    """Test adding a milestone to an existing phase."""
    mock_data_store.save_project_data.reset_mock()
    milestone = populated_tracker.add_item("main-phase", "milestone", "New Milestone")
    assert isinstance(milestone, Milestone)
    assert milestone.name == "New Milestone"
    assert milestone.slug == "new-milest"
    phase_main = populated_tracker.get_item_by_path("main-phase")
    assert len(phase_main.milestones) == 3  # Existing 2 + new 1
    assert phase_main.milestones[2] == milestone
    mock_data_store.save_project_data.assert_called_once()


def test_add_objective(populated_tracker, mock_data_store):
    """Test adding an objective to an existing milestone."""
    mock_data_store.save_project_data.reset_mock()
    objective = populated_tracker.add_item(
        "main-phase.data-model", "objective", "New Objective"
    )
    assert isinstance(objective, Objective)
    assert objective.name == "New Objective"
    milestone_dm = populated_tracker.get_item_by_path("main-phase.data-model")
    assert len(milestone_dm.objectives) == 2
    mock_data_store.save_project_data.assert_called_once()


def test_add_deliverable(populated_tracker, mock_data_store):
    """Test adding a deliverable to an existing objective."""
    mock_data_store.save_project_data.reset_mock()
    deliverable = populated_tracker.add_item(
        "main-phase.data-model.base-item", "deliverable", "New Deliverable"
    )
    assert isinstance(deliverable, Deliverable)
    assert deliverable.name == "New Deliverable"
    objective_bi = populated_tracker.get_item_by_path("main-phase.data-model.base-item")
    assert len(objective_bi.deliverables) == 2
    mock_data_store.save_project_data.assert_called_once()


def test_add_action(populated_tracker, mock_data_store):
    """Test adding an action to an existing deliverable."""
    mock_data_store.save_project_data.reset_mock()
    action = populated_tracker.add_item(
        "main-phase.data-model.base-item.slug-logic", "action", "New Action"
    )
    assert isinstance(action, Action)
    assert action.name == "New Action"
    deliverable_sl = populated_tracker.get_item_by_path(
        "main-phase.data-model.base-item.slug-logic"
    )
    assert len(deliverable_sl.actions) == 3
    mock_data_store.save_project_data.assert_called_once()


def test_add_item_invalid_item_type_raises_error(tracker):
    """Test adding an item with an invalid type."""
    with pytest.raises(ValueError, match="Unknown item type: invalid"):
        tracker.add_item(None, "invalid", "Some Name")


def test_add_item_no_parent_path_for_non_phase_raises_error(tracker):
    """Test adding a non-phase item without a parent path."""
    with pytest.raises(ValueError, match="Parent path is required for milestones."):
        tracker.add_item(None, "milestone", "Some Milestone")


def test_add_item_non_existent_parent_raises_error(tracker):
    """Test adding an item to a non-existent parent."""
    tracker.add_item(None, "phase", "Parent Phase")
    with pytest.raises(
        ValueError, match="Parent item at path 'non-existent' not found."
    ):
        tracker.add_item("non-existent", "milestone", "Some Milestone")


def test_add_item_wrong_parent_type_raises_error(populated_tracker):
    """Test adding an item to a parent of the wrong type."""
    with pytest.raises(
        ValueError, match="Cannot add milestone to parent type Deliverable."
    ):
        populated_tracker.add_item(
            "main-phase.data-model.base-item.slug-logic", "milestone", "Some Milestone"
        )

    with pytest.raises(ValueError, match="Phases cannot have parent items. They are top-level items."): # Corrected regex
        populated_tracker.add_item(
            "main-phase", "phase", "Another Phase"
        )  # Cannot add phase to phase


# New tests for traversal functionality


def test_set_current_item_valid_path(populated_tracker):
    """Test setting current item with a valid path."""
    path = "main-phase.data-model.base-item.slug-logic"
    populated_tracker.set_current_item(path)
    assert populated_tracker.current_item is not None
    assert populated_tracker.current_item.name == "Slug Logic"
    assert populated_tracker.current_item_path == path


def test_set_current_item_non_existent_path_raises_error(populated_tracker):
    """Test setting current item with a non-existent path."""
    with pytest.raises(ValueError, match="No item found at path: non-existent-path"):
        populated_tracker.set_current_item("non-existent-path")
    assert populated_tracker.current_item is None
    assert populated_tracker.current_item_path is None


def test_set_current_item_empty_path_raises_error(populated_tracker):
    """Test setting current item with an empty path."""
    with pytest.raises(ValueError, match="No item found at path: "):
        populated_tracker.set_current_item("")
    assert populated_tracker.current_item is None
    assert populated_tracker.current_item_path is None


def test_next_item_from_beginning_of_tree(populated_tracker):
    """Test next_item starting from no current item (should go to first phase)."""
    populated_tracker.current_item = None
    populated_tracker.current_item_path = None
    next_item = populated_tracker.next_item()
    assert next_item is not None
    assert next_item.name == "Main Phase"
    assert populated_tracker.current_item_path == "main-phase"


def test_next_item_traversal_children_and_siblings(populated_tracker):
    """Test next_item for depth-first traversal through children and siblings."""
    # Start at 'Main Phase'
    populated_tracker.set_current_item("main-phase")
    assert populated_tracker.current_item.name == "Main Phase"

    # Next should be 'Data Model' (first child of Main Phase)
    next_item = populated_tracker.next_item()
    assert next_item.name == "Data Model"
    assert populated_tracker.current_item_path == "main-phase.data-model"

    # Next should be 'Base Item' (first child of Data Model)
    next_item = populated_tracker.next_item()
    assert next_item.name == "Base Item"
    assert populated_tracker.current_item_path == "main-phase.data-model.base-item"

    # Next should be 'Slug Logic' (first child of Base Item)
    next_item = populated_tracker.next_item()
    assert next_item.name == "Slug Logic"
    assert (
        populated_tracker.current_item_path
        == "main-phase.data-model.base-item.slug-logic"
    )

    # Next should be 'Write Test' (first child of Slug Logic)
    next_item = populated_tracker.next_item()
    assert next_item.name == "Write Test"
    assert (
        populated_tracker.current_item_path
        == "main-phase.data-model.base-item.slug-logic.write-test"
    )

    # Next should be 'Impl Code' (second child/sibling of Write Test)
    next_item = populated_tracker.next_item()
    assert next_item.name == "Impl Code"
    assert (
        populated_tracker.current_item_path
        == "main-phase.data-model.base-item.slug-logic.impl-code"
    )

    # Next should be 'Data Stor' (sibling of Data Model, no more children in Impl Code, no more siblings in Slug Logic, no more siblings in Base Item)
    next_item = populated_tracker.next_item()
    assert next_item.name == "Data Stor"
    assert populated_tracker.current_item_path == "main-phase.data-stor"

    # After Data Stor, there are no more items, so next_item should be None
    next_item = populated_tracker.next_item()
    assert next_item is None
    assert populated_tracker.current_item is None
    assert populated_tracker.current_item_path is None


def test_next_item_empty_project_data(tracker):
    """Test next_item with empty project data."""
    tracker.current_item = None
    tracker.current_item_path = None
    next_item = tracker.next_item()
    assert next_item is None
    assert tracker.current_item is None
    assert tracker.current_item_path is None


def test_previous_item_from_end_of_tree(populated_tracker):
    """Test previous_item starting from the last item."""
    # Set current item to the last item ('Impl Code')
    populated_tracker.set_current_item(
        "main-phase.data-model.base-item.slug-logic.impl-code"
    )
    assert populated_tracker.current_item.name == "Impl Code"

    # Previous should be 'Write Test' (sibling)
    previous_item = populated_tracker.previous_item()
    assert previous_item.name == "Write Test"
    assert (
        populated_tracker.current_item_path
        == "main-phase.data-model.base-item.slug-logic.write-test"
    )

    # Previous should be 'Slug Logic' (parent)
    previous_item = populated_tracker.previous_item()
    assert previous_item.name == "Slug Logic"
    assert (
        populated_tracker.current_item_path
        == "main-phase.data-model.base-item.slug-logic"
    )

    # Previous should be 'Base Item' (parent)
    previous_item = populated_tracker.previous_item()
    assert previous_item.name == "Base Item"
    assert populated_tracker.current_item_path == "main-phase.data-model.base-item"

    # Previous should be 'Data Model' (parent)
    previous_item = populated_tracker.previous_item()
    assert previous_item.name == "Data Model"
    assert populated_tracker.current_item_path == "main-phase.data-model"

    # Previous should be 'Main Phase' (parent)
    previous_item = populated_tracker.previous_item()
    assert previous_item.name == "Main Phase"
    assert populated_tracker.current_item_path == "main-phase"

    # After Main Phase, there are no more items, so previous_item should be None
    previous_item = populated_tracker.previous_item()
    assert previous_item is None
    assert populated_tracker.current_item is None
    assert populated_tracker.current_item_path is None


def test_previous_item_empty_project_data(tracker):
    """Test previous_item with empty project data."""
    tracker.current_item = None
    tracker.current_item_path = None
    previous_item = tracker.previous_item()
    assert previous_item is None
    assert tracker.current_item is None
    assert tracker.current_item_path is None


def test_previous_item_from_middle_of_tree(populated_tracker):
    """Test previous_item starting from a middle item."""
    # Set current item to 'Data Stor'
    populated_tracker.set_current_item("main-phase.data-stor")
    assert populated_tracker.current_item.name == "Data Stor"

    # Previous should be 'Impl Code' (deepest descendant of previous sibling 'Data Model')
    previous_item = populated_tracker.previous_item()
    assert previous_item.name == "Impl Code"
    assert (
        populated_tracker.current_item_path
        == "main-phase.data-model.base-item.slug-logic.impl-code"
    )
