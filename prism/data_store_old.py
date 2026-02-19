"""
DEPRECATED: Old Prism DataStore using project.json storage.

This module is deprecated and will be removed in a future version.
Use prism.managers.StorageManager with .prism/ folder-based storage instead.
"""
import warnings
warnings.warn(
    "Old DataStore (project.json storage) is deprecated. "
    "Use prism.managers.StorageManager with .prism/ storage instead.",
    DeprecationWarning,
    stacklevel=2
)

"""
This module handles the persistence of project data to a JSON file.
"""
import json
import os
import tempfile
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from prism.models_old import ProjectData


class DataStore:
    """
    Handles loading and saving project data to/from a JSON file.
    """
    
    def __init__(self, project_file: Optional[Path] = None):
        """
        Initialize the DataStore with a project file path.
        
        Args:
            project_file: Path to the project file. Defaults to project.json in current directory.
        """
        self.project_file = project_file if project_file else Path("project.json")

    def load_project_data(self) -> ProjectData:
        """
        Load project data from the JSON file.
        
        Returns:
            ProjectData: The loaded project data, or a new empty ProjectData if file doesn't exist.
        """
        if self.project_file.exists():
            try:
                with open(self.project_file, "r") as f:
                    data = json.load(f)
                return ProjectData.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as e:
                raise Exception(
                    f"Error loading project data from {self.project_file}: {e}"
                )
        return ProjectData()

    def save_project_data(self, data: ProjectData) -> None:
        """
        Save project data to the JSON file using atomic write to prevent corruption.
        
        Args:
            data: The project data to save.
        """
        # Create a temporary file in the same directory as the target file
        temp_dir = self.project_file.parent
        temp_fd, temp_path = tempfile.mkstemp(dir=temp_dir, prefix='.tmp_prism_', suffix='.json')
        
        try:
            # Write data to the temporary file
            with os.fdopen(temp_fd, 'w') as temp_file:
                temp_file.write(data.model_dump_json(indent=2))
            
            # Atomically replace the original file with the temporary file
            os.replace(temp_path, self.project_file)
        except Exception as e:
            # Clean up the temporary file if something goes wrong
            try:
                os.unlink(temp_path)
            except OSError:
                pass  # Ignore errors during cleanup
            raise e
