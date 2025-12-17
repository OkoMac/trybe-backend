"""Review service for business logic"""

from typing import Optional, List, Tuple, Dict
from datetime import datetime
import uuid

from app.repositories.review_repository import ReviewRepository
from app.models.review import Review, ReviewFlag, ReviewSummary, ReviewTypeEnum, ReviewStatusEnum
from app.schemas.review import (
    ReviewCreate,
    ReviewUpdate,
    ReviewFilters,
    ReviewResponse,
    ReviewListResponse,
    ReviewSummaryResponse,
    ReviewStats
)


class ReviewService:
    """Service for review business logic"""

    def __init__(self, repository: ReviewRepository):
        self.repository = repository

    async def create_review(
        self,
        reviewer_id: uuid.UUID,
        review_data: ReviewCreate,
        is_verified_purchase: bool = False
    ) -> Tuple[Optional[Review], Optional[str]]:
        """
        Create a new review

        Returns:
            Tuple of (Review, error_message)
        """
        # Check if user can review
        can_review, error_message = await self.repository.check_user_can_review(
            reviewer_id,
            review_data.target_id,
            review_data.review_type
        )

        if not can_review:
            return None, error_message

        # Create review
        review = await self.repository.create_review(
            reviewer_id=reviewer_id,
            review_type=review_data.review_type,
            target_id=review_data.target_id,
            rating=review_data.rating,
            comment=review_data.comment,
            title=review_data.title,
            ratings_breakdown=review_data.ratings_breakdown,
            is_verified_purchase=is_verified_purchase
        )

        return review, None

    async def get_review(self, review_id: uuid.UUID) -> Optional[Review]:
        """Get a review by ID"""
        return await self.repository.get_review_by_id(review_id)

    async def get_reviews(
        self,
        filters: ReviewFilters
    ) -> ReviewListResponse:
        """
        Get reviews with filters and pagination

        Returns paginated review list with statistics
        """
        reviews, total = await self.repository.get_reviews(filters)

        # Calculate average rating from returned reviews
        if reviews:
            avg_rating = sum(r.rating for r in reviews) / len(reviews)
            avg_rating = round(avg_rating, 2)

            # Calculate rating distribution
            rating_dist = {str(i): 0 for i in range(1, 6)}
            for review in reviews:
                rating_dist[str(review.rating)] += 1
        else:
            avg_rating = 0.0
            rating_dist = {str(i): 0 for i in range(1, 6)}

        # Convert to response format
        review_responses = [
            ReviewResponse(
                id=r.id,
                review_type=r.review_type,
                target_id=r.target_id,
                reviewer_id=r.reviewer_id,
                rating=r.rating,
                title=r.title,
                comment=r.comment,
                ratings_breakdown=r.ratings_breakdown,
                status=r.status,
                helpful_count=r.helpful_count,
                is_verified_purchase=r.is_verified_purchase,
                response=r.response,
                response_date=r.response_date,
                flag_count=r.flag_count,
                created_at=r.created_at,
                updated_at=r.updated_at,
                reviewer_name=r.reviewer.full_name if r.reviewer else None,
                reviewer_avatar=r.reviewer.avatar_url if r.reviewer else None
            )
            for r in reviews
        ]

        return ReviewListResponse(
            reviews=review_responses,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            average_rating=avg_rating,
            rating_distribution=rating_dist
        )

    async def update_review(
        self,
        review_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        review_data: ReviewUpdate
    ) -> Tuple[Optional[Review], Optional[str]]:
        """
        Update a review

        Returns:
            Tuple of (Review, error_message)
        """
        # Get existing review
        review = await self.repository.get_review_by_id(review_id)
        if not review:
            return None, "Review not found"

        # Check ownership
        if review.reviewer_id != reviewer_id:
            return None, "You can only edit your own reviews"

        # Update review
        updated_review = await self.repository.update_review(
            review_id=review_id,
            rating=review_data.rating,
            title=review_data.title,
            comment=review_data.comment,
            ratings_breakdown=review_data.ratings_breakdown
        )

        return updated_review, None

    async def delete_review(
        self,
        review_id: uuid.UUID,
        user_id: uuid.UUID,
        is_admin: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Delete a review

        Returns:
            Tuple of (success, error_message)
        """
        # Get existing review
        review = await self.repository.get_review_by_id(review_id)
        if not review:
            return False, "Review not found"

        # Check ownership (or admin)
        if not is_admin and review.reviewer_id != user_id:
            return False, "You can only delete your own reviews"

        # Delete review
        success = await self.repository.delete_review(review_id)
        return success, None

    async def add_response(
        self,
        review_id: uuid.UUID,
        target_owner_id: uuid.UUID,
        response_text: str
    ) -> Tuple[Optional[Review], Optional[str]]:
        """
        Add a response to a review (for the reviewed party)

        Returns:
            Tuple of (Review, error_message)
        """
        # Get review
        review = await self.repository.get_review_by_id(review_id)
        if not review:
            return None, "Review not found"

        # TODO: Verify that target_owner_id owns the reviewed entity
        # This would require additional logic based on review_type

        # Add response
        updated_review = await self.repository.add_response(review_id, response_text)
        return updated_review, None

    async def vote_helpful(
        self,
        review_id: uuid.UUID,
        user_id: uuid.UUID,
        is_helpful: bool
    ) -> Tuple[bool, Optional[str]]:
        """
        Vote on whether a review is helpful

        Returns:
            Tuple of (success, error_message)
        """
        # Check if review exists
        review = await self.repository.get_review_by_id(review_id)
        if not review:
            return False, "Review not found"

        # Can't vote on your own review
        if review.reviewer_id == user_id:
            return False, "You cannot vote on your own review"

        # Add vote
        success = await self.repository.vote_helpful(review_id, user_id, is_helpful)
        return success, None

    async def flag_review(
        self,
        review_id: uuid.UUID,
        reporter_id: uuid.UUID,
        reason: str,
        details: Optional[str] = None
    ) -> Tuple[Optional[ReviewFlag], Optional[str]]:
        """
        Flag a review for moderation

        Returns:
            Tuple of (ReviewFlag, error_message)
        """
        # Check if review exists
        review = await self.repository.get_review_by_id(review_id)
        if not review:
            return None, "Review not found"

        # Can't flag your own review
        if review.reviewer_id == reporter_id:
            return None, "You cannot flag your own review"

        # Create flag
        flag = await self.repository.flag_review(
            review_id=review_id,
            reporter_id=reporter_id,
            reason=reason,
            details=details
        )

        return flag, None

    async def moderate_review(
        self,
        review_id: uuid.UUID,
        status: ReviewStatusEnum,
        moderation_notes: Optional[str] = None
    ) -> Tuple[Optional[Review], Optional[str]]:
        """
        Moderate a review (admin only)

        Returns:
            Tuple of (Review, error_message)
        """
        review = await self.repository.moderate_review(
            review_id=review_id,
            status=status,
            moderation_notes=moderation_notes
        )

        if not review:
            return None, "Review not found"

        return review, None

    async def get_review_summary(
        self,
        target_id: uuid.UUID,
        review_type: ReviewTypeEnum
    ) -> Optional[ReviewSummaryResponse]:
        """
        Get review summary statistics for a target

        Returns aggregated review data
        """
        summary = await self.repository.get_review_summary(target_id, review_type)

        if not summary:
            # Return empty summary
            return ReviewSummaryResponse(
                target_id=target_id,
                review_type=review_type,
                total_reviews=0,
                average_rating=0.0,
                rating_distribution={str(i): 0 for i in range(1, 6)},
                last_updated=datetime.utcnow()
            )

        return ReviewSummaryResponse(
            target_id=summary.target_id,
            review_type=summary.review_type,
            total_reviews=summary.total_reviews,
            average_rating=summary.average_rating,
            rating_distribution=summary.rating_distribution,
            ratings_breakdown_avg=summary.ratings_breakdown_avg,
            last_updated=summary.last_updated
        )

    async def get_review_stats(
        self,
        target_id: uuid.UUID,
        review_type: ReviewTypeEnum
    ) -> ReviewStats:
        """
        Get detailed review statistics

        Returns comprehensive stats for display
        """
        summary = await self.repository.get_review_summary(target_id, review_type)

        if not summary:
            return ReviewStats(
                total_reviews=0,
                average_rating=0.0,
                five_star=0,
                four_star=0,
                three_star=0,
                two_star=0,
                one_star=0,
                verified_purchases=0,
                recent_reviews=0
            )

        # Get verified purchase count
        filters = ReviewFilters(
            target_id=target_id,
            review_type=review_type,
            verified_only=True,
            page=1,
            page_size=1
        )
        _, verified_count = await self.repository.get_reviews(filters)

        # Get recent reviews count (last 30 days)
        # TODO: Add date filtering to repository
        recent_count = 0

        return ReviewStats(
            total_reviews=summary.total_reviews,
            average_rating=summary.average_rating,
            five_star=summary.rating_distribution.get("5", 0),
            four_star=summary.rating_distribution.get("4", 0),
            three_star=summary.rating_distribution.get("3", 0),
            two_star=summary.rating_distribution.get("2", 0),
            one_star=summary.rating_distribution.get("1", 0),
            verified_purchases=verified_count,
            recent_reviews=recent_count
        )
