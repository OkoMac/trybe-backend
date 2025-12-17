"""Review API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import uuid

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.repositories.review_repository import ReviewRepository
from app.services.review_service import ReviewService
from app.schemas.review import (
    ReviewCreate,
    ReviewUpdate,
    ReviewResponse,
    ReviewWithDetails,
    ReviewListResponse,
    ReviewSummaryResponse,
    ReviewResponseCreate,
    ReviewFlagCreate,
    ReviewHelpfulVote,
    ReviewModerationUpdate,
    ReviewStats,
    ReviewFilters,
    ReviewTypeEnum,
    ReviewStatusEnum
)


router = APIRouter()


def get_review_service(db: AsyncSession = Depends(get_db)) -> ReviewService:
    """Dependency to get review service"""
    repository = ReviewRepository(db)
    return ReviewService(repository)


@router.post("/", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    review_data: ReviewCreate,
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service)
):
    """
    Create a new review

    - **review_type**: Type of entity being reviewed (opportunity, user, employer, hackathon)
    - **target_id**: ID of the entity being reviewed
    - **rating**: Star rating from 1-5
    - **title**: Optional review title
    - **comment**: Review text (minimum 10 characters)
    - **ratings_breakdown**: Optional additional ratings (e.g., communication, quality)

    Only one review per user per target is allowed.
    """
    review, error = await service.create_review(
        reviewer_id=current_user.id,
        review_data=review_data,
        is_verified_purchase=False  # TODO: Check if user actually used the service
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )

    return ReviewResponse(
        id=review.id,
        review_type=review.review_type,
        target_id=review.target_id,
        reviewer_id=review.reviewer_id,
        rating=review.rating,
        title=review.title,
        comment=review.comment,
        ratings_breakdown=review.ratings_breakdown,
        status=review.status,
        helpful_count=review.helpful_count,
        is_verified_purchase=review.is_verified_purchase,
        response=review.response,
        response_date=review.response_date,
        flag_count=review.flag_count,
        created_at=review.created_at,
        updated_at=review.updated_at,
        reviewer_name=current_user.full_name,
        reviewer_avatar=current_user.avatar_url
    )


@router.get("/", response_model=ReviewListResponse)
async def get_reviews(
    review_type: Optional[ReviewTypeEnum] = Query(None, description="Filter by review type"),
    target_id: Optional[uuid.UUID] = Query(None, description="Filter by target ID"),
    rating: Optional[int] = Query(None, ge=1, le=5, description="Filter by rating"),
    status: Optional[ReviewStatusEnum] = Query(None, description="Filter by status"),
    verified_only: bool = Query(False, description="Only show verified purchases"),
    min_rating: Optional[int] = Query(None, ge=1, le=5, description="Minimum rating filter"),
    max_rating: Optional[int] = Query(None, ge=1, le=5, description="Maximum rating filter"),
    has_response: Optional[bool] = Query(None, description="Filter by response presence"),
    sort_by: str = Query("created_at", description="Sort by: created_at, rating, helpful_count"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    service: ReviewService = Depends(get_review_service)
):
    """
    Get reviews with filters and pagination

    Returns a paginated list of reviews with aggregated statistics.
    """
    filters = ReviewFilters(
        review_type=review_type,
        target_id=target_id,
        rating=rating,
        status=status,
        verified_only=verified_only,
        min_rating=min_rating,
        max_rating=max_rating,
        has_response=has_response,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size
    )

    return await service.get_reviews(filters)


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: uuid.UUID,
    service: ReviewService = Depends(get_review_service)
):
    """Get a review by ID"""
    review = await service.get_review(review_id)

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )

    return ReviewResponse(
        id=review.id,
        review_type=review.review_type,
        target_id=review.target_id,
        reviewer_id=review.reviewer_id,
        rating=review.rating,
        title=review.title,
        comment=review.comment,
        ratings_breakdown=review.ratings_breakdown,
        status=review.status,
        helpful_count=review.helpful_count,
        is_verified_purchase=review.is_verified_purchase,
        response=review.response,
        response_date=review.response_date,
        flag_count=review.flag_count,
        created_at=review.created_at,
        updated_at=review.updated_at,
        reviewer_name=review.reviewer.full_name if review.reviewer else None,
        reviewer_avatar=review.reviewer.avatar_url if review.reviewer else None
    )


@router.put("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: uuid.UUID,
    review_data: ReviewUpdate,
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service)
):
    """
    Update your own review

    You can only update reviews that you created.
    """
    review, error = await service.update_review(
        review_id=review_id,
        reviewer_id=current_user.id,
        review_data=review_data
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )

    return ReviewResponse(
        id=review.id,
        review_type=review.review_type,
        target_id=review.target_id,
        reviewer_id=review.reviewer_id,
        rating=review.rating,
        title=review.title,
        comment=review.comment,
        ratings_breakdown=review.ratings_breakdown,
        status=review.status,
        helpful_count=review.helpful_count,
        is_verified_purchase=review.is_verified_purchase,
        response=review.response,
        response_date=review.response_date,
        flag_count=review.flag_count,
        created_at=review.created_at,
        updated_at=review.updated_at,
        reviewer_name=current_user.full_name,
        reviewer_avatar=current_user.avatar_url
    )


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service)
):
    """
    Delete your own review

    You can only delete reviews that you created.
    """
    success, error = await service.delete_review(
        review_id=review_id,
        user_id=current_user.id,
        is_admin=False  # TODO: Check if user is admin
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )


@router.post("/{review_id}/response", response_model=ReviewResponse)
async def add_review_response(
    review_id: uuid.UUID,
    response_data: ReviewResponseCreate,
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service)
):
    """
    Add a response to a review

    Only the owner of the reviewed entity can respond.
    """
    review, error = await service.add_response(
        review_id=review_id,
        target_owner_id=current_user.id,
        response_text=response_data.response
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )

    return ReviewResponse(
        id=review.id,
        review_type=review.review_type,
        target_id=review.target_id,
        reviewer_id=review.reviewer_id,
        rating=review.rating,
        title=review.title,
        comment=review.comment,
        ratings_breakdown=review.ratings_breakdown,
        status=review.status,
        helpful_count=review.helpful_count,
        is_verified_purchase=review.is_verified_purchase,
        response=review.response,
        response_date=review.response_date,
        flag_count=review.flag_count,
        created_at=review.created_at,
        updated_at=review.updated_at
    )


@router.post("/{review_id}/helpful")
async def vote_review_helpful(
    review_id: uuid.UUID,
    vote_data: ReviewHelpfulVote,
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service)
):
    """
    Vote on whether a review is helpful

    You can update your vote by calling this endpoint again.
    """
    success, error = await service.vote_helpful(
        review_id=review_id,
        user_id=current_user.id,
        is_helpful=vote_data.is_helpful
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )

    return {
        "success": True,
        "message": "Vote recorded successfully"
    }


@router.post("/{review_id}/flag")
async def flag_review(
    review_id: uuid.UUID,
    flag_data: ReviewFlagCreate,
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service)
):
    """
    Flag a review for moderation

    Reasons: spam, inappropriate, offensive, fake, misleading, other
    """
    flag, error = await service.flag_review(
        review_id=review_id,
        reporter_id=current_user.id,
        reason=flag_data.reason,
        details=flag_data.details
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )

    return {
        "success": True,
        "message": "Review flagged for moderation",
        "flag_id": str(flag.id)
    }


@router.get("/summary/{review_type}/{target_id}", response_model=ReviewSummaryResponse)
async def get_review_summary(
    review_type: ReviewTypeEnum,
    target_id: uuid.UUID,
    service: ReviewService = Depends(get_review_service)
):
    """
    Get review summary statistics for an entity

    Returns aggregated data including:
    - Total number of reviews
    - Average rating
    - Rating distribution (1-5 stars)
    - Additional breakdown if available
    """
    return await service.get_review_summary(target_id, review_type)


@router.get("/stats/{review_type}/{target_id}", response_model=ReviewStats)
async def get_review_stats(
    review_type: ReviewTypeEnum,
    target_id: uuid.UUID,
    service: ReviewService = Depends(get_review_service)
):
    """
    Get detailed review statistics

    Returns comprehensive stats for display on detail pages.
    """
    return await service.get_review_stats(target_id, review_type)


# Admin endpoints
@router.put("/{review_id}/moderate", response_model=ReviewResponse)
async def moderate_review(
    review_id: uuid.UUID,
    moderation_data: ReviewModerationUpdate,
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service)
):
    """
    Moderate a review (Admin only)

    Change review status to: pending, approved, rejected, or flagged
    """
    # TODO: Check if user is admin
    # if current_user.user_type != UserTypeEnum.admin:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Admin access required"
    #     )

    review, error = await service.moderate_review(
        review_id=review_id,
        status=moderation_data.status,
        moderation_notes=moderation_data.moderation_notes
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )

    return ReviewWithDetails(
        id=review.id,
        review_type=review.review_type,
        target_id=review.target_id,
        reviewer_id=review.reviewer_id,
        rating=review.rating,
        title=review.title,
        comment=review.comment,
        ratings_breakdown=review.ratings_breakdown,
        status=review.status,
        helpful_count=review.helpful_count,
        is_verified_purchase=review.is_verified_purchase,
        response=review.response,
        response_date=review.response_date,
        flag_count=review.flag_count,
        created_at=review.created_at,
        updated_at=review.updated_at,
        moderation_notes=review.moderation_notes,
        deleted_at=review.deleted_at
    )
