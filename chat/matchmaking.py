"""
Redis-based matchmaking engine.

Users are pushed into a Redis list based on their requested mode ('video' or 'text').
The matchmaking consumer pops two users from the same queue and creates a chat room for them.
"""

import json
import logging

from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

USER_CHANNEL_MAP_KEY = "antigravity:matchmaking:user_channels"

def get_queue_key(mode):
    return f"antigravity:matchmaking:queue:{mode}"


async def add_to_queue(channel_layer, user_id, channel_name, mode="video"):
    """Add a user to the matchmaking queue in Redis (text or video)."""
    try:
        redis = channel_layer._get_redis()
    except Exception:
        # Fallback for in-memory channel layer — use a simple dict approach
        if not hasattr(channel_layer, '_ag_queues'):
            channel_layer._ag_queues = {"video": [], "text": []}
            channel_layer._ag_channels = {}
        
        channel_layer._ag_channels[str(user_id)] = channel_name
        if mode not in channel_layer._ag_queues:
            channel_layer._ag_queues[mode] = []
        channel_layer._ag_queues[mode].append(str(user_id))
        return await try_match(channel_layer, mode)

    async with redis.client() as conn:
        await conn.hset(USER_CHANNEL_MAP_KEY, str(user_id), channel_name)
        await conn.rpush(get_queue_key(mode), str(user_id))

    return await try_match(channel_layer, mode)


async def remove_from_queue(channel_layer, user_id, mode="video"):
    """Remove a user from the matchmaking queue."""
    try:
        redis = channel_layer._get_redis()
    except Exception:
        if hasattr(channel_layer, '_ag_queues'):
            uid = str(user_id)
            if mode in channel_layer._ag_queues:
                channel_layer._ag_queues[mode] = [u for u in channel_layer._ag_queues[mode] if u != uid]
            channel_layer._ag_channels.pop(uid, None)
        return

    async with redis.client() as conn:
        queue_key = get_queue_key(mode)
        await conn.lrem(queue_key, 0, str(user_id))
        await conn.hdel(USER_CHANNEL_MAP_KEY, str(user_id))


async def try_match(channel_layer, mode="video"):
    """Try to match two users from the specified queue. Returns matched pair or None."""
    try:
        redis = channel_layer._get_redis()
    except Exception:
        # In-memory fallback
        if not hasattr(channel_layer, '_ag_queues'):
            return None
        queue = channel_layer._ag_queues.get(mode, [])
        if len(queue) < 2:
            return None
            
        user1_id = queue.pop(0)
        user2_id = queue.pop(0)
        ch1 = channel_layer._ag_channels.pop(user1_id, None)
        ch2 = channel_layer._ag_channels.pop(user2_id, None)
        if ch1 and ch2:
            return (int(user1_id), ch1, int(user2_id), ch2)
        return None

    async with redis.client() as conn:
        queue_key = get_queue_key(mode)
        queue_len = await conn.llen(queue_key)
        if queue_len < 2:
            return None

        user1_id = await conn.lpop(queue_key)
        user2_id = await conn.lpop(queue_key)

        if not user1_id or not user2_id:
            return None

        user1_id = user1_id.decode() if isinstance(user1_id, bytes) else user1_id
        user2_id = user2_id.decode() if isinstance(user2_id, bytes) else user2_id

        ch1 = await conn.hget(USER_CHANNEL_MAP_KEY, user1_id)
        ch2 = await conn.hget(USER_CHANNEL_MAP_KEY, user2_id)

        # Clean up channel map
        await conn.hdel(USER_CHANNEL_MAP_KEY, user1_id, user2_id)

        if ch1 and ch2:
            ch1 = ch1.decode() if isinstance(ch1, bytes) else ch1
            ch2 = ch2.decode() if isinstance(ch2, bytes) else ch2
            return (int(user1_id), ch1, int(user2_id), ch2)

    return None
