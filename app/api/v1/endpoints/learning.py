"""Learning endpoints - Courses, lessons, enrollments, and AI recommendations"""

from datetime import datetime
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc, or_
import uuid
import re

from app.core.database import get_db
from app.models.learning import Course, Lesson, Enrollment, LessonProgress
from app.models.user import User
from app.schemas.learning import (
    CourseCreate,
    CourseUpdate,
    CourseResponse,
    CourseWithEnrollment,
    CourseList,
    LessonCreate,
    LessonUpdate,
    LessonResponse,
    LessonWithProgress,
    EnrollmentCreate,
    EnrollmentResponse,
    EnrollmentWithCourse,
    EnrollmentList,
    LessonProgressUpdate,
    LessonProgressResponse,
    LearningPathRequest,
    LearningPathResponse,
    RecommendedCourse,
    CourseStatistics,
    UserLearningStats
)
from app.api.deps import get_current_user
from app.services.learning_path_service import LearningPathService

router = APIRouter()


# ============================================================================
# Helper Functions
# ============================================================================

def generate_slug(title: str) -> str:
    """Generate URL-friendly slug from title"""
    slug = title.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug[:255]


async def get_user_enrollment(
    db: AsyncSession,
    user_id: uuid.UUID,
    course_id: uuid.UUID
) -> Optional[Enrollment]:
    """Get user's enrollment for a course"""
    result = await db.execute(
        select(Enrollment).where(
            and_(
                Enrollment.user_id == user_id,
                Enrollment.course_id == course_id
            )
        )
    )
    return result.scalar_one_or_none()


# ============================================================================
# Course Endpoints
# ============================================================================

