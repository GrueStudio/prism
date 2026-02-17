"""
File models for the Prism CLI.

Models representing the structure of JSON files in the .prism/ directory.
"""
from typing import List, Dict, Any

from pydantic import BaseModel, Field

from .orphan import Orphan


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
    slug_max_length: int = 15
    slug_regex_pattern: str = r"[a-z0-9\-]"  # Character class, combined with length in validation
    slug_word_limit: int = 3
    slug_filler_words: List[str] = Field(default_factory=lambda: [
        "a", "an", "and", "as", "at", "by", "for", "from", "if", "in",
        "into", "of", "on", "or", "the", "to", "with"
    ])
    
    # Date settings (defaults, will be populated from constants)
    date_formats: List[str] = Field(default_factory=lambda: [
        "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y",
        "%m-%d-%Y", "%m/%d/%Y", "%Y%m%d", "%d %B %Y",
        "%d %b %Y", "%B %d, %Y", "%b %d, %Y"
    ])
    date_max_years_future: int = 10
    date_max_years_past: int = 1
    
    # Display settings
    status_header_width: int = 25
    percentage_round_precision: int = 1
