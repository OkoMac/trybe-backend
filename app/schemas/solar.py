"""Solar Revolution Schemas"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from decimal import Decimal

from app.models.solar import ExperienceLevel, ProjectStatus, DevelopmentPlanStatus


# Training Enrollment Schemas
class TrainingEnrollmentCreate(BaseModel):
    """Create training enrollment"""
    name: str
    email: EmailStr
    phone: Optional[str] = None
    experience_level: ExperienceLevel = ExperienceLevel.NONE
    current_occupation: Optional[str] = None
    relevant_experience: Optional[str] = None
    preferred_training_type: List[str] = []
    location: Optional[str] = None
    career_goals: List[str] = []
    specific_interests: List[str] = []
    motivation: Optional[str] = None


class TrainingEnrollmentResponse(BaseModel):
    """Training enrollment response"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: Optional[UUID] = None
    name: str
    email: str
    experience_level: ExperienceLevel
    enrollment_status: str
    is_approved: bool
    created_at: datetime


# Solar Opportunity Schemas
class SolarOpportunityCreate(BaseModel):
    """Create solar opportunity"""
    title: str
    description: str
    company_name: Optional[str] = None
    location: str
    is_remote: bool = False
    job_type: str
    experience_required: ExperienceLevel
    required_skills: List[str] = []
    required_certifications: List[str] = []
    salary_min: Optional[Decimal] = None
    salary_max: Optional[Decimal] = None
    solar_categories: List[str] = []
    project_type: List[str] = []


class SolarOpportunityResponse(BaseModel):
    """Solar opportunity response"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    posted_by_id: UUID
    title: str
    description: str
    company_name: Optional[str] = None
    location: str
    is_remote: bool
    job_type: str
    experience_required: ExperienceLevel
    required_skills: List[str]
    solar_categories: List[str]
    is_active: bool
    view_count: int
    application_count: int
    created_at: datetime


# Solar Project Schemas
class SolarProjectCreate(BaseModel):
    """Create solar project"""
    name: str
    description: Optional[str] = None
    project_type: str
    location: Optional[dict] = None
    capacity_kw: Optional[Decimal] = None
    estimated_cost: Optional[Decimal] = None
    is_public: bool = False


class SolarProjectResponse(BaseModel):
    """Solar project response"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    name: str
    description: Optional[str] = None
    project_type: str
    status: ProjectStatus
    capacity_kw: Optional[Decimal] = None
    estimated_cost: Optional[Decimal] = None
    progress_percentage: int
    created_at: datetime


# Development Plan Schemas
class DevelopmentPlanCreate(BaseModel):
    """Create development plan"""
    current_skills: List[str]
    current_experience_level: ExperienceLevel
    current_role: Optional[str] = None
    target_role: str
    target_skills: List[str] = []
    timeline_months: Optional[int] = None


class DevelopmentPlanResponse(BaseModel):
    """Development plan response"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    current_experience_level: ExperienceLevel
    target_role: str
    skill_gaps: List[str]
    learning_path: List[dict]
    progress_percentage: int
    status: DevelopmentPlanStatus
    created_at: datetime


# Resource Schemas
class SolarResourceCreate(BaseModel):
    """Create solar resource"""
    title: str
    description: Optional[str] = None
    resource_type: str
    url: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = []
    difficulty_level: Optional[ExperienceLevel] = None
    is_free: bool = True
    price: Optional[Decimal] = None


class SolarResourceResponse(BaseModel):
    """Solar resource response"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_by_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    resource_type: str
    url: Optional[str] = None
    category: Optional[str] = None
    tags: List[str]
    view_count: int
    rating: Decimal
    is_official: bool
    is_free: bool
    created_at: datetime
