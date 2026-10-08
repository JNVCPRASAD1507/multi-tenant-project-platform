
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.chat import ChatParticipant

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

from app.services.notification_service import (
    create_notification,
)

from app.services.notification_broadcast import (
    publish_notification,
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


@router.post(
    "/rooms/{room_id}/messages",
    response_model=ChatMessageResponse,
    status_code=201,
)
async def post_message(
    room_id: int,
    data: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a chat message.

    Flow:

        1. Save message to PostgreSQL.
        2. Publish chat event to Redis.
        3. Find other chat participant.
        4. Create notification in PostgreSQL.
        5. Publish notification to Redis.
        6. Notification WebSocket delivers it instantly.
    """

    try:

        # -------------------------------------------------
        # 1. Save chat message
        # -------------------------------------------------

        msg = send_message(
            db,
            room_id=room_id,
            sender_id=current_user.id,
            body=data.body,
        )

        # -------------------------------------------------
        # 2. Publish chat message
        # -------------------------------------------------

        from app.services.chat_broadcast import (
            publish_chat_message,
        )

        await publish_chat_message(
            room_id,
            msg,
        )

        # -------------------------------------------------
        # 3. Find other participant
        # -------------------------------------------------

        participants = db.scalars(
            select(ChatParticipant).where(
                ChatParticipant.room_id == room_id,
                ChatParticipant.user_id != current_user.id,
            )
        ).all()

        # -------------------------------------------------
        # 4. Create notification for each participant
        # -------------------------------------------------

        for participant in participants:

            notification = create_notification(
                db,
                user_id=participant.user_id,
                organization_id=None,
                notification_type="chat_message",
                title=f"New message from {current_user.full_name}",
                message=data.body,
                entity_type="chat_room",
                entity_id=room_id,
            )

            # -------------------------------------------------
            # 5. Publish notification to Redis
            # -------------------------------------------------

            await publish_notification(
                participant.user_id,
                {
                    "id": notification.id,
                    "user_id": notification.user_id,
                    "organization_id": notification.organization_id,
                    "type": notification.type,
                    "title": notification.title,
                    "message": notification.message,
                    "entity_type": notification.entity_type,
                    "entity_id": notification.entity_id,
                    "is_read": notification.is_read,
                    "created_at": notification.created_at.isoformat(),
                },
            )

        return msg

    except ChatServiceError as e:

        _err(e)
        
        
        