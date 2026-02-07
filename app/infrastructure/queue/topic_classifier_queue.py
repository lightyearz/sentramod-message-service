"""
Redis Queue Publisher for Topic Classification
Publishes messages to Redis queue for async classification by Topic Classifier Service
"""
import redis.asyncio as redis
import json
import logging
from typing import Dict, Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class TopicClassifierQueue:
    """Publishes messages to Redis queue for topic classification"""

    QUEUE_NAME = "topic_classification_queue"

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None

    async def connect(self):
        """Connect to Redis"""
        if not self.redis_client:
            self.redis_client = await redis.from_url(
                self.redis_url,
                decode_responses=True
            )
            logger.info(f"Connected to Redis for topic classification queue")

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")

    async def publish_for_classification(
        self,
        message_id: UUID,
        conversation_id: UUID,
        teen_id: UUID,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Publish a message to the classification queue

        Args:
            message_id: UUID of the message
            conversation_id: UUID of the conversation
            teen_id: UUID of the teen
            content: Message content to classify
            metadata: Optional additional metadata

        Returns:
            True if published successfully
        """
        try:
            if not self.redis_client:
                await self.connect()

            job = {
                "message_id": str(message_id),
                "conversation_id": str(conversation_id),
                "teen_id": str(teen_id),
                "content": content,
                "metadata": metadata or {}
            }

            # Push to Redis LIST (right side)
            # Workers will BLPOP from left side (FIFO queue)
            await self.redis_client.rpush(
                self.QUEUE_NAME,
                json.dumps(job)
            )

            logger.info(f"Published message {message_id} to classification queue")
            return True

        except Exception as e:
            logger.error(f"Failed to publish to classification queue: {e}")
            return False


# Global instance
_queue: Optional[TopicClassifierQueue] = None


async def get_topic_classifier_queue() -> TopicClassifierQueue:
    """Get or create global queue instance"""
    global _queue
    if _queue is None:
        _queue = TopicClassifierQueue()
        await _queue.connect()
    return _queue
