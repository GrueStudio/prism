import uuid
import json
from datetime import datetime, date, timedelta
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
import re

MAX_SLUG_SIZE = 10

def to_kebab_case(text: str) -> str:
    """
    Generates a simplified slug:
    1. Converts to lowercase.
    2. Replaces spaces with hyphens.
    3. Removes non-alphanumeric characters (except hyphens).
    4. Collapses multiple hyphens and strips leading/trailing.
    5. Truncates to MAX_SLUG_SIZE characters.
    """
    s = text.lower()
    s = s.replace(' ', '-')
    s = re.sub(r'[^\w-]+', '', s) # Keep alphanumeric and hyphens
    s = re.sub(r'-+', '-', s).strip('-')
    return s[:MAX_SLUG_SIZE]

class BaseItem(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    description: Optional[str] = None
    slug: Optional[str] = Field(None)
    status: str = "pending" # pending, in-progress, completed, cancelled
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @field_validator('slug')
    @classmethod
    def validate_provided_slug_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            # Slug must be kebab-case (alphanumeric and hyphens only)
            if not re.fullmatch(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', v):
                raise ValueError(f'Slug "{v}" must be in kebab-case (e.g., "my-slug").')
            if len(v) > MAX_SLUG_SIZE:
                raise ValueError(f'Slug "{v}" must be {MAX_SLUG_SIZE} characters or less.')
        return v

    @model_validator(mode='after')
    def generate_slug_if_missing(self) -> 'BaseItem':
        if self.slug is None:
            if self.name:
                generated_slug = to_kebab_case(self.name)
                if len(generated_slug) == 0:
                    raise ValueError('Generated slug from name is empty.')
                self.slug = generated_slug
            else:
                raise ValueError('Could not generate slug without a name. Please provide either a name or a slug.')
        return self

    model_config = ConfigDict(
        json_encoders = {
            uuid.UUID: str,
            datetime: lambda dt: dt.isoformat(),
            date: lambda d: d.isoformat(),
            timedelta: str,
        },
        arbitrary_types_allowed = True,
        json_schema_extra = {
            'json_dumps': lambda x: json.dumps(x, indent=2), # type: ignore
            'json_loads': json.loads # type: ignore
        }
    )


# Define the models for hierarchy
class Action(BaseItem):
    time_spent: timedelta = Field(default_factory=lambda: timedelta(0))
    due_date: Optional[date] = None

class Deliverable(BaseItem):
    actions: List[Action] = Field(default_factory=list)

class Objective(BaseItem):
    deliverables: List[Deliverable] = Field(default_factory=list)

class Milestone(BaseItem):
    objectives: List[Objective] = Field(default_factory=list)

class Phase(BaseItem):
    current: bool = False
    milestones: List[Milestone] = Field(default_factory=list)

class ProjectData(BaseModel):
    phases: List[Phase] = Field(default_factory=list)

    model_config = ConfigDict(
        json_encoders = {
            uuid.UUID: str,
            datetime: lambda dt: dt.isoformat(),
            date: lambda d: d.isoformat(),
            timedelta: str,
        },
        arbitrary_types_allowed = True,
        json_schema_extra = {
            'json_dumps': lambda x: json.dumps(x, indent=2), # type: ignore
            'json_loads': json.loads # type: ignore
        }
    )