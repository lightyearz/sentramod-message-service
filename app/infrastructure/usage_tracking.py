"""
Usage Tracking Integration for Message Service.

Tracks all teen actions on the platform by:
1. Calculating tokens locally (tiktoken)
2. Publishing events to Redis for async processing by User Service
3. Checking daily limits synchronously via HTTP
"""

import logging
import os
from typing import Optional, List
import httpx
import tiktoken

from app.infrastructure.queue.usage_queue import get_usage_tracking_queue

logger = logging.getLogger(__name__)

# User Service URL from environment (for sync checks)
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8001")


class UsageTrackingService:
    """
    Service for tracking teen usage metrics.
    
    Uses Redis Queue for high-throughput logging (fire-and-forget).
    Uses HTTP for blocking checks (daily limits).
    """

    def __init__(self, user_service_url: str = USER_SERVICE_URL):
        self.user_service_url = user_service_url
        # Token encoding cache
        self._encodings = {}

    def count_tokens(self, text: str, model: str = "gpt-3.5-turbo") -> int:
        """
        Count tokens for a given text and model using tiktoken.
        Falls back to cl100k_base if model not found.
        """
        try:
            if model not in self._encodings:
                try:
                    encoding = tiktoken.encoding_for_model(model)
                except KeyError:
                    # Fallback for unknown models (e.g. claude, gemini)
                    # We use cl100k_base as a reasonable approximation for modern LLMs
                    encoding = tiktoken.get_encoding("cl100k_base")
                self._encodings[model] = encoding
            
            return len(self._encodings[model].encode(text))
        except Exception as e:
            logger.warning(f"Token counting failed: {e}. Defaulting to word count approximation.")
            return int(len(text.split()) * 1.3)  # Rough approximation

    async def record_token_usage(
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
        """
        Record LLM token usage via Redis Queue.
        """
        try:
            queue = await get_usage_tracking_queue()
            return await queue.publish_token_usage(
                user_id=user_id,
                provider=provider,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                session_id=session_id,
                cost_usd=cost_usd,
            )
        except Exception as e:
            logger.error(f"❌ Token tracking error for user={user_id}: {e}")
            return False

    async def check_daily_message_limit(
        self,
        user_id: str,
        teen_age: Optional[int] = None,
    ) -> dict:
        """
        Check if the teen has reached their daily message limit.
        
        This MUST stay synchronous (HTTP) because we need the result 
        to decide whether to block the message.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Get today's usage
                usage_response = await client.get(
                    f"{self.user_service_url}/api/v1/usage/today",
                    params={"user_id": user_id},
                )

                messages_sent = 0
                if usage_response.status_code == 200:
                    messages_sent = usage_response.json().get("messages_sent", 0)

                # Get age-group limit
                messages_limit = 100  # default fallback
                if teen_age:
                    age_response = await client.get(
                        f"{self.user_service_url}/api/v1/age-groups/for-age/{teen_age}"
                    )
                    if age_response.status_code == 200:
                        messages_limit = age_response.json().get("max_daily_messages", 100)

                return {
                    "allowed": messages_sent < messages_limit,
                    "messages_sent": messages_sent,
                    "messages_limit": messages_limit,
                }

        except Exception as e:
            logger.warning(f"⚠️ Daily limit check failed for user={user_id}: {e} — failing open")
            return {"allowed": True, "messages_sent": 0, "messages_limit": 100}

    async def record_message(
        self,
        user_id: str,
        conversation_id: Optional[str] = None,
        topic_category: Optional[str] = None,
        topic_tier: Optional[int] = None,
        safety_incident: Optional[str] = None,
    ) -> bool:
        """
        Record a message sent by the teen via Redis Queue.
        """
        try:
            queue = await get_usage_tracking_queue()
            return await queue.publish_message_record(
                user_id=user_id,
                conversation_id=conversation_id,
                topic_category=topic_category,
                topic_tier=topic_tier,
                safety_incident=safety_incident,
            )
        except Exception as e:
            logger.error(f"❌ Usage tracking error for user={user_id}: {e}")
            return False

    async def record_session(
        self,
        user_id: str,
        session_id: str,
        duration_seconds: int,
        topic_categories: Optional[List[str]] = None,
    ) -> bool:
        """
        Record a completed session via Redis Queue.
        """
        try:
            queue = await get_usage_tracking_queue()
            return await queue.publish_session_record(
                user_id=user_id,
                session_id=session_id,
                duration_seconds=duration_seconds,
                topic_categories=topic_categories,
            )
        except Exception as e:
            logger.error(f"❌ Session tracking error for user={user_id}: {e}")
            return False


# Singleton instance
_usage_tracking_service: Optional[UsageTrackingService] = None


def get_usage_tracking_service() -> UsageTrackingService:
    """Get or create the usage tracking service instance."""
    global _usage_tracking_service
    if _usage_tracking_service is None:
        _usage_tracking_service = UsageTrackingService()
    return _usage_tracking_service
