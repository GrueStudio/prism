import json
import tempfile
from pathlib import Path

import pytest

from prism.data_store_old import DataStore
from prism.models_old import ProjectData


def test_data_store_initialization():
    """Test that DataStore initializes with correct file path."""
    # Test default initialization
    data_store = DataStore()
    assert data_store.project_file == Path("project.json")
    
    # Test custom file path
    custom_path = Path("/tmp/test_project.json")
    data_store_custom = DataStore(custom_path)
    assert data_store_custom.project_file == custom_path


def test_load_project_data_empty_file():
    """Test loading from a non-existent file returns empty ProjectData."""
    with tempfile.NamedTemporaryFile(delete=True) as tmp:
        # Remove the temp file so it doesn't exist
        Path(tmp.name).unlink()
        
        data_store = DataStore(Path(tmp.name))
        project_data = data_store.load_project_data()
        
        assert isinstance(project_data, ProjectData)
        assert len(project_data.phases) == 0
        assert project_data.cursor is None


def test_load_project_data_existing_file():
    """Test loading from an existing file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
        # Create a sample project data
        sample_data = {
            "phases": [
                {
                    "name": "Test Phase",
                    "description": "A test phase",
                    "slug": "test-phase",
                    "status": "pending",
                    "created_at": "2023-01-01T00:00:00",
                    "updated_at": "2023-01-01T00:00:00",
                    "milestones": []
                }
            ],
            "cursor": None
        }
        json.dump(sample_data, tmp)
        tmp.flush()
        
        data_store = DataStore(Path(tmp.name))
        project_data = data_store.load_project_data()
        
        assert isinstance(project_data, ProjectData)
        assert len(project_data.phases) == 1
        assert project_data.phases[0].name == "Test Phase"
        
        # Clean up
        Path(tmp.name).unlink()


def test_save_project_data():
    """Test saving project data to file."""
    with tempfile.NamedTemporaryFile(delete=True) as tmp:
        # Remove the temp file so we can test creating a new one
        Path(tmp.name).unlink()
        
        # Create some project data
        project_data = ProjectData()
        project_data.phases = []
        project_data.cursor = "test/path"
        
        data_store = DataStore(Path(tmp.name))
        data_store.save_project_data(project_data)
        
        # Verify the file was created and contains the data
        assert Path(tmp.name).exists()
        
        with open(tmp.name, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data["cursor"] == "test/path"
        assert saved_data["phases"] == []


def test_atomic_write():
    """Test that save_project_data performs atomic writes."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_file = Path(tmp_dir) / "project.json"
        
        # Create some project data
        project_data = ProjectData()
        project_data.cursor = "initial/path"
        
        data_store = DataStore(project_file)
        data_store.save_project_data(project_data)
        
        # Verify initial state
        with open(project_file, 'r') as f:
            content = json.load(f)
        assert content["cursor"] == "initial/path"
        
        # Update and save again
        project_data.cursor = "updated/path"
        data_store.save_project_data(project_data)
        
        # Verify updated state
        with open(project_file, 'r') as f:
            content = json.load(f)
        assert content["cursor"] == "updated/path"


def test_load_project_data_invalid_json():
    """Test loading from a file with invalid JSON raises exception."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
        tmp.write("{invalid json}")
        tmp.flush()
        
        data_store = DataStore(Path(tmp.name))
        
        with pytest.raises(Exception, match="Error loading project data"):
            data_store.load_project_data()
        
        # Clean up
        Path(tmp.name).unlink()


def test_save_project_data_exception_handling():
    """Test that save_project_data handles exceptions properly."""
    # Use a read-only directory to trigger an exception
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Make the directory read-only temporarily
        import os
        os.chmod(tmp_dir, 0o444)  # Read-only
        
        project_file = Path(tmp_dir) / "project.json"
        project_data = ProjectData()
        
        data_store = DataStore(project_file)
        
        # This should raise an exception, but not leave temp files behind
        with pytest.raises(Exception):
            data_store.save_project_data(project_data)
        
        # Restore write permissions so cleanup works
        os.chmod(tmp_dir, 0o755)