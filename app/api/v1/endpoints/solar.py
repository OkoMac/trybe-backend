"""Solar Revolution API Endpoints"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.solar import (
    SolarTrainingEnrollment,
    SolarOpportunity,
    SolarProject,
    SolarDevelopmentPlan,
    SolarResource,
    ExperienceLevel,
    ProjectStatus
)
from app.schemas.solar import (
    TrainingEnrollmentCreate,
    TrainingEnrollmentResponse,
    SolarOpportunityCreate,
    SolarOpportunityResponse,
    SolarProjectCreate,
    SolarProjectResponse,
    DevelopmentPlanCreate,
    DevelopmentPlanResponse,
    SolarResourceCreate,
    SolarResourceResponse
)

router = APIRouter()


# ==================== TRAINING ENDPOINTS ====================

@router.post("/training/enroll", response_model=TrainingEnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def enroll_in_training(
    enrollment_data: TrainingEnrollmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Enroll in solar training program"""

    enrollment = SolarTrainingEnrollment(
        **enrollment_data.model_dump(),
        user_id=current_user.id
    )

    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)

    return enrollment


@router.get("/training/my-enrollments", response_model=List[TrainingEnrollmentResponse])
async def get_my_enrollments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's training enrollments"""

    query = select(SolarTrainingEnrollment).where(
        SolarTrainingEnrollment.user_id == current_user.id
    ).order_by(desc(SolarTrainingEnrollment.created_at))

    result = await db.execute(query)
    enrollments = result.scalars().all()

    return enrollments


# ==================== OPPORTUNITY ENDPOINTS ====================

@router.post("/opportunities", response_model=SolarOpportunityResponse, status_code=status.HTTP_201_CREATED)
async def create_solar_opportunity(
    opportunity_data: SolarOpportunityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a solar-specific job opportunity"""

    opportunity = SolarOpportunity(
        **opportunity_data.model_dump(),
        posted_by_id=current_user.id
    )

    db.add(opportunity)
    await db.commit()
    await db.refresh(opportunity)

    return opportunity


@router.get("/opportunities", response_model=List[SolarOpportunityResponse])
async def list_solar_opportunities(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    experience_level: Optional[ExperienceLevel] = None,
    solar_category: Optional[str] = None,
    is_remote: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """List solar job opportunities"""

    query = select(SolarOpportunity).where(SolarOpportunity.is_active == True)

    if experience_level:
        query = query.where(SolarOpportunity.experience_required == experience_level)

    if solar_category:
        query = query.where(SolarOpportunity.solar_categories.any(solar_category))

    if is_remote is not None:
        query = query.where(SolarOpportunity.is_remote == is_remote)

    query = query.order_by(desc(SolarOpportunity.created_at)).offset(skip).limit(limit)

    result = await db.execute(query)
    opportunities = result.scalars().all()

    return opportunities


@router.get("/opportunities/{opportunity_id}", response_model=SolarOpportunityResponse)
async def get_solar_opportunity(
    opportunity_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get solar opportunity by ID"""

    query = select(SolarOpportunity).where(SolarOpportunity.id == opportunity_id)
    result = await db.execute(query)
    opportunity = result.scalar_one_or_none()

    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solar opportunity not found"
        )

    # Increment view count
    opportunity.view_count += 1
    await db.commit()

    return opportunity


# ==================== PROJECT ENDPOINTS ====================

@router.post("/projects", response_model=SolarProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_solar_project(
    project_data: SolarProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a solar project"""

    project = SolarProject(
        **project_data.model_dump(),
        owner_id=current_user.id
    )

    db.add(project)
    await db.commit()
    await db.refresh(project)

    return project


@router.get("/projects", response_model=List[SolarProjectResponse])
async def list_solar_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    project_type: Optional[str] = None,
    status: Optional[ProjectStatus] = None,
    public_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List solar projects"""

    filters = []

    if public_only:
        filters.append(SolarProject.is_public == True)
    else:
        filters.append(
            or_(
                SolarProject.is_public == True,
                SolarProject.owner_id == current_user.id
            )
        )

    if project_type:
        filters.append(SolarProject.project_type == project_type)

    if status:
        filters.append(SolarProject.status == status)

    query = select(SolarProject).where(and_(*filters) if filters else True)
    query = query.order_by(desc(SolarProject.created_at)).offset(skip).limit(limit)

    result = await db.execute(query)
    projects = result.scalars().all()

    return projects


# ==================== DEVELOPMENT PLAN ENDPOINTS ====================

@router.post("/development-plans", response_model=DevelopmentPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_development_plan(
    plan_data: DevelopmentPlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create AI-powered development plan"""

    # AI-generated skill gap analysis and learning path
    skill_gaps = list(set(plan_data.target_skills) - set(plan_data.current_skills))

    # Simple learning path generation
    learning_path = [
        {
            "step": i + 1,
            "title": f"Learn {skill}",
            "description": f"Master {skill} for {plan_data.target_role}",
            "estimated_hours": 40,
            "resources": []
        }
        for i, skill in enumerate(skill_gaps[:5])
    ]

    plan = SolarDevelopmentPlan(
        user_id=current_user.id,
        title=f"Path to {plan_data.target_role}",
        description=f"Development plan from {plan_data.current_role or 'current role'} to {plan_data.target_role}",
        **plan_data.model_dump(),
        skill_gaps=skill_gaps,
        learning_path=learning_path
    )

    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    return plan


@router.get("/development-plans/my", response_model=List[DevelopmentPlanResponse])
async def get_my_development_plans(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's development plans"""

    query = select(SolarDevelopmentPlan).where(
        SolarDevelopmentPlan.user_id == current_user.id
    ).order_by(desc(SolarDevelopmentPlan.created_at))

    result = await db.execute(query)
    plans = result.scalars().all()

    return plans


# ==================== RESOURCE ENDPOINTS ====================

@router.post("/resources", response_model=SolarResourceResponse, status_code=status.HTTP_201_CREATED)
async def create_solar_resource(
    resource_data: SolarResourceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a solar learning resource"""

    resource = SolarResource(
        **resource_data.model_dump(),
        created_by_id=current_user.id
    )

    db.add(resource)
    await db.commit()
    await db.refresh(resource)

    return resource


@router.get("/resources", response_model=List[SolarResourceResponse])
async def list_solar_resources(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    resource_type: Optional[str] = None,
    difficulty_level: Optional[ExperienceLevel] = None,
    free_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """List solar learning resources"""

    filters = []

    if category:
        filters.append(SolarResource.category == category)

    if resource_type:
        filters.append(SolarResource.resource_type == resource_type)

    if difficulty_level:
        filters.append(SolarResource.difficulty_level == difficulty_level)

    if free_only:
        filters.append(SolarResource.is_free == True)

    query = select(SolarResource).where(and_(*filters) if filters else True)
    query = query.order_by(desc(SolarResource.rating), desc(SolarResource.created_at))
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    resources = result.scalars().all()

    return resources


@router.get("/resources/{resource_id}", response_model=SolarResourceResponse)
async def get_solar_resource(
    resource_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get solar resource by ID"""

    query = select(SolarResource).where(SolarResource.id == resource_id)
    result = await db.execute(query)
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )

    # Increment view count
    resource.view_count += 1
    await db.commit()

    return resource
