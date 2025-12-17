"""Notification endpoints - Manage user notifications"""

from datetime import datetime
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc, update
import uuid

from app.core.database import get_db
from app.models.notification import Notification, NotificationPreference
from app.models.user import User
from app.schemas.notification import (
    NotificationResponse,
    NotificationWithActor,
    NotificationList,
    NotificationStats,
    NotificationUpdate,
    NotificationPreferenceUpdate,
    NotificationPreferenceResponse,
    MarkAllReadResponse
)
from app.api.deps import get_current_user
from app.services.notification_service import NotificationService

router = APIRouter()


# ============================================================================
# Helper Functions
# ============================================================================

async def get_actor_info(db: AsyncSession, actor_id: Optional[uuid.UUID]) -> dict:
    """Get actor user info"""
    if not actor_id:
        return {"name": None, "avatar": None}

    result = await db.execute(
        select(User).where(User.id == actor_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        return {"name": "Unknown User", "avatar": None}

    return {"name": user.full_name, "avatar": user.avatar_url}


# ============================================================================
# Notification Endpoints
# ============================================================================

@router.get("/", response_model=NotificationList)
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    notification_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    List notifications for current user

    Filters:
    - unread_only: Only show unread notifications
    - notification_type: Filter by notification type
    """
    # Build query
    query = select(Notification).where(Notification.user_id == current_user.id)

    if unread_only:
        query = query.where(Notification.is_read == False)

    if notification_type:
        query = query.where(Notification.notification_type == notification_type)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get unread count
    unread_query = select(func.count()).select_from(Notification).where(
        and_(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        )
    )
    unread_result = await db.execute(unread_query)
    unread_count = unread_result.scalar()

    # Add pagination and ordering
    query = query.order_by(desc(Notification.created_at)).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    notifications = result.scalars().all()

    # Enrich with actor info
    notification_list = []
    for notif in notifications:
        actor_info = await get_actor_info(db, notif.actor_id)

        notification_list.append(
            NotificationWithActor(
                id=notif.id,
                notification_type=notif.notification_type,
                priority=notif.priority,
                title=notif.title,
                message=notif.message,
                actor_id=notif.actor_id,
                actor_name=actor_info["name"],
                actor_avatar=actor_info["avatar"],
                action_url=notif.action_url,
                is_read=notif.is_read,
                read_at=notif.read_at,
                notification_data=notif.notification_data,
                created_at=notif.created_at
            )
        )

    return NotificationList(
        items=notification_list,
        total=total,
        unread_count=unread_count,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/stats", response_model=NotificationStats)
async def get_notification_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get notification statistics for current user"""
    # Total count
    total_result = await db.execute(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == current_user.id
        )
    )
    total = total_result.scalar()

    # Unread count
    unread_result = await db.execute(
        select(func.count()).select_from(Notification).where(
            and_(
                Notification.user_id == current_user.id,
                Notification.is_read == False
            )
        )
    )
    unread = unread_result.scalar()

    # Count by type
    by_type_result = await db.execute(
        select(
            Notification.notification_type,
            func.count(Notification.id)
        ).where(
            Notification.user_id == current_user.id
        ).group_by(Notification.notification_type)
    )
    by_type = {row[0]: row[1] for row in by_type_result}

    # Count by priority
    by_priority_result = await db.execute(
        select(
            Notification.priority,
            func.count(Notification.id)
        ).where(
            Notification.user_id == current_user.id
        ).group_by(Notification.priority)
    )
    by_priority = {row[0]: row[1] for row in by_priority_result}

    return NotificationStats(
        total=total,
        unread=unread,
        by_type=by_type,
        by_priority=by_priority
    )


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get a specific notification"""
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    # Verify ownership
    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this notification"
        )

    return notification


@router.put("/{notification_id}", response_model=NotificationResponse)
async def update_notification(
    notification_id: uuid.UUID,
    notification_data: NotificationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Update notification (mark as read/unread)"""
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    # Verify ownership
    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this notification"
        )

    # Update fields
    if notification_data.is_read is not None:
        notification.is_read = notification_data.is_read
        if notification_data.is_read and not notification.read_at:
            notification.read_at = datetime.utcnow()
        elif not notification_data.is_read:
            notification.read_at = None

    await db.commit()
    await db.refresh(notification)

    return notification


@router.post("/mark-all-read", response_model=MarkAllReadResponse)
async def mark_all_as_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Mark all notifications as read for current user"""
    result = await db.execute(
        update(Notification)
        .where(
            and_(
                Notification.user_id == current_user.id,
                Notification.is_read == False
            )
        )
        .values(is_read=True, read_at=datetime.utcnow())
    )

    marked_count = result.rowcount
    await db.commit()

    return MarkAllReadResponse(
        marked_count=marked_count,
        message=f"Marked {marked_count} notifications as read"
    )


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a notification"""
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    # Verify ownership
    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this notification"
        )

    await db.delete(notification)
    await db.commit()


# ============================================================================
# Notification Preferences Endpoints
# ============================================================================

@router.get("/preferences/me", response_model=NotificationPreferenceResponse)
async def get_my_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get current user's notification preferences"""
    preferences = await NotificationService.get_user_preferences(db, current_user.id)
    return preferences


@router.put("/preferences/me", response_model=NotificationPreferenceResponse)
async def update_my_preferences(
    preference_data: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Update current user's notification preferences"""
    preferences = await NotificationService.get_user_preferences(db, current_user.id)

    # Update only provided fields
    update_data = preference_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(preferences, field, value)

    await db.commit()
    await db.refresh(preferences)

    return preferences
