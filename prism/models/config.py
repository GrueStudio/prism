"""
Configuration models for the Prism CLI.

Isolated from other models to prevent circular dependencies.
"""

import re
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from prism.constants import (
    DEFAULT_DATE_FORMATS,
    DEFAULT_DATE_MAX_YEARS_FUTURE,
    DEFAULT_DATE_MAX_YEARS_PAST,
    DEFAULT_PERCENTAGE_ROUND_PRECISION,
    DEFAULT_SLUG_FILLER_WORDS,
    DEFAULT_SLUG_MAX_LENGTH,
    DEFAULT_SLUG_REGEX_PATTERN,
    DEFAULT_SLUG_WORD_LIMIT,
    DEFAULT_STATUS_HEADER_WIDTH,
)

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

class ConfigFile(BaseModel):
    """Model for config.json file.

    Project settings and configuration.
    """

    schema_version: str = "0.2.0"

    # Slug settings
    slug_max_length: int = DEFAULT_SLUG_MAX_LENGTH
    slug_regex_pattern: str = DEFAULT_SLUG_REGEX_PATTERN
    slug_word_limit: int = DEFAULT_SLUG_WORD_LIMIT
    slug_filler_words: List[str] = Field(
        default_factory=lambda: list(DEFAULT_SLUG_FILLER_WORDS)
    )

    # Date settings
    date_formats: List[str] = Field(default_factory=lambda: list(DEFAULT_DATE_FORMATS))
    date_max_years_future: int = DEFAULT_DATE_MAX_YEARS_FUTURE
    date_max_years_past: int = DEFAULT_DATE_MAX_YEARS_PAST

    # Display settings
    status_header_width: int = DEFAULT_STATUS_HEADER_WIDTH
    percentage_round_precision: int = DEFAULT_PERCENTAGE_ROUND_PRECISION

    # Orphan settings
    orphan_name_regex: str = r"^[a-zA-Z0-9\s\-_'\"]+$"
    orphan_default_priority: int = 0
    orphan_priority_min: int = -100
    orphan_priority_max: int = 100
    orphan_priority_labels: dict[str, int] = Field(
        default_factory=lambda: {
            "low": -10,
            "medium": 0,
            "high": 10,
            "critical": 50,
        }
    )

    # Bug settings
    bug_types: List[BugType] = Field(default_factory=list)
