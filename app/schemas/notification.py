"""Notification schemas - Pydantic models for validation"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid


# ============================================================================
# Notification Schemas
# ============================================================================

class NotificationCreate(BaseModel):
    """Schema for creating a notification (internal use)"""
    user_id: uuid.UUID
    notification_type: str
    priority: str = "medium"
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    actor_id: Optional[uuid.UUID] = None
    related_opportunity_id: Optional[uuid.UUID] = None
    related_match_id: Optional[uuid.UUID] = None
    related_message_id: Optional[uuid.UUID] = None
    related_payment_id: Optional[uuid.UUID] = None
    action_url: Optional[str] = None
    notification_data: Optional[dict] = None
    expires_at: Optional[datetime] = None


class NotificationUpdate(BaseModel):
    """Schema for updating notification status"""
    is_read: Optional[bool] = None


class NotificationResponse(BaseModel):
    """Schema for notification response"""
    id: uuid.UUID
    user_id: uuid.UUID
    notification_type: str
    priority: str
    title: str
    message: str
    actor_id: Optional[uuid.UUID] = None
    related_opportunity_id: Optional[uuid.UUID] = None
    related_match_id: Optional[uuid.UUID] = None
    related_message_id: Optional[uuid.UUID] = None
    related_payment_id: Optional[uuid.UUID] = None
    action_url: Optional[str] = None
    is_read: bool
    read_at: Optional[datetime] = None
    is_sent_email: bool
    is_sent_push: bool
    notification_data: dict = Field(default_factory=dict)
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NotificationWithActor(BaseModel):
    """Notification response with actor details"""
    id: uuid.UUID
    notification_type: str
    priority: str
    title: str
    message: str
    actor_id: Optional[uuid.UUID] = None
    actor_name: Optional[str] = None
    actor_avatar: Optional[str] = None
    action_url: Optional[str] = None
    is_read: bool
    read_at: Optional[datetime] = None
    notification_data: dict = Field(default_factory=dict)
    created_at: datetime


class NotificationList(BaseModel):
    """Paginated list of notifications"""
    items: List[NotificationWithActor]
    total: int
    unread_count: int
    page: int
    page_size: int
    total_pages: int


class NotificationStats(BaseModel):
    """Notification statistics"""
    total: int
    unread: int
    by_type: dict  # {type: count}
    by_priority: dict  # {priority: count}


class MarkAllReadResponse(BaseModel):
    """Response for mark all as read"""
    marked_count: int
    message: str


# ============================================================================
# Notification Preference Schemas
# ============================================================================

class NotificationPreferenceUpdate(BaseModel):
    """Schema for updating notification preferences"""
    # In-app notifications
    enable_match_notifications: Optional[bool] = None
    enable_message_notifications: Optional[bool] = None
    enable_payment_notifications: Optional[bool] = None
    enable_opportunity_notifications: Optional[bool] = None
    enable_system_notifications: Optional[bool] = None

    # Email notifications
    enable_email_notifications: Optional[bool] = None
    email_match_notifications: Optional[bool] = None
    email_message_notifications: Optional[bool] = None
    email_payment_notifications: Optional[bool] = None
    email_marketing: Optional[bool] = None

    # Push notifications
    enable_push_notifications: Optional[bool] = None
    push_match_notifications: Optional[bool] = None
    push_message_notifications: Optional[bool] = None
    push_payment_notifications: Optional[bool] = None

    # Quiet hours
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = Field(None, pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    quiet_hours_end: Optional[str] = Field(None, pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$")


class NotificationPreferenceResponse(BaseModel):
    """Schema for notification preference response"""
    id: uuid.UUID
    user_id: uuid.UUID

    # In-app notifications
    enable_match_notifications: bool
    enable_message_notifications: bool
    enable_payment_notifications: bool
    enable_opportunity_notifications: bool
    enable_system_notifications: bool

    # Email notifications
    enable_email_notifications: bool
    email_match_notifications: bool
    email_message_notifications: bool
    email_payment_notifications: bool
    email_marketing: bool

    # Push notifications
    enable_push_notifications: bool
    push_match_notifications: bool
    push_message_notifications: bool
    push_payment_notifications: bool

    # Quiet hours
    quiet_hours_enabled: bool
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
