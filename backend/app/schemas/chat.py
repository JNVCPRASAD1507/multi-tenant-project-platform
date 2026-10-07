from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class ChatMessageCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=5000)


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int
    sender_id: int
    sender_name: Optional[str] = None
    body: str
    created_at: datetime


class ChatRoomCreate(BaseModel):
    """Create a direct chat with another user (any organization)."""
    participant_user_id: int
    name: Optional[str] = None


class ChatRoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: Optional[str]
    room_type: str
    created_at: datetime
    other_participant_name: Optional[str] = None
    other_participant_id: Optional[int] = None


class ChatRoomListResponse(BaseModel):
    items: list[ChatRoomResponse]


class ChatMessageListResponse(BaseModel):
    items: list[ChatMessageResponse]
    total: int
