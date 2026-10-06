
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Dict, Set
import json

router = APIRouter(tags=["WebSocket"])

# Simple in-memory connection manager (one process)
class ConnectionManager:
    def __init__(self):
        # user_id -> set of websockets
        self.active: Dict[int, Set[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active.setdefault(user_id, set()).add(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket):
        if user_id in self.active:
            self.active[user_id].discard(websocket)
            if not self.active[user_id]:
                del self.active[user_id]

    async def send_to_user(self, user_id: int, message: dict):
        if user_id in self.active:
            dead = []
            for ws in self.active[user_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(user_id, ws)


manager = ConnectionManager()


@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    """
    Connect with:  ws://127.0.0.1:8000/api/v1/ws/notifications?token=YOUR_ACCESS_TOKEN
    """
    from app.core.security import decode_access_token
    from app.db.session import SessionLocal
    from app.models.user import User

    # Validate token
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except Exception:
        await websocket.close(code=4001)
        return

    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        if not user or not user.is_active:
            await websocket.close(code=4003)
            return
    finally:
        db.close()

    await manager.connect(user_id, websocket)
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connected successfully",
            "user_id": user_id,
        })

        while True:
            # Keep connection alive / receive client pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
        
            