"""Learning schemas - Pydantic models for validation"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import uuid


# ============================================================================
# Course Schemas
# ============================================================================

class CourseCreate(BaseModel):
    """Schema for creating a course"""
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10)
    short_description: str = Field(..., min_length=10, max_length=500)
    difficulty: str = Field(..., pattern="^(beginner|intermediate|advanced|expert)$")
    category: str = Field(..., min_length=2, max_length=100)
    tags: Optional[List[str]] = None
    thumbnail_url: Optional[str] = None
    trailer_url: Optional[str] = None
    estimated_duration_minutes: int = Field(..., ge=1)
    prerequisites: Optional[List[uuid.UUID]] = None
    required_skills: Optional[List[str]] = None
    learning_outcomes: Optional[List[str]] = None
    skills_gained: Optional[List[str]] = None
    is_free: bool = True
    price: Optional[float] = Field(None, ge=0)
    currency: str = "USD"
    has_certificate: bool = True


class CourseUpdate(BaseModel):
    """Schema for updating a course"""
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, min_length=10)
    short_description: Optional[str] = Field(None, min_length=10, max_length=500)
    difficulty: Optional[str] = Field(None, pattern="^(beginner|intermediate|advanced|expert)$")
    category: Optional[str] = Field(None, min_length=2, max_length=100)
    tags: Optional[List[str]] = None
    thumbnail_url: Optional[str] = None
    trailer_url: Optional[str] = None
    estimated_duration_minutes: Optional[int] = Field(None, ge=1)
    prerequisites: Optional[List[uuid.UUID]] = None
    required_skills: Optional[List[str]] = None
    learning_outcomes: Optional[List[str]] = None
    skills_gained: Optional[List[str]] = None
    is_free: Optional[bool] = None
    price: Optional[float] = Field(None, ge=0)
    status: Optional[str] = Field(None, pattern="^(draft|published|archived)$")


class CourseResponse(BaseModel):
    """Schema for course response"""
    id: uuid.UUID
    title: str
    slug: str
    description: str
    short_description: str
    instructor_id: uuid.UUID
    instructor_name: str
    difficulty: str
    status: str
    category: str
    tags: Optional[List[str]] = None
    thumbnail_url: Optional[str] = None
    trailer_url: Optional[str] = None
    total_lessons: int
    estimated_duration_minutes: int
    prerequisites: Optional[List[uuid.UUID]] = None
    required_skills: Optional[List[str]] = None
    learning_outcomes: Optional[List[str]] = None
    skills_gained: Optional[List[str]] = None
    is_free: bool
    price: Optional[float] = None
    currency: str
    is_ai_recommended: bool
    ai_match_score: Optional[float] = None
    enrollment_count: int
    completion_count: int
    average_rating: Optional[float] = None
    total_reviews: int
    has_certificate: bool
    certificate_template: Optional[str] = None
    course_metadata: dict = Field(default_factory=dict)
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CourseWithEnrollment(BaseModel):
    """Course with user enrollment status"""
    id: uuid.UUID
    title: str
    slug: str
    short_description: str
    instructor_name: str
    difficulty: str
    category: str
    thumbnail_url: Optional[str] = None
    total_lessons: int
    estimated_duration_minutes: int
    is_free: bool
    price: Optional[float] = None
    average_rating: Optional[float] = None
    enrollment_count: int
    is_enrolled: bool
    enrollment_progress: Optional[float] = None
    is_ai_recommended: bool
    ai_match_score: Optional[float] = None


class CourseList(BaseModel):
    """Paginated list of courses"""
    items: List[CourseWithEnrollment]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# Lesson Schemas
# ============================================================================

class LessonCreate(BaseModel):
    """Schema for creating a lesson"""
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    lesson_type: str = Field(..., pattern="^(video|text|quiz|interactive|assignment|live_session)$")
    content_url: Optional[str] = None
    content_text: Optional[str] = None
    duration_minutes: int = Field(default=0, ge=0)
    order: int = Field(..., ge=1)
    is_preview: bool = False
    quiz_questions: Optional[List[dict]] = None
    passing_score: Optional[int] = Field(None, ge=0, le=100)
    resources: Optional[List[dict]] = None


class LessonUpdate(BaseModel):
    """Schema for updating a lesson"""
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    lesson_type: Optional[str] = Field(None, pattern="^(video|text|quiz|interactive|assignment|live_session)$")
    content_url: Optional[str] = None
    content_text: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, ge=0)
    order: Optional[int] = Field(None, ge=1)
    is_preview: Optional[bool] = None
    quiz_questions: Optional[List[dict]] = None
    passing_score: Optional[int] = Field(None, ge=0, le=100)
    resources: Optional[List[dict]] = None


class LessonResponse(BaseModel):
    """Schema for lesson response"""
    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    description: Optional[str] = None
    lesson_type: str
    content_url: Optional[str] = None
    content_text: Optional[str] = None
    duration_minutes: int
    order: int
    is_preview: bool
    quiz_questions: Optional[List[dict]] = None
    passing_score: Optional[int] = None
    resources: Optional[List[dict]] = None
    lesson_metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LessonWithProgress(BaseModel):
    """Lesson with user progress"""
    id: uuid.UUID
    title: str
    lesson_type: str
    duration_minutes: int
    order: int
    is_preview: bool
    is_completed: bool
    progress_percentage: float
    time_spent_minutes: int


# ============================================================================
# Enrollment Schemas
# ============================================================================

class EnrollmentCreate(BaseModel):
    """Schema for enrolling in a course"""
    course_id: uuid.UUID


class EnrollmentResponse(BaseModel):
    """Schema for enrollment response"""
    id: uuid.UUID
    user_id: uuid.UUID
    course_id: uuid.UUID
    status: str
    progress_percentage: float
    lessons_completed: int
    current_lesson_id: Optional[uuid.UUID] = None
    total_time_spent_minutes: int
    is_completed: bool
    completed_at: Optional[datetime] = None
    final_score: Optional[float] = None
    certificate_issued: bool
    certificate_id: Optional[str] = None
    certificate_url: Optional[str] = None
    enrollment_metadata: dict = Field(default_factory=dict)
    enrolled_at: datetime
    last_accessed_at: Optional[datetime] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class EnrollmentWithCourse(BaseModel):
    """Enrollment with course details"""
    id: uuid.UUID
    course_id: uuid.UUID
    course_title: str
    course_thumbnail: Optional[str] = None
    instructor_name: str
    status: str
    progress_percentage: float
    lessons_completed: int
    total_lessons: int
    is_completed: bool
    last_accessed_at: Optional[datetime] = None
    enrolled_at: datetime


class EnrollmentList(BaseModel):
    """Paginated list of enrollments"""
    items: List[EnrollmentWithCourse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# Lesson Progress Schemas
# ============================================================================

class LessonProgressUpdate(BaseModel):
    """Schema for updating lesson progress"""
    progress_percentage: Optional[float] = Field(None, ge=0, le=100)
    time_spent_minutes: Optional[int] = Field(None, ge=0)
    quiz_score: Optional[float] = Field(None, ge=0, le=100)
    user_notes: Optional[str] = None
    is_completed: Optional[bool] = None


class LessonProgressResponse(BaseModel):
    """Schema for lesson progress response"""
    id: uuid.UUID
    user_id: uuid.UUID
    enrollment_id: uuid.UUID
    lesson_id: uuid.UUID
    is_completed: bool
    progress_percentage: float
    time_spent_minutes: int
    quiz_score: Optional[float] = None
    quiz_attempts: int
    quiz_passed: bool
    user_notes: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    last_accessed_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============================================================================
# Learning Path Schemas
# ============================================================================

class LearningPathRequest(BaseModel):
    """Request for AI learning path recommendation"""
    user_skills: Optional[List[str]] = None
    target_skills: Optional[List[str]] = None
    difficulty_preference: Optional[str] = Field(None, pattern="^(beginner|intermediate|advanced|expert)$")
    time_available_hours_per_week: Optional[int] = Field(None, ge=1, le=168)
    career_goal: Optional[str] = None


class RecommendedCourse(BaseModel):
    """AI recommended course"""
    course: CourseResponse
    match_score: float = Field(..., ge=0, le=100)
    recommendation_reason: str
    estimated_completion_weeks: int


class LearningPathResponse(BaseModel):
    """AI-generated learning path"""
    recommended_courses: List[RecommendedCourse]
    total_estimated_hours: int
    total_estimated_weeks: int
    skill_gaps: List[str]
    path_description: str


# ============================================================================
# Certificate Schema
# ============================================================================

class CertificateResponse(BaseModel):
    """Certificate details"""
    certificate_id: str
    certificate_url: str
    course_title: str
    user_name: str
    issued_at: datetime
    completion_score: Optional[float] = None


# ============================================================================
# Statistics Schemas
# ============================================================================

class CourseStatistics(BaseModel):
    """Course statistics"""
    total_enrollments: int
    active_enrollments: int
    completed_enrollments: int
    average_completion_rate: float
    average_time_to_complete_hours: float
    average_rating: Optional[float] = None


class UserLearningStats(BaseModel):
    """User learning statistics"""
    total_courses_enrolled: int
    courses_in_progress: int
    courses_completed: int
    total_time_spent_hours: int
    certificates_earned: int
    skills_acquired: List[str]
