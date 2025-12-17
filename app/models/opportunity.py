"""Opportunity model - Jobs and gigs for matching"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Enum, Integer, Numeric, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
import enum

from app.core.database import Base


class OpportunityStatusEnum(str, enum.Enum):
    """Opportunity status enumeration"""
    open = "open"
    closed = "closed"
    filled = "filled"
    archived = "archived"


class OpportunityTypeEnum(str, enum.Enum):
    """Opportunity type enumeration"""
    full_time = "full_time"
    part_time = "part_time"
    contract = "contract"
    freelance = "freelance"
    gig = "gig"
    internship = "internship"


class ExperienceLevelEnum(str, enum.Enum):
    """Experience level enumeration"""
    entry = "entry"
    junior = "junior"
    mid = "mid"
    senior = "senior"
    expert = "expert"


class Opportunity(Base):
    """Opportunity model - represents jobs/gigs"""

    __tablename__ = "opportunities"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # Employer/Poster Information
    employer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Basic Information
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Type and Status
    opportunity_type: Mapped[OpportunityTypeEnum] = mapped_column(
        Enum(OpportunityTypeEnum, name="opportunity_type_enum"),
        nullable=False,
        index=True
    )
    status: Mapped[OpportunityStatusEnum] = mapped_column(
        Enum(OpportunityStatusEnum, name="opportunity_status_enum", create_constraint=False),
        nullable=False,
        default=OpportunityStatusEnum.open,
        index=True
    )

    # Location
    location: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Location as JSONB: {country, city, coordinates, remote}"
    )
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Requirements
    required_skills: Mapped[Optional[list]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Array of required skills"
    )
    preferred_skills: Mapped[Optional[list]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Array of preferred skills"
    )
    experience_level: Mapped[Optional[ExperienceLevelEnum]] = mapped_column(
        Enum(ExperienceLevelEnum, name="experience_level_enum"),
        nullable=True
    )
    education_required: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Compensation
    salary_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    hourly_rate: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)

    # Additional Details
    benefits: Mapped[Optional[list]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Array of benefits offered"
    )
    application_deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    start_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Metadata
    views_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    applications_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matches_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Additional metadata (flexible JSONB field)
    opportunity_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        default=dict,
        comment="Additional metadata"
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
        return f"<Opportunity {self.title} ({self.company_name})>"
