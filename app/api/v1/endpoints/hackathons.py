"""Hackathon API Endpoints"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.hackathon import (
    Hackathon,
    HackathonTeam,
    HackathonRegistration,
    HackathonSubmission,
    AptitudeTest,
    TestResult,
    HackathonStatus,
    SubmissionStatus,
    team_members
)
from app.schemas.hackathon import (
    HackathonCreate,
    HackathonUpdate,
    HackathonResponse,
    HackathonStats,
    TeamCreate,
    TeamUpdate,
    TeamResponse,
    TeamDetailResponse,
    RegistrationCreate,
    RegistrationUpdate,
    RegistrationResponse,
    SubmissionCreate,
    SubmissionUpdate,
    SubmissionResponse,
    SubmissionScore,
    AptitudeTestCreate,
    AptitudeTestResponse,
    TestSubmission,
    TestResultResponse,
    LeaderboardEntry
)

router = APIRouter()


# ==================== HACKATHON ENDPOINTS ====================

@router.post("/", response_model=HackathonResponse, status_code=status.HTTP_201_CREATED)
async def create_hackathon(
    hackathon_data: HackathonCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new hackathon (organizers only)"""

    # Calculate total prize pool
    total_prize_pool = sum(prize.amount for prize in hackathon_data.prizes)

    # Create hackathon
    hackathon = Hackathon(
        **hackathon_data.model_dump(exclude={"prizes", "judging_criteria"}),
        organizer_id=current_user.id,
        prizes=[prize.model_dump() for prize in hackathon_data.prizes],
        judging_criteria=[criteria.model_dump() for criteria in hackathon_data.judging_criteria],
        total_prize_pool=total_prize_pool
    )

    db.add(hackathon)
    await db.commit()
    await db.refresh(hackathon)

    return hackathon


@router.get("/", response_model=List[HackathonResponse])
async def list_hackathons(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[HackathonStatus] = None,
    difficulty: Optional[str] = None,
    featured_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """List hackathons with filters"""

    query = select(Hackathon)

    # Apply filters
    filters = [Hackathon.is_public == True]

    if status:
        filters.append(Hackathon.status == status)

    if difficulty:
        filters.append(Hackathon.difficulty_level == difficulty)

    if featured_only:
        filters.append(Hackathon.is_featured == True)

    query = query.where(and_(*filters))
    query = query.order_by(desc(Hackathon.created_at))
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    hackathons = result.scalars().all()

    return hackathons


@router.get("/{hackathon_id}", response_model=HackathonResponse)
async def get_hackathon(
    hackathon_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get hackathon by ID"""

    query = select(Hackathon).where(Hackathon.id == hackathon_id)
    result = await db.execute(query)
    hackathon = result.scalar_one_or_none()

    if not hackathon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hackathon not found"
        )

    # Increment view count
    hackathon.view_count += 1
    await db.commit()
    await db.refresh(hackathon)

    return hackathon


@router.patch("/{hackathon_id}", response_model=HackathonResponse)
async def update_hackathon(
    hackathon_id: UUID,
    hackathon_data: HackathonUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update hackathon (organizer only)"""

    query = select(Hackathon).where(Hackathon.id == hackathon_id)
    result = await db.execute(query)
    hackathon = result.scalar_one_or_none()

    if not hackathon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hackathon not found"
        )

    # Check permission
    if hackathon.organizer_id != current_user.id and current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this hackathon"
        )

    # Update fields
    update_data = hackathon_data.model_dump(exclude_unset=True)

    if "prizes" in update_data:
        update_data["prizes"] = [prize.model_dump() for prize in hackathon_data.prizes]
        update_data["total_prize_pool"] = sum(prize.amount for prize in hackathon_data.prizes)

    if "judging_criteria" in update_data:
        update_data["judging_criteria"] = [c.model_dump() for c in hackathon_data.judging_criteria]

    for field, value in update_data.items():
        setattr(hackathon, field, value)

    hackathon.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(hackathon)

    return hackathon


