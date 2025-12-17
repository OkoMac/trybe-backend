"""Analytics endpoints - Platform metrics, event tracking, and reporting"""

from datetime import datetime, timedelta
from typing import Any, Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
import uuid

from app.core.database import get_db
from app.models.analytics import UserActivity, PlatformMetrics
from app.models.user import User
from app.models.opportunity import Opportunity, OpportunityStatusEnum
from app.models.payment import Transaction, TransactionStatusEnum
from app.models.learning import Course, CourseStatusEnum
from app.models.match import Match
from app.models.message import Message
from app.schemas.analytics import (
    EventCreate,
    UserActivityResponse,
    PlatformMetricsResponse,
    MetricsSummary,
    UserAnalytics,
    DashboardMetrics,
    AnalyticsQuery
)
from app.api.deps import get_current_user
from app.services.analytics_service import AnalyticsService

router = APIRouter()


# ============================================================================
# Event Tracking
# ============================================================================

@router.post("/events", response_model=UserActivityResponse, status_code=status.HTTP_201_CREATED)
async def track_event(
    event: EventCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Track a user event

    - **event_type**: Type of event (login, page_view, etc.)
    - **event_category**: Category (user, opportunity, match, payment, learning, message, general)
    - **resource_id**: Optional ID of related resource
    - **resource_type**: Optional type of resource
    - **session_id**: Session identifier
    - **event_metadata**: Additional event data
    """
    # Extract IP and user agent from request
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    activity = await AnalyticsService.track_event(
        db=db,
        event_type=event.event_type,
        event_category=event.event_category,
        user_id=current_user.id,
        resource_id=event.resource_id,
        resource_type=event.resource_type,
        session_id=event.session_id,
        ip_address=ip_address,
        user_agent=user_agent,
        event_metadata=event.event_metadata
    )

    return activity


@router.get("/events/my", response_model=List[UserActivityResponse])
async def get_my_events(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    event_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get current user's event history

    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    - **event_type**: Optional filter by event type
    - **start_date**: Optional filter by start date
    """
    query = select(UserActivity).where(UserActivity.user_id == current_user.id)

    if event_type:
        query = query.where(UserActivity.event_type == event_type)

    if start_date:
        query = query.where(UserActivity.created_at >= start_date)

    query = query.order_by(desc(UserActivity.created_at)).offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


# ============================================================================
# Platform Metrics
# ============================================================================

@router.get("/metrics/platform", response_model=List[PlatformMetricsResponse])
async def get_platform_metrics(
    start_date: Optional[datetime] = Query(default=None, description="Start date (default: 30 days ago)"),
    end_date: Optional[datetime] = Query(default=None, description="End date (default: now)"),
    period: str = Query(default="daily", pattern="^(hourly|daily|weekly|monthly)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get platform metrics for a date range

    - **start_date**: Start of date range
    - **end_date**: End of date range
    - **period**: Metric period (hourly, daily, weekly, monthly)

    Returns aggregated platform metrics including users, opportunities, matches, payments, learning, and messages.
    """
    metrics = await AnalyticsService.get_platform_metrics(
        db=db,
        start_date=start_date,
        end_date=end_date,
        period=period
    )

    return metrics


@router.post("/metrics/calculate", response_model=PlatformMetricsResponse)
async def calculate_metrics(
    target_date: Optional[datetime] = Query(default=None, description="Date to calculate (default: today)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Calculate and store platform metrics for a specific date

    Admin endpoint to manually trigger metric calculation.

    - **target_date**: Date to calculate metrics for (default: today)
    """
    # TODO: Add admin role check
    # For now, any authenticated user can trigger this

    if target_date is None:
        target_date = datetime.utcnow()

    metrics = await AnalyticsService.calculate_daily_metrics(db=db, target_date=target_date)

    return metrics


@router.get("/metrics/summary", response_model=MetricsSummary)
async def get_metrics_summary(
    period: str = Query(default="daily", pattern="^(daily|weekly|monthly)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get summarized platform metrics

    - **period**: Summary period (daily, weekly, monthly)

    Returns aggregated summary with growth rates and key performance indicators.
    """
    # Determine date range based on period
    end_date = datetime.utcnow()

    if period == "daily":
        start_date = end_date - timedelta(days=1)
        previous_start = start_date - timedelta(days=1)
    elif period == "weekly":
        start_date = end_date - timedelta(days=7)
        previous_start = start_date - timedelta(days=7)
    else:  # monthly
        start_date = end_date - timedelta(days=30)
        previous_start = start_date - timedelta(days=30)

    # Get current period metrics
    current_metrics = await AnalyticsService.get_platform_metrics(
        db=db,
        start_date=start_date,
        end_date=end_date,
        period="daily"
    )

    # Get previous period metrics for comparison
    previous_metrics = await AnalyticsService.get_platform_metrics(
        db=db,
        start_date=previous_start,
        end_date=start_date,
        period="daily"
    )

    # Aggregate metrics
    total_users = sum(m.total_users for m in current_metrics) // len(current_metrics) if current_metrics else 0
    new_users = sum(m.new_users for m in current_metrics)
    active_users = sum(m.active_users for m in current_metrics) // len(current_metrics) if current_metrics else 0

    total_opportunities = sum(m.total_opportunities for m in current_metrics) // len(current_metrics) if current_metrics else 0
    new_opportunities = sum(m.new_opportunities for m in current_metrics)
    opportunity_views = sum(m.opportunity_views for m in current_metrics)

    total_matches = sum(m.new_matches for m in current_metrics)
    total_payment_volume = sum(m.total_payment_volume for m in current_metrics)
    successful_payments = sum(m.successful_payments for m in current_metrics)
    total_enrollments = sum(m.new_enrollments for m in current_metrics)
    course_completions = sum(m.course_completions for m in current_metrics)

    # Calculate rates
    user_growth_rate = (new_users / total_users * 100) if total_users > 0 else 0.0
    views_per_opportunity = (opportunity_views / total_opportunities) if total_opportunities > 0 else 0.0
    match_rate = (total_matches / total_users * 100) if total_users > 0 else 0.0
    payment_success_rate = (successful_payments / (successful_payments + sum(m.failed_payments for m in current_metrics)) * 100) if (successful_payments + sum(m.failed_payments for m in current_metrics)) > 0 else 0.0
    completion_rate = (course_completions / total_enrollments * 100) if total_enrollments > 0 else 0.0

    page_views = sum(m.page_views for m in current_metrics)
    engagement_rate = (active_users / total_users * 100) if total_users > 0 else 0.0

    return MetricsSummary(
        period=period,
        start_date=start_date,
        end_date=end_date,
        total_users=total_users,
        new_users=new_users,
        active_users=active_users,
        user_growth_rate=round(user_growth_rate, 2),
        total_opportunities=total_opportunities,
        new_opportunities=new_opportunities,
        opportunity_views=opportunity_views,
        views_per_opportunity=round(views_per_opportunity, 2),
        total_matches=total_matches,
        new_matches=total_matches,
        match_rate=round(match_rate, 2),
        total_payment_volume=round(total_payment_volume, 2),
        successful_payments=successful_payments,
        payment_success_rate=round(payment_success_rate, 2),
        platform_revenue=sum(m.platform_revenue for m in current_metrics),
        total_enrollments=total_enrollments,
        course_completions=course_completions,
        completion_rate=round(completion_rate, 2),
        page_views=page_views,
        average_session_duration=sum(m.average_session_duration for m in current_metrics if m.average_session_duration) / len([m for m in current_metrics if m.average_session_duration]) if any(m.average_session_duration for m in current_metrics) else None,
        engagement_rate=round(engagement_rate, 2)
    )


# ============================================================================
# User Analytics
# ============================================================================

@router.get("/user-analytics/my", response_model=Dict)
async def get_my_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get analytics for the current user

    Returns detailed analytics including:
    - Total events
    - Event breakdown by type
    - First and last activity
    - Total sessions
    """
    analytics = await AnalyticsService.get_user_analytics(db=db, user_id=current_user.id)

    return analytics


@router.get("/user-analytics/{user_id}", response_model=Dict)
async def get_user_analytics(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get analytics for a specific user

    Admin endpoint to view analytics for any user.

    - **user_id**: ID of user to analyze
    """
    # TODO: Add admin role check

    analytics = await AnalyticsService.get_user_analytics(db=db, user_id=user_id)

    return analytics


# ============================================================================
# Dashboard
# ============================================================================

@router.get("/dashboard", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get comprehensive dashboard metrics

    Returns an overview of platform performance including:
    - User statistics (total, active, new)
    - Opportunity statistics
    - Match statistics
    - Learning statistics
    - Revenue metrics
    - Growth trends
    - Top performers
    """
    from app.models.opportunity import Opportunity
    from app.models.match import Match
    from app.models.learning import Enrollment, Course
    from app.models.payment import Transaction

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today_start - timedelta(days=30)

    # User stats
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar() or 0

    active_users_today_result = await db.execute(
        select(func.count(func.distinct(UserActivity.user_id)))
        .where(
            and_(
                UserActivity.created_at >= today_start,
                UserActivity.user_id.isnot(None)
            )
        )
    )
    active_users_today = active_users_today_result.scalar() or 0

    new_users_today_result = await db.execute(
        select(func.count(User.id))
        .where(User.created_at >= today_start)
    )
    new_users_today = new_users_today_result.scalar() or 0

    # Opportunity stats
    total_opps_result = await db.execute(select(func.count(Opportunity.id)))
    total_opportunities = total_opps_result.scalar() or 0

    active_opps_result = await db.execute(
        select(func.count(Opportunity.id))
        .where(Opportunity.status == OpportunityStatusEnum.open)
    )
    active_opportunities = active_opps_result.scalar() or 0

    new_opps_today_result = await db.execute(
        select(func.count(Opportunity.id))
        .where(Opportunity.created_at >= today_start)
    )
    new_opportunities_today = new_opps_today_result.scalar() or 0

    # Match stats
    total_matches_result = await db.execute(select(func.count(Match.id)))
    total_matches = total_matches_result.scalar() or 0

    new_matches_today_result = await db.execute(
        select(func.count(Match.id))
        .where(Match.created_at >= today_start)
    )
    new_matches_today = new_matches_today_result.scalar() or 0

    # Learning stats
    total_enrollments_result = await db.execute(select(func.count(Enrollment.id)))
    total_enrollments = total_enrollments_result.scalar() or 0

    new_enrollments_today_result = await db.execute(
        select(func.count(Enrollment.id))
        .where(Enrollment.enrolled_at >= today_start)
    )
    new_enrollments_today = new_enrollments_today_result.scalar() or 0

    # Revenue stats
    total_revenue_result = await db.execute(
        select(func.sum(Transaction.platform_fee))
        .where(Transaction.status == TransactionStatusEnum.succeeded)
    )
    total_revenue = total_revenue_result.scalar() or 0.0

    revenue_today_result = await db.execute(
        select(func.sum(Transaction.platform_fee))
        .where(
            and_(
                Transaction.status == TransactionStatusEnum.succeeded,
                Transaction.created_at >= today_start
            )
        )
    )
    revenue_today = revenue_today_result.scalar() or 0.0

    revenue_this_month_result = await db.execute(
        select(func.sum(Transaction.platform_fee))
        .where(
            and_(
                Transaction.status == TransactionStatusEnum.succeeded,
                Transaction.created_at >= month_start
            )
        )
    )
    revenue_this_month = revenue_this_month_result.scalar() or 0.0

    # Top opportunities by views
    top_opps_result = await db.execute(
        select(Opportunity.id, Opportunity.title, Opportunity.views_count)
        .where(Opportunity.status == OpportunityStatusEnum.open)
        .order_by(desc(Opportunity.views_count))
        .limit(5)
    )
    top_opportunities = [
        {"id": str(row[0]), "title": row[1], "views": row[2]}
        for row in top_opps_result
    ]

    # Top courses by enrollments
    top_courses_result = await db.execute(
        select(Course.id, Course.title, Course.enrollment_count)
        .where(Course.status == CourseStatusEnum.published)
        .order_by(desc(Course.enrollment_count))
        .limit(5)
    )
    top_courses = [
        {"id": str(row[0]), "title": row[1], "enrollments": row[2]}
        for row in top_courses_result
    ]

    # Most active users (by event count in last 30 days)
    most_active_result = await db.execute(
        select(
            UserActivity.user_id,
            User.full_name,
            func.count(UserActivity.id).label("event_count")
        )
        .join(User, User.id == UserActivity.user_id)
        .where(UserActivity.created_at >= month_start)
        .group_by(UserActivity.user_id, User.full_name)
        .order_by(desc("event_count"))
        .limit(5)
    )
    most_active_users = [
        {"user_id": str(row[0]), "name": row[1], "events": row[2]}
        for row in most_active_result
    ]

    # Recent activity counts (last 24h)
    recent_matches = new_matches_today

    recent_messages_result = await db.execute(
        select(func.count(Message.id))
        .where(Message.created_at >= today_start)
    )
    recent_messages = recent_messages_result.scalar() or 0

    recent_payments_result = await db.execute(
        select(func.count(Transaction.id))
        .where(
            and_(
                Transaction.status == TransactionStatusEnum.succeeded,
                Transaction.created_at >= today_start
            )
        )
    )
    recent_payments = recent_payments_result.scalar() or 0

    # Calculate growth trends (vs previous day/month)
    yesterday_start = today_start - timedelta(days=1)
    new_users_yesterday_result = await db.execute(
        select(func.count(User.id))
        .where(
            and_(
                User.created_at >= yesterday_start,
                User.created_at < today_start
            )
        )
    )
    new_users_yesterday = new_users_yesterday_result.scalar() or 0
    user_growth_trend = ((new_users_today - new_users_yesterday) / new_users_yesterday * 100) if new_users_yesterday > 0 else 0.0

    # Similar calculations for other trends...
    new_opps_yesterday_result = await db.execute(
        select(func.count(Opportunity.id))
        .where(
            and_(
                Opportunity.created_at >= yesterday_start,
                Opportunity.created_at < today_start
            )
        )
    )
    new_opps_yesterday = new_opps_yesterday_result.scalar() or 0
    opportunity_growth_trend = ((new_opportunities_today - new_opps_yesterday) / new_opps_yesterday * 100) if new_opps_yesterday > 0 else 0.0

    new_matches_yesterday_result = await db.execute(
        select(func.count(Match.id))
        .where(
            and_(
                Match.created_at >= yesterday_start,
                Match.created_at < today_start
            )
        )
    )
    new_matches_yesterday = new_matches_yesterday_result.scalar() or 0
    match_growth_trend = ((new_matches_today - new_matches_yesterday) / new_matches_yesterday * 100) if new_matches_yesterday > 0 else 0.0

    revenue_yesterday_result = await db.execute(
        select(func.sum(Transaction.platform_fee))
        .where(
            and_(
                Transaction.status == TransactionStatusEnum.succeeded,
                Transaction.created_at >= yesterday_start,
                Transaction.created_at < today_start
            )
        )
    )
    revenue_yesterday = revenue_yesterday_result.scalar() or 0.0
    revenue_growth_trend = ((revenue_today - revenue_yesterday) / revenue_yesterday * 100) if revenue_yesterday > 0 else 0.0

    return DashboardMetrics(
        total_users=total_users,
        active_users_today=active_users_today,
        new_users_today=new_users_today,
        total_opportunities=total_opportunities,
        active_opportunities=active_opportunities,
        new_opportunities_today=new_opportunities_today,
        total_matches=total_matches,
        new_matches_today=new_matches_today,
        total_enrollments=total_enrollments,
        new_enrollments_today=new_enrollments_today,
        total_revenue=round(total_revenue, 2),
        revenue_today=round(revenue_today, 2),
        revenue_this_month=round(revenue_this_month, 2),
        user_growth_trend=round(user_growth_trend, 2),
        opportunity_growth_trend=round(opportunity_growth_trend, 2),
        match_growth_trend=round(match_growth_trend, 2),
        revenue_growth_trend=round(revenue_growth_trend, 2),
        top_opportunities=top_opportunities,
        top_courses=top_courses,
        most_active_users=most_active_users,
        recent_matches=recent_matches,
        recent_messages=recent_messages,
        recent_payments=recent_payments
    )
