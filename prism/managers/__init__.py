"""
Managers for the Prism CLI.

This package contains focused manager classes that handle specific aspects of Prism functionality:
- ItemManager: CRUD operations for items
- TaskManager: Task operations (start, complete, next)
- CompletionTracker: Cascade completion and percentage calculations
- NavigationManager: Path resolution and item lookup
"""

from prism.managers.item_manager import ItemManager

__all__ = ["ItemManager"]
