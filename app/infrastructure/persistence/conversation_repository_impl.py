"""
Conversation Repository Implementation

PostgreSQL implementation of the conversation repository.
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.conversation import Conversation, ConversationStatus
from app.domain.repositories.conversation_repository import IConversationRepository
from app.infrastructure.persistence.models import ConversationModel


class ConversationRepositoryImpl(IConversationRepository):
    """PostgreSQL implementation of conversation repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, conversation: Conversation) -> Conversation:
        """Create a new conversation"""
        model = ConversationModel.from_entity(conversation)
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return model.to_entity()

    async def get_by_id(self, conversation_id: UUID) -> Optional[Conversation]:
        """Get a conversation by ID"""
        result = await self.session.execute(
            select(ConversationModel).where(ConversationModel.id == conversation_id)
        )
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None

    async def get_by_teen_id(
        self,
        teen_id: UUID,
        status: Optional[ConversationStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Conversation]:
        """Get conversations for a teen"""
        query = select(ConversationModel).where(ConversationModel.teen_id == teen_id)

        if status:
            query = query.where(ConversationModel.status == status)

        query = query.order_by(ConversationModel.last_message_at.desc().nulls_last(), ConversationModel.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        models = result.scalars().all()
        return [model.to_entity() for model in models]

    async def update(self, conversation: Conversation) -> Conversation:
        """Update a conversation"""
        result = await self.session.execute(
            select(ConversationModel).where(ConversationModel.id == conversation.id)
        )
        model = result.scalar_one_or_none()

        if not model:
            raise ValueError(f"Conversation not found: {conversation.id}")

        # Update fields
        model.title = conversation.title
        model.status = conversation.status
        model.updated_at = conversation.updated_at
        model.last_message_at = conversation.last_message_at
        model.message_count = conversation.message_count
        model.metadata = conversation.metadata

        await self.session.commit()
        await self.session.refresh(model)
        return model.to_entity()

    async def delete(self, conversation_id: UUID) -> bool:
        """Delete a conversation (hard delete)"""
        result = await self.session.execute(
            select(ConversationModel).where(ConversationModel.id == conversation_id)
        )
        model = result.scalar_one_or_none()

        if not model:
            return False

        await self.session.delete(model)
        await self.session.commit()
        return True

    async def count_by_teen_id(
        self,
        teen_id: UUID,
        status: Optional[ConversationStatus] = None,
    ) -> int:
        """Count conversations for a teen"""
        query = select(func.count()).select_from(ConversationModel).where(ConversationModel.teen_id == teen_id)

        if status:
            query = query.where(ConversationModel.status == status)

        result = await self.session.execute(query)
        return result.scalar() or 0
