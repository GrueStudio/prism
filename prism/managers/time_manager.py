"""
TimeManager for time tracking operations in the Prism CLI.

Handles:
- Starting and stopping timers for Actions (active_timers.json)
- Appending completed logs to timelogs.csv
- Aggregating total time spent and cascading up the execution tree
- Condensing (truncating) historical logs into Action.time_spent
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Callable, Dict, Any

from prism.models.time import TimeLog
from prism.models.files import ActiveTimersFile
from prism.models.base import Action, BaseItem
from prism.managers.storage_manager import StorageManager
from prism.managers.navigation_manager import NavigationManager


class TimeManager:
    """
    Manages time log entries and their aggregation into the project tree.
    """

    def __init__(
        self,
        storage_manager: StorageManager,
        navigator: NavigationManager,
        save_project_callback: Callable[[], None],
    ) -> None:
        """
        Initialize TimeManager.

        Args:
            storage_manager: Storage manager for timelogs.
            navigator: NavigationManager for finding items to update.
            save_project_callback: Callback to save the main project tree.
        """
        self.storage = storage_manager
        self.navigator = navigator
        self._save_project_callback = save_project_callback
        self._active_timers: ActiveTimersFile = self.storage.load_active_timers()

    def start_timer(self, action_uuid: str, description: Optional[str] = None) -> TimeLog:
        """
        Start a new timer for an action in active_timers.json.
        """
        # Check if there's already a running timer for THIS action
        for timer in self._active_timers.timers:
            if timer.action_uuid == action_uuid:
                return timer
        
        new_timer = TimeLog(action_uuid=action_uuid, description=description)
        self._active_timers.timers.append(new_timer)
        self.storage.save_active_timers(self._active_timers)
        return new_timer

    def stop_timer(self, action_uuid: str) -> Optional[TimeLog]:
        """
        Stop the active timer for an action, move to CSV, and update tree.
        """
        for i, timer in enumerate(self._active_timers.timers):
            if timer.action_uuid == action_uuid:
                timer.stop()
                # 1. Save to CSV
                self.storage.append_timelog_csv(timer)
                # 2. Remove from active
                stopped_timer = self._active_timers.timers.pop(i)
                self.storage.save_active_timers(self._active_timers)
                # 3. Update tree (incrementally add this timer's duration)
                self.increment_action_time(action_uuid, stopped_timer.duration)
                return stopped_timer
        return None

    def increment_action_time(self, action_uuid: str, duration: timedelta) -> None:
        """
        Add a duration to an action's time_spent and cascade up.
        """
        action = self.navigator.get_item_by_uuid(action_uuid)
        if not action or not isinstance(action, Action):
            return

        action.time_spent += duration
        self._cascade_time_spent(action, duration)
        self._save_project_callback()

    def _cascade_time_spent(self, item: BaseItem, duration: timedelta) -> None:
        """
        Add duration to parent's time_spent recursively.
        """
        item_path = self.navigator.get_item_path(item)
        if not item_path:
            return

        segments = item_path.split("/")
        if len(segments) < 2:
            return

        parent_path = "/".join(segments[:-1])
        parent = self.navigator.get_item_by_path(parent_path)
        if not parent:
            return

        parent.time_spent += duration
        self._cascade_time_spent(parent, duration)

    def condense_logs(self, before_date: Optional[datetime] = None) -> int:
        """
        Summarize historical logs into Action.time_spent and remove them from CSV.
        
        Since we already keep time_spent updated incrementally in stop_timer,
        condensing here mostly means just deleting the rows from CSV to save space.
        
        If we find that time_spent is out of sync, we could use this to resync.
        
        Args:
            before_date: If provided, only logs before this date are removed.
            
        Returns:
            Number of logs removed.
        """
        # TODO: Implement full CSV rewrite logic for truncation.
        # For now, this is a placeholder for the scaling strategy.
        return 0

    def get_active_timer(self, action_uuid: str) -> Optional[TimeLog]:
        """Get the active timer for an action if any."""
        for timer in self._active_timers.timers:
            if timer.action_uuid == action_uuid:
                return timer
        return None
