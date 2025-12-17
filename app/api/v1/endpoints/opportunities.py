"""Opportunity endpoints - CRUD and swipe functionality"""

from datetime import datetime
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from math import ceil

from app.core.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.opportunity import Opportunity, OpportunityStatusEnum
from app.models.match import Swipe, Match, SwipeActionEnum, MatchStatusEnum
from app.schemas.opportunity import (
    OpportunityCreate,
    OpportunityUpdate,
    OpportunityResponse,
    OpportunityListResponse,
    NearbyOpportunityResponse,
    NearbyOpportunityListResponse,
    SwipeCreate,
    SwipeResponse,
    MatchResponse,
    MatchListResponse
)

router = APIRouter()


@router.post("/", response_model=OpportunityResponse, status_code=status.HTTP_201_CREATED)
async def create_opportunity(
    opportunity_data: OpportunityCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create a new opportunity

    Only employers and companies can create opportunities
    """
    # Check if user is employer or company
    if current_user.user_type not in ["employer", "company"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers and companies can create opportunities"
        )

    # Create new opportunity
    new_opportunity = Opportunity(
        employer_id=current_user.id,
        **opportunity_data.model_dump()
    )

    db.add(new_opportunity)
    await db.commit()
    await db.refresh(new_opportunity)

    return OpportunityResponse.model_validate(new_opportunity)


@router.get("/", response_model=OpportunityListResponse)
async def list_opportunities(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str = Query("open", pattern="^(open|closed|filled|archived|all)$"),
    opportunity_type: str = Query(None, pattern="^(full_time|part_time|contract|freelance|gig|internship)$"),
    is_remote: bool = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    List opportunities with pagination and filters

    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **status_filter**: Filter by status (default: open)
    - **opportunity_type**: Filter by type
    - **is_remote**: Filter by remote status
    """
    # Build query
    query = select(Opportunity)

    # Apply filters
    filters = []
    if status_filter != "all":
        filters.append(Opportunity.status == status_filter)
    if opportunity_type:
        filters.append(Opportunity.opportunity_type == opportunity_type)
    if is_remote is not None:
        filters.append(Opportunity.is_remote == is_remote)

    if filters:
        query = query.where(and_(*filters))

    # Order by created_at descending
    query = query.order_by(Opportunity.created_at.desc())

    # Get total count
    count_query = select(func.count()).select_from(Opportunity)
    if filters:
        count_query = count_query.where(and_(*filters))
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    opportunities = result.scalars().all()

    return OpportunityListResponse(
        items=[OpportunityResponse.model_validate(opp) for opp in opportunities],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total > 0 else 0
    )


@router.get("/{opportunity_id}", response_model=OpportunityResponse)
async def get_opportunity(
    opportunity_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get a specific opportunity by ID

    Increments view count
    """
    # Fetch opportunity
    result = await db.execute(
        select(Opportunity).where(Opportunity.id == opportunity_id)
    )
    opportunity = result.scalar_one_or_none()

    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )

    # Increment views count
    opportunity.views_count += 1
    await db.commit()
    await db.refresh(opportunity)

    return OpportunityResponse.model_validate(opportunity)


@router.put("/{opportunity_id}", response_model=OpportunityResponse)
async def update_opportunity(
    opportunity_id: str,
    opportunity_data: OpportunityUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update an opportunity

    Only the employer who created it can update
    """
    # Fetch opportunity
    result = await db.execute(
        select(Opportunity).where(Opportunity.id == opportunity_id)
    )
    opportunity = result.scalar_one_or_none()

    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )

    # Check ownership
    if opportunity.employer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own opportunities"
        )

    # Update fields
    update_data = opportunity_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(opportunity, field, value)

    await db.commit()
    await db.refresh(opportunity)

    return OpportunityResponse.model_validate(opportunity)


