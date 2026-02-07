"""
Usage Tracking Integration for Message Service.

Tracks all teen actions on the platform by calling User Service usage tracking APIs.
"""

import logging
import os
from typing import Optional, List
from uuid import UUID

import httpx

logger = logging.getLogger(__name__)

# User Service URL from environment
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8001")


class UsageTrackingService:
    """
    Service for tracking teen usage metrics.

    Integrates with User Service /api/v1/usage endpoints to track:
    - Messages sent
    - Topics discussed
    - Session duration
    - Safety incidents
    """

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
        Record LLM token usage.

        Args:
            user_id: User ID
            provider: LLM provider (e.g., openai)
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count
            total_tokens: Total token count
            session_id: Session ID (optional)
            cost_usd: Estimated cost (optional)

        Returns:
            True if recorded, False otherwise
        """
        try:
            payload = {
                "user_id": user_id,
                "provider": provider,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
            }
            if session_id:
                payload["session_id"] = session_id
            if cost_usd is not None:
                payload["cost_usd"] = cost_usd

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    self.record_token_usage_url,
                    json=payload,
                )

                if response.status_code in [200, 201]:
                    # verbose logging only for debug
                    # logger.debug(f"💰 Tokens tracked: user={user_id}, total={total_tokens}")
                    return True
                else:
                    logger.warning(
                        f"⚠️ Token tracking failed: status={response.status_code}, user={user_id}"
                    )
                    return False

        except Exception as e:
            logger.error(f"❌ Token tracking error for user={user_id}: {e}")
            return False

    def __init__(self, user_service_url: str = USER_SERVICE_URL):
        self.user_service_url = user_service_url
        self.record_message_url = f"{user_service_url}/api/v1/usage/record-message"
        self.record_session_url = f"{user_service_url}/api/v1/usage/record-session"
        self.record_token_usage_url = f"{user_service_url}/api/v1/usage/record-token-usage"

    async def check_daily_message_limit(
        self,
        user_id: str,
        teen_age: Optional[int] = None,
    ) -> dict:
        """
        Check if the teen has reached their daily message limit.

        Returns:
            {"allowed": bool, "messages_sent": int, "messages_limit": int}
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
        Record a message sent by the teen.

        Args:
            user_id: Teen's user ID
            conversation_id: Conversation ID (optional)
            topic_category: Topic category from classifier (optional)
            topic_tier: Topic tier 1-4 (optional)
            safety_incident: Safety incident type if any (optional)

        Returns:
            True if successfully recorded, False otherwise
        """
        try:
            payload = {"user_id": user_id}

            if conversation_id:
                payload["conversation_id"] = conversation_id
            if topic_category:
                payload["topic_category"] = topic_category
            if topic_tier:
                payload["topic_tier"] = topic_tier
            if safety_incident:
                payload["safety_incident"] = safety_incident

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    self.record_message_url,
                    json=payload,
                )

                if response.status_code in [200, 201]:
                    logger.info(
                        f"📊 Usage tracked: user={user_id}, topic={topic_category}, tier={topic_tier}"
                    )
                    return True
                else:
                    logger.warning(
                        f"⚠️ Usage tracking failed: status={response.status_code}, user={user_id}"
                    )
                    return False

        except httpx.TimeoutException:
            logger.error(f"⏱️ Usage tracking timeout for user={user_id}")
            return False
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
        Record a completed session.

        Args:
            user_id: Teen's user ID
            session_id: Session ID
            duration_seconds: Session duration in seconds
            topic_categories: List of topics discussed (optional)

        Returns:
            True if successfully recorded, False otherwise
        """
        try:
            payload = {
                "user_id": user_id,
                "session_id": session_id,
                "duration_seconds": duration_seconds,
            }

            if topic_categories:
                payload["topic_categories"] = topic_categories

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    self.record_session_url,
                    json=payload,
                )

                if response.status_code in [200, 201]:
                    logger.info(
                        f"📊 Session tracked: user={user_id}, session={session_id}, duration={duration_seconds}s"
                    )
                    return True
                else:
                    logger.warning(
                        f"⚠️ Session tracking failed: status={response.status_code}, user={user_id}"
                    )
                    return False

        except httpx.TimeoutException:
            logger.error(f"⏱️ Session tracking timeout for user={user_id}")
            return False
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
