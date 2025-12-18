"""
Swipe Service for Trybe Mobile Interface
Provides Tinder-style swipe functionality for opportunities and connections
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, not_, func
from enum import Enum
import logging
import random

from app.models.user import User
from app.models.opportunity import Opportunity

logger = logging.getLogger(__name__)


class SwipeAction(str, Enum):
    """Swipe action types"""
    RIGHT = "right"  # Interested/Like
    LEFT = "left"    # Not interested/Pass
    UP = "up"        # Super like/Priority interest


class SwipeType(str, Enum):
    """Types of swipeable content"""
    OPPORTUNITY = "opportunity"
    PROFILE = "profile"
    COMPANY = "company"


class SwipeService:
    """Service for managing swipe-based interactions"""

    def __init__(self):
        """Initialize swipe service"""
        self.cards_per_batch = 20  # Number of cards to load at once
        self.match_threshold = 0.7  # Skill match percentage for recommendations

    # ==================== Card Generation ====================

    async def get_swipe_cards(
        self,
        db: AsyncSession,
        user_id: str,
        swipe_type: SwipeType = SwipeType.OPPORTUNITY,
        limit: int = 20,
        include_seen: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get cards for swiping

        Args:
            db: Database session
            user_id: Current user ID
            swipe_type: Type of content to swipe (opportunity, profile, company)
            limit: Number of cards to return
            include_seen: Include previously seen cards

        Returns:
            List of swipeable cards
        """
        try:
            if swipe_type == SwipeType.OPPORTUNITY:
                return await self._get_opportunity_cards(db, user_id, limit, include_seen)
            elif swipe_type == SwipeType.PROFILE:
                return await self._get_profile_cards(db, user_id, limit, include_seen)
            elif swipe_type == SwipeType.COMPANY:
                return await self._get_company_cards(db, user_id, limit, include_seen)
            else:
                raise ValueError(f"Invalid swipe type: {swipe_type}")

        except Exception as e:
            logger.error(f"Failed to get swipe cards: {str(e)}")
            raise

    async def _get_opportunity_cards(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int,
        include_seen: bool
    ) -> List[Dict[str, Any]]:
        """Get opportunity cards optimized for swiping"""
        # TODO: Implement actual database query
        # For now, return mock data structure

        # Get user profile
        user = await self._get_user(db, user_id)
        user_skills = user.get("skills", [])
        user_location = user.get("location", "")

        # Get opportunities (mock)
        opportunities = await self._fetch_opportunities(db, user_id, limit, include_seen)

        cards = []
        for opp in opportunities:
            # Calculate match score
            match_score = self._calculate_match_score(user_skills, opp.get("skills_required", []))

            # Calculate distance (if geolocation available)
            distance = self._calculate_distance(user_location, opp.get("location", ""))

            card = {
                "id": opp.get("id"),
                "type": "opportunity",
                "title": opp.get("title"),
                "company_name": opp.get("company_name"),
                "company_logo": opp.get("company_logo"),
                "description": opp.get("description", "")[:200] + "...",  # Truncated for mobile
                "category": opp.get("category"),
                "opportunity_type": opp.get("opportunity_type"),
                "location": opp.get("location"),
                "remote": opp.get("remote", False),
                "salary_min": opp.get("salary_min"),
                "salary_max": opp.get("salary_max"),
                "currency": opp.get("currency", "USD"),
                "skills_required": opp.get("skills_required", [])[:5],  # Top 5 skills
                "match_score": round(match_score * 100),  # Percentage
                "distance": distance,
                "posted_ago": self._format_time_ago(opp.get("created_at")),
                "application_count": opp.get("application_count", 0),
                "image": opp.get("image_url"),  # Card image/background
                "badges": self._generate_badges(opp),
                "swipe_metadata": {
                    "seen_at": None,
                    "swipe_action": None,
                    "is_new": not include_seen
                }
            }
            cards.append(card)

        return cards

    async def _get_profile_cards(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int,
        include_seen: bool
    ) -> List[Dict[str, Any]]:
        """Get user profile cards for networking"""
        # Get current user
        user = await self._get_user(db, user_id)
        user_interests = user.get("interests", [])

        # Get other users (mock)
        profiles = await self._fetch_profiles(db, user_id, limit, include_seen)

        cards = []
        for profile in profiles:
            match_score = self._calculate_interest_match(user_interests, profile.get("interests", []))

            card = {
                "id": profile.get("id"),
                "type": "profile",
                "full_name": profile.get("full_name"),
                "username": profile.get("username"),
                "profile_picture": profile.get("profile_picture"),
                "bio": profile.get("bio", "")[:150] + "...",
                "location": profile.get("location"),
                "user_type": profile.get("user_type"),
                "skills": profile.get("skills", [])[:5],
                "interests": profile.get("interests", [])[:5],
                "experience_level": profile.get("experience_level"),
                "match_score": round(match_score * 100),
                "mutual_connections": 0,  # TODO: Calculate
                "badges": [
                    {"label": "Verified", "color": "blue"} if profile.get("is_verified") else None,
                    {"label": profile.get("user_type", "").title(), "color": "green"}
                ],
                "stats": {
                    "projects_completed": profile.get("projects_completed", 0),
                    "average_rating": profile.get("average_rating", 0.0),
                    "response_time": profile.get("response_time", "1 hour")
                },
                "swipe_metadata": {
                    "seen_at": None,
                    "swipe_action": None,
                    "is_new": not include_seen
                }
            }
            cards.append(card)

        return cards

    async def _get_company_cards(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int,
        include_seen: bool
    ) -> List[Dict[str, Any]]:
        """Get company cards for discovery"""
        companies = await self._fetch_companies(db, user_id, limit, include_seen)

        cards = []
        for company in companies:
            card = {
                "id": company.get("id"),
                "type": "company",
                "name": company.get("name"),
                "logo": company.get("logo"),
                "description": company.get("description", "")[:200] + "...",
                "industry": company.get("industry"),
                "size": company.get("size"),
                "location": company.get("location"),
                "website": company.get("website"),
                "active_opportunities_count": company.get("active_opportunities_count", 0),
                "badges": [
                    {"label": "Verified", "color": "blue"} if company.get("is_verified") else None,
                    {"label": "Hiring", "color": "green"} if company.get("active_opportunities_count", 0) > 0 else None
                ],
                "culture_tags": company.get("culture_tags", []),
                "benefits": company.get("benefits", [])[:3],
                "swipe_metadata": {
                    "seen_at": None,
                    "swipe_action": None,
                    "is_new": not include_seen
                }
            }
            cards.append(card)

        return cards

    # ==================== Swipe Actions ====================

    async def record_swipe(
        self,
        db: AsyncSession,
        user_id: str,
        card_id: str,
        card_type: SwipeType,
        action: SwipeAction,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Record a swipe action

        Args:
            db: Database session
            user_id: User performing the swipe
            card_id: ID of the card being swiped
            card_type: Type of card (opportunity, profile, company)
            action: Swipe action (right, left, up)
            metadata: Additional metadata (swipe speed, position, etc.)

        Returns:
            Swipe result with match information
        """
        try:
            swipe_record = {
                "id": self._generate_swipe_id(),
                "user_id": user_id,
                "card_id": card_id,
                "card_type": card_type,
                "action": action,
                "swiped_at": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }

            # TODO: Save to database

            # Check for matches
            match_result = None
            if action in [SwipeAction.RIGHT, SwipeAction.UP]:
                match_result = await self._check_for_match(db, user_id, card_id, card_type, action)

            result = {
                "swipe_id": swipe_record["id"],
                "action": action,
                "is_match": match_result is not None,
                "match": match_result,
                "next_card": None  # Will be populated by client
            }

            # Handle super like (up swipe) - Send notification
            if action == SwipeAction.UP:
                await self._handle_super_like(db, user_id, card_id, card_type)

            logger.info(f"Recorded swipe: user={user_id}, card={card_id}, action={action}")

            return result

        except Exception as e:
            logger.error(f"Failed to record swipe: {str(e)}")
            raise

    async def _check_for_match(
        self,
        db: AsyncSession,
        user_id: str,
        card_id: str,
        card_type: SwipeType,
        action: SwipeAction
    ) -> Optional[Dict[str, Any]]:
        """
        Check if swipe results in a match

        For opportunities: Right swipe = application intent
        For profiles: Check if other user also swiped right
        For companies: Right swipe = follow
        """
        if card_type == SwipeType.OPPORTUNITY:
            # Opportunity swipe right = express interest
            return {
                "type": "opportunity_interest",
                "message": "You've shown interest! Apply now to get noticed.",
                "action_url": f"/api/v1/opportunities/{card_id}/apply"
            }

        elif card_type == SwipeType.PROFILE:
            # Check if other user swiped right on you
            mutual_interest = await self._check_mutual_swipe(db, user_id, card_id)

            if mutual_interest:
                return {
                    "type": "profile_match",
                    "message": "It's a match! You can now connect.",
                    "profile": await self._get_profile_summary(db, card_id),
                    "action_url": f"/api/v1/messages/start/{card_id}"
                }

        elif card_type == SwipeType.COMPANY:
            # Company swipe right = follow
            return {
                "type": "company_follow",
                "message": "Following! You'll see their updates.",
                "action_url": f"/api/v1/companies/{card_id}"
            }

        return None

    async def _check_mutual_swipe(
        self,
        db: AsyncSession,
        user_id: str,
        other_user_id: str
    ) -> bool:
        """Check if two users have swiped right on each other"""
        # TODO: Implement actual database query
        # For now, return mock result
        return random.choice([True, False])

    async def _handle_super_like(
        self,
        db: AsyncSession,
        user_id: str,
        card_id: str,
        card_type: SwipeType
    ):
        """Handle super like action - send notification"""
        # TODO: Send push notification to the recipient
        # TODO: Increase visibility of the swiper's profile
        logger.info(f"Super like: user={user_id}, target={card_id}, type={card_type}")
        pass

    # ==================== Swipe History & Analytics ====================

    async def get_swipe_history(
        self,
        db: AsyncSession,
        user_id: str,
        action: Optional[SwipeAction] = None,
        card_type: Optional[SwipeType] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get user's swipe history

        Args:
            db: Database session
            user_id: User ID
            action: Filter by action (optional)
            card_type: Filter by card type (optional)
            limit: Number of records to return

        Returns:
            List of swipe records
        """
        # TODO: Implement actual database query
        return []

    async def get_matches(
        self,
        db: AsyncSession,
        user_id: str,
        match_type: Optional[SwipeType] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get user's matches"""
        # TODO: Implement actual database query
        return []

    async def get_swipe_stats(
        self,
        db: AsyncSession,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get swipe statistics for user

        Returns metrics like:
        - Total swipes
        - Right/left/up swipe counts
        - Match rate
        - Response rate
        """
        # TODO: Implement actual statistics calculation
        return {
            "total_swipes": 0,
            "right_swipes": 0,
            "left_swipes": 0,
            "super_likes": 0,
            "matches": 0,
            "match_rate": 0.0,
            "response_rate": 0.0,
            "average_swipes_per_day": 0.0
        }

    # ==================== Preferences & Settings ====================

    async def get_swipe_preferences(
        self,
        db: AsyncSession,
        user_id: str
    ) -> Dict[str, Any]:
        """Get user's swipe preferences"""
        # TODO: Get from database
        return {
            "opportunity_types": ["full-time", "part-time", "contract", "gig"],
            "remote_preference": "any",  # any, remote-only, on-site-only
            "salary_min": None,
            "location_radius_km": 50,
            "experience_levels": ["entry", "mid", "senior"],
            "categories": [],  # Empty = all categories
            "show_seen_cards": False,
            "auto_swipe_enabled": False
        }

    async def update_swipe_preferences(
        self,
        db: AsyncSession,
        user_id: str,
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user's swipe preferences"""
        # TODO: Save to database
        logger.info(f"Updated swipe preferences for user {user_id}")
        return preferences

    # ==================== Helper Methods ====================

    def _calculate_match_score(
        self,
        user_skills: List[str],
        required_skills: List[str]
    ) -> float:
        """Calculate skill match score (0.0 to 1.0)"""
        if not required_skills:
            return 0.5

        user_skills_lower = [s.lower() for s in user_skills]
        required_skills_lower = [s.lower() for s in required_skills]

        matches = sum(1 for skill in required_skills_lower if skill in user_skills_lower)
        return matches / len(required_skills_lower) if required_skills_lower else 0.0

    def _calculate_interest_match(
        self,
        user_interests: List[str],
        other_interests: List[str]
    ) -> float:
        """Calculate interest match score"""
        if not user_interests or not other_interests:
            return 0.3

        user_set = set(i.lower() for i in user_interests)
        other_set = set(i.lower() for i in other_interests)

        intersection = user_set.intersection(other_set)
        union = user_set.union(other_set)

        return len(intersection) / len(union) if union else 0.0

    def _calculate_distance(self, location1: str, location2: str) -> Optional[str]:
        """Calculate distance between locations"""
        # TODO: Implement actual distance calculation using geolocation
        return "5 km"

    def _format_time_ago(self, timestamp) -> str:
        """Format timestamp as 'X ago'"""
        if not timestamp:
            return "Recently"

        # TODO: Implement actual time ago formatting
        return "2 days ago"

    def _generate_badges(self, opportunity: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate badges for opportunity card"""
        badges = []

        if opportunity.get("remote"):
            badges.append({"label": "Remote", "color": "blue"})

        if opportunity.get("featured"):
            badges.append({"label": "Featured", "color": "gold"})

        if opportunity.get("urgent"):
            badges.append({"label": "Urgent", "color": "red"})

        # Add "New" badge if posted within last 24 hours
        # TODO: Check actual timestamp
        badges.append({"label": "New", "color": "green"})

        return badges[:3]  # Max 3 badges

    async def _get_user(self, db: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Get user data"""
        # TODO: Implement actual database query
        return {
            "id": user_id,
            "skills": ["Python", "FastAPI", "React"],
            "location": "San Francisco, CA",
            "interests": ["AI", "Startups", "Remote Work"]
        }

    async def _get_profile_summary(self, db: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Get profile summary for match"""
        # TODO: Implement actual database query
        return {
            "id": user_id,
            "full_name": "John Doe",
            "profile_picture": "https://example.com/pic.jpg"
        }

    async def _fetch_opportunities(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int,
        include_seen: bool
    ) -> List[Dict[str, Any]]:
        """Fetch opportunities from database"""
        # TODO: Implement actual database query with:
        # - Exclude already swiped (unless include_seen=True)
        # - Filter by user preferences
        # - Order by match score
        # - Apply limit
        return []

    async def _fetch_profiles(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int,
        include_seen: bool
    ) -> List[Dict[str, Any]]:
        """Fetch user profiles from database"""
        # TODO: Implement actual database query
        return []

    async def _fetch_companies(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int,
        include_seen: bool
    ) -> List[Dict[str, Any]]:
        """Fetch companies from database"""
        # TODO: Implement actual database query
        return []

    def _generate_swipe_id(self) -> str:
        """Generate unique swipe ID"""
        import uuid
        return f"swipe_{uuid.uuid4().hex[:16]}"


# Global service instance
swipe_service = SwipeService()
