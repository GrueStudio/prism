"""
Bug data models for the Prism CLI.

Models for tracking bugs with custom ID format, logs, and lifecycle management.
Bugs are standalone items (similar to orphans), not part of the BaseItem hierarchy.
"""

import re
import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class BugStatus(str, Enum):
    """Valid status values for bugs representing the lifecycle."""

    OPEN = "open"  # Bug reported, not yet investigated
    REPRODUCED = "reproduced"  # Bug has been reproduced consistently
    FOUND = "found"  # Root cause identified
    FIXED = "fixed"  # Fix implemented
    IMPLEMENTED = "implemented"  # Fix merged and deployed


class BugType(BaseModel):
    """
    Configurable bug type with name and prefix.

    The prefix is used to generate bug IDs (e.g., PHYS for physics bugs).
    """

    name: str
    prefix: str = Field(..., min_length=2, max_length=4)
    description: Optional[str] = None

    @field_validator("prefix")
    @classmethod
    def validate_prefix(cls, v: str) -> str:
        """Validate prefix is 2-4 uppercase letters."""
        if not re.match(r"^[A-Z]{2,4}$", v):
            raise ValueError("Prefix must be 2-4 uppercase letters")
        return v


class BugLog(BaseModel):
    """
    Metadata for a bug log entry.

    The actual log content is stored as a plain text file in .prism/buglogs/.
    This model stores only metadata for listing and management.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    title: str  # Descriptive name (e.g., "Crash Report", "Stack Trace")
    log_type: str = "general"  # e.g., "stack_trace", "error_log", "note", "attachment_ref"
    file_name: Optional[str] = None  # Auto-generated: {id}.log
    metadata: Optional[dict] = None


class BugItem(BaseModel):
    """
    Bug model for tracking issues through their lifecycle.

    Bug ID format: {PREFIX}{DDMMYY}_{COUNTER}
    Example: PHYS100326_01 (physics bug #1 on March 10, 2026)

    Fields:
    - uuid: Unique identifier (internal use)
    - bug_type: The type of bug (determines prefix)
    - bug_id: Auto-generated unique identifier
    - description: Description of the faulty behavior
    - steps_to_reproduce: Steps to reproduce the bug (added as bug progresses)
    - root_cause: Description of what is going wrong (added when found)
    - fix_description: Description of the fix (added when fixed)
    - logs: List of log entries (stack traces, etc.)
    - counter: Daily counter for uniqueness
    - status: Bug lifecycle status
    """

    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bug_type: BugType
    bug_id: str
    description: str  # Description of faulty behavior
    steps_to_reproduce: Optional[str] = None
    root_cause: Optional[str] = None
    fix_description: Optional[str] = None
    logs: List[BugLog] = Field(default_factory=list)  # Metadata references to log files
    counter: int = 0
    status: BugStatus = BugStatus.OPEN
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate description is not empty."""
        if not v or not v.strip():
            raise ValueError("Description is required and cannot be empty")
        return v

    @field_validator("bug_id")
    @classmethod
    def validate_bug_id(cls, v: str) -> str:
        """Validate bug ID format: PREFIX{DDMMYY}_NN"""
        if not re.match(r"^[A-Z]{2,4}\d{6}_\d+$", v):
            raise ValueError(
                "Bug ID must be in format PREFIX{DDMMYY}_NN (e.g., PHYS100326_01)"
            )
        return v

    def add_log(
        self, title: str, log_type: str = "general", metadata: Optional[dict] = None
    ) -> BugLog:
        """
        Create a log entry metadata for the bug.

        The actual log content is stored as a plain text file in .prism/buglogs/.

        Args:
            title: Descriptive name for the log (e.g., "Crash Report", "Stack Trace")
            log_type: Type of log (stack_trace, error_log, note, attachment_ref)
            metadata: Optional metadata dictionary

        Returns:
            The created BugLog metadata (log file created separately via BugManager)
        """
        log = BugLog(
            title=title, log_type=log_type, metadata=metadata or {}
        )
        log.file_name = f"{log.id}.log"
        self.logs.append(log)
        self.updated_at = datetime.now()
        return log

    def set_status(self, value: BugStatus | str) -> None:
        """
        Set bug status from string or BugStatus enum.
        """
        if isinstance(value, BugStatus):
            self.status = value
        elif isinstance(value, str):
            self.status = BugStatus(value)
        self.updated_at = datetime.now()
