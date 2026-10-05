
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ProjectStatus = Literal[
    "active",
    "on_hold",
    "completed",
    "archived",
]


class ProjectCreateRequest(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=150,
    )

    description: str | None = Field(
        default=None,
        max_length=5000,
    )

    status: ProjectStatus = "active"


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    description: str | None = Field(
        default=None,
        max_length=5000,
    )

    status: ProjectStatus | None = None

    is_active: bool | None = None


class ProjectResponse(BaseModel):
    id: int
    organization_id: int
    name: str
    description: str | None
    status: ProjectStatus
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    
    