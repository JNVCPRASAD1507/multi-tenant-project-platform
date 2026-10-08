import asyncio

from app.api.v1.ws import ConnectionManager


def test_connection_manager_user_and_room_broadcast():
    class FakeWebSocket:
        def __init__(self):
            self.messages = []
        async def send_json(self, message):
            self.messages.append(message)

    manager = ConnectionManager()
    ws1 = FakeWebSocket()
    ws2 = FakeWebSocket()

    # Bypass accept because these are unit-test doubles.
    manager.user_sockets[1] = {ws1, ws2}
    manager.room_sockets[10] = {ws1, ws2}

    asyncio.run(manager.send_to_user(1, {"type": "notification"}))
    assert len(ws1.messages) == 1
    assert len(ws2.messages) == 1

    asyncio.run(manager.broadcast_room(10, {"type": "chat_message"}, exclude=ws1))
    assert len(ws1.messages) == 1
    assert len(ws2.messages) == 2
