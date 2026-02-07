"""
API Request and Response Models for Message Service
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID


# Conversation Models

class CreateConversationRequest(BaseModel):
    """Request model for creating a conversation"""
    teen_id: UUID
    title: Optional[str] = None

    model_config = {"json_schema_extra": {"example": {
        "teen_id": "550e8400-e29b-41d4-a716-446655440000",
        "title": "Homework Help - Math"
    }}}


class UpdateConversationRequest(BaseModel):
    """Request model for updating a conversation"""
    title: Optional[str] = None
    status: Optional[str] = None


class ConversationResponse(BaseModel):
    """Response model for conversation"""
    id: UUID
    teen_id: UUID
    title: str
    status: str
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime] = None
    message_count: int
    metadata: dict


# Message Models

class CreateMessageRequest(BaseModel):
    """Request model for creating a message"""
    role: str = Field(..., description="user or assistant")
    content: str = Field(..., min_length=1)
    # Optional safety metadata from Topic Classifier
    topic_tier: Optional[int] = Field(None, ge=1, le=4, description="Safety tier (1-4)")
    topic_categories: List[str] = Field(default_factory=list, description="Detected topic categories")
    
    # Optional Usage/Token Metadata (for Assistant messages)
    provider: Optional[str] = Field(None, description="LLM provider (e.g., openai)")
    model: Optional[str] = Field(None, description="Model name (e.g., gpt-4o)")
    input_tokens: Optional[int] = Field(None, ge=0)
    output_tokens: Optional[int] = Field(None, ge=0)
    total_tokens: Optional[int] = Field(None, ge=0)
    cost_usd: Optional[float] = Field(None, ge=0)

    model_config = {"json_schema_extra": {"example": {
        "role": "assistant",
        "content": "Sure, I can help with algebra!",
        "topic_tier": 1,
        "topic_categories": ["Math", "Homework"],
        "provider": "openai",
        "model": "gpt-4o",
        "total_tokens": 150
    }}}


class MessageResponse(BaseModel):
    """Response model for message"""
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    topic_tier: Optional[str] = None
    topic_categories: List[str] = []
    safety_flags: dict = {}
    created_at: datetime
    metadata: dict


class ConversationWithMessagesResponse(BaseModel):
    """Response model for conversation with messages"""
    conversation: ConversationResponse
    messages: List[MessageResponse]
    total_messages: int


class ErrorResponse(BaseModel):
    """Standard error response"""
    detail: str
