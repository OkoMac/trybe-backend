"""Learning models - Courses, lessons, enrollments, and progress tracking"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Text, ForeignKey, Integer, Float, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
import uuid
import enum

from app.core.database import Base


class CourseDifficultyEnum(str, enum.Enum):
    """Course difficulty levels"""
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"
    expert = "expert"


class CourseStatusEnum(str, enum.Enum):
    """Course status"""
    draft = "draft"
    published = "published"
    archived = "archived"


class LessonTypeEnum(str, enum.Enum):
    """Lesson content types"""
    video = "video"
    text = "text"
    quiz = "quiz"
    interactive = "interactive"
    assignment = "assignment"
    live_session = "live_session"


class EnrollmentStatusEnum(str, enum.Enum):
    """Enrollment status"""
    active = "active"
    completed = "completed"
    dropped = "dropped"
    expired = "expired"


class Course(Base):
    """Course model - represents a learning course"""

    __tablename__ = "courses"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # Course Information
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    slug: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="URL-friendly course identifier"
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    short_description: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Brief course summary"
    )

    # Course Creator
    instructor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    instructor_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Cached instructor name for performance"
    )

    # Course Metadata
    difficulty: Mapped[CourseDifficultyEnum] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )
    status: Mapped[CourseStatusEnum] = mapped_column(
        String(20),
        default=CourseStatusEnum.draft,
        nullable=False,
        index=True
    )
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Course category (e.g., 'Programming', 'Design', 'Business')"
    )
    tags: Mapped[Optional[list]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Array of searchable tags"
    )

    # Course Content
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    trailer_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Course preview/trailer video URL"
    )

    # Course Structure
    total_lessons: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Estimated time to complete in minutes"
    )

    # Prerequisites
    prerequisites: Mapped[Optional[list]] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        nullable=True,
        comment="Array of prerequisite course IDs"
    )
    required_skills: Mapped[Optional[list]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Skills required before taking this course"
    )

    # Learning Outcomes
    learning_outcomes: Mapped[Optional[list]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="What students will learn"
    )
    skills_gained: Mapped[Optional[list]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Skills acquired after completion"
    )

    # Pricing
    is_free: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    price: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Course price (if not free)"
    )
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    # AI Recommendations
    is_ai_recommended: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if AI recommends this course"
    )
    ai_match_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="AI match score for user (0-100)"
    )

    # Statistics
    enrollment_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_reviews: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Certificates
    has_certificate: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether course awards a certificate"
    )
    certificate_template: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Certificate template name"
    )

    # Additional data
    course_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        default=dict,
        comment="Additional course metadata"
    )

    # Timestamps
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When course was published"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Indexes
    __table_args__ = (
        Index('ix_courses_difficulty_category', 'difficulty', 'category'),
        Index('ix_courses_status_created', 'status', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<Course {self.title}>"


class Lesson(Base):
    """Lesson model - individual lessons within a course"""

    __tablename__ = "lessons"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # Course Relationship
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Lesson Information
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lesson_type: Mapped[LessonTypeEnum] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )

    # Lesson Content
    content_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Video URL, document URL, etc."
    )
    content_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Text content for text-based lessons"
    )
    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Estimated lesson duration"
    )

    # Lesson Order
    order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Lesson order within the course"
    )
    is_preview: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if lesson is available as preview"
    )

    # Quiz/Assessment
    quiz_questions: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Array of quiz question objects (for quiz lessons)"
    )
    passing_score: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Minimum score to pass (for quiz lessons)"
    )

    # Resources
    resources: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Downloadable resources, links, etc."
    )

    # Additional data
    lesson_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        default=dict,
        comment="Additional lesson metadata"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Indexes
    __table_args__ = (
        Index('ix_lessons_course_order', 'course_id', 'order'),
    )

    def __repr__(self) -> str:
        return f"<Lesson {self.title}>"


class Enrollment(Base):
    """Enrollment model - tracks user course enrollments"""

    __tablename__ = "enrollments"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # User and Course
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Enrollment Status
    status: Mapped[EnrollmentStatusEnum] = mapped_column(
        String(20),
        default=EnrollmentStatusEnum.active,
        nullable=False,
        index=True
    )

    # Progress
    progress_percentage: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Overall course completion percentage (0-100)"
    )
    lessons_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_lesson_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lessons.id", ondelete="SET NULL"),
        nullable=True,
        comment="Last lesson user was on"
    )

    # Time Tracking
    total_time_spent_minutes: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total time spent on course"
    )

    # Completion
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    final_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Final course score (if applicable)"
    )

    # Certificate
    certificate_issued: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    certificate_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
        comment="Unique certificate identifier"
    )
    certificate_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )

    # Additional data
    enrollment_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        default=dict,
        comment="Additional enrollment metadata"
    )

    # Timestamps
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When user last accessed the course"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Constraints
    __table_args__ = (
        Index('ix_enrollments_user_course', 'user_id', 'course_id', unique=True),
        Index('ix_enrollments_status_enrolled', 'status', 'enrolled_at'),
    )

    def __repr__(self) -> str:
        return f"<Enrollment user={self.user_id} course={self.course_id}>"


class LessonProgress(Base):
    """Lesson progress model - tracks user progress through individual lessons"""

    __tablename__ = "lesson_progress"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # Relationships
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    enrollment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enrollments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Progress
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    progress_percentage: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Lesson completion percentage (0-100)"
    )
    time_spent_minutes: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    # Quiz/Assessment Results
    quiz_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Score on quiz (if applicable)"
    )
    quiz_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    quiz_passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Notes
    user_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="User's notes for this lesson"
    )

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    last_accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Constraints
    __table_args__ = (
        Index('ix_lesson_progress_user_lesson', 'user_id', 'lesson_id', unique=True),
        Index('ix_lesson_progress_enrollment_lesson', 'enrollment_id', 'lesson_id'),
    )

    def __repr__(self) -> str:
        return f"<LessonProgress user={self.user_id} lesson={self.lesson_id}>"