@router.post("/courses", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    course_data: CourseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create a new course

    Only instructors can create courses
    """
    # Generate unique slug
    base_slug = generate_slug(course_data.title)
    slug = base_slug

    # Ensure unique slug
    counter = 1
    while True:
        existing = await db.execute(
            select(Course).where(Course.slug == slug)
        )
        if not existing.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    course = Course(
        title=course_data.title,
        slug=slug,
        description=course_data.description,
        short_description=course_data.short_description,
        instructor_id=current_user.id,
        instructor_name=current_user.full_name,
        difficulty=course_data.difficulty,
        category=course_data.category,
        tags=course_data.tags,
        thumbnail_url=course_data.thumbnail_url,
        trailer_url=course_data.trailer_url,
        estimated_duration_minutes=course_data.estimated_duration_minutes,
        prerequisites=course_data.prerequisites,
        required_skills=course_data.required_skills,
        learning_outcomes=course_data.learning_outcomes,
        skills_gained=course_data.skills_gained,
        is_free=course_data.is_free,
        price=course_data.price if not course_data.is_free else None,
        currency=course_data.currency,
        has_certificate=course_data.has_certificate
    )

    db.add(course)
    await db.commit()
    await db.refresh(course)

    return course


@router.get("/courses", response_model=CourseList)
async def list_courses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    is_free: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    List all published courses with filters

    Returns courses with enrollment status if user is authenticated
    """
    # Build query
    query = select(Course).where(Course.status == "published")

    if category:
        query = query.where(Course.category == category)

    if difficulty:
        query = query.where(Course.difficulty == difficulty)

    if is_free is not None:
        query = query.where(Course.is_free == is_free)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Course.title.ilike(search_pattern),
                Course.description.ilike(search_pattern)
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Add pagination and ordering
    query = query.order_by(desc(Course.created_at)).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    courses = result.scalars().all()

    # Get enrollment status for user
    course_list = []
    for course in courses:
        enrollment_progress = None
        is_enrolled = False

        if current_user:
            enrollment = await get_user_enrollment(db, current_user.id, course.id)
            if enrollment:
                is_enrolled = True
                enrollment_progress = enrollment.progress_percentage

        course_list.append(
            CourseWithEnrollment(
                id=course.id,
                title=course.title,
                slug=course.slug,
                short_description=course.short_description,
                instructor_name=course.instructor_name,
                difficulty=course.difficulty,
                category=course.category,
                thumbnail_url=course.thumbnail_url,
                total_lessons=course.total_lessons,
                estimated_duration_minutes=course.estimated_duration_minutes,
                is_free=course.is_free,
                price=course.price,
                average_rating=course.average_rating,
                enrollment_count=course.enrollment_count,
                is_enrolled=is_enrolled,
                enrollment_progress=enrollment_progress,
                is_ai_recommended=course.is_ai_recommended,
                ai_match_score=course.ai_match_score
            )
        )

    return CourseList(
        items=course_list,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/courses/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get a specific course by ID"""
    result = await db.execute(
        select(Course).where(Course.id == course_id)
    )
    course = result.scalar_one_or_none()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    return course


@router.put("/courses/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: uuid.UUID,
    course_data: CourseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Update a course (only course instructor can update)"""
    result = await db.execute(
        select(Course).where(Course.id == course_id)
    )
    course = result.scalar_one_or_none()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    # Only instructor can update
    if course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor can update this course"
        )

    # Update fields
    update_data = course_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(course, field, value)

    # Update slug if title changed
    if "title" in update_data:
        course.slug = generate_slug(update_data["title"])

    # Publish course if status changed to published
    if course_data.status == "published" and not course.published_at:
        course.published_at = datetime.utcnow()

    await db.commit()
    await db.refresh(course)

    return course


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a course (only instructor can delete)"""
    result = await db.execute(
        select(Course).where(Course.id == course_id)
    )
    course = result.scalar_one_or_none()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    # Only instructor can delete
    if course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor can delete this course"
        )

    await db.delete(course)
    await db.commit()


# ============================================================================
# Lesson Endpoints
# ============================================================================

@router.post("/courses/{course_id}/lessons", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    course_id: uuid.UUID,
    lesson_data: LessonCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Create a new lesson in a course (instructor only)"""
    # Verify course exists and user is instructor
    course_result = await db.execute(
        select(Course).where(Course.id == course_id)
    )
    course = course_result.scalar_one_or_none()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    if course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor can add lessons"
        )

    lesson = Lesson(
        course_id=course_id,
        title=lesson_data.title,
        description=lesson_data.description,
        lesson_type=lesson_data.lesson_type,
        content_url=lesson_data.content_url,
        content_text=lesson_data.content_text,
        duration_minutes=lesson_data.duration_minutes,
        order=lesson_data.order,
        is_preview=lesson_data.is_preview,
        quiz_questions=lesson_data.quiz_questions,
        passing_score=lesson_data.passing_score,
        resources=lesson_data.resources
    )

    db.add(lesson)

    # Update course total lessons and duration
    course.total_lessons += 1
    course.estimated_duration_minutes += lesson_data.duration_minutes

    await db.commit()
    await db.refresh(lesson)

    return lesson


@router.get("/courses/{course_id}/lessons", response_model=list[LessonResponse])
async def list_course_lessons(
    course_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List all lessons in a course"""
    result = await db.execute(
        select(Lesson).where(Lesson.course_id == course_id).order_by(Lesson.order)
    )
    lessons = result.scalars().all()

    return lessons


@router.put("/lessons/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    lesson_id: uuid.UUID,
    lesson_data: LessonUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Update a lesson (instructor only)"""
    result = await db.execute(
        select(Lesson).where(Lesson.id == lesson_id)
    )
    lesson = result.scalar_one_or_none()

    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )

    # Check if user is course instructor
    course_result = await db.execute(
        select(Course).where(Course.id == lesson.course_id)
    )
    course = course_result.scalar_one_or_none()

    if course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor can update lessons"
        )

    # Update fields
    update_data = lesson_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lesson, field, value)

    await db.commit()
    await db.refresh(lesson)

    return lesson


# ============================================================================
# Enrollment Endpoints
# ============================================================================

