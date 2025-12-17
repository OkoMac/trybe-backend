"""User model - matches frontend requirements"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
import enum

from app.core.database import Base


class UserTypeEnum(str, enum.Enum):
    """User type enumeration"""
    professional = "professional"
    employer = "employer"
    company = "company"
    admin = "admin"


class User(Base):
    """User model"""

    __tablename__ = "users"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # Authentication
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Profile Information
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Location (stored as JSONB: {country, city, coordinates})
    location: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # User Type
    user_type: Mapped[UserTypeEnum] = mapped_column(
        Enum(UserTypeEnum, name="user_type_enum", create_constraint=False),
        nullable=False,
        default=UserTypeEnum.professional,
        index=True
    )

    # Verification Status
    verification_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # User Metadata (flexible JSONB field for additional data)
    user_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata",  # Use 'metadata' as column name in DB
        JSONB,
        nullable=True,
        default=dict
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
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    report_templates: Mapped[list["ReportTemplate"]] = relationship(
        "ReportTemplate",
        back_populates="created_by",
        foreign_keys="ReportTemplate.created_by_id"
    )
    reports: Mapped[list["Report"]] = relationship(
        "Report",
        back_populates="generated_by",
        foreign_keys="Report.generated_by_id"
    )
    report_schedules: Mapped[list["ReportSchedule"]] = relationship(
        "ReportSchedule",
        back_populates="created_by",
        foreign_keys="ReportSchedule.created_by_id"
    )

    # Hackathon relationships
    organized_hackathons: Mapped[list["Hackathon"]] = relationship(
        "Hackathon",
        back_populates="organizer",
        foreign_keys="Hackathon.organizer_id"
    )
    hackathon_teams: Mapped[list["HackathonTeam"]] = relationship(
        "HackathonTeam",
        secondary="team_members",
        back_populates="members"
    )
    hackathon_registrations: Mapped[list["HackathonRegistration"]] = relationship(
        "HackathonRegistration",
        back_populates="user"
    )
    test_results: Mapped[list["TestResult"]] = relationship(
        "TestResult",
        back_populates="user"
    )

    # Community relationships
    posts: Mapped[list["CommunityPost"]] = relationship(
        "CommunityPost",
        back_populates="author",
        foreign_keys="CommunityPost.author_id"
    )
    comments: Mapped[list["Comment"]] = relationship(
        "Comment",
        back_populates="author",
        foreign_keys="Comment.author_id"
    )

    # Solar Revolution relationships
    solar_enrollments: Mapped[list["SolarTrainingEnrollment"]] = relationship(
        "SolarTrainingEnrollment",
        back_populates="user"
    )
    solar_development_plans: Mapped[list["SolarDevelopmentPlan"]] = relationship(
        "SolarDevelopmentPlan",
        back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.email})>"
