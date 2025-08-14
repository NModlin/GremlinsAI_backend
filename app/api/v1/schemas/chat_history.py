# app/api/v1/schemas/chat_history.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class MessageBase(BaseModel):
    """Base schema for messages."""
    role: str = Field(..., description="Role of the message sender (user, assistant, system)")
    content: str = Field(..., description="Content of the message")
    tool_calls: Optional[Dict[str, Any]] = Field(None, description="Tool calls made in this message")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class MessageCreate(MessageBase):
    """Schema for creating a new message."""
    conversation_id: str = Field(..., description="ID of the conversation this message belongs to")


class MessageResponse(MessageBase):
    """Schema for message responses."""
    id: str = Field(..., description="Unique identifier for the message")
    conversation_id: str = Field(..., description="ID of the conversation this message belongs to")
    created_at: datetime = Field(..., description="Timestamp when the message was created")

    class Config:
        from_attributes = True


class ConversationBase(BaseModel):
    """Base schema for conversations."""
    title: Optional[str] = Field(None, description="Title of the conversation")


class ConversationCreate(ConversationBase):
    """Schema for creating a new conversation."""
    initial_message: Optional[str] = Field(None, description="Initial message to start the conversation")


class ConversationUpdate(BaseModel):
    """Schema for updating a conversation."""
    title: Optional[str] = Field(None, description="New title for the conversation")
    is_active: Optional[bool] = Field(None, description="Whether the conversation is active")


class ConversationResponse(ConversationBase):
    """Schema for conversation responses."""
    id: str = Field(..., description="Unique identifier for the conversation")
    title: str = Field(..., description="Title of the conversation")
    created_at: datetime = Field(..., description="Timestamp when the conversation was created")
    updated_at: datetime = Field(..., description="Timestamp when the conversation was last updated")
    is_active: bool = Field(..., description="Whether the conversation is active")
    messages: Optional[List[MessageResponse]] = Field(None, description="Messages in the conversation")

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    """Schema for conversation list responses."""
    conversations: List[ConversationResponse] = Field(..., description="List of conversations")
    total: int = Field(..., description="Total number of conversations")
    limit: int = Field(..., description="Number of conversations per page")
    offset: int = Field(..., description="Offset for pagination")


class MessageListResponse(BaseModel):
    """Schema for message list responses."""
    messages: List[MessageResponse] = Field(..., description="List of messages")
    conversation_id: str = Field(..., description="ID of the conversation")
    total: int = Field(..., description="Total number of messages")
    limit: int = Field(..., description="Number of messages per page")
    offset: int = Field(..., description="Offset for pagination")


class ConversationContextResponse(BaseModel):
    """Schema for conversation context responses."""
    conversation_id: str = Field(..., description="ID of the conversation")
    context: List[Dict[str, Any]] = Field(..., description="Conversation context for AI agents")
    message_count: int = Field(..., description="Number of messages in the context")


# Agent-specific schemas for integration
class AgentConversationRequest(BaseModel):
    """Schema for agent requests with conversation context."""
    input: str = Field(..., description="User input/query")
    conversation_id: Optional[str] = Field(None, description="ID of existing conversation")
    save_conversation: bool = Field(True, description="Whether to save this interaction")


class AgentConversationResponse(BaseModel):
    """Schema for agent responses with conversation context."""
    output: Dict[str, Any] = Field(..., description="Agent response")
    conversation_id: str = Field(..., description="ID of the conversation")
    message_id: str = Field(..., description="ID of the response message")
    context_used: bool = Field(..., description="Whether conversation context was used")
