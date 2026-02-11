"""
Redis Queue Publisher for Usage Tracking
Publishes usage events to Redis queue for async processing by User Service
"""
import redis.asyncio as redis
import json
import logging
import os
from typing import Dict, Any, Optional, List
from uuid import UUID

logger = logging.getLogger(__name__)


class UsageTrackingQueue:
    """Publishes usage events to Redis queue"""

    # Queue name must match what User Service consumer expects
    QUEUE_NAME = "token_usage_queue"

    def __init__(self, redis_url: Optional[str] = None):
        # Default to localhost if not provided (dev/test), but docker-compose should provide it
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client: Optional[redis.Redis] = None

    async def connect(self):
        """Connect to Redis"""
        if not self.redis_client:
            self.redis_client = await redis.from_url(
                self.redis_url,
                decode_responses=True
            )
            logger.info(f"Connected to Redis for usage tracking queue")

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")

    async def _publish(self, event_type: str, payload: Dict[str, Any]) -> bool:
        """Internal helper to publish event"""
        try:
            if not self.redis_client:
                await self.connect()

            job = {
                "event_type": event_type,
                "payload": payload
            }

            # Push to Redis LIST (right side)
            if self.redis_client:
                await self.redis_client.rpush(
                    self.QUEUE_NAME,
                    json.dumps(job)
                )
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to publish {event_type} to usage queue: {e}")
            return False

    async def publish_token_usage(
        self,
        user_id: str,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        session_id: Optional[str] = None,
        cost_usd: Optional[float] = None,
    ) -> bool:
        """Publish token usage event"""
        payload = {
            "user_id": user_id,
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "session_id": session_id,
            "cost_usd": cost_usd
        }
        return await self._publish("token_usage", payload)

    async def publish_message_record(
        self,
        user_id: str,
        conversation_id: Optional[str] = None,
        topic_category: Optional[str] = None,
        topic_tier: Optional[int] = None,
        safety_incident: Optional[str] = None,
    ) -> bool:
        """Publish message record event"""
        payload = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "topic_category": topic_category,
            "topic_tier": topic_tier,
            "safety_incident": safety_incident
        }
        return await self._publish("message_record", payload)

    async def publish_session_record(
        self,
        user_id: str,
        session_id: str,
        duration_seconds: int,
        topic_categories: Optional[List[str]] = None,
    ) -> bool:
        """Publish session record event"""
        payload = {
            "user_id": user_id,
            "session_id": session_id,
            "duration_seconds": duration_seconds,
            "topic_categories": topic_categories
        }
        return await self._publish("session_record", payload)


# Global instance
_usage_queue: Optional[UsageTrackingQueue] = None


async def get_usage_tracking_queue() -> UsageTrackingQueue:
    """Get or create global queue instance"""
    global _usage_queue
    if _usage_queue is None:
        _usage_queue = UsageTrackingQueue()
        await _usage_queue.connect()
    return _usage_queue
