"""Analytics models - User activity tracking and platform metrics"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Integer, Float, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
import uuid
import enum

from app.core.database import Base


class EventTypeEnum(str, enum.Enum):
    """Event types for tracking"""
    # User events
    user_login = "user_login"
    user_logout = "user_logout"
    user_register = "user_register"
    profile_view = "profile_view"
    profile_update = "profile_update"

    # Opportunity events
    opportunity_create = "opportunity_create"
    opportunity_view = "opportunity_view"
    opportunity_apply = "opportunity_apply"
    opportunity_search = "opportunity_search"

    # Match events
    swipe_like = "swipe_like"
    swipe_pass = "swipe_pass"
    swipe_superlike = "swipe_superlike"
    match_created = "match_created"
    match_accepted = "match_accepted"

    # Payment events
    proposal_create = "proposal_create"
    proposal_accept = "proposal_accept"
    payment_success = "payment_success"
    payment_failed = "payment_failed"

    # Learning events
    course_view = "course_view"
    course_enroll = "course_enroll"
    lesson_start = "lesson_start"
    lesson_complete = "lesson_complete"
    course_complete = "course_complete"

    # Message events
    message_sent = "message_sent"
    conversation_start = "conversation_start"

    # General events
    page_view = "page_view"
    search = "search"
    error = "error"


class UserActivity(Base):
    """User activity tracking - individual events and actions"""

    __tablename__ = "user_activities"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # User who performed the action (nullable for anonymous events)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="User who performed the action (null for anonymous)"
    )

    # Event details
    event_type: Mapped[EventTypeEnum] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of event that occurred"
    )
    event_category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Category: user, opportunity, match, payment, learning, message, general"
    )

    # Context
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="ID of related resource (opportunity, course, etc.)"
    )
    resource_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Type of resource (opportunity, course, match, etc.)"
    )

    # Session information
    session_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Session identifier for grouping events"
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        comment="IP address of the user"
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Browser/client user agent"
    )

    # Location
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Additional metadata
    event_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        default=dict,
        comment="Additional event-specific data"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True
    )

    # Indexes for performance
    __table_args__ = (
        Index('ix_user_activities_user_created', 'user_id', 'created_at'),
        Index('ix_user_activities_event_created', 'event_type', 'created_at'),
        Index('ix_user_activities_category_created', 'event_category', 'created_at'),
        Index('ix_user_activities_resource', 'resource_type', 'resource_id'),
    )

    def __repr__(self) -> str:
        return f"<UserActivity {self.event_type} by {self.user_id}>"


class PlatformMetrics(Base):
    """Aggregated platform metrics - daily/hourly statistics"""

    __tablename__ = "platform_metrics"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # Time period
    metric_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Date this metric represents"
    )
    metric_period: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Period type: hourly, daily, weekly, monthly"
    )

    # User metrics
    total_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active_users: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Users who performed any action"
    )
    verified_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Opportunity metrics
    total_opportunities: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_opportunities: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active_opportunities: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Published opportunities"
    )
    opportunity_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Match metrics
    total_swipes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_matches: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_matches: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    match_acceptance_rate: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Percentage of matches that were accepted"
    )

    # Payment metrics
    total_proposals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_proposals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_payments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_payments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_payment_volume: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Total payment amount processed"
    )
    platform_revenue: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Platform fees collected"
    )

    # Learning metrics
    total_courses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_courses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_enrollments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_enrollments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    course_completions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_course_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Message metrics
    total_conversations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_conversations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_messages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_messages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Engagement metrics
    average_session_duration: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Average session duration in minutes"
    )
    page_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unique_visitors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Additional metrics
    metrics_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        default=dict,
        comment="Additional metric data"
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

    # Indexes
    __table_args__ = (
        Index('ix_platform_metrics_date_period', 'metric_date', 'metric_period', unique=True),
    )

    def __repr__(self) -> str:
        return f"<PlatformMetrics {self.metric_date} ({self.metric_period})>"


class SystemLog(Base):
    """System logs and errors for monitoring"""

    __tablename__ = "system_logs"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # Log details
    log_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Log level: debug, info, warning, error, critical"
    )
    log_category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Category: api, database, payment, auth, etc."
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Context
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True
    )
    endpoint: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="API endpoint that generated the log"
    )
    request_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Request identifier for tracing"
    )

    # Error details
    exception_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Additional data
    log_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        default=dict
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True
    )

    # Indexes
    __table_args__ = (
        Index('ix_system_logs_level_created', 'log_level', 'created_at'),
        Index('ix_system_logs_category_created', 'log_category', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<SystemLog {self.log_level}: {self.message[:50]}>"
