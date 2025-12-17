"""Review and Rating schemas/DTOs"""

from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, validator
import uuid

from app.models.review import ReviewTypeEnum, ReviewStatusEnum


class ReviewBase(BaseModel):
    """Base review schema"""
    review_type: ReviewTypeEnum
    target_id: uuid.UUID
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5 stars")
    title: Optional[str] = Field(None, max_length=255)
    comment: str = Field(..., min_length=10, max_length=5000)
    ratings_breakdown: Optional[Dict[str, int]] = Field(
        None,
        description="Additional ratings (e.g., communication, quality, timeliness)"
    )

    @validator("rating")
    def validate_rating(cls, v):
        if not 1 <= v <= 5:
            raise ValueError("Rating must be between 1 and 5")
        return v

    @validator("ratings_breakdown")
    def validate_ratings_breakdown(cls, v):
        if v:
            for key, value in v.items():
                if not isinstance(value, int) or not 1 <= value <= 5:
                    raise ValueError(f"Rating '{key}' must be an integer between 1 and 5")
        return v


class ReviewCreate(ReviewBase):
    """Schema for creating a review"""
    pass


class ReviewUpdate(BaseModel):
    """Schema for updating a review"""
    rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = Field(None, max_length=255)
    comment: Optional[str] = Field(None, min_length=10, max_length=5000)
    ratings_breakdown: Optional[Dict[str, int]] = None


class ReviewResponse(ReviewBase):
    """Schema for review response"""
    id: uuid.UUID
    reviewer_id: uuid.UUID
    status: ReviewStatusEnum
    helpful_count: int
    is_verified_purchase: bool
    response: Optional[str]
    response_date: Optional[datetime]
    flag_count: int
    created_at: datetime
    updated_at: datetime

    # Optional reviewer info (can be populated from join)
    reviewer_name: Optional[str] = None
    reviewer_avatar: Optional[str] = None

    class Config:
        from_attributes = True


class ReviewWithDetails(ReviewResponse):
    """Schema for review with full details"""
    moderation_notes: Optional[str] = None
    deleted_at: Optional[datetime] = None


class ReviewListResponse(BaseModel):
    """Schema for paginated review list"""
    reviews: List[ReviewResponse]
    total: int
    page: int
    page_size: int
    average_rating: float
    rating_distribution: Dict[str, int]


class ReviewSummaryResponse(BaseModel):
    """Schema for review summary statistics"""
    target_id: uuid.UUID
    review_type: ReviewTypeEnum
    total_reviews: int
    average_rating: float
    rating_distribution: Dict[str, int]
    ratings_breakdown_avg: Optional[Dict[str, float]] = None
    last_updated: datetime

    class Config:
        from_attributes = True


class ReviewResponseCreate(BaseModel):
    """Schema for responding to a review"""
    response: str = Field(..., min_length=10, max_length=2000)


class ReviewFlagCreate(BaseModel):
    """Schema for flagging a review"""
    reason: str = Field(
        ...,
        description="Reason for flag: spam, inappropriate, offensive, fake, other"
    )
    details: Optional[str] = Field(None, max_length=500)

    @validator("reason")
    def validate_reason(cls, v):
        valid_reasons = ["spam", "inappropriate", "offensive", "fake", "misleading", "other"]
        if v.lower() not in valid_reasons:
            raise ValueError(f"Reason must be one of: {', '.join(valid_reasons)}")
        return v.lower()


class ReviewFlagResponse(BaseModel):
    """Schema for review flag response"""
    id: uuid.UUID
    review_id: uuid.UUID
    reporter_id: uuid.UUID
    reason: str
    details: Optional[str]
    resolved: bool
    resolved_by: Optional[uuid.UUID]
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewHelpfulVote(BaseModel):
    """Schema for marking a review as helpful"""
    is_helpful: bool = Field(..., description="True for helpful, False for not helpful")


class ReviewModerationUpdate(BaseModel):
    """Schema for moderating a review (admin only)"""
    status: ReviewStatusEnum
    moderation_notes: Optional[str] = Field(None, max_length=1000)


class ReviewStats(BaseModel):
    """Schema for review statistics"""
    total_reviews: int
    average_rating: float
    five_star: int
    four_star: int
    three_star: int
    two_star: int
    one_star: int
    verified_purchases: int
    recent_reviews: int  # Reviews in last 30 days


class ReviewFilters(BaseModel):
    """Schema for filtering reviews"""
    review_type: Optional[ReviewTypeEnum] = None
    target_id: Optional[uuid.UUID] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    status: Optional[ReviewStatusEnum] = None
    verified_only: bool = False
    min_rating: Optional[int] = Field(None, ge=1, le=5)
    max_rating: Optional[int] = Field(None, ge=1, le=5)
    has_response: Optional[bool] = None
    sort_by: str = Field("created_at", description="Sort by: created_at, rating, helpful_count")
    sort_order: str = Field("desc", description="Sort order: asc or desc")
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

    @validator("sort_by")
    def validate_sort_by(cls, v):
        valid_fields = ["created_at", "rating", "helpful_count", "updated_at"]
        if v not in valid_fields:
            raise ValueError(f"sort_by must be one of: {', '.join(valid_fields)}")
        return v

    @validator("sort_order")
    def validate_sort_order(cls, v):
        if v.lower() not in ["asc", "desc"]:
            raise ValueError("sort_order must be 'asc' or 'desc'")
        return v.lower()
