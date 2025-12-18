"""
Swipe API Endpoints - Mobile-First Interface
Primary interface for mobile app after login
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import BaseModel, Field

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.services.swipe_service import (
    swipe_service,
    SwipeAction,
    SwipeType
)

router = APIRouter()


# ==================== Schemas ====================

class SwipeCardResponse(BaseModel):
    """Response schema for swipe card"""
    id: str
    type: str
    # Additional fields vary by type


class GetCardsRequest(BaseModel):
    """Request schema for getting cards"""
    swipe_type: str = Field("opportunity", description="Type: opportunity, profile, company")
    limit: int = Field(20, ge=1, le=50, description="Number of cards to load")
    include_seen: bool = Field(False, description="Include previously seen cards")


class RecordSwipeRequest(BaseModel):
    """Request schema for recording a swipe"""
    card_id: str = Field(..., description="ID of the swiped card")
    card_type: str = Field(..., description="Type of card")
    action: str = Field(..., description="Swipe action: right, left, up")
    swipe_metadata: Optional[dict] = Field(None, description="Additional swipe metadata")


class SwipePreferencesRequest(BaseModel):
    """Request schema for swipe preferences"""
    opportunity_types: Optional[List[str]] = Field(None, description="Preferred opportunity types")
    remote_preference: Optional[str] = Field(None, description="Remote preference: any, remote-only, on-site-only")
    salary_min: Optional[int] = Field(None, description="Minimum salary")
    location_radius_km: Optional[int] = Field(None, ge=0, le=500, description="Location radius in km")
    experience_levels: Optional[List[str]] = Field(None, description="Preferred experience levels")
    categories: Optional[List[str]] = Field(None, description="Preferred categories")
    show_seen_cards: Optional[bool] = Field(None, description="Show previously seen cards")


# ==================== Mobile Home - Swipe Interface ====================

@router.get("/home")
async def get_mobile_home(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get mobile home screen data

    **PRIMARY ENDPOINT FOR MOBILE APP AFTER LOGIN**

    Returns everything needed for the initial swipe interface:
    - Stack of swipeable cards (opportunities by default)
    - User stats
    - Recent matches
    - Quick actions

    This is the first thing users see after login on mobile.
    """
    try:
        # Get initial card stack
        cards = await swipe_service.get_swipe_cards(
            db=db,
            user_id=str(current_user.id),
            swipe_type=SwipeType.OPPORTUNITY,
            limit=20,
            include_seen=False
        )

        # Get user stats
        stats = await swipe_service.get_swipe_stats(db, str(current_user.id))

        # Get recent matches (last 5)
        recent_matches = await swipe_service.get_matches(
            db=db,
            user_id=str(current_user.id),
            limit=5
        )

        return {
            "cards": cards,
            "stats": {
                "new_matches": stats.get("matches", 0),
                "swipes_today": stats.get("average_swipes_per_day", 0),
                "match_rate": f"{stats.get('match_rate', 0) * 100:.0f}%"
            },
            "recent_matches": recent_matches,
            "quick_actions": [
                {
                    "type": "switch_mode",
                    "label": "Find Talent",
                    "icon": "users",
                    "action": "switch_to_profiles"
                },
                {
                    "type": "view_matches",
                    "label": "Matches",
                    "icon": "heart",
                    "badge_count": stats.get("matches", 0),
                    "action": "navigate_to_matches"
                },
                {
                    "type": "messages",
                    "label": "Messages",
                    "icon": "message",
                    "badge_count": 0,  # TODO: Get unread count
                    "action": "navigate_to_messages"
                }
            ],
            "swipe_preferences": await swipe_service.get_swipe_preferences(db, str(current_user.id))
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load home screen: {str(e)}"
        )


# ==================== Card Operations ====================

