"""Redis Manager - Pub/Sub with Fallback"""
import asyncio
import json
import logging
from typing import Optional, AsyncGenerator
import redis.asyncio as aioredis
from app.core.config import get_settings

log = logging.getLogger("whalex.redis")
settings = get_settings()


class RedisManager:
    """Manages Redis connection with automatic fallback to local queue"""
    
    PRICES_CHANNEL = "whalex:prices"
    SIGNALS_CHANNEL = "whalex:signals"
    
    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None
        self._pubsub = None
        self._available = False
        self._local_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    
    async def connect(self):
        """Establish Redis connection"""
        try:
            self._redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
            await self._redis.ping()
            self._available = True
            log.info("✅ Redis connected - Pub/Sub enabled")
        except Exception as e:
            self._available = False
            log.warning(f"⚠️ Redis unavailable ({e}) — Fallback to Local Queue")
    
    async def publish(self, channel: str, data: dict):
        """Publish message to channel"""
        msg = json.dumps(data, ensure_ascii=False)
        if self._available and self._redis:
            try:
                await self._redis.publish(channel, msg)
                return
            except Exception as e:
                log.debug(f"Redis publish error: {e}")
        # Fallback to local queue
        try:
            self._local_queue.put_nowait({"channel": channel, "data": data})
        except asyncio.QueueFull:
            pass
    
    async def subscribe(self, channels: list[str]) -> AsyncGenerator:
        """Subscribe to channels and yield messages"""
        if self._available and self._redis:
            try:
                pubsub = self._redis.pubsub()
                await pubsub.subscribe(*channels)
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        try:
                            yield json.loads(message["data"])
                        except:
                            pass
                return
            except Exception as e:
                log.warning(f"Redis subscribe error: {e} — Fallback to queue")
        
        # Fallback to local queue
        while True:
            try:
                item = await asyncio.wait_for(self._local_queue.get(), timeout=5.0)
                yield item["data"]
            except asyncio.TimeoutError:
                continue
    
    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
    
    @property
    def is_available(self) -> bool:
        return self._available


# Singleton instance
redis_mgr = RedisManager()