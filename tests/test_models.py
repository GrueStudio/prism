import pytest
from datetime import datetime, date, timedelta
import uuid

from pydantic_core import ValidationError

from prism.models import BaseItem, Action, Deliverable, Objective, Milestone, Phase, ProjectData, to_kebab_case, MAX_SLUG_SIZE

def _assert_slug_matches_generated(item_name: str, actual_slug: str):
    """Helper to assert that a generated slug matches the expected format and length."""
    expected_generated_slug = to_kebab_case(item_name)
    assert actual_slug == expected_generated_slug

def test_to_kebab_case():
    assert to_kebab_case("My New Item") == "my-new-ite"
    assert to_kebab_case("AnotherOne") == "anotherone" # Corrected expected value
    assert to_kebab_case("long name that should be truncated") == "long-name"
    assert to_kebab_case("short") == "short"
    assert to_kebab_case("CAMELCaseName") == "camelcasen"
    assert to_kebab_case("already-kebab") == "already-ke"
    assert to_kebab_case("SpecialChars!@#") == "specialcha"

def test_base_item_slug_generation_from_name():
    item_name_1 = "Test Item"
    item = BaseItem(name=item_name_1, slug="test-item")
    _assert_slug_matches_generated(item_name_1, item.slug)

    item_name_2 = "Another Test"
    item_gen_slug = BaseItem(name=item_name_2)
    _assert_slug_matches_generated(item_name_2, item_gen_slug.slug)

    item_name_3 = "A very very very very long name for an item"
    long_name_item = BaseItem(name=item_name_3)
    _assert_slug_matches_generated(item_name_3, long_name_item.slug)


def test_base_item_slug_validation():
    # Valid explicit slug
    item = BaseItem(name="Name", slug="valid-slug")
    assert item.slug == "valid-slug"

    # Slug too long
    with pytest.raises(ValidationError) as exc_info:
        BaseItem(name="Name", slug="too-long-slug")
    assert f'Slug "too-long-slug" must be {MAX_SLUG_SIZE} characters or less.' in str(exc_info.value)

    # Slug not kebab-case
    with pytest.raises(ValidationError) as exc_info:
        BaseItem(name="Name", slug="Invalid Slug")
    assert 'Slug "Invalid Slug" must be in kebab-case' in str(exc_info.value)

    # Test case for when generated slug is empty (e.g., from an empty name)
    with pytest.raises(ValidationError) as exc_info:
        BaseItem(name="!@#", slug=None)
    assert "Generated slug from name is empty." in str(exc_info.value)


def test_base_item_default_values():
    item_name = "Default Test"
    item = BaseItem(name=item_name)
    assert isinstance(item.id, uuid.UUID)
    assert item.status == "pending"
    assert isinstance(item.created_at, datetime)
    assert isinstance(item.updated_at, datetime)
    assert item.description is None
    _assert_slug_matches_generated(item_name, item.slug)

def test_action_model():
    action_name_1 = "My Action"
    action = Action(name=action_name_1)
    assert action.name == action_name_1
    assert action.time_spent == timedelta(0)
    assert action.due_date is None
    _assert_slug_matches_generated(action_name_1, action.slug)

    action_name_2 = "Due Action"
    specific_date = date(2023, 12, 31)
    action_with_details = Action(name=action_name_2, due_date=specific_date, time_spent=timedelta(hours=2))
    assert action_with_details.due_date == specific_date
    assert action_with_details.time_spent == timedelta(hours=2)
    _assert_slug_matches_generated(action_name_2, action_with_details.slug)

def test_deliverable_model():
    action1 = Action(name="Action 1")
    deliverable_name = "My Deliverable"
    deliverable = Deliverable(name=deliverable_name, actions=[action1])
    assert deliverable.name == deliverable_name
    _assert_slug_matches_generated(deliverable_name, deliverable.slug)
    assert len(deliverable.actions) == 1
    assert deliverable.actions[0].name == "Action 1"

def test_objective_model():
    deliverable1 = Deliverable(name="Deliverable 1")
    objective_name = "My Objective"
    objective = Objective(name=objective_name, deliverables=[deliverable1])
    assert objective.name == objective_name
    _assert_slug_matches_generated(objective_name, objective.slug)
    assert len(objective.deliverables) == 1

def test_milestone_model():
    objective1 = Objective(name="Objective 1")
    milestone_name = "My Milestone"
    milestone = Milestone(name=milestone_name, objectives=[objective1])
    assert milestone.name == milestone_name
    _assert_slug_matches_generated(milestone_name, milestone.slug)
    assert len(milestone.objectives) == 1

def test_phase_model():
    milestone1 = Milestone(name="Milestone 1")
    phase_name = "My Phase"
    phase = Phase(name=phase_name, milestones=[milestone1], current=True)
    assert phase.name == phase_name
    _assert_slug_matches_generated(phase_name, phase.slug)
    assert phase.current is True
    assert len(phase.milestones) == 1

def test_project_data_model():
    phase_name = "Phase 1"
    phase1 = Phase(name=phase_name)
    project_data = ProjectData(phases=[phase1])
    assert len(project_data.phases) == 1
    assert project_data.phases[0].name == phase_name
    _assert_slug_matches_generated(phase_name, project_data.phases[0].slug)

    # Test with no phases
    empty_project = ProjectData()
    assert len(empty_project.phases) == 0