@router.post("/enrollments", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def enroll_in_course(
    enrollment_data: EnrollmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Enroll in a course"""
    # Check if course exists
    course_result = await db.execute(
        select(Course).where(Course.id == enrollment_data.course_id)
    )
    course = course_result.scalar_one_or_none()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    if course.status != "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot enroll in unpublished course"
        )

    # Check if already enrolled
    existing_enrollment = await get_user_enrollment(db, current_user.id, course.id)
    if existing_enrollment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already enrolled in this course"
        )

    enrollment = Enrollment(
        user_id=current_user.id,
        course_id=course.id
    )

    db.add(enrollment)

    # Update course enrollment count
    course.enrollment_count += 1

    await db.commit()
    await db.refresh(enrollment)

    return enrollment


@router.get("/enrollments/my", response_model=EnrollmentList)
async def list_my_enrollments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, pattern="^(active|completed|dropped)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List current user's course enrollments"""
    query = select(Enrollment).where(Enrollment.user_id == current_user.id)

    if status_filter:
        query = query.where(Enrollment.status == status_filter)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Add pagination and ordering
    query = query.order_by(desc(Enrollment.last_accessed_at)).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    enrollments = result.scalars().all()

    # Enrich with course details
    enrollment_list = []
    for enrollment in enrollments:
        course_result = await db.execute(
            select(Course).where(Course.id == enrollment.course_id)
        )
        course = course_result.scalar_one_or_none()

        if course:
            enrollment_list.append(
                EnrollmentWithCourse(
                    id=enrollment.id,
                    course_id=course.id,
                    course_title=course.title,
                    course_thumbnail=course.thumbnail_url,
                    instructor_name=course.instructor_name,
                    status=enrollment.status,
                    progress_percentage=enrollment.progress_percentage,
                    lessons_completed=enrollment.lessons_completed,
                    total_lessons=course.total_lessons,
                    is_completed=enrollment.is_completed,
                    last_accessed_at=enrollment.last_accessed_at,
                    enrolled_at=enrollment.enrolled_at
                )
            )

    return EnrollmentList(
        items=enrollment_list,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/enrollments/{enrollment_id}", response_model=EnrollmentResponse)
async def get_enrollment(
    enrollment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get specific enrollment"""
    result = await db.execute(
        select(Enrollment).where(Enrollment.id == enrollment_id)
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found"
        )

    # Verify ownership
    if enrollment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this enrollment"
        )

    return enrollment


# ============================================================================
# Lesson Progress Endpoints
# ============================================================================

@router.post("/enrollments/{enrollment_id}/lessons/{lesson_id}/progress", response_model=LessonProgressResponse)
async def update_lesson_progress(
    enrollment_id: uuid.UUID,
    lesson_id: uuid.UUID,
    progress_data: LessonProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Update progress for a specific lesson"""
    # Verify enrollment
    enrollment_result = await db.execute(
        select(Enrollment).where(Enrollment.id == enrollment_id)
    )
    enrollment = enrollment_result.scalar_one_or_none()

    if not enrollment or enrollment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found"
        )

    # Get or create lesson progress
    progress_result = await db.execute(
        select(LessonProgress).where(
            and_(
                LessonProgress.user_id == current_user.id,
                LessonProgress.lesson_id == lesson_id
            )
        )
    )
    progress = progress_result.scalar_one_or_none()

    if not progress:
        progress = LessonProgress(
            user_id=current_user.id,
            enrollment_id=enrollment_id,
            lesson_id=lesson_id
        )
        db.add(progress)

    # Update fields
    update_data = progress_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(progress, field, value)

    # Mark as completed if 100%
    if progress.progress_percentage >= 100 and not progress.is_completed:
        progress.is_completed = True
        progress.completed_at = datetime.utcnow()

        # Update enrollment
        enrollment.lessons_completed += 1
        enrollment.current_lesson_id = lesson_id

    progress.last_accessed_at = datetime.utcnow()
    enrollment.last_accessed_at = datetime.utcnow()

    # Update overall enrollment progress
    course_result = await db.execute(
        select(Course).where(Course.id == enrollment.course_id)
    )
    course = course_result.scalar_one()

    if course.total_lessons > 0:
        enrollment.progress_percentage = (enrollment.lessons_completed / course.total_lessons) * 100

        # Mark enrollment as completed if all lessons done
        if enrollment.lessons_completed >= course.total_lessons and not enrollment.is_completed:
            enrollment.is_completed = True
            enrollment.completed_at = datetime.utcnow()
            enrollment.status = "completed"

            # Update course completion count
            course.completion_count += 1

    await db.commit()
    await db.refresh(progress)

    return progress


# ============================================================================
# AI Learning Path Endpoints
# ============================================================================

@router.post("/learning-path/recommend", response_model=LearningPathResponse)
async def get_learning_path_recommendations(
    request_data: LearningPathRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get AI-powered learning path recommendations

    Analyzes user skills, goals, and preferences to recommend personalized course paths
    """
    recommendations, metadata = await LearningPathService.recommend_courses(
        db=db,
        user_id=current_user.id,
        user_skills=request_data.user_skills,
        target_skills=request_data.target_skills,
        difficulty_preference=request_data.difficulty_preference,
        time_available_hours_per_week=request_data.time_available_hours_per_week,
        career_goal=request_data.career_goal
    )

    # Convert to response format
    recommended_courses = [
        RecommendedCourse(
            course=CourseResponse.model_validate(rec["course"]),
            match_score=rec["match_score"],
            recommendation_reason=rec["recommendation_reason"],
            estimated_completion_weeks=rec["estimated_completion_weeks"]
        )
        for rec in recommendations
    ]

    return LearningPathResponse(
        recommended_courses=recommended_courses,
        total_estimated_hours=metadata["total_estimated_hours"],
        total_estimated_weeks=metadata["total_estimated_weeks"],
        skill_gaps=metadata["skill_gaps"],
        path_description=metadata["path_description"]
    )


# ============================================================================
# Statistics Endpoints
# ============================================================================

@router.get("/stats/my", response_model=UserLearningStats)
async def get_my_learning_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get current user's learning statistics"""
    # Total enrollments
    total_result = await db.execute(
        select(func.count()).select_from(Enrollment).where(
            Enrollment.user_id == current_user.id
        )
    )
    total_enrolled = total_result.scalar()

    # In progress
    in_progress_result = await db.execute(
        select(func.count()).select_from(Enrollment).where(
            and_(
                Enrollment.user_id == current_user.id,
                Enrollment.status == "active"
            )
        )
    )
    in_progress = in_progress_result.scalar()

    # Completed
    completed_result = await db.execute(
        select(func.count()).select_from(Enrollment).where(
            and_(
                Enrollment.user_id == current_user.id,
                Enrollment.status == "completed"
            )
        )
    )
    completed = completed_result.scalar()

    # Total time spent
    time_result = await db.execute(
        select(func.sum(Enrollment.total_time_spent_minutes)).where(
            Enrollment.user_id == current_user.id
        )
    )
    total_time_minutes = time_result.scalar() or 0

    # Certificates earned
    cert_result = await db.execute(
        select(func.count()).select_from(Enrollment).where(
            and_(
                Enrollment.user_id == current_user.id,
                Enrollment.certificate_issued == True
            )
        )
    )
    certificates = cert_result.scalar()

    # Skills acquired (from completed courses)
    completed_enrollments = await db.execute(
        select(Enrollment).where(
            and_(
                Enrollment.user_id == current_user.id,
                Enrollment.status == "completed"
            )
        )
    )
    skills_set = set()
    for enrollment in completed_enrollments.scalars():
        course_result = await db.execute(
            select(Course).where(Course.id == enrollment.course_id)
        )
        course = course_result.scalar_one_or_none()
        if course and course.skills_gained:
            skills_set.update(course.skills_gained)

    return UserLearningStats(
        total_courses_enrolled=total_enrolled,
        courses_in_progress=in_progress,
        courses_completed=completed,
        total_time_spent_hours=int(total_time_minutes / 60),
        certificates_earned=certificates,
        skills_acquired=list(skills_set)
    )
