
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OrganizationCreateRequest(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=150,
    )


class OrganizationUpdateRequest(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=150,
    )


class OrganizationResponse(BaseModel):
    id: int
    name: str
    slug: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class OrganizationListResponse(BaseModel):
    items: list[OrganizationResponse]
    total: int
    
    