"""
Message Repository Interface

Defines the contract for message persistence operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from app.domain.entities.message import Message, MessageRole


class IMessageRepository(ABC):
    """Interface for message persistence operations"""

    @abstractmethod
    async def create(self, message: Message) -> Message:
        """
        Create a new message

        Args:
            message: The message to create

        Returns:
            The created message with generated ID
        """
        pass

    @abstractmethod
    async def get_by_id(self, message_id: UUID) -> Optional[Message]:
        """
        Get a message by ID

        Args:
            message_id: The message ID

        Returns:
            The message if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_by_conversation_id(
        self,
        conversation_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Message]:
        """
        Get messages for a conversation

        Args:
            conversation_id: The conversation ID
            limit: Maximum number of messages to return
            offset: Number of messages to skip

        Returns:
            List of messages ordered by created_at ASC
        """
        pass

    @abstractmethod
    async def count_by_conversation_id(self, conversation_id: UUID) -> int:
        """
        Count messages in a conversation

        Args:
            conversation_id: The conversation ID

        Returns:
            Number of messages
        """
        pass

    @abstractmethod
    async def delete(self, message_id: UUID) -> bool:
        """
        Delete a message (hard delete)

        Args:
            message_id: The message ID

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def delete_by_conversation_id(self, conversation_id: UUID) -> int:
        """
        Delete all messages in a conversation

        Args:
            conversation_id: The conversation ID

        Returns:
            Number of messages deleted
        """
        pass
