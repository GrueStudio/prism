"""
Time tracking models for the Prism CLI.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from pydantic import BaseModel, Field, computed_field


class TimeLog(BaseModel):
    """
    Represents a single block of time spent on an Action.
    """

    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action_uuid: str
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    description: Optional[str] = None

    @computed_field
    @property
    def duration(self) -> timedelta:
        """Calculate the duration of this log entry."""
        if not self.end_time:
            # If still running, calculate duration up to now
            return datetime.now(timezone.utc) - self.start_time
        return self.end_time - self.start_time

    def is_running(self) -> bool:
        """Check if this time log is currently active (no end time)."""
        return self.end_time is None

    def stop(self) -> None:
        """Stop the timer by setting the end time to now."""
        if self.is_running():
            self.end_time = datetime.now(timezone.utc)
