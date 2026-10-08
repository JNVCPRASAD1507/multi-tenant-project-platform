
"""
Redis Pub/Sub based notification broadcasting.

Notifications are persisted in PostgreSQL and then published
through Redis so connected users receive them immediately.
"""

import json
from typing import Any

import redis.asyncio as redis

from app.core.config import settings


NOTIFICATION_CHANNEL_PREFIX = "notification:user:"


def get_notification_channel(user_id: int) -> str:
    return f"{NOTIFICATION_CHANNEL_PREFIX}{user_id}"


async def publish_notification(
    user_id: int,
    notification: dict[str, Any],
) -> None:
    """
    Publish a notification to a specific user's Redis channel.
    """

    redis_client = redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )

    try:
        channel = get_notification_channel(user_id)

        payload = json.dumps(
            {
                "type": "notification",
                **notification,
            },
            default=str,
        )

        await redis_client.publish(
            channel,
            payload,
        )

    finally:
        await redis_client.aclose()


async def subscribe_to_notifications(
    user_id: int,
    websocket,
) -> None:
    """
    Subscribe a user's WebSocket to their Redis notification channel.
    """

    redis_client = redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )

    pubsub = redis_client.pubsub()

    channel = get_notification_channel(user_id)

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

                        await websocket.send_json(
                            payload
                        )

                    except Exception:
                        break

    finally:

        try:

            await pubsub.unsubscribe(
                channel
            )

            await pubsub.aclose()

            await redis_client.aclose()

        except Exception:
            pass
        
        