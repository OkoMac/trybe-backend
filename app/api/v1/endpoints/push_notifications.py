"""Push Notification API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.device_token import DeviceToken, DevicePlatformEnum, NotificationLog
from app.services.push_notification_service import push_notification_service


router = APIRouter()


# Schemas
class DeviceTokenCreate(BaseModel):
    """Schema for registering a device token"""
    token: str = Field(..., description="FCM device token")
    platform: DevicePlatformEnum
    device_name: Optional[str] = Field(None, max_length=100)
    device_id: Optional[str] = Field(None, max_length=100)
    app_version: Optional[str] = Field(None, max_length=20)


class DeviceTokenResponse(BaseModel):
    """Schema for device token response"""
    id: uuid.UUID
    platform: DevicePlatformEnum
    device_name: Optional[str]
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]

    class Config:
        from_attributes = True


class TopicSubscription(BaseModel):
    """Schema for topic subscription"""
    topic: str = Field(..., description="Topic name (e.g., 'new_opportunities', 'all_users')")


class TestNotificationRequest(BaseModel):
    """Schema for sending a test notification"""
    title: str = Field(..., max_length=100)
    body: str = Field(..., max_length=500)
    data: Optional[dict] = None


# Endpoints

@router.post("/tokens", response_model=DeviceTokenResponse, status_code=status.HTTP_201_CREATED)
async def register_device_token(
    token_data: DeviceTokenCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Register a device token for push notifications

    - **token**: FCM device token from the mobile app
    - **platform**: ios, android, or web
    - **device_name**: Optional friendly name for the device
    - **device_id**: Optional unique device identifier
    - **app_version**: Optional app version

    If the token already exists, it will be reactivated.
    """
    # Check if token already exists
    result = await db.execute(
        select(DeviceToken).where(DeviceToken.token == token_data.token)
    )
    existing_token = result.scalar_one_or_none()

    if existing_token:
        # Reactivate and update
        existing_token.user_id = current_user.id
        existing_token.is_active = True
        existing_token.device_name = token_data.device_name
        existing_token.device_id = token_data.device_id
        existing_token.app_version = token_data.app_version
        existing_token.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(existing_token)

        return DeviceTokenResponse(
            id=existing_token.id,
            platform=existing_token.platform,
            device_name=existing_token.device_name,
            is_active=existing_token.is_active,
            created_at=existing_token.created_at,
            last_used_at=existing_token.last_used_at
        )

    # Create new token
    device_token = DeviceToken(
        user_id=current_user.id,
        token=token_data.token,
        platform=token_data.platform,
        device_name=token_data.device_name,
        device_id=token_data.device_id,
        app_version=token_data.app_version
    )

    db.add(device_token)
    await db.commit()
    await db.refresh(device_token)

    return DeviceTokenResponse(
        id=device_token.id,
        platform=device_token.platform,
        device_name=device_token.device_name,
        is_active=device_token.is_active,
        created_at=device_token.created_at,
        last_used_at=device_token.last_used_at
    )


@router.get("/tokens", response_model=List[DeviceTokenResponse])
async def get_user_device_tokens(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all registered device tokens for the current user

    Returns active and inactive tokens.
    """
    result = await db.execute(
        select(DeviceToken)
        .where(DeviceToken.user_id == current_user.id)
        .order_by(DeviceToken.created_at.desc())
    )
    tokens = result.scalars().all()

    return [
        DeviceTokenResponse(
            id=token.id,
            platform=token.platform,
            device_name=token.device_name,
            is_active=token.is_active,
            created_at=token.created_at,
            last_used_at=token.last_used_at
        )
        for token in tokens
    ]


@router.delete("/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device_token(
    token_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete/deactivate a device token

    This marks the token as inactive so it won't receive notifications.
    """
    result = await db.execute(
        select(DeviceToken).where(
            and_(
                DeviceToken.id == token_id,
                DeviceToken.user_id == current_user.id
            )
        )
    )
    token = result.scalar_one_or_none()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device token not found"
        )

    # Mark as inactive instead of deleting
    token.is_active = False
    token.updated_at = datetime.utcnow()

    await db.commit()


