"""Solar Revolution Models - Industry Vertical"""

from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Boolean, Enum as SQLEnum, DECIMAL
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from enum import Enum

from app.core.database import Base


# Enums
class ExperienceLevel(str, Enum):
    """Experience level"""
    NONE = "none"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class ProjectStatus(str, Enum):
    """Solar project status"""
    PLANNING = "planning"
    FUNDING = "funding"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"


class DevelopmentPlanStatus(str, Enum):
    """Development plan status"""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


# Models
class SolarTrainingEnrollment(Base):
    """Solar training enrollment model"""
    __tablename__ = "solar_training_enrollments"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))

    # Personal info
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(20))

    # Experience
    experience_level = Column(SQLEnum(ExperienceLevel), default=ExperienceLevel.NONE)
    current_occupation = Column(String(255))
    relevant_experience = Column(Text)

    # Training preferences
    preferred_training_type = Column(JSONB, default=[])  # online, in-person, hybrid
    availability = Column(JSONB, default={})  # {"days": ["monday", "tuesday"], "time": "morning"}
    location = Column(String(255))

    # Goals
    career_goals = Column(ARRAY(String), default=[])
    specific_interests = Column(ARRAY(String), default=[])  # installation, maintenance, sales, etc.

    # Additional info
    motivation = Column(Text)
    previous_training = Column(Text)
    certifications = Column(ARRAY(String), default=[])

    # Status
    is_approved = Column(Boolean, default=False)
    approved_at = Column(DateTime)
    enrollment_status = Column(String(50), default="pending")  # pending, approved, rejected, completed

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="solar_enrollments")


class SolarOpportunity(Base):
    """Solar-specific job opportunity"""
    __tablename__ = "solar_opportunities"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    posted_by_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    # Basic info
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    company_name = Column(String(255))

    # Location
    location = Column(String(255))
    is_remote = Column(Boolean, default=False)

    # Job details
    job_type = Column(String(50))  # full-time, contract, freelance
    experience_required = Column(SQLEnum(ExperienceLevel), default=ExperienceLevel.BEGINNER)
    required_skills = Column(ARRAY(String), default=[])
    required_certifications = Column(ARRAY(String), default=[])

    # Compensation
    salary_min = Column(DECIMAL(10, 2))
    salary_max = Column(DECIMAL(10, 2))
    currency = Column(String(10), default="USD")

    # Solar-specific
    solar_categories = Column(ARRAY(String), default=[])  # installation, maintenance, sales, design, etc.
    project_type = Column(ARRAY(String), default=[])  # residential, commercial, utility-scale

    # Status
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime)

    # Metadata
    view_count = Column(Integer, default=0)
    application_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    posted_by = relationship("User", foreign_keys=[posted_by_id])


class SolarProject(Base):
    """Solar project tracking"""
    __tablename__ = "solar_projects"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    # Project info
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    project_type = Column(String(100))  # residential, commercial, utility-scale, off-grid

    # Location
    location = Column(JSONB)  # {"address": "...", "coordinates": {...}}
    region = Column(String(100))

    # Technical details
    capacity_kw = Column(DECIMAL(10, 2))  # System capacity in kilowatts
    estimated_cost = Column(DECIMAL(12, 2))
    estimated_savings = Column(DECIMAL(12, 2))
    payback_period_years = Column(Integer)

    # Project phases
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.PLANNING, index=True)
    start_date = Column(DateTime)
    completion_date = Column(DateTime)
    actual_completion_date = Column(DateTime)

    # Team and partners
    team_members = Column(JSONB, default=[])  # [{"user_id": "...", "role": "installer"}]
    contractors = Column(JSONB, default=[])
    suppliers = Column(JSONB, default=[])

    # Progress tracking
    milestones = Column(JSONB, default=[])  # [{"name": "...", "status": "...", "date": "..."}]
    progress_percentage = Column(Integer, default=0)

    # Documentation
    attachments = Column(JSONB, default=[])
    images = Column(ARRAY(String), default=[])
    permits = Column(JSONB, default=[])

    # Metadata
    is_public = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])


class SolarDevelopmentPlan(Base):
    """Personalized solar career development plan"""
    __tablename__ = "solar_development_plans"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # Plan details
    title = Column(String(255), nullable=False)
    description = Column(Text)

    # Current state
    current_skills = Column(ARRAY(String), default=[])
    current_experience_level = Column(SQLEnum(ExperienceLevel))
    current_role = Column(String(100))

    # Goals
    target_role = Column(String(100))
    target_skills = Column(ARRAY(String), default=[])
    timeline_months = Column(Integer)

    # AI-generated plan
    learning_path = Column(JSONB, default=[])  # [{"step": 1, "title": "...", "resources": [...]}]
    skill_gaps = Column(ARRAY(String), default=[])
    recommended_courses = Column(JSONB, default=[])
    recommended_certifications = Column(ARRAY(String), default=[])

    # Progress
    completed_steps = Column(ARRAY(Integer), default=[])
    progress_percentage = Column(Integer, default=0)
    status = Column(SQLEnum(DevelopmentPlanStatus), default=DevelopmentPlanStatus.DRAFT)

    # Metadata
    generated_by_ai = Column(Boolean, default=True)
    last_reviewed = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="solar_development_plans")


class SolarResource(Base):
    """Solar industry resources and learning materials"""
    __tablename__ = "solar_resources"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_by_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))

    # Resource info
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    resource_type = Column(String(50))  # article, video, course, tool, guide, template

    # Content
    url = Column(String(500))
    content = Column(Text)

    # Media
    thumbnail_url = Column(String(500))
    file_url = Column(String(500))

    # Categorization
    category = Column(String(100))  # installation, design, sales, policy, financing
    tags = Column(ARRAY(String), default=[])
    difficulty_level = Column(SQLEnum(ExperienceLevel))

    # Engagement
    view_count = Column(Integer, default=0)
    download_count = Column(Integer, default=0)
    rating = Column(DECIMAL(3, 2), default=0)
    rating_count = Column(Integer, default=0)

    # Metadata
    is_official = Column(Boolean, default=False)  # Official Trybe resource
    is_free = Column(Boolean, default=True)
    price = Column(DECIMAL(10, 2))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
