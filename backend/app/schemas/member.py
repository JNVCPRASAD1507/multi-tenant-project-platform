from datetime import datetime

from pydantic import BaseModel, Field


class MemberCreateRequest(BaseModel):
    user_id: int = Field(ge=1)
    role_id: int = Field(ge=1)
    
class MemberUpdateRequest(BaseModel):
    role_id: int = Field(ge=1)
    is_active: bool

class MemberResponse(BaseModel):
    user_id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    joined_at: datetime


class MemberListResponse(BaseModel):
    items: list[MemberResponse]
    total: int