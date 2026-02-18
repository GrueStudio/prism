"""
Managers for the Prism CLI.

This package contains focused manager classes that handle specific aspects of Prism functionality:
- ItemManager: CRUD operations for items
- TaskManager: Task operations (start, complete, next)
- CompletionTracker: Cascade completion and percentage calculations
- NavigationManager: Path resolution and item lookup
- StorageManager: Persistence to .prism/ folder structure
- ProjectManager: Build hierarchical structure from flat storage
- EventBus: Event-driven architecture for decoupled communication
- AutoArchiveListener: Auto-archive completed items
"""

from prism.managers.item_manager import ItemManager
from prism.managers.task_manager import TaskManager
from prism.managers.completion_tracker import CompletionTracker
from prism.managers.navigation_manager import NavigationManager
from prism.managers.storage_manager import StorageManager, StorageError
from prism.managers.project_manager import ProjectManager, Project
from prism.managers.events import (
    EventBus,
    Event,
    ItemEvent,
    EventType,
    EventListener,
    get_event_bus,
    publish_event,
    subscribe_listener,
)
from prism.managers.auto_archive import AutoArchiveListener
from prism.exceptions import NavigationError

__all__ = [
    "ItemManager",
    "TaskManager",
    "CompletionTracker",
    "NavigationManager",
    "NavigationError",
    "StorageManager",
    "StorageError",
    "ProjectManager",
    "Project",
    "EventBus",
    "Event",
    "ItemEvent",
    "EventType",
    "EventListener",
    "get_event_bus",
    "publish_event",
    "subscribe_listener",
    "AutoArchiveListener",
]
