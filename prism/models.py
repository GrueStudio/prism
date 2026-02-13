from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
import re
import uuid

class BaseItem(BaseModel):
    name: str
    description: Optional[str] = None
    slug: str = Field(min_length=1, max_length=15)
    status: str = "pending"  # e.g., pending, in-progress, completed, cancelled
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @field_validator('slug', mode='before')
    @classmethod
    def validate_slug(cls, v, info):
        if v:
            if not re.fullmatch(r"[a-z0-9\-]{1,15}", v):
                raise ValueError("Slug must be kebab-case, alphanumeric with hyphens, and max 15 characters.")
            return v
        if 'name' in info.data:
            slug = re.sub(r'[^a-z0-9]+', '-', info.data['name'].lower()).strip('-')
            return slug[:15]
        return "" # Should not happen if name is always present

class Action(BaseItem):
    time_spent: Optional[int] = None  # in minutes
    due_date: Optional[datetime] = None

class Deliverable(BaseItem):
    actions: List[Action] = Field(default_factory=list)

class Objective(BaseItem):
    deliverables: List[Deliverable] = Field(default_factory=list)

class Milestone(BaseItem):
    objectives: List[Objective] = Field(default_factory=list)

class Phase(BaseItem):
    milestones: List[Milestone] = Field(default_factory=list)

class ProjectData(BaseModel):
    phases: List[Phase] = Field(default_factory=list)