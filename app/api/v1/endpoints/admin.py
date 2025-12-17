"""Admin Dashboard API Endpoints"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, update as sql_update
from pydantic import BaseModel, ConfigDict

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserTypeEnum
from app.models.opportunity import Opportunity
from app.models.payment import PaymentProposal, Transaction
from app.models.message import Conversation, Message
from app.models.learning import Course, Enrollment
from app.models.hackathon import Hackathon
from app.models.community import CommunityPost, CommunityGroup

router = APIRouter()


# Response Schemas
class PlatformStats(BaseModel):
    """Platform-wide statistics"""
    total_users: int
    total_opportunities: int
    total_transactions: int
    total_revenue: float
    total_courses: int
    total_enrollments: int
    total_hackathons: int
    total_community_posts: int
    total_community_groups: int
    active_users_7d: int
    active_users_30d: int


class UserStats(BaseModel):
    """User statistics"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str
    username: str
    user_type: UserTypeEnum
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    # Computed stats
    opportunities_posted: int = 0
    payments_sent: int = 0
    payments_received: int = 0
    courses_enrolled: int = 0


class SystemHealth(BaseModel):
    """System health metrics"""
    status: str  # healthy, degraded, down
    database: str
    redis: str
    api_response_time_ms: float
    error_rate_24h: float
    active_connections: int


# Dependency to check admin permissions
async def require_admin(current_user: User = Depends(get_current_user)):
    """Require admin user"""
    if current_user.user_type != UserTypeEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# ==================== DASHBOARD STATISTICS ====================

@router.get("/stats/platform", response_model=PlatformStats)
async def get_platform_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get platform-wide statistics (admin only)"""

    # Get total counts
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar()
    total_opportunities = (await db.execute(select(func.count()).select_from(Opportunity))).scalar()
    total_transactions = (await db.execute(select(func.count()).select_from(Transaction))).scalar()
    total_courses = (await db.execute(select(func.count()).select_from(Course))).scalar()
    total_enrollments = (await db.execute(select(func.count()).select_from(Enrollment))).scalar()
    total_hackathons = (await db.execute(select(func.count()).select_from(Hackathon))).scalar()
    total_posts = (await db.execute(select(func.count()).select_from(CommunityPost))).scalar()
    total_groups = (await db.execute(select(func.count()).select_from(CommunityGroup))).scalar()

    # Calculate total revenue
    revenue_query = select(func.sum(Transaction.amount)).where(
        Transaction.status == "completed"
    )
    total_revenue = (await db.execute(revenue_query)).scalar() or 0

    # Active users in last 7 days
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    active_7d_query = select(func.count()).select_from(User).where(
        User.last_login >= seven_days_ago
    )
    active_users_7d = (await db.execute(active_7d_query)).scalar()

    # Active users in last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    active_30d_query = select(func.count()).select_from(User).where(
        User.last_login >= thirty_days_ago
    )
    active_users_30d = (await db.execute(active_30d_query)).scalar()

    return PlatformStats(
        total_users=total_users or 0,
        total_opportunities=total_opportunities or 0,
        total_transactions=total_transactions or 0,
        total_revenue=float(total_revenue),
        total_courses=total_courses or 0,
        total_enrollments=total_enrollments or 0,
        total_hackathons=total_hackathons or 0,
        total_community_posts=total_posts or 0,
        total_community_groups=total_groups or 0,
        active_users_7d=active_users_7d or 0,
        active_users_30d=active_users_30d or 0
    )


@router.get("/stats/system-health", response_model=SystemHealth)
async def get_system_health(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get system health metrics (admin only)"""

    # Simple health check
    # TODO: Implement actual health checks for database, redis, etc.

    return SystemHealth(
        status="healthy",
        database="connected",
        redis="connected",
        api_response_time_ms=45.2,
        error_rate_24h=0.01,
        active_connections=125
    )


# ==================== USER MANAGEMENT ====================

