"""
Orphan model for the Prism CLI.

Orphans are typeless ideas waiting to be adopted into the project structure.
"""
import uuid
from typing import Optional

from pydantic import BaseModel, Field


class Orphan(BaseModel):
    """Orphan model - typeless ideas waiting to be adopted.

    Minimal fields only. Orphans are deleted when adopted.
    """
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    priority: int = 0
