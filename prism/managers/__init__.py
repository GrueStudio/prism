"""
Managers for the Prism CLI.

This package contains focused manager classes that handle specific aspects of Prism functionality:
- CRUDManager: CRUD operations for strategic and execution items
- TaskManager: Task operations (start/done/next) and completion tracking
- NavigationManager: Path resolution and item lookup
- StorageManager: Persistence to .prism/ folder structure
- ProjectManager: Build hierarchical structure from flat storage
- ArchiveManager: Archive operations with lazy-loading via signals
"""

from prism.exceptions import NavigationError
from prism.managers.archive_manager import ArchiveManager
from prism.managers.crud_manager import CRUDManager
from prism.managers.navigation_manager import NavigationManager
from prism.managers.project_manager import ProjectManager
from prism.managers.storage_manager import StorageError, StorageManager
from prism.managers.task_manager import TaskManager

__all__ = [
    "CRUDManager",
    "TaskManager",
    "NavigationManager",
    "NavigationError",
    "StorageManager",
    "StorageError",
    "ProjectManager",
    "ArchiveManager",
]
