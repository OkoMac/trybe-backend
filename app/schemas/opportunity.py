"""Opportunity schemas - Pydantic models for API validation"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import uuid


class OpportunityBase(BaseModel):
    """Base opportunity schema"""
    title: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=20)
    company_name: str = Field(..., min_length=2, max_length=255)
    opportunity_type: str = Field(..., pattern="^(full_time|part_time|contract|freelance|gig|internship)$")
    location: Optional[dict] = None
    is_remote: bool = False
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    experience_level: Optional[str] = Field(None, pattern="^(entry|junior|mid|senior|expert)$")
    education_required: Optional[str] = None
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    salary_currency: str = Field(default="USD", max_length=3)
    hourly_rate: Optional[float] = Field(None, ge=0)
    benefits: Optional[List[str]] = None
    application_deadline: Optional[datetime] = None
    start_date: Optional[datetime] = None

    @field_validator("salary_max")
    @classmethod
    def validate_salary_range(cls, v: Optional[int], info) -> Optional[int]:
        """Validate salary_max is greater than salary_min"""
        if v is not None and info.data.get("salary_min") is not None:
            if v < info.data["salary_min"]:
                raise ValueError("salary_max must be greater than or equal to salary_min")
        return v


class OpportunityCreate(OpportunityBase):
    """Schema for creating a new opportunity"""
    pass


class OpportunityUpdate(BaseModel):
    """Schema for updating an opportunity"""
    title: Optional[str] = Field(None, min_length=5, max_length=255)
    description: Optional[str] = Field(None, min_length=20)
    company_name: Optional[str] = Field(None, min_length=2, max_length=255)
    opportunity_type: Optional[str] = Field(None, pattern="^(full_time|part_time|contract|freelance|gig|internship)$")
    status: Optional[str] = Field(None, pattern="^(open|closed|filled|archived)$")
    location: Optional[dict] = None
    is_remote: Optional[bool] = None
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    experience_level: Optional[str] = Field(None, pattern="^(entry|junior|mid|senior|expert)$")
    education_required: Optional[str] = None
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    salary_currency: Optional[str] = Field(None, max_length=3)
    hourly_rate: Optional[float] = Field(None, ge=0)
    benefits: Optional[List[str]] = None
    application_deadline: Optional[datetime] = None
    start_date: Optional[datetime] = None


class OpportunityResponse(OpportunityBase):
    """Schema for opportunity response"""
    id: uuid.UUID
    employer_id: uuid.UUID
    status: str
    views_count: int
    applications_count: int
    matches_count: int
    opportunity_metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OpportunityListResponse(BaseModel):
    """Schema for paginated opportunity list"""
    items: List[OpportunityResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SwipeCreate(BaseModel):
    """Schema for creating a swipe"""
    opportunity_id: uuid.UUID
    action: str = Field(..., pattern="^(like|pass|superlike)$")


class SwipeResponse(BaseModel):
    """Schema for swipe response"""
    id: uuid.UUID
    user_id: uuid.UUID
    opportunity_id: uuid.UUID
    action: str
    created_at: datetime
    is_match: bool = False  # True if the swipe resulted in a match

    model_config = {"from_attributes": True}


class MatchResponse(BaseModel):
    """Schema for match response"""
    id: uuid.UUID
    user_id: uuid.UUID
    opportunity_id: uuid.UUID
    employer_id: uuid.UUID
    status: str
    match_score: Optional[float] = None
    is_mutual: bool
    user_viewed: bool
    employer_viewed: bool
    match_metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None

    # Include opportunity details
    opportunity: Optional[OpportunityResponse] = None

    model_config = {"from_attributes": True}


class MatchListResponse(BaseModel):
    """Schema for paginated match list"""
    items: List[MatchResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class NearbyOpportunityResponse(OpportunityResponse):
    """Schema for nearby opportunity response with distance"""
    distance_km: Optional[float] = Field(None, description="Distance from search location in kilometers")
    distance_text: Optional[str] = Field(None, description="Formatted distance text")

    class Config:
        from_attributes = True


class NearbyOpportunityListResponse(BaseModel):
    """Schema for paginated nearby opportunity list"""
    items: List[NearbyOpportunityResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    search_radius_km: float
    search_location: dict = Field(..., description="Search center coordinates")

    class Config:
        from_attributes = True
