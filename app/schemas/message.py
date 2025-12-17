"""Message and Conversation schemas - Pydantic models for validation"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import uuid


# ============================================================================
# Attachment Schemas
# ============================================================================

class Attachment(BaseModel):
    """Attachment object schema"""
    url: str
    filename: str
    size: int  # in bytes
    type: str  # mime type


# ============================================================================
# Message Schemas
# ============================================================================

class MessageCreate(BaseModel):
    """Schema for creating a new message"""
    recipient_id: uuid.UUID
    content: str = Field(..., min_length=1, max_length=5000)
    message_type: str = Field(default="text", pattern="^(text|image|file|system)$")
    attachments: Optional[List[Attachment]] = None

    # Optional: specify conversation_id to add to existing conversation
    # If not provided, will find or create conversation with recipient
    conversation_id: Optional[uuid.UUID] = None


class MessageUpdate(BaseModel):
    """Schema for updating a message (editing)"""
    content: str = Field(..., min_length=1, max_length=5000)


class MessageResponse(BaseModel):
    """Schema for message response"""
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    recipient_id: uuid.UUID
    content: str
    message_type: str
    attachments: Optional[List[dict]] = None
    is_read: bool
    read_at: Optional[datetime] = None
    is_edited: bool
    edited_at: Optional[datetime] = None
    is_deleted: bool
    deleted_at: Optional[datetime] = None
    message_metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============================================================================
# Conversation Schemas
# ============================================================================

class ConversationCreate(BaseModel):
    """Schema for creating a new conversation"""
    participant_id: uuid.UUID  # The other user in the conversation
    opportunity_id: Optional[uuid.UUID] = None
    match_id: Optional[uuid.UUID] = None
    initial_message: Optional[str] = Field(None, min_length=1, max_length=5000)


class ConversationResponse(BaseModel):
    """Schema for conversation response"""
    id: uuid.UUID
    user1_id: uuid.UUID
    user2_id: uuid.UUID
    opportunity_id: Optional[uuid.UUID] = None
    match_id: Optional[uuid.UUID] = None
    last_message_at: Optional[datetime] = None
    last_message_preview: Optional[str] = None
    user1_last_read_at: Optional[datetime] = None
    user2_last_read_at: Optional[datetime] = None
    user1_unread_count: int
    user2_unread_count: int
    is_archived_by_user1: bool
    is_archived_by_user2: bool
    is_blocked: bool
    conversation_metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationWithParticipant(BaseModel):
    """Conversation response with participant details"""
    id: uuid.UUID
    participant_id: uuid.UUID  # The other user's ID
    participant_name: str  # The other user's full name
    participant_avatar: Optional[str] = None
    participant_user_type: str
    opportunity_id: Optional[uuid.UUID] = None
    match_id: Optional[uuid.UUID] = None
    last_message_at: Optional[datetime] = None
    last_message_preview: Optional[str] = None
    unread_count: int  # Current user's unread count
    is_archived: bool  # Current user's archive status
    is_blocked: bool
    created_at: datetime


class ConversationWithMessages(BaseModel):
    """Conversation with messages"""
    conversation: ConversationResponse
    messages: List[MessageResponse]
    total_messages: int


# ============================================================================
# WebSocket Schemas
# ============================================================================

class WSMessageEvent(BaseModel):
    """WebSocket message event"""
    event: str  # "new_message", "message_read", "typing", "user_online", "user_offline"
    data: dict


class TypingIndicator(BaseModel):
    """Typing indicator event"""
    conversation_id: uuid.UUID
    user_id: uuid.UUID
    is_typing: bool


class MessageReadEvent(BaseModel):
    """Message read event"""
    message_id: uuid.UUID
    conversation_id: uuid.UUID
    read_at: datetime


# ============================================================================
# Pagination Schemas
# ============================================================================

class ConversationList(BaseModel):
    """Paginated list of conversations"""
    items: List[ConversationWithParticipant]
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageList(BaseModel):
    """Paginated list of messages"""
    items: List[MessageResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
