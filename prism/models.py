from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
import re
import uuid
from prism.constants import SLUG_MAX_LENGTH, SLUG_REGEX_PATTERN, SLUG_ERROR_MESSAGE, DEFAULT_STATUS

class BaseItem(BaseModel):
    name: str
    description: Optional[str] = None
    slug: str = Field(min_length=1, max_length=SLUG_MAX_LENGTH)
    status: str = Field(default=DEFAULT_STATUS)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @field_validator('slug', mode='before')
    @classmethod
    def validate_slug(cls, v, info):
        if v:
            pattern = f"{SLUG_REGEX_PATTERN}{{1,{SLUG_MAX_LENGTH}}}"
            if not re.fullmatch(pattern, v):
                raise ValueError(f"{SLUG_ERROR_MESSAGE} {SLUG_ERROR_DETAILED}")
            return v
        if 'name' in info.data:
            slug = re.sub(r'[^a-z0-9]+', '-', info.data['name'].lower()).strip('-')
            return slug[:SLUG_MAX_LENGTH]
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

    cursor: Optional[str] = None
