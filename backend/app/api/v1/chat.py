from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.chat import (
    ChatRoomCreate,
    ChatRoomResponse,
    ChatRoomListResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    ChatMessageListResponse,
)
from app.services.chat_service import (
    ChatServiceError,
    get_or_create_direct_room,
    list_user_rooms,
    list_messages,
    send_message,
    search_users_for_chat,
)

router = APIRouter(prefix="/chat", tags=["Chat"])


def _err(exc: ChatServiceError):
    code_map = {
        "INVALID_PARTICIPANT": 400,
        "USER_NOT_FOUND": 404,
        "ROOM_ACCESS_DENIED": 403,
    }
    raise HTTPException(
        status_code=code_map.get(exc.code, 400),
        detail={"code": exc.code, "message": exc.message},
    )


@router.get("/users/search")
def search_users(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search users across organizations to start a chat."""
    return search_users_for_chat(db, query=q, current_user_id=current_user.id)


@router.get("/rooms", response_model=ChatRoomListResponse)
def get_rooms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = list_user_rooms(db, current_user.id)
    return ChatRoomListResponse(items=items)


@router.post("/rooms", response_model=ChatRoomResponse, status_code=201)
def create_or_get_room(
    data: ChatRoomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        room = get_or_create_direct_room(
            db,
            current_user_id=current_user.id,
            other_user_id=data.participant_user_id,
        )
        rooms = list_user_rooms(db, current_user.id)
        match = next((r for r in rooms if r["id"] == room.id), None)
        return match or {
            "id": room.id,
            "name": room.name,
            "room_type": room.room_type,
            "created_at": room.created_at,
        }
    except ChatServiceError as e:
        _err(e)


@router.get("/rooms/{room_id}/messages", response_model=ChatMessageListResponse)
def get_messages(
    room_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        items, total = list_messages(
            db, room_id=room_id, user_id=current_user.id, page=page, page_size=page_size
        )
        return ChatMessageListResponse(items=items, total=total)
    except ChatServiceError as e:
        _err(e)


@router.post("/rooms/{room_id}/messages", response_model=ChatMessageResponse, status_code=201)
def post_message(
    room_id: int,
    data: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        msg = send_message(
            db, room_id=room_id, sender_id=current_user.id, body=data.body
        )
        # Broadcast via WebSocket manager if available
        try:
            from app.api.v1.ws import manager
            import asyncio
            # Fire-and-forget broadcast to room participants would go here
            # For simplicity we rely on client polling / WS ping for now
        except Exception:
            pass
        return msg
    except ChatServiceError as e:
        _err(e)
