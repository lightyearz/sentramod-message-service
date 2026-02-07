"""
API Routes for Message Service
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models import (
    CreateConversationRequest,
    UpdateConversationRequest,
    ConversationResponse,
    CreateMessageRequest,
    MessageResponse,
    ConversationWithMessagesResponse,
    ErrorResponse,
)
from app.domain.entities.conversation import Conversation, ConversationStatus
from app.domain.entities.message import Message, MessageRole, TopicTier
from app.domain.repositories.conversation_repository import IConversationRepository
from app.domain.repositories.message_repository import IMessageRepository
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.conversation_repository_impl import ConversationRepositoryImpl
from app.infrastructure.persistence.message_repository_impl import MessageRepositoryImpl
from app.infrastructure.queue.topic_classifier_queue import get_topic_classifier_queue
from app.infrastructure.usage_tracking import get_usage_tracking_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Conversations & Messages"])


# Dependency injection
def get_conversation_repository(db: AsyncSession = Depends(get_db)) -> IConversationRepository:
    """Get conversation repository instance"""
    return ConversationRepositoryImpl(db)


def get_message_repository(db: AsyncSession = Depends(get_db)) -> IMessageRepository:
    """Get message repository instance"""
    return MessageRepositoryImpl(db)


# Conversation Endpoints

@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation",
)
async def create_conversation(
    request_data: CreateConversationRequest,
    conv_repo: IConversationRepository = Depends(get_conversation_repository),
):
    """Create a new conversation for a teen"""
    try:
        conversation = Conversation(
            teen_id=request_data.teen_id,
            title=request_data.title or "New Conversation",
        )

        conversation = await conv_repo.create(conversation)

        return ConversationResponse(**conversation.to_dict())

    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    summary="Get conversation by ID",
)
async def get_conversation(
    conversation_id: UUID,
    conv_repo: IConversationRepository = Depends(get_conversation_repository),
):
    """Get a conversation by ID"""
    try:
        conversation = await conv_repo.get_by_id(conversation_id)

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return ConversationResponse(**conversation.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/teens/{teen_id}/conversations",
    response_model=List[ConversationResponse],
    summary="Get conversations for a teen",
)
async def get_teen_conversations(
    teen_id: UUID,
    status: str = "active",
    limit: int = 50,
    offset: int = 0,
    conv_repo: IConversationRepository = Depends(get_conversation_repository),
):
    """Get all conversations for a teen"""
    try:
        conv_status = ConversationStatus(status) if status else None
        conversations = await conv_repo.get_by_teen_id(
            teen_id, status=conv_status, limit=limit, offset=offset
        )

        return [ConversationResponse(**conv.to_dict()) for conv in conversations]

    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    except Exception as e:
        logger.error(f"Error getting teen conversations: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    summary="Update conversation",
)
async def update_conversation(
    conversation_id: UUID,
    request_data: UpdateConversationRequest,
    conv_repo: IConversationRepository = Depends(get_conversation_repository),
):
    """Update a conversation"""
    try:
        conversation = await conv_repo.get_by_id(conversation_id)

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if request_data.title:
            conversation.set_title(request_data.title)

        if request_data.status:
            if request_data.status == "archived":
                conversation.archive()
            elif request_data.status == "active":
                conversation.restore()
            elif request_data.status == "deleted":
                conversation.delete()

        conversation = await conv_repo.update(conversation)

        return ConversationResponse(**conversation.to_dict())

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete conversation",
)
async def delete_conversation(
    conversation_id: UUID,
    conv_repo: IConversationRepository = Depends(get_conversation_repository),
):
    """Delete a conversation (hard delete)"""
    try:
        deleted = await conv_repo.delete(conversation_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Conversation not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Message Endpoints

@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add message to conversation",
)
async def create_message(
    conversation_id: UUID,
    request_data: CreateMessageRequest,
    conv_repo: IConversationRepository = Depends(get_conversation_repository),
    msg_repo: IMessageRepository = Depends(get_message_repository),
):
    """Add a new message to a conversation"""
    try:
        # Verify conversation exists and is active
        conversation = await conv_repo.get_by_id(conversation_id)

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if not conversation.can_add_messages():
            raise HTTPException(
                status_code=400,
                detail="Cannot add messages to this conversation"
            )

        # Enforce daily message limit for user messages (defense-in-depth)
        if request_data.role == "user":
            try:
                usage_service = get_usage_tracking_service()
                limit_check = await usage_service.check_daily_message_limit(
                    user_id=str(conversation.teen_id),
                )
                if not limit_check.get("allowed", True):
                    raise HTTPException(
                        status_code=429,
                        detail=f"Daily message limit reached ({limit_check['messages_sent']}/{limit_check['messages_limit']})",
                    )
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"Daily limit check failed for teen={conversation.teen_id}: {e}")

        # Convert topic_tier integer to enum if provided
        topic_tier_enum = None
        if request_data.topic_tier is not None:
            tier_map = {1: TopicTier.TIER_1, 2: TopicTier.TIER_2, 3: TopicTier.TIER_3, 4: TopicTier.TIER_4}
            topic_tier_enum = tier_map.get(request_data.topic_tier)

        # Create message with safety metadata
        message = Message(
            conversation_id=conversation_id,
            role=MessageRole(request_data.role),
            content=request_data.content,
            topic_tier=topic_tier_enum,
            topic_categories=request_data.topic_categories or [],
        )

        message = await msg_repo.create(message)

        # Update conversation
        conversation.add_message()
        await conv_repo.update(conversation)

        # Publish to Redis queue for async topic classification
        # Only classify user messages (not assistant responses)
        if message.role == MessageRole.USER:
            try:
                queue = await get_topic_classifier_queue()
                await queue.publish_for_classification(
                    message_id=message.id,
                    conversation_id=conversation_id,
                    teen_id=conversation.teen_id,
                    content=message.content
                )
            except Exception as e:
                # Log error but don't fail the request
                # Classification will happen async
                logger.error(f"Failed to publish message for classification: {e}")

            # Track usage for teen messages (async, non-blocking)
            try:
                usage_service = get_usage_tracking_service()
                await usage_service.record_message(
                    user_id=str(conversation.teen_id),
                    conversation_id=str(conversation_id),
                    topic_category=request_data.topic_categories[0] if request_data.topic_categories else None,
                    topic_tier=request_data.topic_tier,
                )
            except Exception as e:
                # Log error but don't fail the request
                logger.error(f"Failed to track usage: {e}")

        # Track usage for ASSISTANT messages (Token Usage)
        elif message.role == MessageRole.ASSISTANT and request_data.total_tokens:
            try:
                usage_service = get_usage_tracking_service()
                await usage_service.record_token_usage(
                    user_id=str(conversation.teen_id),
                    session_id=None,  # Not tracked here yet
                    provider=request_data.provider or "unknown",
                    model=request_data.model or "unknown",
                    input_tokens=request_data.input_tokens or 0,
                    output_tokens=request_data.output_tokens or 0,
                    total_tokens=request_data.total_tokens,
                    cost_usd=request_data.cost_usd,
                )
            except Exception as e:
                logger.error(f"Failed to track token usage: {e}")

        return MessageResponse(**message.to_dict())

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating message: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=List[MessageResponse],
    summary="Get conversation messages",
)
async def get_conversation_messages(
    conversation_id: UUID,
    limit: int = 100,
    offset: int = 0,
    msg_repo: IMessageRepository = Depends(get_message_repository),
):
    """Get all messages in a conversation"""
    try:
        messages = await msg_repo.get_by_conversation_id(
            conversation_id, limit=limit, offset=offset
        )

        return [MessageResponse(**msg.to_dict()) for msg in messages]

    except Exception as e:
        logger.error(f"Error getting messages: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/conversations/{conversation_id}/with-messages",
    response_model=ConversationWithMessagesResponse,
    summary="Get conversation with messages",
)
async def get_conversation_with_messages(
    conversation_id: UUID,
    limit: int = 100,
    offset: int = 0,
    conv_repo: IConversationRepository = Depends(get_conversation_repository),
    msg_repo: IMessageRepository = Depends(get_message_repository),
):
    """Get conversation with its messages"""
    try:
        conversation = await conv_repo.get_by_id(conversation_id)

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        messages = await msg_repo.get_by_conversation_id(
            conversation_id, limit=limit, offset=offset
        )

        total_messages = await msg_repo.count_by_conversation_id(conversation_id)

        return ConversationWithMessagesResponse(
            conversation=ConversationResponse(**conversation.to_dict()),
            messages=[MessageResponse(**msg.to_dict()) for msg in messages],
            total_messages=total_messages,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation with messages: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/messages/{message_id}",
    response_model=MessageResponse,
    summary="Get message by ID",
)
async def get_message(
    message_id: UUID,
    msg_repo: IMessageRepository = Depends(get_message_repository),
):
    """Get a message by ID"""
    try:
        message = await msg_repo.get_by_id(message_id)

        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        return MessageResponse(**message.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting message: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