@router.delete("/{hackathon_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hackathon(
    hackathon_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete hackathon (organizer/admin only)"""

    query = select(Hackathon).where(Hackathon.id == hackathon_id)
    result = await db.execute(query)
    hackathon = result.scalar_one_or_none()

    if not hackathon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hackathon not found"
        )

    # Check permission
    if hackathon.organizer_id != current_user.id and current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this hackathon"
        )

    await db.delete(hackathon)
    await db.commit()


@router.get("/{hackathon_id}/stats", response_model=HackathonStats)
async def get_hackathon_stats(
    hackathon_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get hackathon statistics"""

    # Verify hackathon exists
    query = select(Hackathon).where(Hackathon.id == hackathon_id)
    result = await db.execute(query)
    hackathon = result.scalar_one_or_none()

    if not hackathon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hackathon not found"
        )

    # Get counts
    registrations_query = select(func.count()).select_from(HackathonRegistration).where(
        HackathonRegistration.hackathon_id == hackathon_id
    )
    total_participants = (await db.execute(registrations_query)).scalar()

    teams_query = select(func.count()).select_from(HackathonTeam).where(
        HackathonTeam.hackathon_id == hackathon_id
    )
    total_teams = (await db.execute(teams_query)).scalar()

    submissions_query = select(func.count()).select_from(HackathonSubmission).where(
        HackathonSubmission.hackathon_id == hackathon_id
    )
    total_submissions = (await db.execute(submissions_query)).scalar()

    # Submissions by status
    submissions_by_status_query = select(
        HackathonSubmission.status,
        func.count(HackathonSubmission.id)
    ).where(
        HackathonSubmission.hackathon_id == hackathon_id
    ).group_by(HackathonSubmission.status)

    result = await db.execute(submissions_by_status_query)
    submissions_by_status = {row[0].value: row[1] for row in result}

    return HackathonStats(
        total_participants=total_participants or 0,
        total_teams=total_teams or 0,
        total_submissions=total_submissions or 0,
        submissions_by_status=submissions_by_status,
        average_team_size=0.0,  # TODO: Calculate actual average
        top_skills=[]  # TODO: Aggregate skills from registrations
    )


@router.get("/{hackathon_id}/leaderboard", response_model=List[LeaderboardEntry])
async def get_hackathon_leaderboard(
    hackathon_id: UUID,
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get hackathon leaderboard"""

    # Get submissions ordered by score
    query = select(HackathonSubmission).where(
        and_(
            HackathonSubmission.hackathon_id == hackathon_id,
            HackathonSubmission.status.in_([SubmissionStatus.SUBMITTED, SubmissionStatus.WINNER])
        )
    ).options(
        selectinload(HackathonSubmission.team).selectinload(HackathonTeam.members)
    ).order_by(desc(HackathonSubmission.total_score)).limit(limit)

    result = await db.execute(query)
    submissions = result.scalars().all()

    leaderboard = []
    for rank, submission in enumerate(submissions, 1):
        leaderboard.append(LeaderboardEntry(
            rank=rank,
            team_id=submission.team_id,
            team_name=submission.team.name,
            submission_title=submission.title,
            total_score=submission.total_score,
            team_members=[member.full_name for member in submission.team.members]
        ))

    return leaderboard


# ==================== TEAM ENDPOINTS ====================

@router.post("/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_data: TeamCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a hackathon team"""

    # Verify hackathon exists
    query = select(Hackathon).where(Hackathon.id == team_data.hackathon_id)
    result = await db.execute(query)
    hackathon = result.scalar_one_or_none()

    if not hackathon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hackathon not found"
        )

    # Create team
    team = HackathonTeam(
        **team_data.model_dump(),
        team_leader_id=current_user.id
    )

    db.add(team)
    await db.commit()
    await db.refresh(team)

    # Add team leader as first member
    await db.execute(
        team_members.insert().values(
            team_id=team.id,
            user_id=current_user.id,
            joined_at=datetime.utcnow()
        )
    )
    await db.commit()

    return team


