"""
WebSocket endpoints for notifications and chat.

Chat messages are distributed through Redis Pub/Sub so that
multiple FastAPI processes/containers can communicate in real time.
"""

import asyncio
import json
from typing import Dict, Set

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.services.chat_broadcast import (
    subscribe_to_room,
)

from app.services.notification_broadcast import (
    subscribe_to_notifications,
)

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """
    Keeps track of active WebSocket connections.

    This manager is still useful for local connections,
    while Redis Pub/Sub handles cross-process broadcasting.
    """

    def __init__(self):
        self.user_sockets: Dict[int, Set[WebSocket]] = {}
        self.room_sockets: Dict[int, Set[WebSocket]] = {}

    async def connect_user(
        self,
        user_id: int,
        websocket: WebSocket,
    ):
        await websocket.accept()

        self.user_sockets.setdefault(
            user_id,
            set(),
        ).add(websocket)

    def disconnect_user(
        self,
        user_id: int,
        websocket: WebSocket,
    ):
        sockets = self.user_sockets.get(user_id)

        if not sockets:
            return

        sockets.discard(websocket)

        if not sockets:
            del self.user_sockets[user_id]

    async def join_room(
        self,
        room_id: int,
        websocket: WebSocket,
    ):
        self.room_sockets.setdefault(
            room_id,
            set(),
        ).add(websocket)

    def leave_room(
        self,
        room_id: int,
        websocket: WebSocket,
    ):
        sockets = self.room_sockets.get(room_id)

        if not sockets:
            return

        sockets.discard(websocket)

        if not sockets:
            del self.room_sockets[room_id]

    async def send_to_user(
        self,
        user_id: int,
        message: dict,
    ):
        sockets = list(self.user_sockets.get(user_id, []))

        for websocket in sockets:

            try:
                await websocket.send_json(message)

            except Exception:
                self.disconnect_user(
                    user_id,
                    websocket,
                )

    async def broadcast_room(
        self,
        room_id: int,
        message: dict,
        exclude: WebSocket | None = None,
    ):
        sockets = list(self.room_sockets.get(room_id, []))

        for websocket in sockets:

            if websocket is exclude:
                continue

            try:
                await websocket.send_json(message)

            except Exception:
                self.leave_room(
                    room_id,
                    websocket,
                )


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

        user = db.get(
            User,
            user_id,
        )

        if not user:
            return None

        if not user.is_active:
            return None

        return user_id

    finally:
        db.close()


@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    Real-time notification WebSocket.

    Flow:

        Browser
           ↓
        WebSocket
           ↓
        Validate JWT
           ↓
        Redis notification channel
           ↓
        Notification event
           ↓
        Browser
    """

    user_id = _validate_token(token)

    if user_id is None:

        await websocket.close(code=4001)

        return

    await manager.connect_user(
        user_id,
        websocket,
    )

    subscriber_task = asyncio.create_task(
        subscribe_to_notifications(
            user_id,
            websocket,
        )
    )

    try:

        await websocket.send_json(
            {
                "type": "connected",
                "message": "Notification WebSocket connected",
                "user_id": user_id,
            }
        )

        while True:

            data = await websocket.receive_text()

            if data == "ping":

                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:

        pass

    finally:

        manager.disconnect_user(
            user_id,
            websocket,
        )

        subscriber_task.cancel()

        try:

            await subscriber_task

        except asyncio.CancelledError:

            pass


@router.websocket("/ws/chat/{room_id}")
async def websocket_chat(
    websocket: WebSocket,
    room_id: int,
    token: str = Query(...),
):
    """
    Real-time chat.

    Flow:

        WebSocket
            ↓
        Validate JWT
            ↓
        Verify room participant
            ↓
        Redis Pub/Sub subscription
            ↓
        Receive chat events
            ↓
        Send events to browser
    """

    user_id = _validate_token(token)

    if user_id is None:

        await websocket.close(code=4001)

        return

    # -------------------------------------------------
    # Verify chat room membership
    # -------------------------------------------------

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

    # -------------------------------------------------
    # Register WebSocket
    # -------------------------------------------------

    await manager.connect_user(
        user_id,
        websocket,
    )

    await manager.join_room(
        room_id,
        websocket,
    )

    # -------------------------------------------------
    # Redis subscriber
    # -------------------------------------------------

    subscriber_task = asyncio.create_task(
        subscribe_to_room(
            room_id,
            websocket,
        )
    )

    try:

        await websocket.send_json(
            {
                "type": "joined",
                "room_id": room_id,
            }
        )

        while True:

            raw = await websocket.receive_text()

            if raw == "ping":

                await websocket.send_json({"type": "pong"})

                continue

            try:

                payload = json.loads(raw)

                body = (payload.get("body") or "").strip()

                if not body:
                    continue

                from app.services.chat_service import (
                    send_message,
                )

                from app.services.chat_broadcast import (
                    publish_chat_message,
                )

                db = SessionLocal()

                try:

                    msg = send_message(
                        db,
                        room_id=room_id,
                        sender_id=user_id,
                        body=body,
                    )

                finally:

                    db.close()

                # -------------------------------------------------
                # Publish message to Redis
                # -------------------------------------------------

                await publish_chat_message(
                    room_id,
                    msg,
                )

            except json.JSONDecodeError:
                continue

    except WebSocketDisconnect:

        manager.disconnect_user(
            user_id,
            websocket,
        )

        manager.leave_room(
            room_id,
            websocket,
        )

    finally:

        subscriber_task.cancel()

        try:
            await subscriber_task
        except asyncio.CancelledError:
            pass
