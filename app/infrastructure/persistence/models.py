"""
SQLAlchemy Models for Message Service

Database models for conversation and message persistence.
"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, JSON, Enum as SQLEnum, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid

from app.domain.entities.conversation import ConversationStatus
from app.domain.entities.message import MessageRole, TopicTier

Base = declarative_base()


class ConversationModel(Base):
    """SQLAlchemy model for conversations"""

    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    teen_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String(255), nullable=False, default="New Conversation")
    status = Column(
        SQLEnum(ConversationStatus, name="conversation_status"),
        default=ConversationStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_message_at = Column(DateTime, nullable=True, index=True)
    message_count = Column(Integer, default=0, nullable=False)
    meta_data = Column(JSON, default=dict, nullable=False)

    # Relationship to messages
    messages = relationship("MessageModel", back_populates="conversation", cascade="all, delete-orphan")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_conversations_teen_status", "teen_id", "status"),
        Index("idx_conversations_teen_last_message", "teen_id", "last_message_at"),
    )

    def to_entity(self):
        """Convert model to domain entity"""
        from app.domain.entities.conversation import Conversation

        return Conversation(
            id=self.id,
            teen_id=self.teen_id,
            title=self.title,
            status=self.status,
            created_at=self.created_at,
            updated_at=self.updated_at,
            last_message_at=self.last_message_at,
            message_count=self.message_count,
            metadata=self.meta_data or {},
        )

    @classmethod
    def from_entity(cls, entity):
        """Create model from domain entity"""
        return cls(
            id=entity.id,
            teen_id=entity.teen_id,
            title=entity.title,
            status=entity.status,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            last_message_at=entity.last_message_at,
            message_count=entity.message_count,
            meta_data=entity.metadata,
        )


class MessageModel(Base):
    """SQLAlchemy model for messages"""

    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(
        SQLEnum(MessageRole, name="message_role"),
        nullable=False,
    )
    content = Column(Text, nullable=False)
    topic_tier = Column(
        SQLEnum(TopicTier, name="topic_tier"),
        nullable=True,
        index=True,
    )
    topic_categories = Column(JSON, default=list, nullable=False)
    safety_flags = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    meta_data = Column(JSON, default=dict, nullable=False)

    # Relationship to conversation
    conversation = relationship("ConversationModel", back_populates="messages")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_messages_conversation_created", "conversation_id", "created_at"),
        Index("idx_messages_role", "role"),
    )

    def to_entity(self):
        """Convert model to domain entity"""
        from app.domain.entities.message import Message

        return Message(
            id=self.id,
            conversation_id=self.conversation_id,
            role=self.role,
            content=self.content,
            topic_tier=self.topic_tier,
            topic_categories=self.topic_categories or [],
            safety_flags=self.safety_flags or {},
            created_at=self.created_at,
            metadata=self.meta_data or {},
        )

    @classmethod
    def from_entity(cls, entity):
        """Create model from domain entity"""
        return cls(
            id=entity.id,
            conversation_id=entity.conversation_id,
            role=entity.role,
            content=entity.content,
            topic_tier=entity.topic_tier,
            topic_categories=entity.topic_categories,
            safety_flags=entity.safety_flags,
            created_at=entity.created_at,
            meta_data=entity.metadata,
        )
