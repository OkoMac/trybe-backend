"""Analytics schemas - Pydantic models for analytics API"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid


# ============================================================================
# User Activity Schemas
# ============================================================================

class EventCreate(BaseModel):
    """Schema for tracking a user event"""
    event_type: str = Field(..., min_length=3, max_length=50)
    event_category: str = Field(..., pattern="^(user|opportunity|match|payment|learning|message|general)$")
    resource_id: Optional[uuid.UUID] = None
    resource_type: Optional[str] = Field(None, max_length=50)
    session_id: Optional[str] = None
    event_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class UserActivityResponse(BaseModel):
    """Schema for user activity response"""
    id: uuid.UUID
    user_id: Optional[uuid.UUID]
    event_type: str
    event_category: str
    resource_id: Optional[uuid.UUID]
    resource_type: Optional[str]
    session_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    country: Optional[str]
    city: Optional[str]
    event_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


# ============================================================================
# Platform Metrics Schemas
# ============================================================================

class PlatformMetricsResponse(BaseModel):
    """Schema for platform metrics response"""
    id: uuid.UUID
    metric_date: datetime
    metric_period: str

    # User metrics
    total_users: int
    new_users: int
    active_users: int
    verified_users: int

    # Opportunity metrics
    total_opportunities: int
    new_opportunities: int
    active_opportunities: int
    opportunity_views: int

    # Match metrics
    total_swipes: int
    total_likes: int
    total_matches: int
    new_matches: int
    match_acceptance_rate: Optional[float]

    # Payment metrics
    total_proposals: int
    new_proposals: int
    successful_payments: int
    failed_payments: int
    total_payment_volume: float
    platform_revenue: float

    # Learning metrics
    total_courses: int
    new_courses: int
    total_enrollments: int
    new_enrollments: int
    course_completions: int
    average_course_rating: Optional[float]

    # Message metrics
    total_conversations: int
    new_conversations: int
    total_messages: int
    new_messages: int

    # Engagement metrics
    average_session_duration: Optional[float]
    page_views: int
    unique_visitors: int

    metrics_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MetricsSummary(BaseModel):
    """Summarized metrics for dashboards"""
    period: str
    start_date: datetime
    end_date: datetime

    # User summary
    total_users: int
    new_users: int
    active_users: int
    user_growth_rate: float

    # Opportunity summary
    total_opportunities: int
    new_opportunities: int
    opportunity_views: int
    views_per_opportunity: float

    # Match summary
    total_matches: int
    new_matches: int
    match_rate: float

    # Payment summary
    total_payment_volume: float
    successful_payments: int
    payment_success_rate: float
    platform_revenue: float

    # Learning summary
    total_enrollments: int
    course_completions: int
    completion_rate: float

    # Engagement summary
    page_views: int
    average_session_duration: Optional[float]
    engagement_rate: float


# ============================================================================
# Analytics Query Schemas
# ============================================================================

class AnalyticsQuery(BaseModel):
    """Query parameters for analytics endpoints"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    period: str = Field(default="daily", pattern="^(hourly|daily|weekly|monthly)$")
    metric_type: Optional[str] = None


class UserAnalytics(BaseModel):
    """User-specific analytics"""
    user_id: uuid.UUID
    total_events: int
    event_breakdown: Dict[str, int]
    first_seen: datetime
    last_seen: datetime
    total_sessions: int
    average_session_duration: Optional[float]

    # User activity summary
    opportunities_created: int
    opportunities_viewed: int
    swipes_made: int
    matches_created: int
    messages_sent: int
    courses_enrolled: int
    courses_completed: int


class OpportunityAnalytics(BaseModel):
    """Opportunity performance analytics"""
    opportunity_id: uuid.UUID
    opportunity_title: str
    total_views: int
    unique_viewers: int
    total_swipes: int
    likes_received: int
    passes_received: int
    matches_created: int
    like_rate: float
    match_conversion_rate: float
    created_at: datetime


class CourseAnalytics(BaseModel):
    """Course performance analytics"""
    course_id: uuid.UUID
    course_title: str
    total_views: int
    total_enrollments: int
    active_enrollments: int
    completed_enrollments: int
    completion_rate: float
    average_progress: float
    average_rating: Optional[float]
    total_reviews: int
    created_at: datetime


class PaymentAnalytics(BaseModel):
    """Payment analytics"""
    period: str
    total_proposals: int
    accepted_proposals: int
    total_transactions: int
    successful_transactions: int
    failed_transactions: int
    total_volume: float
    platform_fees: float
    success_rate: float
    average_transaction_value: float


# ============================================================================
# Dashboard Schemas
# ============================================================================

class DashboardMetrics(BaseModel):
    """Comprehensive dashboard metrics"""

    # Overview stats
    total_users: int
    active_users_today: int
    new_users_today: int

    total_opportunities: int
    active_opportunities: int
    new_opportunities_today: int

    total_matches: int
    new_matches_today: int

    total_enrollments: int
    new_enrollments_today: int

    # Revenue
    total_revenue: float
    revenue_today: float
    revenue_this_month: float

    # Trends (vs previous period)
    user_growth_trend: float  # percentage change
    opportunity_growth_trend: float
    match_growth_trend: float
    revenue_growth_trend: float

    # Top performers
    top_opportunities: List[Dict[str, Any]]  # Top 5 by views
    top_courses: List[Dict[str, Any]]  # Top 5 by enrollments
    most_active_users: List[Dict[str, Any]]  # Top 5 by activity

    # Recent activity
    recent_matches: int  # last 24h
    recent_messages: int  # last 24h
    recent_payments: int  # last 24h


class ActivityTimeline(BaseModel):
    """Timeline of events for visualization"""
    timestamps: List[datetime]
    event_counts: List[int]
    event_type: str
    period: str


# ============================================================================
# System Log Schemas
# ============================================================================

class SystemLogResponse(BaseModel):
    """Schema for system log response"""
    id: uuid.UUID
    log_level: str
    log_category: str
    message: str
    user_id: Optional[uuid.UUID]
    endpoint: Optional[str]
    request_id: Optional[str]
    exception_type: Optional[str]
    stack_trace: Optional[str]
    log_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class LogQuery(BaseModel):
    """Query parameters for log endpoints"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    log_level: Optional[str] = Field(None, pattern="^(debug|info|warning|error|critical)$")
    log_category: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=1000)


# ============================================================================
# Report Schemas
# ============================================================================

class AnalyticsReport(BaseModel):
    """Comprehensive analytics report"""
    report_id: uuid.UUID
    report_type: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime

    summary: MetricsSummary
    user_analytics: Optional[List[UserAnalytics]] = None
    opportunity_analytics: Optional[List[OpportunityAnalytics]] = None
    course_analytics: Optional[List[CourseAnalytics]] = None
    payment_analytics: Optional[PaymentAnalytics] = None

    recommendations: List[str] = Field(
        default_factory=list,
        description="AI-generated insights and recommendations"
    )
