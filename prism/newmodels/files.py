"""
File models for the Prism CLI.

Models representing the structure of JSON files in the .prism/ directory.
"""
from typing import List, Dict, Any

from pydantic import BaseModel, Field

from .orphan import Orphan
from prism.constants import (
    DEFAULT_SLUG_MAX_LENGTH,
    DEFAULT_SLUG_REGEX_PATTERN,
    DEFAULT_SLUG_WORD_LIMIT,
    DEFAULT_SLUG_FILLER_WORDS,
    DEFAULT_DATE_FORMATS,
    DEFAULT_DATE_MAX_YEARS_FUTURE,
    DEFAULT_DATE_MAX_YEARS_PAST,
    DEFAULT_STATUS_HEADER_WIDTH,
    DEFAULT_PERCENTAGE_ROUND_PRECISION,
)


class StrategicFile(BaseModel):
    """Model for strategic.json file.

    Flat list of all strategic items with parent_uuid references.
    """
    items: List[Dict[str, Any]] = Field(default_factory=list)


class ExecutionFile(BaseModel):
    """Model for execution.json file.

    Flat list of all execution items with parent_uuid references.
    """
    deliverables: List[Dict[str, Any]] = Field(default_factory=list)
    actions: List[Dict[str, Any]] = Field(default_factory=list)


class OrphansFile(BaseModel):
    """Model for orphans.json file.

    List of orphan ideas.
    """
    orphans: List[Orphan] = Field(default_factory=list)


class ConfigFile(BaseModel):
    """Model for config.json file.

    Project settings and configuration.
    """
    schema_version: str = "0.2.0"

    # Slug settings
    slug_max_length: int = DEFAULT_SLUG_MAX_LENGTH
    slug_regex_pattern: str = DEFAULT_SLUG_REGEX_PATTERN
    slug_word_limit: int = DEFAULT_SLUG_WORD_LIMIT
    slug_filler_words: List[str] = Field(default_factory=lambda: list(DEFAULT_SLUG_FILLER_WORDS))

    # Date settings
    date_formats: List[str] = Field(default_factory=lambda: list(DEFAULT_DATE_FORMATS))
    date_max_years_future: int = DEFAULT_DATE_MAX_YEARS_FUTURE
    date_max_years_past: int = DEFAULT_DATE_MAX_YEARS_PAST

    # Display settings
    status_header_width: int = DEFAULT_STATUS_HEADER_WIDTH
    percentage_round_precision: int = DEFAULT_PERCENTAGE_ROUND_PRECISION
