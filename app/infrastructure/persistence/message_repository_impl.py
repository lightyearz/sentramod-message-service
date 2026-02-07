"""
Message Repository Implementation

PostgreSQL implementation of the message repository.
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.message import Message
from app.domain.repositories.message_repository import IMessageRepository
from app.infrastructure.persistence.models import MessageModel


class MessageRepositoryImpl(IMessageRepository):
    """PostgreSQL implementation of message repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, message: Message) -> Message:
        """Create a new message"""
        model = MessageModel.from_entity(message)
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return model.to_entity()

    async def get_by_id(self, message_id: UUID) -> Optional[Message]:
        """Get a message by ID"""
        result = await self.session.execute(
            select(MessageModel).where(MessageModel.id == message_id)
        )
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None

    async def get_by_conversation_id(
        self,
        conversation_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Message]:
        """Get messages for a conversation"""
        query = (
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            .order_by(MessageModel.created_at.asc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(query)
        models = result.scalars().all()
        return [model.to_entity() for model in models]

    async def count_by_conversation_id(self, conversation_id: UUID) -> int:
        """Count messages in a conversation"""
        result = await self.session.execute(
            select(func.count())
            .select_from(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
        )
        return result.scalar() or 0

    async def delete(self, message_id: UUID) -> bool:
        """Delete a message (hard delete)"""
        result = await self.session.execute(
            select(MessageModel).where(MessageModel.id == message_id)
        )
        model = result.scalar_one_or_none()

        if not model:
            return False

        await self.session.delete(model)
        await self.session.commit()
        return True

    async def delete_by_conversation_id(self, conversation_id: UUID) -> int:
        """Delete all messages in a conversation"""
        result = await self.session.execute(
            delete(MessageModel).where(MessageModel.conversation_id == conversation_id)
        )
        await self.session.commit()
        return result.rowcount
