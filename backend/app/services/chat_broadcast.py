
"""
Redis Pub/Sub based chat broadcasting.

Purpose:
- Persist messages in PostgreSQL separately.
- Publish real-time chat events through Redis.
- Allow multiple FastAPI processes/containers to share chat events.
"""

import asyncio
import json
from typing import Any

import redis.asyncio as redis

from app.core.config import settings


CHAT_CHANNEL_PREFIX = "chat:room:"


def get_chat_channel(room_id: int) -> str:
    """
    Return the Redis Pub/Sub channel for a chat room.
    """
    return f"{CHAT_CHANNEL_PREFIX}{room_id}"


async def publish_chat_message(
    room_id: int,
    message: dict[str, Any],
) -> None:
    """
    Publish a chat message to the room's Redis channel.
    """

    redis_client = redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )

    try:
        channel = get_chat_channel(room_id)

        payload = json.dumps(
            {
                "type": "chat_message",
                **message,
            },
            default=str,
        )

        await redis_client.publish(channel, payload)

    finally:
        await redis_client.close()


async def subscribe_to_room(
    room_id: int,
    websocket,
) -> None:
    """
    Subscribe one WebSocket connection to a Redis room channel.

    Every message published to the room is forwarded
    to the connected WebSocket.
    """

    redis_client = redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )

    pubsub = redis_client.pubsub()

    channel = get_chat_channel(room_id)

    await pubsub.subscribe(channel)

    try:
        while True:

            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0,
            )

            if message is not None:

                data = message.get("data")

                if data:
                    try:
                        payload = json.loads(data)

                        await websocket.send_json(payload)

                    except Exception:
                        # WebSocket may already be closed.
                        break

            await asyncio.sleep(0.01)

    finally:
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            await redis_client.close()
        except Exception:
            pass
        
        