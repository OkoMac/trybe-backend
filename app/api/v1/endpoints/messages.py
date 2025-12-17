"""Message endpoints - Real-time messaging with WebSocket and REST APIs"""

import json
import logging
from datetime import datetime
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func, desc
from sqlalchemy.orm import selectinload
import uuid

from app.core.database import get_db
from app.core.websocket import manager
from app.models.message import Conversation, Message
from app.models.user import User
from app.schemas.message import (
    MessageCreate,
    MessageUpdate,
    MessageResponse,
    ConversationCreate,
    ConversationResponse,
    ConversationWithParticipant,
    ConversationList,
    MessageList,
    TypingIndicator,
    MessageReadEvent
)
from app.api.deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# Helper Functions
# ============================================================================

async def get_or_create_conversation(
    db: AsyncSession,
    user1_id: uuid.UUID,
    user2_id: uuid.UUID,
    opportunity_id: Optional[uuid.UUID] = None,
    match_id: Optional[uuid.UUID] = None
) -> Conversation:
    """
    Get existing conversation or create new one between two users
    Always stores user IDs in sorted order (user1_id < user2_id) for consistency
    """
    # Ensure user1_id < user2_id for consistent storage
    if user1_id > user2_id:
        user1_id, user2_id = user2_id, user1_id

    # Try to find existing conversation
    result = await db.execute(
        select(Conversation).where(
            and_(
                Conversation.user1_id == user1_id,
                Conversation.user2_id == user2_id
            )
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        # Create new conversation
        conversation = Conversation(
            user1_id=user1_id,
            user2_id=user2_id,
            opportunity_id=opportunity_id,
            match_id=match_id
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

    return conversation


async def update_conversation_metadata(
    db: AsyncSession,
    conversation: Conversation,
    last_message: Message
):
    """Update conversation metadata after new message"""
    conversation.last_message_at = last_message.created_at
    conversation.last_message_preview = last_message.content[:200]

    # Increment unread count for recipient
    if last_message.recipient_id == conversation.user1_id:
        conversation.user1_unread_count += 1
    else:
        conversation.user2_unread_count += 1

    await db.commit()


async def get_participant_info(db: AsyncSession, participant_id: uuid.UUID) -> dict:
    """Get participant user info"""
    result = await db.execute(
        select(User).where(User.id == participant_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        return {
            "id": participant_id,
            "full_name": "Unknown User",
            "avatar_url": None,
            "user_type": "unknown"
        }

    return {
        "id": user.id,
        "full_name": user.full_name,
        "avatar_url": user.avatar_url,
        "user_type": user.user_type
    }


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: uuid.UUID,
    token: str = Query(...),  # Pass JWT token as query parameter
    db: AsyncSession = Depends(get_db)
):
    """
    WebSocket endpoint for real-time messaging

    Connect: ws://localhost:8000/api/v1/messages/ws/{user_id}?token=<jwt_token>

    Events sent from client:
    - {"event": "typing", "conversation_id": "...", "is_typing": true}
    - {"event": "read", "message_id": "...", "conversation_id": "..."}
    - {"event": "view_conversation", "conversation_id": "..."}
    - {"event": "leave_conversation", "conversation_id": "..."}

    Events sent to client:
    - {"event": "new_message", "conversation_id": "...", "data": {...}}
    - {"event": "typing", "conversation_id": "...", "data": {"user_id": "...", "is_typing": true}}
    - {"event": "message_read", "conversation_id": "...", "data": {"message_id": "..."}}
    - {"event": "user_online", "data": {"user_id": "..."}}
    - {"event": "user_offline", "data": {"user_id": "..."}}
    """
    # TODO: Validate JWT token from query parameter
    # For now, we'll skip validation (implement in production)

    await manager.connect(websocket, user_id)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message_data = json.loads(data)
                event = message_data.get("event")

                if event == "typing":
                    # Handle typing indicator
                    conversation_id = uuid.UUID(message_data["conversation_id"])
                    is_typing = message_data["is_typing"]

                    # Get conversation to find recipient
                    result = await db.execute(
                        select(Conversation).where(Conversation.id == conversation_id)
                    )
                    conversation = result.scalar_one_or_none()

                    if conversation:
                        # Determine recipient
                        recipient_id = (
                            conversation.user2_id
                            if conversation.user1_id == user_id
                            else conversation.user1_id
                        )

                        await manager.broadcast_typing_indicator(
                            conversation_id, user_id, recipient_id, is_typing
                        )

                elif event == "read":
                    # Handle message read
                    message_id = uuid.UUID(message_data["message_id"])
                    conversation_id = uuid.UUID(message_data["conversation_id"])

                    # Mark message as read
                    result = await db.execute(
                        select(Message).where(Message.id == message_id)
                    )
                    message = result.scalar_one_or_none()

                    if message and message.recipient_id == user_id and not message.is_read:
                        message.is_read = True
                        message.read_at = datetime.utcnow()
                        await db.commit()

                        # Update conversation unread count
                        result = await db.execute(
                            select(Conversation).where(Conversation.id == conversation_id)
                        )
                        conversation = result.scalar_one_or_none()

                        if conversation:
                            if user_id == conversation.user1_id:
                                conversation.user1_unread_count = max(0, conversation.user1_unread_count - 1)
                                conversation.user1_last_read_at = datetime.utcnow()
                            else:
                                conversation.user2_unread_count = max(0, conversation.user2_unread_count - 1)
                                conversation.user2_last_read_at = datetime.utcnow()
                            await db.commit()

                        # Notify sender
                        await manager.broadcast_message_read(
                            conversation_id, message_id, message.sender_id, user_id
                        )

                elif event == "view_conversation":
                    # User is viewing a conversation
                    conversation_id = uuid.UUID(message_data["conversation_id"])
                    manager.set_user_active_conversation(user_id, conversation_id)

                elif event == "leave_conversation":
                    # User left conversation view
                    conversation_id = uuid.UUID(message_data["conversation_id"])
                    manager.unset_user_active_conversation(user_id, conversation_id)

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from user {user_id}")
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")

    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id)


# ============================================================================
# REST Endpoints - Conversations
# ============================================================================

@router.get("/conversations", response_model=ConversationList)
async def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    include_archived: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    List all conversations for current user

    Returns conversations with participant details and unread counts
    """
    # Build query - find conversations where user is participant
    query = select(Conversation).where(
        or_(
            Conversation.user1_id == current_user.id,
            Conversation.user2_id == current_user.id
        )
    )

    # Filter archived if needed
    if not include_archived:
        query = query.where(
            or_(
                and_(
                    Conversation.user1_id == current_user.id,
                    Conversation.is_archived_by_user1 == False
                ),
                and_(
                    Conversation.user2_id == current_user.id,
                    Conversation.is_archived_by_user2 == False
                )
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Add pagination and ordering
    query = query.order_by(desc(Conversation.last_message_at)).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    conversations = result.scalars().all()

    # Transform to ConversationWithParticipant format
    conversation_list = []
    for conv in conversations:
        # Determine other participant
        participant_id = conv.user2_id if conv.user1_id == current_user.id else conv.user1_id

        # Get participant info
        participant_info = await get_participant_info(db, participant_id)

        # Get current user's unread count and archive status
        if current_user.id == conv.user1_id:
            unread_count = conv.user1_unread_count
            is_archived = conv.is_archived_by_user1
        else:
            unread_count = conv.user2_unread_count
            is_archived = conv.is_archived_by_user2

        conversation_list.append(
            ConversationWithParticipant(
                id=conv.id,
                participant_id=participant_id,
                participant_name=participant_info["full_name"],
                participant_avatar=participant_info["avatar_url"],
                participant_user_type=participant_info["user_type"],
                opportunity_id=conv.opportunity_id,
                match_id=conv.match_id,
                last_message_at=conv.last_message_at,
                last_message_preview=conv.last_message_preview,
                unread_count=unread_count,
                is_archived=is_archived,
                is_blocked=conv.is_blocked,
                created_at=conv.created_at
            )
        )

    return ConversationList(
        items=conversation_list,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create a new conversation with another user

    Optionally send an initial message
    """
    # Check that participant exists
    result = await db.execute(
        select(User).where(User.id == conversation_data.participant_id)
    )
    participant = result.scalar_one_or_none()

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found"
        )

    # Can't create conversation with yourself
    if participant.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create conversation with yourself"
        )

    # Get or create conversation
    conversation = await get_or_create_conversation(
        db,
        current_user.id,
        participant.id,
        conversation_data.opportunity_id,
        conversation_data.match_id
    )

    # Send initial message if provided
    if conversation_data.initial_message:
        message = Message(
            conversation_id=conversation.id,
            sender_id=current_user.id,
            recipient_id=participant.id,
            content=conversation_data.initial_message
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)

        # Update conversation metadata
        await update_conversation_metadata(db, conversation, message)

        # Send via WebSocket if recipient is online
        message_dict = MessageResponse.model_validate(message).model_dump(mode='json')
        await manager.send_conversation_message(
            message_dict, conversation.id, current_user.id, participant.id
        )

    return conversation


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get a specific conversation"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    # Verify user is participant
    if conversation.user1_id != current_user.id and conversation.user2_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this conversation"
        )

    return conversation


