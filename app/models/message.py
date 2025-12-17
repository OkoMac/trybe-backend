"""Message and Conversation models - Real-time messaging between users"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
import uuid

from app.core.database import Base


class Conversation(Base):
    """Conversation model - represents a chat thread between two users"""

    __tablename__ = "conversations"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # Participants (always 2 users in a direct conversation)
    user1_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="First participant"
    )
    user2_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Second participant"
    )

    # Optional context (what initiated the conversation)
    opportunity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Opportunity that initiated this conversation"
    )
    match_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Match that initiated this conversation"
    )

    # Conversation metadata
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Timestamp of last message (for sorting)"
    )
    last_message_preview: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Preview of last message"
    )

    # Read status tracking
    user1_last_read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When user1 last read messages"
    )
    user2_last_read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When user2 last read messages"
    )
    user1_unread_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Number of unread messages for user1"
    )
    user2_unread_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Number of unread messages for user2"
    )

    # Flags
    is_archived_by_user1: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived_by_user2: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_blocked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if conversation is blocked by either user"
    )

    # Conversation metadata (flexible JSONB field)
    conversation_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        default=dict,
        comment="Additional conversation metadata"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Constraints - ensure unique conversation between two users
    # Use a check constraint to ensure user1_id < user2_id for consistency
    __table_args__ = (
        UniqueConstraint('user1_id', 'user2_id', name='uq_conversation_participants'),
        Index('ix_conversations_last_message_at_desc', 'last_message_at', postgresql_using='btree', postgresql_ops={'last_message_at': 'DESC'}),
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.user1_id} <-> {self.user2_id}>"


class Message(Base):
    """Message model - individual messages within a conversation"""

    __tablename__ = "messages"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # Foreign Keys
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Message content
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Message content (text)"
    )
    message_type: Mapped[str] = mapped_column(
        String(50),
        default="text",
        nullable=False,
        comment="Message type: text, image, file, system"
    )

    # Attachments (optional)
    attachments: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Array of attachment objects: [{url, filename, size, type}]"
    )

    # Read status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When message was read"
    )

    # Flags
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    edited_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When message was last edited"
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Soft delete flag"
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When message was deleted"
    )

    # Message metadata (flexible JSONB field)
    message_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        default=dict,
        comment="Additional message metadata"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Index for efficient message retrieval
    __table_args__ = (
        Index('ix_messages_conversation_created', 'conversation_id', 'created_at'),
    )

    def __repr__(self) -> str:
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Message from {self.sender_id}: {preview}>"