@router.get("/teams/{team_id}", response_model=TeamDetailResponse)
async def get_team(
    team_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get team details with members"""

    query = select(HackathonTeam).where(
        HackathonTeam.id == team_id
    ).options(
        selectinload(HackathonTeam.members)
    )

    result = await db.execute(query)
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )

    # Build response with member count
    team_dict = {
        "id": team.id,
        "hackathon_id": team.hackathon_id,
        "name": team.name,
        "description": team.description,
        "team_leader_id": team.team_leader_id,
        "logo_url": team.logo_url,
        "is_public": team.is_public,
        "max_members": team.max_members,
        "member_count": len(team.members),
        "created_at": team.created_at,
        "updated_at": team.updated_at,
        "members": team.members
    }

    return team_dict


@router.post("/teams/{team_id}/join", response_model=dict)
async def join_team(
    team_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Join a hackathon team"""

    # Get team
    query = select(HackathonTeam).where(
        HackathonTeam.id == team_id
    ).options(selectinload(HackathonTeam.members))

    result = await db.execute(query)
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )

    # Check if team is full
    if len(team.members) >= team.max_members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team is full"
        )

    # Check if user already in team
    if current_user in team.members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already in this team"
        )

    # Add user to team
    await db.execute(
        team_members.insert().values(
            team_id=team.id,
            user_id=current_user.id,
            joined_at=datetime.utcnow()
        )
    )
    await db.commit()

    return {"message": "Successfully joined team"}


@router.post("/teams/{team_id}/leave", response_model=dict)
async def leave_team(
    team_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Leave a hackathon team"""

    # Get team
    query = select(HackathonTeam).where(HackathonTeam.id == team_id)
    result = await db.execute(query)
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )

    # Team leader cannot leave
    if team.team_leader_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team leader cannot leave team. Transfer leadership first or delete the team."
        )

    # Remove user from team
    await db.execute(
        team_members.delete().where(
            and_(
                team_members.c.team_id == team.id,
                team_members.c.user_id == current_user.id
            )
        )
    )
    await db.commit()

    return {"message": "Successfully left team"}


# ==================== REGISTRATION ENDPOINTS ====================

@router.post("/registrations", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_for_hackathon(
    registration_data: RegistrationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Register for a hackathon"""

    # Verify hackathon exists and is open for registration
    query = select(Hackathon).where(Hackathon.id == registration_data.hackathon_id)
    result = await db.execute(query)
    hackathon = result.scalar_one_or_none()

    if not hackathon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hackathon not found"
        )

    # Check if registration is open
    now = datetime.utcnow()
    if now < hackathon.registration_start or now > hackathon.registration_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration is not open"
        )

    # Check if already registered
    existing_query = select(HackathonRegistration).where(
        and_(
            HackathonRegistration.hackathon_id == registration_data.hackathon_id,
            HackathonRegistration.user_id == current_user.id
        )
    )
    existing = await db.execute(existing_query)
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already registered for this hackathon"
        )

    # Create registration
    registration = HackathonRegistration(
        **registration_data.model_dump(),
        user_id=current_user.id
    )

    db.add(registration)

    # Increment participant count
    hackathon.participant_count += 1

    await db.commit()
    await db.refresh(registration)

    return registration


@router.get("/registrations/my", response_model=List[RegistrationResponse])
async def get_my_registrations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's hackathon registrations"""

    query = select(HackathonRegistration).where(
        HackathonRegistration.user_id == current_user.id
    ).order_by(desc(HackathonRegistration.registered_at))

    result = await db.execute(query)
    registrations = result.scalars().all()

    return registrations


# ==================== SUBMISSION ENDPOINTS ====================