@router.delete("/{opportunity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_opportunity(
    opportunity_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete an opportunity

    Only the employer who created it can delete
    """
    # Fetch opportunity
    result = await db.execute(
        select(Opportunity).where(Opportunity.id == opportunity_id)
    )
    opportunity = result.scalar_one_or_none()

    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )

    # Check ownership
    if opportunity.employer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own opportunities"
        )

    await db.delete(opportunity)
    await db.commit()


@router.get("/my/posted", response_model=OpportunityListResponse)
async def get_my_opportunities(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get opportunities posted by current user

    Only for employers and companies
    """
    if current_user.user_type not in ["employer", "company"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers and companies can view posted opportunities"
        )

    # Build query
    query = select(Opportunity).where(
        Opportunity.employer_id == current_user.id
    ).order_by(Opportunity.created_at.desc())

    # Get total count
    count_query = select(func.count()).select_from(Opportunity).where(
        Opportunity.employer_id == current_user.id
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    opportunities = result.scalars().all()

    return OpportunityListResponse(
        items=[OpportunityResponse.model_validate(opp) for opp in opportunities],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total > 0 else 0
    )


@router.post("/swipe", response_model=SwipeResponse)
async def swipe_opportunity(
    swipe_data: SwipeCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Swipe on an opportunity (like/pass/superlike)

    Returns swipe information and whether it resulted in a match
    """
    # Check if opportunity exists
    opp_result = await db.execute(
        select(Opportunity).where(Opportunity.id == swipe_data.opportunity_id)
    )
    opportunity = opp_result.scalar_one_or_none()

    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )

    # Check if already swiped
    existing_swipe_result = await db.execute(
        select(Swipe).where(
            and_(
                Swipe.user_id == current_user.id,
                Swipe.opportunity_id == swipe_data.opportunity_id
            )
        )
    )
    existing_swipe = existing_swipe_result.scalar_one_or_none()

    if existing_swipe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already swiped on this opportunity"
        )

    # Create swipe
    new_swipe = Swipe(
        user_id=current_user.id,
        opportunity_id=swipe_data.opportunity_id,
        action=swipe_data.action
    )

    db.add(new_swipe)

    # Check if it's a match (user liked the opportunity)
    is_match = False
    if swipe_data.action in ["like", "superlike"]:
        # Create a match
        new_match = Match(
            user_id=current_user.id,
            opportunity_id=swipe_data.opportunity_id,
            employer_id=opportunity.employer_id,
            status=MatchStatusEnum.pending,
            is_mutual=False  # Waiting for employer response
        )

        db.add(new_match)
        is_match = True

        # Update opportunity matches count
        opportunity.matches_count += 1

    await db.commit()
    await db.refresh(new_swipe)

    return SwipeResponse(
        id=new_swipe.id,
        user_id=new_swipe.user_id,
        opportunity_id=new_swipe.opportunity_id,
        action=new_swipe.action,
        created_at=new_swipe.created_at,
        is_match=is_match
    )


@router.get("/matches/my", response_model=MatchListResponse)
async def get_my_matches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str = Query("all", pattern="^(pending|accepted|rejected|expired|all)$"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get matches for current user

    Returns paginated list of matches with opportunity details
    """
    # Build query
    query = select(Match).where(Match.user_id == current_user.id)

    # Apply status filter
    if status_filter != "all":
        query = query.where(Match.status == status_filter)

    # Order by created_at descending
    query = query.order_by(Match.created_at.desc())

    # Get total count
    count_query = select(func.count()).select_from(Match).where(
        Match.user_id == current_user.id
    )
    if status_filter != "all":
        count_query = count_query.where(Match.status == status_filter)
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    matches = result.scalars().all()

    # Fetch opportunity details for each match
    match_responses = []
    for match in matches:
        opp_result = await db.execute(
            select(Opportunity).where(Opportunity.id == match.opportunity_id)
        )
        opportunity = opp_result.scalar_one_or_none()

        match_response = MatchResponse.model_validate(match)
        if opportunity:
            match_response.opportunity = OpportunityResponse.model_validate(opportunity)

        match_responses.append(match_response)

    return MatchListResponse(
        items=match_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total > 0 else 0
    )

@router.get("/nearby/search", response_model=NearbyOpportunityListResponse)
async def search_nearby_opportunities(
    latitude: float = Query(..., description="User's latitude", ge=-90, le=90),
    longitude: float = Query(..., description="User's longitude", ge=-180, le=180),
    radius_km: float = Query(25, description="Search radius in kilometers", ge=1, le=500),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    opportunity_type: str = Query(None, pattern="^(full_time|part_time|contract|freelance|gig|internship)$"),
    is_remote: bool = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Search for opportunities near a specific location

    Uses haversine formula to calculate distances and returns opportunities
    within the specified radius, sorted by distance.

    - **latitude**: User's current latitude (-90 to 90)
    - **longitude**: User's current longitude (-180 to 180)
    - **radius_km**: Search radius in kilometers (default: 25km, max: 500km)
    - **page**: Page number
    - **page_size**: Items per page
    - **opportunity_type**: Filter by type
    - **is_remote**: Filter by remote status (remote jobs always included)
    """
    from app.utils.geolocation import Coordinates, GeoLocationService

    # User's location
    user_location = Coordinates(latitude, longitude)

    # Calculate bounding box for efficient query
    bbox = GeoLocationService.calculate_bounding_box(user_location, radius_km)

    # Build query with bounding box filter
    query = select(Opportunity).where(
        and_(
            Opportunity.status == "open",
            Opportunity.location.isnot(None),  # Only opportunities with location
            # Bounding box filter using JSONB
            Opportunity.location["coordinates"]["latitude"].as_float() >= bbox["min_lat"],
            Opportunity.location["coordinates"]["latitude"].as_float() <= bbox["max_lat"],
            Opportunity.location["coordinates"]["longitude"].as_float() >= bbox["min_lon"],
            Opportunity.location["coordinates"]["longitude"].as_float() <= bbox["max_lon"]
        )
    )

    # Additional filters
    if opportunity_type:
        query = query.where(Opportunity.opportunity_type == opportunity_type)
    if is_remote is not None and not is_remote:
        query = query.where(Opportunity.is_remote == is_remote)

    # Execute query
    result = await db.execute(query)
    opportunities = result.scalars().all()

    # Calculate exact distances and filter by radius
    opportunities_with_distance = []
    for opp in opportunities:
        # Skip if location data is incomplete
        if not opp.location or "coordinates" not in opp.location:
            continue

        coords = opp.location.get("coordinates", {})
        if "latitude" not in coords or "longitude" not in coords:
            continue

        opp_location = Coordinates(
            latitude=coords["latitude"],
            longitude=coords["longitude"]
        )

        distance = GeoLocationService.haversine_distance(
            user_location,
            opp_location,
            unit="km"
        )

        # Filter by exact radius
        if distance <= radius_km or opp.is_remote:  # Include remote jobs
            opportunities_with_distance.append((opp, distance))

    # Sort by distance (remote jobs at the end)
    opportunities_with_distance.sort(
        key=lambda x: (x[0].is_remote, x[1])  # Remote jobs last, then by distance
    )

    # Get total count
    total = len(opportunities_with_distance)

    # Apply pagination
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated = opportunities_with_distance[start_idx:end_idx]

    # Build response with distance information
    response_items = []
    for opp, distance in paginated:
        # Create dict from opportunity
        opp_dict = OpportunityResponse.model_validate(opp).model_dump()

        # Add distance fields
        opp_dict["distance_km"] = round(distance, 2) if not opp.is_remote else None
        opp_dict["distance_text"] = (
            GeoLocationService.format_distance(distance)
            if not opp.is_remote
            else "Remote"
        )

        # Create NearbyOpportunityResponse
        nearby_opp = NearbyOpportunityResponse(**opp_dict)
        response_items.append(nearby_opp)

    return NearbyOpportunityListResponse(
        items=response_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total > 0 else 0,
        search_radius_km=radius_km,
        search_location={
            "latitude": latitude,
            "longitude": longitude
        }
    )
