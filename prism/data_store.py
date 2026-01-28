from pathlib import Path
import json
from typing import Optional

from prism.models import ProjectData

class DataStore:
    """
    Handles reading from and writing to a JSON file for project data persistence.
    """
    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path or self._get_default_file_path()
        # Ensure the directory for the file path exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_default_file_path(self) -> Path:
        """Determines the default project data file path."""
        # Default to a file in the current working directory for now.
        return Path("./project_data.json")

    def load_project_data(self) -> ProjectData:
        """
        Loads project data from the JSON file.
        If the file does not exist, returns an empty ProjectData instance.
        """
        if not self.file_path.exists():
            return ProjectData()
        
        try:
            # Use model_validate_json for Pydantic V2 compatible deserialization
            return ProjectData.model_validate_json(self.file_path.read_text())
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Corrupt JSON data in {self.file_path}: {e.msg}", e.doc, e.pos)

    def save_project_data(self, project_data: ProjectData):
        """Saves the project data to the JSON file."""
        # Use model_dump_json() for Pydantic V2 compatible serialization
        json_output = project_data.model_dump_json(indent=2) # indent is now handled here
        with open(self.file_path, 'w') as f:
            f.write(json_output)