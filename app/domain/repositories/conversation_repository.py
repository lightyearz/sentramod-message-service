"""
Conversation Repository Interface

Defines the contract for conversation persistence operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from app.domain.entities.conversation import Conversation, ConversationStatus


class IConversationRepository(ABC):
    """Interface for conversation persistence operations"""

    @abstractmethod
    async def create(self, conversation: Conversation) -> Conversation:
        """
        Create a new conversation

        Args:
            conversation: The conversation to create

        Returns:
            The created conversation with generated ID
        """
        pass

    @abstractmethod
    async def get_by_id(self, conversation_id: UUID) -> Optional[Conversation]:
        """
        Get a conversation by ID

        Args:
            conversation_id: The conversation ID

        Returns:
            The conversation if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_by_teen_id(
        self,
        teen_id: UUID,
        status: Optional[ConversationStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Conversation]:
        """
        Get conversations for a teen

        Args:
            teen_id: The teen's user ID
            status: Filter by status (optional)
            limit: Maximum number of conversations to return
            offset: Number of conversations to skip

        Returns:
            List of conversations
        """
        pass

    @abstractmethod
    async def update(self, conversation: Conversation) -> Conversation:
        """
        Update a conversation

        Args:
            conversation: The conversation to update

        Returns:
            The updated conversation
        """
        pass

    @abstractmethod
    async def delete(self, conversation_id: UUID) -> bool:
        """
        Delete a conversation (hard delete)

        Args:
            conversation_id: The conversation ID

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def count_by_teen_id(
        self,
        teen_id: UUID,
        status: Optional[ConversationStatus] = None,
    ) -> int:
        """
        Count conversations for a teen

        Args:
            teen_id: The teen's user ID
            status: Filter by status (optional)

        Returns:
            Number of conversations
        """
        pass
