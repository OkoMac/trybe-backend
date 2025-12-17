"""Aptitude Test API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_active_user
from app.models.user import User
from app.models.hackathon import AptitudeTest, TestResult
from app.services.aptitude_service import AptitudeTestService


router = APIRouter()


# Schemas

class QuestionCreate(BaseModel):
    """Schema for creating a test question"""
    question: str = Field(..., min_length=10, max_length=1000, description="Question text")
    options: List[str] = Field(..., min_items=2, max_items=6, description="Answer options")
    correct: int = Field(..., ge=0, description="Index of correct answer (0-based)")
    points: int = Field(5, ge=1, le=20, description="Points for this question")

    @validator('correct')
    def validate_correct_index(cls, v, values):
        if 'options' in values and v >= len(values['options']):
            raise ValueError('Correct answer index must be within options range')
        return v


class AptitudeTestCreate(BaseModel):
    """Schema for creating an aptitude test"""
    hackathon_id: uuid.UUID = Field(..., description="Associated hackathon ID")
    title: str = Field(..., min_length=5, max_length=255, description="Test title")
    description: Optional[str] = Field(None, max_length=2000, description="Test description")
    duration_minutes: int = Field(60, ge=5, le=180, description="Test duration in minutes")
    passing_score: int = Field(70, ge=0, le=100, description="Passing score percentage")
    questions: List[QuestionCreate] = Field(..., min_items=5, max_items=100, description="Test questions")


class AptitudeTestResponse(BaseModel):
    """Schema for aptitude test response"""
    id: uuid.UUID
    hackathon_id: uuid.UUID
    title: str
    description: Optional[str]
    duration_minutes: int
    passing_score: int
    total_questions: int
    total_points: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TestForUserResponse(BaseModel):
    """Schema for test details shown to users (without answers)"""
    id: str
    title: str
    description: Optional[str]
    duration_minutes: int
    total_questions: int
    total_points: int
    passing_score: int
    questions: List[Dict[str, Any]]
    already_attempted: bool
    previous_score: Optional[float]
    previous_passed: Optional[bool]


class StartTestResponse(BaseModel):
    """Schema for test start response"""
    test_id: str
    started_at: datetime
    expires_at: datetime
    duration_minutes: int


class SubmitTestRequest(BaseModel):
    """Schema for submitting test answers"""
    answers: List[int] = Field(..., description="List of answer indices (0-based)")
    started_at: datetime = Field(..., description="When the test was started")


class TestResultResponse(BaseModel):
    """Schema for test result"""
    id: uuid.UUID
    test_id: uuid.UUID
    score: int
    total_points: int
    percentage: float
    passed: bool
    time_taken_minutes: int
    started_at: datetime
    completed_at: datetime

    class Config:
        from_attributes = True


class DetailedResultResponse(BaseModel):
    """Schema for detailed test result with answer review"""
    id: str
    test_id: str
    test_title: str
    score: int
    total_points: int
    percentage: float
    passed: bool
    passing_score: int
    time_taken_minutes: int
    started_at: str
    completed_at: str
    answer_review: List[Dict[str, Any]]


class TestStatisticsResponse(BaseModel):
    """Schema for test statistics"""
    total_attempts: int
    average_score: float
    pass_rate: float
    average_time_minutes: float
    highest_score: Optional[float] = None
    lowest_score: Optional[float] = None


# Endpoints

@router.post("/tests", response_model=AptitudeTestResponse, status_code=status.HTTP_201_CREATED)
async def create_aptitude_test(
    test_data: AptitudeTestCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new aptitude test

    **Requirements:**
    - At least 5 questions
    - Each question must have 2-6 options
    - Each question must specify correct answer index
    - Points per question (1-20)

    **Question Format:**
    ```json
    {
        "question": "What is 2 + 2?",
        "options": ["2", "3", "4", "5"],
        "correct": 2,
        "points": 5
    }
    ```

    **Only admins or hackathon organizers can create tests.**
    """
    # TODO: Add authorization check (admin or hackathon organizer)

    try:
        # Convert Pydantic questions to dict
        questions_dict = [q.model_dump() for q in test_data.questions]

        test = await AptitudeTestService.create_test(
            db=db,
            hackathon_id=test_data.hackathon_id,
            title=test_data.title,
            description=test_data.description,
            questions=questions_dict,
            duration_minutes=test_data.duration_minutes,
            passing_score=test_data.passing_score
        )

        return test

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/tests", response_model=List[AptitudeTestResponse])
async def list_aptitude_tests(
    hackathon_id: Optional[uuid.UUID] = Query(None, description="Filter by hackathon"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    List all aptitude tests

    Filters:
    - **hackathon_id**: Filter tests by hackathon
    - **is_active**: Filter active/inactive tests
    """
    query = select(AptitudeTest)

    if hackathon_id:
        query = query.where(AptitudeTest.hackathon_id == hackathon_id)

    if is_active is not None:
        query = query.where(AptitudeTest.is_active == is_active)

    # Add pagination
    query = query.order_by(desc(AptitudeTest.created_at)).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    tests = result.scalars().all()

    return tests


@router.get("/tests/{test_id}", response_model=TestForUserResponse)
async def get_aptitude_test(
    test_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get aptitude test details

    Returns test information without correct answers.
    Shows if user has already attempted the test.
    """
    test_data = await AptitudeTestService.get_test_for_user(
        db=db,
        test_id=test_id,
        user_id=current_user.id
    )

    if not test_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found or not active"
        )

    return TestForUserResponse(**test_data)


@router.post("/tests/{test_id}/start", response_model=StartTestResponse)
async def start_aptitude_test(
    test_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Start an aptitude test

    Records the start time and returns test expiration time.
    User must submit answers before expiration.

    **Note:** Each user can only attempt a test once.
    """
    # Check if test exists and is active
    result = await db.execute(
        select(AptitudeTest).where(AptitudeTest.id == test_id)
    )
    test = result.scalar_one_or_none()

    if not test or not test.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found or not active"
        )

    # Check if user already took the test
    result_check = await db.execute(
        select(TestResult).where(
            and_(
                TestResult.test_id == test_id,
                TestResult.user_id == current_user.id
            )
        )
    )
    if result_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already attempted this test"
        )

    started_at = datetime.utcnow()
    expires_at = started_at + timedelta(minutes=test.duration_minutes)

    return StartTestResponse(
        test_id=str(test.id),
        started_at=started_at,
        expires_at=expires_at,
        duration_minutes=test.duration_minutes
    )


@router.post("/tests/{test_id}/submit", response_model=TestResultResponse)
async def submit_aptitude_test(
    test_id: uuid.UUID,
    submission: SubmitTestRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit aptitude test answers

    Automatically scores the test and returns results.

    **Request Body:**
    ```json
    {
        "answers": [2, 0, 3, 1, 2],
        "started_at": "2024-01-01T10:00:00Z"
    }
    ```

    **answers**: List of answer indices (0-based), one per question in order

    **Note:**
    - Must submit within test duration
    - Can only submit once
    - Answers are automatically scored
    """
    try:
        # Check time limit
        elapsed_minutes = (datetime.utcnow() - submission.started_at).total_seconds() / 60
        test_result = await db.execute(
            select(AptitudeTest).where(AptitudeTest.id == test_id)
        )
        test = test_result.scalar_one_or_none()

        if test and elapsed_minutes > test.duration_minutes + 5:  # 5 minute grace period
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Test duration exceeded"
            )

        result = await AptitudeTestService.submit_test(
            db=db,
            test_id=test_id,
            user_id=current_user.id,
            answers=submission.answers,
            started_at=submission.started_at
        )

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/results/{result_id}", response_model=DetailedResultResponse)
async def get_test_result(
    result_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed test result

    Shows:
    - Overall score and pass/fail status
    - Time taken
    - Question-by-question review
    - Correct and incorrect answers

    **Only accessible to the user who took the test.**
    """
    result_data = await AptitudeTestService.get_test_result(
        db=db,
        result_id=result_id,
        user_id=current_user.id
    )

    if not result_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found"
        )

    return DetailedResultResponse(**result_data)


@router.get("/results/my/history")
async def get_my_test_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's test history

    Returns all tests taken by the current user with results.
    """
    query = (
        select(TestResult)
        .where(TestResult.user_id == current_user.id)
        .order_by(desc(TestResult.completed_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(query)
    results = result.scalars().all()

    # Enrich with test details
    history = []
    for test_result in results:
        test_query = await db.execute(
            select(AptitudeTest).where(AptitudeTest.id == test_result.test_id)
        )
        test = test_query.scalar_one_or_none()

        if test:
            history.append({
                "result_id": str(test_result.id),
                "test_id": str(test.id),
                "test_title": test.title,
                "score": test_result.score,
                "total_points": test_result.total_points,
                "percentage": float(test_result.percentage),
                "passed": test_result.passed,
                "time_taken_minutes": test_result.time_taken_minutes,
                "completed_at": test_result.completed_at.isoformat()
            })

    return {"history": history}


@router.get("/tests/{test_id}/statistics", response_model=TestStatisticsResponse)
async def get_test_statistics(
    test_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get statistics for a test

    Shows:
    - Total number of attempts
    - Average score
    - Pass rate
    - Average time taken
    - Highest and lowest scores

    **Only admins or test creators can view statistics.**
    """
    # TODO: Add authorization check

    stats = await AptitudeTestService.get_test_statistics(db, test_id)

    return TestStatisticsResponse(**stats)


@router.patch("/tests/{test_id}/deactivate", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_test(
    test_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Deactivate an aptitude test

    Prevents new users from taking the test.
    Existing results are preserved.

    **Only admins or test creators can deactivate tests.**
    """
    # TODO: Add authorization check

    result = await db.execute(
        select(AptitudeTest).where(AptitudeTest.id == test_id)
    )
    test = result.scalar_one_or_none()

    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )

    test.is_active = False
    await db.commit()


@router.patch("/tests/{test_id}/activate", status_code=status.HTTP_204_NO_CONTENT)
async def activate_test(
    test_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reactivate an aptitude test

    Allows users to take the test again.

    **Only admins or test creators can activate tests.**
    """
    # TODO: Add authorization check

    result = await db.execute(
        select(AptitudeTest).where(AptitudeTest.id == test_id)
    )
    test = result.scalar_one_or_none()

    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )

    test.is_active = True
    await db.commit()
