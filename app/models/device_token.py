"""Device Token model for push notifications"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Enum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
import enum

from app.core.database import Base


class DevicePlatformEnum(str, enum.Enum):
    """Device platform enumeration"""
    ios = "ios"
    android = "android"
    web = "web"


class DeviceToken(Base):
    """Device Token model for push notifications"""

    __tablename__ = "device_tokens"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # User relationship
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Device information
    token: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="FCM device token"
    )

    platform: Mapped[DevicePlatformEnum] = mapped_column(
        Enum(DevicePlatformEnum),
        nullable=False,
        index=True
    )

    device_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="User-friendly device name (e.g., 'iPhone 13', 'Samsung Galaxy')"
    )

    device_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Unique device identifier"
    )

    # App information
    app_version: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="App version when token was registered"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether this token is still valid"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Last time a notification was successfully sent to this token"
    )

    # Relationship
    user = relationship("User", backref="device_tokens")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_device_token_user_platform", "user_id", "platform"),
        Index("idx_device_token_active", "is_active", "created_at"),
    )


class NotificationLog(Base):
    """Log of sent push notifications"""

    __tablename__ = "notification_logs"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # Relationships
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    device_token_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("device_tokens.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Notification details
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(String(1000), nullable=False)
    notification_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type: message, opportunity, payment, review, etc."
    )

    # Delivery information
    sent_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )

    delivered: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    delivery_error: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Error message if delivery failed"
    )

    # FCM message ID
    fcm_message_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Firebase Cloud Messaging message ID"
    )

    # Engagement
    opened: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    opened_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )

    # Indexes for analytics
    __table_args__ = (
        Index("idx_notification_log_type_sent", "notification_type", "sent_at"),
        Index("idx_notification_log_user_sent", "user_id", "sent_at"),
        Index("idx_notification_log_delivered", "delivered", "sent_at"),
    )
