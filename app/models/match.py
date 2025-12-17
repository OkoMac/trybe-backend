"""Match and Swipe models - Track user interactions with opportunities"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
import uuid
import enum

from app.core.database import Base


class SwipeActionEnum(str, enum.Enum):
    """Swipe action enumeration"""
    like = "like"
    pass_ = "pass"  # pass is a Python keyword, so we use pass_
    superlike = "superlike"


class MatchStatusEnum(str, enum.Enum):
    """Match status enumeration"""
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    expired = "expired"


class Swipe(Base):
    """Swipe model - tracks user swipes on opportunities"""

    __tablename__ = "swipes"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # Foreign Keys
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Swipe Data
    action: Mapped[SwipeActionEnum] = mapped_column(
        Enum(SwipeActionEnum, name="swipe_action_enum"),
        nullable=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True
    )

    # Constraints - one swipe per user per opportunity
    __table_args__ = (
        UniqueConstraint('user_id', 'opportunity_id', name='uq_user_opportunity_swipe'),
    )

    def __repr__(self) -> str:
        return f"<Swipe {self.action} by {self.user_id}>"


class Match(Base):
    """Match model - represents a match between user and opportunity"""

    __tablename__ = "matches"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # Foreign Keys
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    employer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Employer who posted the opportunity"
    )

    # Match Status
    status: Mapped[MatchStatusEnum] = mapped_column(
        Enum(MatchStatusEnum, name="match_status_enum"),
        nullable=False,
        default=MatchStatusEnum.pending,
        index=True
    )

    # Match Score (AI-generated compatibility score)
    match_score: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        comment="AI-generated compatibility score 0-100"
    )

    # Flags
    is_mutual: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if both user and employer liked each other"
    )
    user_viewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    employer_viewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Match metadata (flexible JSONB field)
    match_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        default=dict,
        comment="Additional match metadata"
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
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Match expiration time"
    )

    # Constraints - one match per user per opportunity
    __table_args__ = (
        UniqueConstraint('user_id', 'opportunity_id', name='uq_user_opportunity_match'),
    )

    def __repr__(self) -> str:
        return f"<Match {self.user_id} <-> {self.opportunity_id} ({self.status})>"