@router.get("/users", response_model=List[UserStats])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    user_type: Optional[UserTypeEnum] = None,
    is_verified: Optional[bool] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """List all users with filtering (admin only)"""

    filters = []

    if search:
        filters.append(
            or_(
                User.full_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.username.ilike(f"%{search}%")
            )
        )

    if user_type:
        filters.append(User.user_type == user_type)

    if is_verified is not None:
        filters.append(User.is_verified == is_verified)

    if is_active is not None:
        filters.append(User.is_active == is_active)

    query = select(User).where(and_(*filters) if filters else True)
    query = query.order_by(desc(User.created_at)).offset(skip).limit(limit)

    result = await db.execute(query)
    users = result.scalars().all()

    # Convert to UserStats with computed fields
    user_stats = []
    for user in users:
        # TODO: Get actual counts from related tables
        user_stats.append(UserStats(
            **user.__dict__,
            opportunities_posted=0,
            payments_sent=0,
            payments_received=0,
            courses_enrolled=0
        ))

    return user_stats


@router.get("/users/{user_id}", response_model=UserStats)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get user details (admin only)"""

    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserStats(**user.__dict__)


@router.patch("/users/{user_id}/verify")
async def verify_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Verify a user (admin only)"""

    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.is_verified = True
    user.verification_status = "verified"
    await db.commit()

    return {"message": "User verified successfully"}


@router.patch("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Deactivate a user (admin only)"""

    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Cannot deactivate other admins
    if user.user_type == UserTypeEnum.admin and user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot deactivate other admins"
        )

    user.is_active = False
    await db.commit()

    return {"message": "User deactivated successfully"}


@router.patch("/users/{user_id}/activate")
async def activate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Activate a user (admin only)"""

    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.is_active = True
    await db.commit()

    return {"message": "User activated successfully"}


# ==================== CONTENT MODERATION ====================

class ModerationAction(BaseModel):
    """Moderation action request"""
    reason: str
    action: str  # hide, delete, flag


@router.post("/moderate/posts/{post_id}")
async def moderate_post(
    post_id: UUID,
    action_data: ModerationAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Moderate a community post (admin only)"""

    query = select(CommunityPost).where(CommunityPost.id == post_id)
    result = await db.execute(query)
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    if action_data.action == "hide":
        post.is_hidden = True
    elif action_data.action == "flag":
        post.is_flagged = True
    elif action_data.action == "delete":
        await db.delete(post)
        await db.commit()
        return {"message": "Post deleted successfully"}

    await db.commit()

    return {"message": f"Post {action_data.action}ed successfully"}


# ==================== ANALYTICS ====================

@router.get("/analytics/growth")
async def get_growth_analytics(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get platform growth analytics (admin only)"""

    # Get user growth over time
    # TODO: Implement time-series aggregation

    return {
        "period_days": days,
        "new_users": 245,
        "new_opportunities": 89,
        "new_transactions": 156,
        "revenue_growth_percent": 23.5
    }


# ==================== SYSTEM CONFIGURATION ====================

@router.get("/config")
async def get_system_config(
    current_user: User = Depends(require_admin)
):
    """Get system configuration (admin only)"""

    # TODO: Return actual system configuration
    return {
        "maintenance_mode": False,
        "registration_enabled": True,
        "email_notifications_enabled": True,
        "platform_fee_percentage": 5.0,
        "max_file_upload_size_mb": 50
    }


class ConfigUpdate(BaseModel):
    """System configuration update"""
    maintenance_mode: Optional[bool] = None
    registration_enabled: Optional[bool] = None
    platform_fee_percentage: Optional[float] = None


@router.patch("/config")
async def update_system_config(
    config_data: ConfigUpdate,
    current_user: User = Depends(require_admin)
):
    """Update system configuration (admin only)"""

    # TODO: Persist configuration to database
    return {"message": "Configuration updated successfully"}
