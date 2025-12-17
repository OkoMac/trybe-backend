"""Notification model - User notifications for various platform events"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
import uuid
import enum

from app.core.database import Base


class NotificationTypeEnum(str, enum.Enum):
    """Notification type enumeration"""
    # Match related
    new_match = "new_match"
    match_accepted = "match_accepted"

    # Message related
    new_message = "new_message"

    # Payment related
    payment_proposal_received = "payment_proposal_received"
    payment_proposal_accepted = "payment_proposal_accepted"
    payment_proposal_rejected = "payment_proposal_rejected"
    payment_proposal_countered = "payment_proposal_countered"
    payment_received = "payment_received"
    payment_sent = "payment_sent"

    # Opportunity related
    opportunity_applied = "opportunity_applied"
    opportunity_filled = "opportunity_filled"
    opportunity_expiring = "opportunity_expiring"

    # System
    system_announcement = "system_announcement"
    account_verification = "account_verification"
    security_alert = "security_alert"


class NotificationPriorityEnum(str, enum.Enum):
    """Notification priority levels"""
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class Notification(Base):
    """Notification model - stores user notifications"""

    __tablename__ = "notifications"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # User who receives the notification
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Notification metadata
    notification_type: Mapped[NotificationTypeEnum] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    priority: Mapped[NotificationPriorityEnum] = mapped_column(
        String(20),
        default=NotificationPriorityEnum.medium,
        nullable=False,
        index=True
    )

    # Content
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Notification title/heading"
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Notification message body"
    )

    # Optional: Actor (who triggered this notification)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who triggered this notification"
    )

    # Related entities (for deep linking)
    related_opportunity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    related_match_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matches.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    related_message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    related_payment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payment_proposals.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Action URL (for deep linking in frontend)
    action_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Frontend URL to navigate to when clicked"
    )

    # Read status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When notification was read"
    )

    # Delivery status
    is_sent_email: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether email notification was sent"
    )
    is_sent_push: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether push notification was sent"
    )

    # Additional data (flexible JSONB field)
    notification_data: Mapped[Optional[dict]] = mapped_column(
        "data",
        JSONB,
        nullable=True,
        default=dict,
        comment="Additional notification data"
    )

    # Expiration
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When notification expires (optional)"
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

    # Composite indexes for efficient querying
    __table_args__ = (
        Index('ix_notifications_user_unread', 'user_id', 'is_read'),
        Index('ix_notifications_user_created', 'user_id', 'created_at'),
        Index('ix_notifications_type_created', 'notification_type', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<Notification {self.notification_type} for {self.user_id}>"


class NotificationPreference(Base):
    """User notification preferences - controls which notifications to receive"""

    __tablename__ = "notification_preferences"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # User
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # In-app notification preferences
    enable_match_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_message_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_payment_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_opportunity_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_system_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Email notification preferences
    enable_email_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_match_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_message_notifications: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_payment_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_marketing: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Push notification preferences
    enable_push_notifications: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    push_match_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_message_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_payment_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Quiet hours
    quiet_hours_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Enable do-not-disturb hours"
    )
    quiet_hours_start: Mapped[Optional[str]] = mapped_column(
        String(5),
        nullable=True,
        comment="Start time in HH:MM format (24-hour)"
    )
    quiet_hours_end: Mapped[Optional[str]] = mapped_column(
        String(5),
        nullable=True,
        comment="End time in HH:MM format (24-hour)"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<NotificationPreference for {self.user_id}>"
