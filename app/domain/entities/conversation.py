"""
Conversation Domain Entity

Represents a conversation between a teen and the AI assistant.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import UUID, uuid4


class ConversationStatus(str, Enum):
    """Conversation status"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class Conversation:
    """
    Conversation Domain Entity

    Represents a conversation thread between a teen and AI assistant.

    Attributes:
        id: Unique identifier for the conversation
        teen_id: ID of the teen who owns this conversation
        title: Conversation title (auto-generated from first message or custom)
        status: Current status of the conversation
        created_at: When the conversation was created
        updated_at: When the conversation was last modified
        last_message_at: When the last message was sent
        message_count: Total number of messages in conversation
        metadata: Additional conversation data (JSON)
    """

    def __init__(
        self,
        teen_id: UUID,
        id: Optional[UUID] = None,
        title: Optional[str] = None,
        status: ConversationStatus = ConversationStatus.ACTIVE,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        last_message_at: Optional[datetime] = None,
        message_count: int = 0,
        metadata: Optional[dict] = None,
    ):
        self.id = id or uuid4()
        self.teen_id = teen_id
        self.title = title or "New Conversation"
        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.last_message_at = last_message_at
        self.message_count = message_count
        self.metadata = metadata or {}

    def add_message(self) -> None:
        """
        Update conversation when a message is added
        """
        self.message_count += 1
        self.last_message_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def set_title(self, title: str) -> None:
        """
        Set or update the conversation title

        Args:
            title: New title for the conversation
        """
        if not title or len(title.strip()) == 0:
            raise ValueError("Title cannot be empty")

        self.title = title.strip()[:200]  # Limit to 200 characters
        self.updated_at = datetime.utcnow()

    def archive(self) -> None:
        """Archive the conversation"""
        if self.status == ConversationStatus.DELETED:
            raise ValueError("Cannot archive a deleted conversation")

        self.status = ConversationStatus.ARCHIVED
        self.updated_at = datetime.utcnow()

    def restore(self) -> None:
        """Restore an archived conversation"""
        if self.status == ConversationStatus.DELETED:
            raise ValueError("Cannot restore a deleted conversation")

        self.status = ConversationStatus.ACTIVE
        self.updated_at = datetime.utcnow()

    def delete(self) -> None:
        """Soft delete the conversation"""
        self.status = ConversationStatus.DELETED
        self.updated_at = datetime.utcnow()

    def is_active(self) -> bool:
        """Check if conversation is active"""
        return self.status == ConversationStatus.ACTIVE

    def is_archived(self) -> bool:
        """Check if conversation is archived"""
        return self.status == ConversationStatus.ARCHIVED

    def is_deleted(self) -> bool:
        """Check if conversation is deleted"""
        return self.status == ConversationStatus.DELETED

    def can_add_messages(self) -> bool:
        """Check if messages can be added to this conversation"""
        return self.status == ConversationStatus.ACTIVE

    def to_dict(self) -> dict:
        """Convert entity to dictionary"""
        return {
            "id": str(self.id),
            "teen_id": str(self.teen_id),
            "title": self.title,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "message_count": self.message_count,
            "metadata": self.metadata,
        }
