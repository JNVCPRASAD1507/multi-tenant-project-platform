"""Cross-organization chat service.

Security notes:
- Any authenticated active user can chat with any other active user.
- Project / organization data remains fully isolated.
- Only chat is intentionally cross-tenant.
"""
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session

from app.models.chat import ChatRoom, ChatParticipant, ChatMessage
from app.models.user import User


class ChatServiceError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def get_or_create_direct_room(
    db: Session,
    *,
    current_user_id: int,
    other_user_id: int,
) -> ChatRoom:
    if current_user_id == other_user_id:
        raise ChatServiceError("INVALID_PARTICIPANT", "Cannot create a chat with yourself.")

    other = db.get(User, other_user_id)
    if not other or not other.is_active:
        raise ChatServiceError("USER_NOT_FOUND", "Target user not found or inactive.")

    # Find existing direct room between these two users
    subq = (
        select(ChatParticipant.room_id)
        .where(ChatParticipant.user_id.in_([current_user_id, other_user_id]))
        .group_by(ChatParticipant.room_id)
        .having(func.count(ChatParticipant.user_id) == 2)
    )
    existing_room_id = db.scalar(
        select(ChatRoom.id).where(
            ChatRoom.room_type == "direct",
            ChatRoom.id.in_(subq),
        )
    )
    if existing_room_id:
        return db.get(ChatRoom, existing_room_id)

    room = ChatRoom(
        room_type="direct",
        name=None,
        created_by_id=current_user_id,
    )
    db.add(room)
    db.flush()

    db.add(ChatParticipant(room_id=room.id, user_id=current_user_id))
    db.add(ChatParticipant(room_id=room.id, user_id=other_user_id))
    db.commit()
    db.refresh(room)
    return room


def list_user_rooms(db: Session, user_id: int) -> list[dict]:
    rooms = db.scalars(
        select(ChatRoom)
        .join(ChatParticipant, ChatParticipant.room_id == ChatRoom.id)
        .where(ChatParticipant.user_id == user_id)
        .order_by(ChatRoom.created_at.desc())
    ).all()

    result = []
    for room in rooms:
        other = db.scalar(
            select(User)
            .join(ChatParticipant, ChatParticipant.user_id == User.id)
            .where(
                ChatParticipant.room_id == room.id,
                ChatParticipant.user_id != user_id,
            )
        )
        result.append({
            "id": room.id,
            "name": room.name or (other.full_name if other else "Chat"),
            "room_type": room.room_type,
            "created_at": room.created_at,
            "other_participant_name": other.full_name if other else None,
            "other_participant_id": other.id if other else None,
        })
    return result


def list_messages(
    db: Session,
    *,
    room_id: int,
    user_id: int,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict], int]:
    # Ensure user is a participant
    is_member = db.scalar(
        select(ChatParticipant.id).where(
            ChatParticipant.room_id == room_id,
            ChatParticipant.user_id == user_id,
        )
    )
    if not is_member:
        raise ChatServiceError("ROOM_ACCESS_DENIED", "You are not a participant of this room.")

    total = db.scalar(
        select(func.count()).select_from(ChatMessage).where(
            ChatMessage.room_id == room_id,
            ChatMessage.is_deleted == False,  # noqa
        )
    ) or 0

    messages = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.room_id == room_id, ChatMessage.is_deleted == False)  # noqa
        .order_by(ChatMessage.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    items = []
    for m in reversed(list(messages)):
        sender = db.get(User, m.sender_id)
        items.append({
            "id": m.id,
            "room_id": m.room_id,
            "sender_id": m.sender_id,
            "sender_name": sender.full_name if sender else None,
            "body": m.body,
            "created_at": m.created_at,
        })
    return items, total


def send_message(
    db: Session,
    *,
    room_id: int,
    sender_id: int,
    body: str,
) -> dict:
    is_member = db.scalar(
        select(ChatParticipant.id).where(
            ChatParticipant.room_id == room_id,
            ChatParticipant.user_id == sender_id,
        )
    )
    if not is_member:
        raise ChatServiceError("ROOM_ACCESS_DENIED", "You are not a participant of this room.")

    msg = ChatMessage(room_id=room_id, sender_id=sender_id, body=body.strip())
    db.add(msg)
    db.commit()
    db.refresh(msg)

    sender = db.get(User, sender_id)
    return {
        "id": msg.id,
        "room_id": msg.room_id,
        "sender_id": msg.sender_id,
        "sender_name": sender.full_name if sender else None,
        "body": msg.body,
        "created_at": msg.created_at,
    }


def search_users_for_chat(db: Session, *, query: str, current_user_id: int, limit: int = 20) -> list[dict]:
    """Search active users across all organizations for starting a chat."""
    q = f"%{query.strip()}%"
    users = db.scalars(
        select(User).where(
            User.is_active == True,  # noqa
            User.id != current_user_id,
            or_(User.full_name.ilike(q), User.email.ilike(q)),
        ).limit(limit)
    ).all()
    return [{"id": u.id, "full_name": u.full_name, "email": u.email} for u in users]