@router.post("/submissions", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def create_submission(
    submission_data: SubmissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a hackathon submission"""

    # Verify team exists and user is a member
    query = select(HackathonTeam).where(
        HackathonTeam.id == submission_data.team_id
    ).options(selectinload(HackathonTeam.members))

    result = await db.execute(query)
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )

    # Check if user is team member
    if current_user not in team.members:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this team"
        )

    # Create submission
    submission = HackathonSubmission(
        **submission_data.model_dump()
    )

    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    return submission


@router.get("/submissions/{submission_id}", response_model=SubmissionResponse)
async def get_submission(
    submission_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get submission by ID"""

    query = select(HackathonSubmission).where(HackathonSubmission.id == submission_id)
    result = await db.execute(query)
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )

    return submission


@router.patch("/submissions/{submission_id}", response_model=SubmissionResponse)
async def update_submission(
    submission_id: UUID,
    submission_data: SubmissionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update submission"""

    query = select(HackathonSubmission).where(
        HackathonSubmission.id == submission_id
    ).options(
        selectinload(HackathonSubmission.team).selectinload(HackathonTeam.members)
    )

    result = await db.execute(query)
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )

    # Check permission
    if current_user not in submission.team.members:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this submission"
        )

    # Update fields
    update_data = submission_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(submission, field, value)

    submission.updated_at = datetime.utcnow()

    # If submitting for first time
    if submission_data.status == SubmissionStatus.SUBMITTED and not submission.submitted_at:
        submission.submitted_at = datetime.utcnow()

    await db.commit()
    await db.refresh(submission)

    return submission


@router.post("/submissions/{submission_id}/score", response_model=dict)
async def score_submission(
    submission_id: UUID,
    score_data: SubmissionScore,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Score a submission (judges only)"""

    # Get submission
    query = select(HackathonSubmission).where(
        HackathonSubmission.id == submission_id
    ).options(selectinload(HackathonSubmission.hackathon))

    result = await db.execute(query)
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )

    # TODO: Verify user is a judge for this hackathon
    # For now, only organizer and admin can score
    if submission.hackathon.organizer_id != current_user.id and current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to score this submission"
        )

    # Calculate total score
    total_score = sum(score_data.criteria_scores.values())

    # Add score to scores array
    if not submission.scores:
        submission.scores = []

    submission.scores.append({
        "judge_id": str(current_user.id),
        "judge_name": current_user.full_name,
        "criteria": score_data.criteria_scores,
        "total": total_score,
        "feedback": score_data.feedback,
        "scored_at": datetime.utcnow().isoformat()
    })

    # Update total score (average of all judge scores)
    all_totals = [score["total"] for score in submission.scores]
    submission.total_score = sum(all_totals) / len(all_totals)

    await db.commit()

    return {"message": "Submission scored successfully", "total_score": float(submission.total_score)}


# ==================== APTITUDE TEST ENDPOINTS ====================

@router.post("/aptitude-tests", response_model=AptitudeTestResponse, status_code=status.HTTP_201_CREATED)
async def create_aptitude_test(
    test_data: AptitudeTestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create an aptitude test"""

    # If hackathon_id is provided, verify user is organizer
    if test_data.hackathon_id:
        query = select(Hackathon).where(Hackathon.id == test_data.hackathon_id)
        result = await db.execute(query)
        hackathon = result.scalar_one_or_none()

        if not hackathon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hackathon not found"
            )

        if hackathon.organizer_id != current_user.id and current_user.user_type != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to create test for this hackathon"
            )

    # Create test
    test = AptitudeTest(
        **test_data.model_dump(exclude={"questions"}),
        questions=[q.model_dump() for q in test_data.questions],
        total_questions=len(test_data.questions)
    )

    db.add(test)
    await db.commit()
    await db.refresh(test)

    return test


@router.post("/aptitude-tests/{test_id}/submit", response_model=TestResultResponse)
async def submit_aptitude_test(
    test_id: UUID,
    submission: TestSubmission,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit aptitude test answers"""

    # Get test
    query = select(AptitudeTest).where(AptitudeTest.id == test_id)
    result = await db.execute(query)
    test = result.scalar_one_or_none()

    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )

    # Calculate score
    score = 0
    total_points = 0
    answers_data = []

    for answer in submission.answers:
        question = test.questions[answer.question_index]
        total_points += question["points"]

        is_correct = answer.selected_option == question["correct"]
        if is_correct:
            score += question["points"]

        answers_data.append({
            "question_index": answer.question_index,
            "selected": answer.selected_option,
            "correct": is_correct
        })

    percentage = (score / total_points * 100) if total_points > 0 else 0
    passed = percentage >= test.passing_score

    # Create test result
    result = TestResult(
        test_id=test_id,
        user_id=current_user.id,
        score=score,
        total_points=total_points,
        percentage=percentage,
        passed=passed,
        answers=answers_data,
        started_at=datetime.utcnow(),  # TODO: Track actual start time
        completed_at=datetime.utcnow(),
        time_taken_minutes=0  # TODO: Calculate actual time
    )

    db.add(result)
    await db.commit()
    await db.refresh(result)

    return result


@router.get("/aptitude-tests/{test_id}/results/{result_id}", response_model=TestResultResponse)
async def get_test_result(
    test_id: UUID,
    result_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get test result"""

    query = select(TestResult).where(
        and_(
            TestResult.id == result_id,
            TestResult.test_id == test_id
        )
    )
    result = await db.execute(query)
    test_result = result.scalar_one_or_none()

    if not test_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test result not found"
        )

    # Only user or admin can view result
    if test_result.user_id != current_user.id and current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this result"
        )

    return test_result
