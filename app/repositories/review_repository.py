"""Review repository for database operations"""

from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict
from sqlalchemy import select, func, and_, or_, update, delete, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import uuid

from app.models.review import (
    Review,
    ReviewHelpful,
    ReviewFlag,
    ReviewSummary,
    ReviewTypeEnum,
    ReviewStatusEnum
)
from app.models.user import User
from app.schemas.review import ReviewFilters


class ReviewRepository:
    """Repository for review database operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_review(
        self,
        reviewer_id: uuid.UUID,
        review_type: ReviewTypeEnum,
        target_id: uuid.UUID,
        rating: int,
        comment: str,
        title: Optional[str] = None,
        ratings_breakdown: Optional[Dict] = None,
        is_verified_purchase: bool = False
    ) -> Review:
        """Create a new review"""
        review = Review(
            reviewer_id=reviewer_id,
            review_type=review_type,
            target_id=target_id,
            rating=rating,
            comment=comment,
            title=title,
            ratings_breakdown=ratings_breakdown,
            is_verified_purchase=is_verified_purchase,
            status=ReviewStatusEnum.approved if is_verified_purchase else ReviewStatusEnum.pending
        )

        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)

        # Update summary statistics
        await self._update_review_summary(target_id, review_type)

        return review

    async def get_review_by_id(self, review_id: uuid.UUID) -> Optional[Review]:
        """Get a review by ID"""
        result = await self.db.execute(
            select(Review)
            .options(selectinload(Review.reviewer))
            .where(Review.id == review_id, Review.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_reviews(
        self,
        filters: ReviewFilters
    ) -> Tuple[List[Review], int]:
        """Get reviews with filters and pagination"""
        # Build query
        query = select(Review).options(selectinload(Review.reviewer))

        # Apply filters
        conditions = [Review.deleted_at.is_(None)]

        if filters.review_type:
            conditions.append(Review.review_type == filters.review_type)

        if filters.target_id:
            conditions.append(Review.target_id == filters.target_id)

        if filters.rating:
            conditions.append(Review.rating == filters.rating)

        if filters.status:
            conditions.append(Review.status == filters.status)
        else:
            # Default to only showing approved reviews
            conditions.append(Review.status == ReviewStatusEnum.approved)

        if filters.verified_only:
            conditions.append(Review.is_verified_purchase == True)

        if filters.min_rating:
            conditions.append(Review.rating >= filters.min_rating)

        if filters.max_rating:
            conditions.append(Review.rating <= filters.max_rating)

        if filters.has_response is not None:
            if filters.has_response:
                conditions.append(Review.response.isnot(None))
            else:
                conditions.append(Review.response.is_(None))

        query = query.where(and_(*conditions))

        # Count total
        count_query = select(func.count()).select_from(Review).where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Sort
        if filters.sort_by == "rating":
            order_col = Review.rating
        elif filters.sort_by == "helpful_count":
            order_col = Review.helpful_count
        elif filters.sort_by == "updated_at":
            order_col = Review.updated_at
        else:
            order_col = Review.created_at

        if filters.sort_order == "asc":
            query = query.order_by(order_col.asc())
        else:
            query = query.order_by(order_col.desc())

        # Pagination
        offset = (filters.page - 1) * filters.page_size
        query = query.offset(offset).limit(filters.page_size)

        # Execute
        result = await self.db.execute(query)
        reviews = result.scalars().all()

        return list(reviews), total

    async def update_review(
        self,
        review_id: uuid.UUID,
        rating: Optional[int] = None,
        title: Optional[str] = None,
        comment: Optional[str] = None,
        ratings_breakdown: Optional[Dict] = None
    ) -> Optional[Review]:
        """Update a review"""
        review = await self.get_review_by_id(review_id)
        if not review:
            return None

        if rating is not None:
            review.rating = rating
        if title is not None:
            review.title = title
        if comment is not None:
            review.comment = comment
        if ratings_breakdown is not None:
            review.ratings_breakdown = ratings_breakdown

        review.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(review)

        # Update summary statistics
        await self._update_review_summary(review.target_id, review.review_type)

        return review

    async def delete_review(self, review_id: uuid.UUID) -> bool:
        """Soft delete a review"""
        review = await self.get_review_by_id(review_id)
        if not review:
            return False

        review.deleted_at = datetime.utcnow()
        await self.db.commit()

        # Update summary statistics
        await self._update_review_summary(review.target_id, review.review_type)

        return True

    async def add_response(
        self,
        review_id: uuid.UUID,
        response: str
    ) -> Optional[Review]:
        """Add a response to a review"""
        review = await self.get_review_by_id(review_id)
        if not review:
            return None

        review.response = response
        review.response_date = datetime.utcnow()
        review.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(review)

        return review

    async def vote_helpful(
        self,
        review_id: uuid.UUID,
        user_id: uuid.UUID,
        is_helpful: bool
    ) -> bool:
        """Vote on whether a review is helpful"""
        # Check if user already voted
        existing_vote = await self.db.execute(
            select(ReviewHelpful).where(
                and_(
                    ReviewHelpful.review_id == review_id,
                    ReviewHelpful.user_id == user_id
                )
            )
        )
        existing = existing_vote.scalar_one_or_none()

        if existing:
            # Update existing vote
            existing.is_helpful = is_helpful
        else:
            # Create new vote
            vote = ReviewHelpful(
                review_id=review_id,
                user_id=user_id,
                is_helpful=is_helpful
            )
            self.db.add(vote)

        await self.db.commit()

        # Update helpful count on review
        await self._update_helpful_count(review_id)

        return True

    async def flag_review(
        self,
        review_id: uuid.UUID,
        reporter_id: uuid.UUID,
        reason: str,
        details: Optional[str] = None
    ) -> ReviewFlag:
        """Flag a review for moderation"""
        flag = ReviewFlag(
            review_id=review_id,
            reporter_id=reporter_id,
            reason=reason,
            details=details
        )

        self.db.add(flag)

        # Increment flag count on review
        await self.db.execute(
            update(Review)
            .where(Review.id == review_id)
            .values(
                flag_count=Review.flag_count + 1,
                status=case(
                    (Review.flag_count >= 2, ReviewStatusEnum.flagged),
                    else_=Review.status
                )
            )
        )

        await self.db.commit()
        await self.db.refresh(flag)

        return flag

    async def moderate_review(
        self,
        review_id: uuid.UUID,
        status: ReviewStatusEnum,
        moderation_notes: Optional[str] = None
    ) -> Optional[Review]:
        """Moderate a review (admin function)"""
        review = await self.get_review_by_id(review_id)
        if not review:
            return None

        review.status = status
        review.moderation_notes = moderation_notes
        review.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(review)

        # Update summary if approved or rejected
        if status in [ReviewStatusEnum.approved, ReviewStatusEnum.rejected]:
            await self._update_review_summary(review.target_id, review.review_type)

        return review

    async def get_review_summary(
        self,
        target_id: uuid.UUID,
        review_type: ReviewTypeEnum
    ) -> Optional[ReviewSummary]:
        """Get review summary statistics for a target"""
        result = await self.db.execute(
            select(ReviewSummary).where(
                and_(
                    ReviewSummary.target_id == target_id,
                    ReviewSummary.review_type == review_type
                )
            )
        )
        return result.scalar_one_or_none()

    async def check_user_can_review(
        self,
        reviewer_id: uuid.UUID,
        target_id: uuid.UUID,
        review_type: ReviewTypeEnum
    ) -> Tuple[bool, Optional[str]]:
        """Check if a user can review a target (one review per user per target)"""
        result = await self.db.execute(
            select(Review).where(
                and_(
                    Review.reviewer_id == reviewer_id,
                    Review.target_id == target_id,
                    Review.review_type == review_type,
                    Review.deleted_at.is_(None)
                )
            )
        )
        existing_review = result.scalar_one_or_none()

        if existing_review:
            return False, "You have already reviewed this"

        # Additional checks can be added here
        # For example, check if user actually used the service

        return True, None

    async def _update_helpful_count(self, review_id: uuid.UUID):
        """Update the helpful count for a review"""
        result = await self.db.execute(
            select(func.count())
            .select_from(ReviewHelpful)
            .where(
                and_(
                    ReviewHelpful.review_id == review_id,
                    ReviewHelpful.is_helpful == True
                )
            )
        )
        count = result.scalar()

        await self.db.execute(
            update(Review)
            .where(Review.id == review_id)
            .values(helpful_count=count)
        )
        await self.db.commit()

    async def _update_review_summary(
        self,
        target_id: uuid.UUID,
        review_type: ReviewTypeEnum
    ):
        """Update or create review summary statistics"""
        # Get all approved, non-deleted reviews for target
        result = await self.db.execute(
            select(Review).where(
                and_(
                    Review.target_id == target_id,
                    Review.review_type == review_type,
                    Review.status == ReviewStatusEnum.approved,
                    Review.deleted_at.is_(None)
                )
            )
        )
        reviews = result.scalars().all()

        if not reviews:
            # No reviews, delete summary if it exists
            await self.db.execute(
                delete(ReviewSummary).where(
                    and_(
                        ReviewSummary.target_id == target_id,
                        ReviewSummary.review_type == review_type
                    )
                )
            )
            await self.db.commit()
            return

        # Calculate statistics
        total_reviews = len(reviews)
        total_rating = sum(r.rating for r in reviews)
        average_rating = round(total_rating / total_reviews, 2)

        # Rating distribution
        rating_distribution = {str(i): 0 for i in range(1, 6)}
        for review in reviews:
            rating_distribution[str(review.rating)] += 1

        # Get or create summary
        summary = await self.get_review_summary(target_id, review_type)

        if summary:
            # Update existing
            summary.total_reviews = total_reviews
            summary.average_rating = average_rating
            summary.rating_distribution = rating_distribution
            summary.last_updated = datetime.utcnow()
        else:
            # Create new
            summary = ReviewSummary(
                target_id=target_id,
                review_type=review_type,
                total_reviews=total_reviews,
                average_rating=average_rating,
                rating_distribution=rating_distribution
            )
            self.db.add(summary)

        await self.db.commit()
