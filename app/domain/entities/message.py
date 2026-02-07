"""
Message Domain Entity

Represents a single message in a conversation.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import UUID, uuid4


class MessageRole(str, Enum):
    """Message role (who sent the message)"""
    USER = "user"  # Teen's message
    ASSISTANT = "assistant"  # AI's response
    SYSTEM = "system"  # System messages (e.g., "Conversation started")


class TopicTier(str, Enum):
    """Topic safety tier"""
    TIER_1 = "tier_1"  # Green - Always allowed
    TIER_2 = "tier_2"  # Yellow - Needs approval
    TIER_3 = "tier_3"  # Orange - Requires supervision
    TIER_4 = "tier_4"  # Red - Auto-blocked


class Message:
    """
    Message Domain Entity

    Represents a single message in a conversation.

    Attributes:
        id: Unique identifier for the message
        conversation_id: ID of the conversation this message belongs to
        role: Who sent the message (user, assistant, system)
        content: The message content (text)
        topic_tier: Safety tier for this message (if classified)
        topic_categories: List of topic categories detected
        safety_flags: Any safety concerns detected
        created_at: When the message was created
        metadata: Additional message data (JSON)
    """

    def __init__(
        self,
        conversation_id: UUID,
        role: MessageRole,
        content: str,
        id: Optional[UUID] = None,
        topic_tier: Optional[TopicTier] = None,
        topic_categories: Optional[List[str]] = None,
        safety_flags: Optional[dict] = None,
        created_at: Optional[datetime] = None,
        metadata: Optional[dict] = None,
    ):
        self.id = id or uuid4()
        self.conversation_id = conversation_id
        self.role = role
        self.content = content
        self.topic_tier = topic_tier
        self.topic_categories = topic_categories or []
        self.safety_flags = safety_flags or {}
        self.created_at = created_at or datetime.utcnow()
        self.metadata = metadata or {}

    def is_user_message(self) -> bool:
        """Check if this is a user (teen) message"""
        return self.role == MessageRole.USER

    def is_assistant_message(self) -> bool:
        """Check if this is an AI assistant message"""
        return self.role == MessageRole.ASSISTANT

    def is_system_message(self) -> bool:
        """Check if this is a system message"""
        return self.role == MessageRole.SYSTEM

    def is_safe(self) -> bool:
        """
        Check if message is safe (no blocking safety flags)

        Returns:
            True if message is safe or hasn't been classified yet
        """
        if not self.safety_flags:
            return True

        # Check for blocking flags
        if self.safety_flags.get("blocked", False):
            return False

        if self.topic_tier == TopicTier.TIER_4:
            return False

        return True

    def needs_approval(self) -> bool:
        """
        Check if message needs parental approval

        Returns:
            True if message is Tier 2 or Tier 3
        """
        return self.topic_tier in [TopicTier.TIER_2, TopicTier.TIER_3]

    def is_tier_4(self) -> bool:
        """Check if message is Tier 4 (blocked)"""
        return self.topic_tier == TopicTier.TIER_4

    def set_topic_classification(
        self,
        tier: TopicTier,
        categories: List[str],
        confidence: Optional[float] = None,
    ) -> None:
        """
        Set topic classification results

        Args:
            tier: The safety tier assigned
            categories: List of topic categories
            confidence: Classification confidence score
        """
        self.topic_tier = tier
        self.topic_categories = categories

        if confidence is not None:
            self.metadata["classification_confidence"] = confidence

    def add_safety_flag(self, flag_type: str, details: dict) -> None:
        """
        Add a safety flag to this message

        Args:
            flag_type: Type of safety flag (e.g., "pii_detected", "toxicity")
            details: Details about the safety concern
        """
        self.safety_flags[flag_type] = details

    def mark_as_blocked(self, reason: str) -> None:
        """
        Mark message as blocked

        Args:
            reason: Reason why message was blocked
        """
        self.safety_flags["blocked"] = True
        self.safety_flags["block_reason"] = reason
        self.topic_tier = TopicTier.TIER_4

    def get_preview(self, length: int = 50) -> str:
        """
        Get a preview of the message content

        Args:
            length: Maximum length of preview

        Returns:
            Truncated message content
        """
        if len(self.content) <= length:
            return self.content

        return self.content[:length] + "..."

    def to_dict(self) -> dict:
        """Convert entity to dictionary"""
        return {
            "id": str(self.id),
            "conversation_id": str(self.conversation_id),
            "role": self.role.value,
            "content": self.content,
            "topic_tier": self.topic_tier.value if self.topic_tier else None,
            "topic_categories": self.topic_categories,
            "safety_flags": self.safety_flags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata,
        }