@router.post("/topics/subscribe")
async def subscribe_to_topic(
    subscription: TopicSubscription,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Subscribe to a notification topic

    Topics allow broadcasting messages to groups of users.

    Common topics:
    - "new_opportunities" - Get notified of new opportunities
    - "hackathon_updates" - Hackathon event updates
    - "system_announcements" - Important platform updates
    """
    # Get all active tokens for user
    result = await db.execute(
        select(DeviceToken).where(
            and_(
                DeviceToken.user_id == current_user.id,
                DeviceToken.is_active == True
            )
        )
    )
    tokens = result.scalars().all()

    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active device tokens found. Please register a device first."
        )

    # Subscribe all user's tokens to topic
    token_strings = [t.token for t in tokens]
    result = await push_notification_service.subscribe_to_topic(
        tokens=token_strings,
        topic=subscription.topic
    )

    return {
        "success": True,
        "message": f"Subscribed to topic '{subscription.topic}'",
        "subscribed_devices": result["success_count"],
        "failed_devices": result["failure_count"]
    }


@router.post("/topics/unsubscribe")
async def unsubscribe_from_topic(
    subscription: TopicSubscription,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Unsubscribe from a notification topic
    """
    # Get all active tokens for user
    result = await db.execute(
        select(DeviceToken).where(
            and_(
                DeviceToken.user_id == current_user.id,
                DeviceToken.is_active == True
            )
        )
    )
    tokens = result.scalars().all()

    if not tokens:
        return {
            "success": True,
            "message": "No active devices to unsubscribe"
        }

    # Unsubscribe all user's tokens from topic
    token_strings = [t.token for t in tokens]
    result = await push_notification_service.unsubscribe_from_topic(
        tokens=token_strings,
        topic=subscription.topic
    )

    return {
        "success": True,
        "message": f"Unsubscribed from topic '{subscription.topic}'",
        "unsubscribed_devices": result["success_count"],
        "failed_devices": result["failure_count"]
    }


@router.post("/test")
async def send_test_notification(
    notification: TestNotificationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a test notification to all your devices

    Useful for testing push notification setup.
    """
    # Get all active tokens for user
    result = await db.execute(
        select(DeviceToken).where(
            and_(
                DeviceToken.user_id == current_user.id,
                DeviceToken.is_active == True
            )
        )
    )
    tokens = result.scalars().all()

    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active device tokens found. Please register a device first."
        )

    # Send to all tokens
    results = []
    for token in tokens:
        success, message_id = await push_notification_service.send_notification(
            token=token.token,
            title=notification.title,
            body=notification.body,
            data=notification.data or {"type": "test"}
        )

        results.append({
            "device": token.device_name or token.platform.value,
            "success": success,
            "message_id": message_id
        })

        # Update last_used_at if successful
        if success:
            token.last_used_at = datetime.utcnow()

    await db.commit()

    success_count = sum(1 for r in results if r["success"])

    return {
        "success": success_count > 0,
        "message": f"Sent test notification to {success_count}/{len(results)} devices",
        "results": results
    }


@router.get("/analytics")
async def get_notification_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get notification analytics for the current user

    Returns statistics about sent and received notifications.
    """
    # Get notification logs
    result = await db.execute(
        select(NotificationLog)
        .where(NotificationLog.user_id == current_user.id)
        .order_by(NotificationLog.sent_at.desc())
        .limit(100)
    )
    logs = result.scalars().all()

    total_sent = len(logs)
    total_delivered = sum(1 for log in logs if log.delivered)
    total_opened = sum(1 for log in logs if log.opened)

    # Group by type
    by_type = {}
    for log in logs:
        if log.notification_type not in by_type:
            by_type[log.notification_type] = {
                "count": 0,
                "delivered": 0,
                "opened": 0
            }
        by_type[log.notification_type]["count"] += 1
        if log.delivered:
            by_type[log.notification_type]["delivered"] += 1
        if log.opened:
            by_type[log.notification_type]["opened"] += 1

    return {
        "total_notifications": total_sent,
        "total_delivered": total_delivered,
        "total_opened": total_opened,
        "delivery_rate": round(total_delivered / total_sent * 100, 2) if total_sent > 0 else 0,
        "open_rate": round(total_opened / total_delivered * 100, 2) if total_delivered > 0 else 0,
        "by_type": by_type,
        "recent_notifications": [
            {
                "title": log.title,
                "type": log.notification_type,
                "sent_at": log.sent_at,
                "delivered": log.delivered,
                "opened": log.opened
            }
            for log in logs[:10]
        ]
    }
