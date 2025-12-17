"""Analytics Service - Event tracking, metrics calculation, and reporting"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc, or_
import uuid

from app.models.analytics import UserActivity, PlatformMetrics, SystemLog
from app.models.user import User
from app.models.opportunity import Opportunity, OpportunityStatusEnum
from app.models.match import Swipe, Match
from app.models.payment import PaymentProposal, Transaction, TransactionStatusEnum
from app.models.learning import Course, Enrollment, CourseStatusEnum
from app.models.message import Conversation, Message

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for analytics tracking and reporting"""

    @staticmethod
    async def track_event(
        db: AsyncSession,
        event_type: str,
        event_category: str,
        user_id: Optional[uuid.UUID] = None,
        resource_id: Optional[uuid.UUID] = None,
        resource_type: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        event_metadata: Optional[Dict] = None
    ) -> UserActivity:
        """
        Track a user event

        Args:
            db: Database session
            event_type: Type of event (from EventTypeEnum)
            event_category: Category (user, opportunity, match, etc.)
            user_id: Optional user who performed the action
            resource_id: Optional related resource ID
            resource_type: Optional type of resource
            session_id: Session identifier
            ip_address: User's IP address
            user_agent: Browser/client user agent
            event_metadata: Additional event data

        Returns:
            Created UserActivity record
        """
        activity = UserActivity(
            user_id=user_id,
            event_type=event_type,
            event_category=event_category,
            resource_id=resource_id,
            resource_type=resource_type,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            event_metadata=event_metadata or {}
        )

        db.add(activity)
        await db.commit()
        await db.refresh(activity)

        return activity

    @staticmethod
    async def get_platform_metrics(
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        period: str = "daily"
    ) -> List[PlatformMetrics]:
        """
        Get platform metrics for a date range

        Args:
            db: Database session
            start_date: Start of range (default: 30 days ago)
            end_date: End of range (default: now)
            period: Metric period (hourly, daily, weekly, monthly)

        Returns:
            List of PlatformMetrics
        """
        if end_date is None:
            end_date = datetime.utcnow()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        result = await db.execute(
            select(PlatformMetrics)
            .where(
                and_(
                    PlatformMetrics.metric_date >= start_date,
                    PlatformMetrics.metric_date <= end_date,
                    PlatformMetrics.metric_period == period
                )
            )
            .order_by(PlatformMetrics.metric_date)
        )

        return result.scalars().all()

    @staticmethod
    async def calculate_daily_metrics(
        db: AsyncSession,
        target_date: datetime
    ) -> PlatformMetrics:
        """
        Calculate and store daily platform metrics

        Args:
            db: Database session
            target_date: Date to calculate metrics for

        Returns:
            PlatformMetrics record
        """
        # Define date range for the day
        day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        # User metrics
        total_users_result = await db.execute(select(func.count(User.id)))
        total_users = total_users_result.scalar() or 0

        new_users_result = await db.execute(
            select(func.count(User.id))
            .where(
                and_(
                    User.created_at >= day_start,
                    User.created_at < day_end
                )
            )
        )
        new_users = new_users_result.scalar() or 0

        active_users_result = await db.execute(
            select(func.count(func.distinct(UserActivity.user_id)))
            .where(
                and_(
                    UserActivity.created_at >= day_start,
                    UserActivity.created_at < day_end,
                    UserActivity.user_id.isnot(None)
                )
            )
        )
        active_users = active_users_result.scalar() or 0

        verified_users_result = await db.execute(
            select(func.count(User.id)).where(User.is_verified == True)
        )
        verified_users = verified_users_result.scalar() or 0

        # Opportunity metrics
        total_opps_result = await db.execute(select(func.count(Opportunity.id)))
        total_opportunities = total_opps_result.scalar() or 0

        new_opps_result = await db.execute(
            select(func.count(Opportunity.id))
            .where(
                and_(
                    Opportunity.created_at >= day_start,
                    Opportunity.created_at < day_end
                )
            )
        )
        new_opportunities = new_opps_result.scalar() or 0

        active_opps_result = await db.execute(
            select(func.count(Opportunity.id))
            .where(Opportunity.status == OpportunityStatusEnum.open)
        )
        active_opportunities = active_opps_result.scalar() or 0

        opp_views_result = await db.execute(
            select(func.count(UserActivity.id))
            .where(
                and_(
                    UserActivity.event_type == "opportunity_view",
                    UserActivity.created_at >= day_start,
                    UserActivity.created_at < day_end
                )
            )
        )
        opportunity_views = opp_views_result.scalar() or 0

        # Match metrics
        total_swipes_result = await db.execute(
            select(func.count(Swipe.id))
            .where(
                and_(
                    Swipe.created_at >= day_start,
                    Swipe.created_at < day_end
                )
            )
        )
        total_swipes = total_swipes_result.scalar() or 0

        total_likes_result = await db.execute(
            select(func.count(Swipe.id))
            .where(
                and_(
                    Swipe.action.in_(["like", "superlike"]),
                    Swipe.created_at >= day_start,
                    Swipe.created_at < day_end
                )
            )
        )
        total_likes = total_likes_result.scalar() or 0

        all_matches_result = await db.execute(select(func.count(Match.id)))
        total_matches = all_matches_result.scalar() or 0

        new_matches_result = await db.execute(
            select(func.count(Match.id))
            .where(
                and_(
                    Match.created_at >= day_start,
                    Match.created_at < day_end
                )
            )
        )
        new_matches = new_matches_result.scalar() or 0

        # Calculate match acceptance rate
        accepted_matches_result = await db.execute(
            select(func.count(Match.id))
            .where(Match.status == "accepted")
        )
        accepted_matches = accepted_matches_result.scalar() or 0
        match_acceptance_rate = (accepted_matches / total_matches * 100) if total_matches > 0 else 0.0

        # Payment metrics
        total_proposals_result = await db.execute(select(func.count(PaymentProposal.id)))
        total_proposals = total_proposals_result.scalar() or 0

        new_proposals_result = await db.execute(
            select(func.count(PaymentProposal.id))
            .where(
                and_(
                    PaymentProposal.created_at >= day_start,
                    PaymentProposal.created_at < day_end
                )
            )
        )
        new_proposals = new_proposals_result.scalar() or 0

        successful_payments_result = await db.execute(
            select(func.count(Transaction.id))
            .where(
                and_(
                    Transaction.status == TransactionStatusEnum.succeeded,
                    Transaction.created_at >= day_start,
                    Transaction.created_at < day_end
                )
            )
        )
        successful_payments = successful_payments_result.scalar() or 0

        failed_payments_result = await db.execute(
            select(func.count(Transaction.id))
            .where(
                and_(
                    Transaction.status == TransactionStatusEnum.failed,
                    Transaction.created_at >= day_start,
                    Transaction.created_at < day_end
                )
            )
        )
        failed_payments = failed_payments_result.scalar() or 0

        payment_volume_result = await db.execute(
            select(func.sum(Transaction.amount))
            .where(
                and_(
                    Transaction.status == TransactionStatusEnum.succeeded,
                    Transaction.created_at >= day_start,
                    Transaction.created_at < day_end
                )
            )
        )
        total_payment_volume = payment_volume_result.scalar() or 0.0

        platform_revenue_result = await db.execute(
            select(func.sum(Transaction.platform_fee))
            .where(
                and_(
                    Transaction.status == TransactionStatusEnum.succeeded,
                    Transaction.created_at >= day_start,
                    Transaction.created_at < day_end
                )
            )
        )
        platform_revenue = platform_revenue_result.scalar() or 0.0

        # Learning metrics
        total_courses_result = await db.execute(select(func.count(Course.id)))
        total_courses = total_courses_result.scalar() or 0

        new_courses_result = await db.execute(
            select(func.count(Course.id))
            .where(
                and_(
                    Course.created_at >= day_start,
                    Course.created_at < day_end
                )
            )
        )
        new_courses = new_courses_result.scalar() or 0

        total_enrollments_result = await db.execute(select(func.count(Enrollment.id)))
        total_enrollments = total_enrollments_result.scalar() or 0

        new_enrollments_result = await db.execute(
            select(func.count(Enrollment.id))
            .where(
                and_(
                    Enrollment.enrolled_at >= day_start,
                    Enrollment.enrolled_at < day_end
                )
            )
        )
        new_enrollments = new_enrollments_result.scalar() or 0

        course_completions_result = await db.execute(
            select(func.count(Enrollment.id))
            .where(
                and_(
                    Enrollment.is_completed == True,
                    Enrollment.completed_at >= day_start,
                    Enrollment.completed_at < day_end
                )
            )
        )
        course_completions = course_completions_result.scalar() or 0

        avg_rating_result = await db.execute(
            select(func.avg(Course.average_rating))
            .where(Course.average_rating.isnot(None))
        )
        average_course_rating = avg_rating_result.scalar()

        # Message metrics
        total_conversations_result = await db.execute(select(func.count(Conversation.id)))
        total_conversations = total_conversations_result.scalar() or 0

        new_conversations_result = await db.execute(
            select(func.count(Conversation.id))
            .where(
                and_(
                    Conversation.created_at >= day_start,
                    Conversation.created_at < day_end
                )
            )
        )
        new_conversations = new_conversations_result.scalar() or 0

        total_messages_result = await db.execute(select(func.count(Message.id)))
        total_messages = total_messages_result.scalar() or 0

        new_messages_result = await db.execute(
            select(func.count(Message.id))
            .where(
                and_(
                    Message.created_at >= day_start,
                    Message.created_at < day_end
                )
            )
        )
        new_messages = new_messages_result.scalar() or 0

        # Page views
        page_views_result = await db.execute(
            select(func.count(UserActivity.id))
            .where(
                and_(
                    UserActivity.event_type == "page_view",
                    UserActivity.created_at >= day_start,
                    UserActivity.created_at < day_end
                )
            )
        )
        page_views = page_views_result.scalar() or 0

        unique_visitors_result = await db.execute(
            select(func.count(func.distinct(UserActivity.session_id)))
            .where(
                and_(
                    UserActivity.created_at >= day_start,
                    UserActivity.created_at < day_end,
                    UserActivity.session_id.isnot(None)
                )
            )
        )
        unique_visitors = unique_visitors_result.scalar() or 0

        # Check if metrics already exist for this date
        existing_result = await db.execute(
            select(PlatformMetrics)
            .where(
                and_(
                    PlatformMetrics.metric_date == day_start,
                    PlatformMetrics.metric_period == "daily"
                )
            )
        )
        existing_metrics = existing_result.scalar_one_or_none()

        if existing_metrics:
            # Update existing metrics
            existing_metrics.total_users = total_users
            existing_metrics.new_users = new_users
            existing_metrics.active_users = active_users
            existing_metrics.verified_users = verified_users
            existing_metrics.total_opportunities = total_opportunities
            existing_metrics.new_opportunities = new_opportunities
            existing_metrics.active_opportunities = active_opportunities
            existing_metrics.opportunity_views = opportunity_views
            existing_metrics.total_swipes = total_swipes
            existing_metrics.total_likes = total_likes
            existing_metrics.total_matches = total_matches
            existing_metrics.new_matches = new_matches
            existing_metrics.match_acceptance_rate = match_acceptance_rate
            existing_metrics.total_proposals = total_proposals
            existing_metrics.new_proposals = new_proposals
            existing_metrics.successful_payments = successful_payments
            existing_metrics.failed_payments = failed_payments
            existing_metrics.total_payment_volume = total_payment_volume
            existing_metrics.platform_revenue = platform_revenue
            existing_metrics.total_courses = total_courses
            existing_metrics.new_courses = new_courses
            existing_metrics.total_enrollments = total_enrollments
            existing_metrics.new_enrollments = new_enrollments
            existing_metrics.course_completions = course_completions
            existing_metrics.average_course_rating = average_course_rating
            existing_metrics.total_conversations = total_conversations
            existing_metrics.new_conversations = new_conversations
            existing_metrics.total_messages = total_messages
            existing_metrics.new_messages = new_messages
            existing_metrics.page_views = page_views
            existing_metrics.unique_visitors = unique_visitors
            existing_metrics.updated_at = datetime.utcnow()

            await db.commit()
            await db.refresh(existing_metrics)
            return existing_metrics
        else:
            # Create new metrics
            metrics = PlatformMetrics(
                metric_date=day_start,
                metric_period="daily",
                total_users=total_users,
                new_users=new_users,
                active_users=active_users,
                verified_users=verified_users,
                total_opportunities=total_opportunities,
                new_opportunities=new_opportunities,
                active_opportunities=active_opportunities,
                opportunity_views=opportunity_views,
                total_swipes=total_swipes,
                total_likes=total_likes,
                total_matches=total_matches,
                new_matches=new_matches,
                match_acceptance_rate=match_acceptance_rate,
                total_proposals=total_proposals,
                new_proposals=new_proposals,
                successful_payments=successful_payments,
                failed_payments=failed_payments,
                total_payment_volume=total_payment_volume,
                platform_revenue=platform_revenue,
                total_courses=total_courses,
                new_courses=new_courses,
                total_enrollments=total_enrollments,
                new_enrollments=new_enrollments,
                course_completions=course_completions,
                average_course_rating=average_course_rating,
                total_conversations=total_conversations,
                new_conversations=new_conversations,
                total_messages=total_messages,
                new_messages=new_messages,
                page_views=page_views,
                unique_visitors=unique_visitors
            )

            db.add(metrics)
            await db.commit()
            await db.refresh(metrics)

            return metrics

    @staticmethod
    async def get_user_analytics(
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> Dict:
        """
        Get analytics for a specific user

        Args:
            db: Database session
            user_id: User to analyze

        Returns:
            Dictionary of user analytics
        """
        # Total events
        total_events_result = await db.execute(
            select(func.count(UserActivity.id))
            .where(UserActivity.user_id == user_id)
        )
        total_events = total_events_result.scalar() or 0

        # Event breakdown
        event_breakdown_result = await db.execute(
            select(
                UserActivity.event_type,
                func.count(UserActivity.id)
            )
            .where(UserActivity.user_id == user_id)
            .group_by(UserActivity.event_type)
        )
        event_breakdown = {row[0]: row[1] for row in event_breakdown_result}

        # First and last seen
        first_seen_result = await db.execute(
            select(func.min(UserActivity.created_at))
            .where(UserActivity.user_id == user_id)
        )
        first_seen = first_seen_result.scalar()

        last_seen_result = await db.execute(
            select(func.max(UserActivity.created_at))
            .where(UserActivity.user_id == user_id)
        )
        last_seen = last_seen_result.scalar()

        # Total sessions
        total_sessions_result = await db.execute(
            select(func.count(func.distinct(UserActivity.session_id)))
            .where(
                and_(
                    UserActivity.user_id == user_id,
                    UserActivity.session_id.isnot(None)
                )
            )
        )
        total_sessions = total_sessions_result.scalar() or 0

        return {
            "user_id": str(user_id),
            "total_events": total_events,
            "event_breakdown": event_breakdown,
            "first_seen": first_seen,
            "last_seen": last_seen,
            "total_sessions": total_sessions
        }
