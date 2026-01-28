import pytest
from pathlib import Path
import tempfile
import json

# Import ValidationError from pydantic_core
from pydantic_core import ValidationError

from prism.data_store import DataStore
from prism.models import ProjectData, Phase, Milestone, Objective, Deliverable, Action

@pytest.fixture
def temp_json_file():
    """Provides a temporary JSON file path for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test_project_data.json"
        yield file_path

@pytest.fixture
def sample_project_data():
    """Provides a sample ProjectData object."""
    action = Action(name="Code Action", description="Write code")
    deliverable = Deliverable(name="Code Deliverable", actions=[action])
    objective = Objective(name="Build Core", deliverables=[deliverable])
    milestone = Milestone(name="Phase Alpha", objectives=[objective])
    phase = Phase(name="Pre-Alpha", current=True, milestones=[milestone])
    return ProjectData(phases=[phase])

def test_load_non_existent_file_initializes_empty_project_data(temp_json_file):
    """Test that loading a non-existent file returns an empty ProjectData."""
    data_store = DataStore(temp_json_file)
    project_data = data_store.load_project_data()
    assert isinstance(project_data, ProjectData)
    assert len(project_data.phases) == 0

def test_save_and_load_project_data(temp_json_file, sample_project_data):
    """Test saving and then loading a ProjectData object."""
    data_store = DataStore(temp_json_file)
    data_store.save_project_data(sample_project_data)

    # Verify file content directly
    with open(temp_json_file, 'r') as f:
        content = json.load(f)
    assert len(content['phases']) == 1
    assert content['phases'][0]['name'] == "Pre-Alpha"

    # Load and verify object integrity
    loaded_data = data_store.load_project_data()
    assert loaded_data == sample_project_data

def test_load_corrupt_json_file_raises_error(temp_json_file):
    """Test that loading a corrupt JSON file raises an error."""
    temp_json_file.write_text("this is not json")
    data_store = DataStore(temp_json_file)
    with pytest.raises(ValidationError): # Changed expected exception
        data_store.load_project_data()

def test_default_file_location_logic():
    """
    Test logic for default file location.
    This test will be more conceptual until the default location logic is implemented in DataStore.
    For now, it just asserts the DataStore can be instantiated without an explicit path.
    """
    data_store = DataStore()
    assert isinstance(data_store, DataStore) # placeholder assertion