# ============================================================================
# REST Endpoints - Messages
# ============================================================================

@router.post("/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Send a new message

    If conversation_id is provided, adds message to that conversation.
    Otherwise, finds or creates conversation with recipient.
    """
    # Verify recipient exists
    result = await db.execute(
        select(User).where(User.id == message_data.recipient_id)
    )
    recipient = result.scalar_one_or_none()

    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipient not found"
        )

    # Can't send message to yourself
    if recipient.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send message to yourself"
        )

    # Get or create conversation
    if message_data.conversation_id:
        result = await db.execute(
            select(Conversation).where(Conversation.id == message_data.conversation_id)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        # Verify user is participant
        if conversation.user1_id != current_user.id and conversation.user2_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to send messages in this conversation"
            )
    else:
        # Find or create conversation
        conversation = await get_or_create_conversation(
            db, current_user.id, recipient.id
        )

    # Check if conversation is blocked
    if conversation.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This conversation is blocked"
        )

    # Create message
    message = Message(
        conversation_id=conversation.id,
        sender_id=current_user.id,
        recipient_id=recipient.id,
        content=message_data.content,
        message_type=message_data.message_type,
        attachments=message_data.attachments
    )

    db.add(message)
    await db.commit()
    await db.refresh(message)

    # Update conversation metadata
    await update_conversation_metadata(db, conversation, message)

    # Send via WebSocket if recipient is online
    message_dict = MessageResponse.model_validate(message).model_dump(mode='json')
    await manager.send_conversation_message(
        message_dict, conversation.id, current_user.id, recipient.id
    )

    return message


@router.get("/conversations/{conversation_id}/messages", response_model=MessageList)
async def list_messages(
    conversation_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    List messages in a conversation

    Returns messages in reverse chronological order (newest first)
    """
    # Verify conversation exists and user is participant
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    if conversation.user1_id != current_user.id and conversation.user2_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this conversation"
        )

    # Get total count
    count_result = await db.execute(
        select(func.count()).select_from(Message).where(
            and_(
                Message.conversation_id == conversation_id,
                Message.is_deleted == False
            )
        )
    )
    total = count_result.scalar()

    # Get messages
    result = await db.execute(
        select(Message).where(
            and_(
                Message.conversation_id == conversation_id,
                Message.is_deleted == False
            )
        ).order_by(desc(Message.created_at)).offset((page - 1) * page_size).limit(page_size)
    )
    messages = result.scalars().all()

    return MessageList(
        items=[MessageResponse.model_validate(msg) for msg in messages],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.put("/messages/{message_id}", response_model=MessageResponse)
async def edit_message(
    message_id: uuid.UUID,
    message_data: MessageUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Edit a message (only sender can edit)"""
    result = await db.execute(
        select(Message).where(Message.id == message_id)
    )
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )

    # Only sender can edit
    if message.sender_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the sender can edit this message"
        )

    # Can't edit deleted messages
    if message.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit deleted message"
        )

    # Update message
    message.content = message_data.content
    message.is_edited = True
    message.edited_at = datetime.utcnow()

    await db.commit()
    await db.refresh(message)

    return message


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """Soft delete a message (only sender can delete)"""
    result = await db.execute(
        select(Message).where(Message.id == message_id)
    )
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )

    # Only sender can delete
    if message.sender_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the sender can delete this message"
        )

    # Soft delete
    message.is_deleted = True
    message.deleted_at = datetime.utcnow()
    message.content = "[Message deleted]"

    await db.commit()