@router.post("/cards")
async def get_cards(
    request: GetCardsRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get swipe cards

    Load a batch of cards for swiping.

    **Card Types:**
    - `opportunity`: Job opportunities (default)
    - `profile`: User profiles for networking
    - `company`: Companies to follow

    **Usage:**
    ```json
    {
      "swipe_type": "opportunity",
      "limit": 20,
      "include_seen": false
    }
    ```

    Returns cards optimized for mobile swipe interface with:
    - Match scores
    - Key information only
    - Optimized images
    - Badges and tags
    """
    try:
        # Validate swipe type
        try:
            swipe_type = SwipeType(request.swipe_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid swipe type. Must be: opportunity, profile, or company"
            )

        cards = await swipe_service.get_swipe_cards(
            db=db,
            user_id=str(current_user.id),
            swipe_type=swipe_type,
            limit=request.limit,
            include_seen=request.include_seen
        )

        return {
            "cards": cards,
            "total": len(cards),
            "swipe_type": request.swipe_type,
            "has_more": len(cards) >= request.limit
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cards: {str(e)}"
        )


@router.get("/cards/next", response_model=dict)
async def get_next_card(
    swipe_type: str = Query("opportunity", description="Card type"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get next single card

    Quick endpoint to get just the next card in the stack.
    Useful for preloading while user is swiping.
    """
    try:
        swipe_type_enum = SwipeType(swipe_type)

        cards = await swipe_service.get_swipe_cards(
            db=db,
            user_id=str(current_user.id),
            swipe_type=swipe_type_enum,
            limit=1,
            include_seen=False
        )

        if not cards:
            return {
                "card": None,
                "message": "No more cards available",
                "has_more": False
            }

        return {
            "card": cards[0],
            "has_more": True
        }

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid swipe type"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get next card: {str(e)}"
        )


# ==================== Swipe Actions ====================

