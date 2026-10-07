"""WebSocket endpoints – notifications + chat.

Security:
- JWT required via query param `token`
- User must be active
- Chat room messages only delivered to room participants
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, Set
import json

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    def __init__(self):
        self.user_sockets: Dict[int, Set[WebSocket]] = {}
        self.room_sockets: Dict[int, Set[WebSocket]] = {}  # room_id -> sockets

    async def connect_user(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.user_sockets.setdefault(user_id, set()).add(websocket)

    def disconnect_user(self, user_id: int, websocket: WebSocket):
        if user_id in self.user_sockets:
            self.user_sockets[user_id].discard(websocket)
            if not self.user_sockets[user_id]:
                del self.user_sockets[user_id]

    async def join_room(self, room_id: int, websocket: WebSocket):
        self.room_sockets.setdefault(room_id, set()).add(websocket)

    def leave_room(self, room_id: int, websocket: WebSocket):
        if room_id in self.room_sockets:
            self.room_sockets[room_id].discard(websocket)

    async def send_to_user(self, user_id: int, message: dict):
        for ws in list(self.user_sockets.get(user_id, [])):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect_user(user_id, ws)

    async def broadcast_room(self, room_id: int, message: dict, exclude: WebSocket | None = None):
        for ws in list(self.room_sockets.get(room_id, [])):
            if ws is exclude:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                self.leave_room(room_id, ws)


manager = ConnectionManager()


def _validate_token(token: str) -> int | None:
    from app.core.security import decode_access_token
    from app.db.session import SessionLocal
    from app.models.user import User

    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except Exception:
        return None

    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        if not user or not user.is_active:
            return None
        return user_id
    finally:
        db.close()


@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(...),
):
    user_id = _validate_token(token)
    if user_id is None:
        await websocket.close(code=4001)
        return

    await manager.connect_user(user_id, websocket)
    try:
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connected",
            "user_id": user_id,
        })
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect_user(user_id, websocket)


@router.websocket("/ws/chat/{room_id}")
async def websocket_chat(
    websocket: WebSocket,
    room_id: int,
    token: str = Query(...),
):
    """Real-time chat for a room. Client must be a participant."""
    user_id = _validate_token(token)
    if user_id is None:
        await websocket.close(code=4001)
        return

    # Verify membership
    from app.db.session import SessionLocal
    from app.models.chat import ChatParticipant
    from sqlalchemy import select

    db = SessionLocal()
    try:
        is_member = db.scalar(
            select(ChatParticipant.id).where(
                ChatParticipant.room_id == room_id,
                ChatParticipant.user_id == user_id,
            )
        )
        if not is_member:
            await websocket.close(code=4003)
            return
    finally:
        db.close()

    await manager.connect_user(user_id, websocket)
    await manager.join_room(room_id, websocket)

    try:
        await websocket.send_json({"type": "joined", "room_id": room_id})
        while True:
            raw = await websocket.receive_text()
            if raw == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            # Client can send JSON messages; we persist + broadcast
            try:
                payload = json.loads(raw)
                body = (payload.get("body") or "").strip()
                if not body:
                    continue
                from app.services.chat_service import send_message
                db = SessionLocal()
                try:
                    msg = send_message(db, room_id=room_id, sender_id=user_id, body=body)
                finally:
                    db.close()
                await manager.broadcast_room(room_id, {"type": "chat_message", **msg})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect_user(user_id, websocket)
        manager.leave_room(room_id, websocket)
