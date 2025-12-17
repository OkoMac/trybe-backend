"""Review and Rating models"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Text, Enum, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
import enum

from app.core.database import Base


class ReviewTypeEnum(str, enum.Enum):
    """Review type enumeration"""
    opportunity = "opportunity"
    user = "user"
    employer = "employer"
    hackathon = "hackathon"


class ReviewStatusEnum(str, enum.Enum):
    """Review moderation status"""
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    flagged = "flagged"


class Review(Base):
    """Review and Rating model"""

    __tablename__ = "reviews"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # Review Type
    review_type: Mapped[ReviewTypeEnum] = mapped_column(
        Enum(ReviewTypeEnum),
        nullable=False,
        index=True
    )

    # Relationships
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Target of review (can be user, opportunity, employer, etc.)
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # Rating (1-5 stars)
    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True
    )

    # Review Content
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    comment: Mapped[str] = mapped_column(Text, nullable=False)

    # Additional Ratings (optional breakdown)
    ratings_breakdown: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional ratings like communication, quality, timeliness"
    )

    # Moderation
    status: Mapped[ReviewStatusEnum] = mapped_column(
        Enum(ReviewStatusEnum),
        nullable=False,
        default=ReviewStatusEnum.pending,
        index=True
    )

    # Helpful votes
    helpful_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    # Verification
    is_verified_purchase: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether reviewer actually used the service/opportunity"
    )

    # Response from reviewed party
    response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Flags and moderation
    flag_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    moderation_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        index=True
    )

    # Relationships
    reviewer = relationship("User", foreign_keys=[reviewer_id], backref="reviews_given")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_review_target_type", "target_id", "review_type"),
        Index("idx_review_status_created", "status", "created_at"),
        Index("idx_review_rating", "rating", "created_at"),
    )


class ReviewHelpful(Base):
    """Track helpful votes on reviews"""

    __tablename__ = "review_helpful"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Relationships
    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Vote value (true for helpful, false for not helpful)
    is_helpful: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    # Unique constraint: one vote per user per review
    __table_args__ = (
        Index("idx_review_helpful_unique", "review_id", "user_id", unique=True),
    )


class ReviewFlag(Base):
    """Track flags/reports on reviews"""

    __tablename__ = "review_flags"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Relationships
    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Flag reason
    reason: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="spam, inappropriate, offensive, fake, etc."
    )

    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Resolution
    resolved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )


class ReviewSummary(Base):
    """Aggregated review statistics for entities"""

    __tablename__ = "review_summaries"

    # Primary Key (target_id + review_type)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Target entity
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    review_type: Mapped[ReviewTypeEnum] = mapped_column(
        Enum(ReviewTypeEnum),
        nullable=False
    )

    # Aggregate statistics
    total_reviews: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    average_rating: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        index=True
    )

    # Rating distribution
    rating_distribution: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default={"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
        comment="Count of reviews for each star rating"
    )

    # Breakdown of additional ratings (if applicable)
    ratings_breakdown_avg: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Average scores for additional rating categories"
    )

    # Last updated
    last_updated: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Unique constraint
    __table_args__ = (
        Index("idx_review_summary_unique", "target_id", "review_type", unique=True),
    )