@router.post("/swipe")
async def record_swipe(
    request: RecordSwipeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Record a swipe action

    **PRIMARY SWIPE ENDPOINT**

    **Actions:**
    - `right`: Interested/Like (Apply intent for opportunities)
    - `left`: Not interested/Pass
    - `up`: Super like/Priority interest (Limited per day)

    **Response includes:**
    - Match status (if applicable)
    - Next actions available
    - Match details (if it's a match)

    Example:
    ```json
    {
      "card_id": "opp_123",
      "card_type": "opportunity",
      "action": "right",
      "swipe_metadata": {
        "swipe_speed": 0.5,
        "swipe_angle": 45
      }
    }
    ```

    **For Opportunities (Right Swipe):**
    - Shows interest in the role
    - Can proceed to quick apply
    - Company sees your profile

    **For Profiles (Right Swipe):**
    - If mutual, instant match!
    - Can start messaging
    - Connection established

    **For Companies (Right Swipe):**
    - Follow the company
    - See their updates
    - Get notifications about new opportunities
    """
    try:
        # Validate action and card type
        try:
            action = SwipeAction(request.action)
            card_type = SwipeType(request.card_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid action or card type"
            )

        # Record the swipe
        result = await swipe_service.record_swipe(
            db=db,
            user_id=str(current_user.id),
            card_id=request.card_id,
            card_type=card_type,
            action=action,
            metadata=request.swipe_metadata
        )

        # Add action-specific response data
        if action == SwipeAction.RIGHT:
            if card_type == SwipeType.OPPORTUNITY:
                result["next_action"] = {
                    "type": "quick_apply",
                    "label": "Quick Apply",
                    "url": f"/api/v1/opportunities/{request.card_id}/quick-apply"
                }
            elif card_type == SwipeType.PROFILE:
                if result.get("is_match"):
                    result["next_action"] = {
                        "type": "start_chat",
                        "label": "Say Hi 👋",
                        "url": f"/api/v1/messages/start/{request.card_id}"
                    }
            elif card_type == SwipeType.COMPANY:
                result["next_action"] = {
                    "type": "view_company",
                    "label": "View Company",
                    "url": f"/api/v1/companies/{request.card_id}"
                }

        elif action == SwipeAction.UP:
            result["message"] = "Super liked! They'll be notified 🌟"
            result["super_likes_remaining"] = 3  # TODO: Calculate actual remaining

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record swipe: {str(e)}"
        )


@router.post("/swipe/undo")
async def undo_swipe(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Undo last swipe

    Allows users to take back their last swipe action.
    Limited to last swipe within last 5 minutes.

    **Note:** May be limited in free tier (premium feature)
    """
    try:
        # TODO: Implement undo functionality
        # - Get last swipe (within last 5 minutes)
        # - Remove swipe record
        # - Return the card

        return {
            "success": True,
            "message": "Last swipe undone",
            "card": None  # Return the card that was undone
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to undo swipe: {str(e)}"
        )


# ==================== Matches ====================

@router.get("/matches")
async def get_matches(
    match_type: Optional[str] = Query(None, description="Filter by type"),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all matches

    Returns all matches (mutual interest) for:
    - Opportunities (interest expressed)
    - Profiles (mutual right swipes)
    - Companies (followed)

    Sorted by most recent first.
    """
    try:
        match_type_enum = SwipeType(match_type) if match_type else None

        matches = await swipe_service.get_matches(
            db=db,
            user_id=str(current_user.id),
            match_type=match_type_enum,
            limit=limit
        )

        return {
            "matches": matches,
            "total": len(matches),
            "unread_count": sum(1 for m in matches if not m.get("read", True))
        }

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid match type"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get matches: {str(e)}"
        )


# ==================== History & Stats ====================

@router.get("/history")
async def get_swipe_history(
    action: Optional[str] = Query(None, description="Filter by action"),
    card_type: Optional[str] = Query(None, description="Filter by card type"),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get swipe history

    View your past swipes. Useful for:
    - Reviewing opportunities you passed on
    - Seeing your swipe patterns
    - Finding cards you swiped right on
    """
    try:
        action_enum = SwipeAction(action) if action else None
        card_type_enum = SwipeType(card_type) if card_type else None

        history = await swipe_service.get_swipe_history(
            db=db,
            user_id=str(current_user.id),
            action=action_enum,
            card_type=card_type_enum,
            limit=limit
        )

        return {
            "history": history,
            "total": len(history)
        }

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action or card type"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get history: {str(e)}"
        )


@router.get("/stats")
async def get_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get swipe statistics

    Returns analytics about your swiping activity:
    - Total swipes
    - Match rate
    - Most common swipe actions
    - Best swipe times
    - Response rates
    """
    try:
        stats = await swipe_service.get_swipe_stats(db, str(current_user.id))

        return {
            "stats": stats,
            "insights": [
                {
                    "type": "match_rate",
                    "title": "Your Match Rate",
                    "value": f"{stats.get('match_rate', 0) * 100:.0f}%",
                    "description": "You match with 1 in every X swipes",
                    "trend": "up"  # or "down" or "stable"
                },
                {
                    "type": "swipe_activity",
                    "title": "Daily Activity",
                    "value": f"{stats.get('average_swipes_per_day', 0):.0f} swipes",
                    "description": "Your average swipes per day",
                    "trend": "stable"
                }
            ]
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )


# ==================== Preferences ====================

@router.get("/preferences")
async def get_preferences(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get swipe preferences

    Returns current swipe filtering preferences.
    These determine which cards appear in your swipe stack.
    """
    try:
        preferences = await swipe_service.get_swipe_preferences(db, str(current_user.id))
        return preferences

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get preferences: {str(e)}"
        )


@router.put("/preferences")
async def update_preferences(
    request: SwipePreferencesRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update swipe preferences

    Customize which opportunities appear in your swipe stack.

    Example:
    ```json
    {
      "opportunity_types": ["full-time", "contract"],
      "remote_preference": "remote-only",
      "salary_min": 80000,
      "location_radius_km": 25,
      "experience_levels": ["mid", "senior"],
      "categories": ["software_development", "data_science"]
    }
    ```
    """
    try:
        preferences_dict = request.dict(exclude_none=True)

        updated_preferences = await swipe_service.update_swipe_preferences(
            db=db,
            user_id=str(current_user.id),
            preferences=preferences_dict
        )

        return {
            "success": True,
            "message": "Preferences updated",
            "preferences": updated_preferences
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update preferences: {str(e)}"
        )


# ==================== Quick Apply ====================

@router.post("/quick-apply/{opportunity_id}")
async def quick_apply(
    opportunity_id: str,
    cover_letter: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Quick apply after swiping right

    Streamlined application process after expressing interest via swipe.
    Uses your profile information automatically.

    Steps:
    1. User swipes right on opportunity
    2. Clicks "Quick Apply"
    3. Optionally adds cover letter
    4. Application submitted instantly

    **Benefits:**
    - 1-tap application
    - Profile auto-filled
    - Resume attached automatically
    - Faster than traditional apply
    """
    try:
        # TODO: Implement quick apply logic
        # - Check if user has resume uploaded
        # - Create application with user's profile data
        # - Attach resume
        # - Send confirmation

        return {
            "success": True,
            "message": "Application submitted!",
            "application_id": "app_123",
            "next_steps": [
                "Employer will review your profile",
                "You'll be notified of any updates",
                "Check your messages for responses"
            ]
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit application: {str(e)}"
        )


# ==================== Health Check ====================

@router.get("/health")
async def swipe_health_check():
    """Health check for swipe service"""
    return {
        "status": "healthy",
        "service": "Swipe Interface",
        "features": [
            "Opportunity swiping",
            "Profile matching",
            "Company following",
            "Match notifications",
            "Quick apply"
        ]
    }
