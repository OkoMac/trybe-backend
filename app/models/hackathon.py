"""Hackathon Models"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Boolean, Enum as SQLEnum, DECIMAL, Table
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from enum import Enum

from app.core.database import Base


# Enums
class HackathonStatus(str, Enum):
    """Hackathon status"""
    DRAFT = "draft"
    UPCOMING = "upcoming"
    REGISTRATION_OPEN = "registration_open"
    IN_PROGRESS = "in_progress"
    JUDGING = "judging"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DifficultyLevel(str, Enum):
    """Difficulty level"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class SubmissionStatus(str, Enum):
    """Submission status"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    WINNER = "winner"


# Association tables
team_members = Table(
    'team_members',
    Base.metadata,
    Column('team_id', PG_UUID(as_uuid=True), ForeignKey('hackathon_teams.id', ondelete='CASCADE')),
    Column('user_id', PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE')),
    Column('joined_at', DateTime, default=datetime.utcnow)
)


# Models
class Hackathon(Base):
    """Hackathon event model"""
    __tablename__ = "hackathons"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    short_description = Column(String(500))

    # Organizer
    organizer_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    # Schedule
    registration_start = Column(DateTime, nullable=False)
    registration_end = Column(DateTime, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)

    # Configuration
    max_participants = Column(Integer)
    max_team_size = Column(Integer, default=5)
    min_team_size = Column(Integer, default=1)
    is_team_required = Column(Boolean, default=False)

    # Details
    difficulty_level = Column(SQLEnum(DifficultyLevel), default=DifficultyLevel.INTERMEDIATE)
    status = Column(SQLEnum(HackathonStatus), default=HackathonStatus.DRAFT, index=True)

    # Prizes
    prizes = Column(JSONB, default=[])  # [{"place": 1, "amount": 5000, "description": "..."}]
    total_prize_pool = Column(DECIMAL(10, 2))

    # Requirements
    required_skills = Column(ARRAY(String), default=[])
    categories = Column(ARRAY(String), default=[])

    # Media
    banner_url = Column(String(500))
    logo_url = Column(String(500))

    # Judging criteria
    judging_criteria = Column(JSONB, default=[])  # [{"name": "Innovation", "weight": 30}]

    # Rules and guidelines
    rules = Column(Text)
    submission_guidelines = Column(Text)

    # Metadata
    is_public = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    view_count = Column(Integer, default=0)
    participant_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organizer = relationship("User", back_populates="organized_hackathons")
    teams = relationship("HackathonTeam", back_populates="hackathon", cascade="all, delete-orphan")
    registrations = relationship("HackathonRegistration", back_populates="hackathon", cascade="all, delete-orphan")
    submissions = relationship("HackathonSubmission", back_populates="hackathon", cascade="all, delete-orphan")


class HackathonTeam(Base):
    """Hackathon team model"""
    __tablename__ = "hackathon_teams"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    hackathon_id = Column(PG_UUID(as_uuid=True), ForeignKey('hackathons.id', ondelete='CASCADE'), nullable=False)

    # Team details
    name = Column(String(255), nullable=False)
    description = Column(Text)
    team_leader_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    # Media
    logo_url = Column(String(500))

    # Metadata
    is_public = Column(Boolean, default=True)
    max_members = Column(Integer, default=5)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    hackathon = relationship("Hackathon", back_populates="teams")
    team_leader = relationship("User", foreign_keys=[team_leader_id])
    members = relationship("User", secondary=team_members, back_populates="hackathon_teams")
    submission = relationship("HackathonSubmission", back_populates="team", uselist=False)


class HackathonRegistration(Base):
    """Hackathon registration model"""
    __tablename__ = "hackathon_registrations"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    hackathon_id = Column(PG_UUID(as_uuid=True), ForeignKey('hackathons.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # Registration details
    team_id = Column(PG_UUID(as_uuid=True), ForeignKey('hackathon_teams.id', ondelete='SET NULL'))

    # Status
    is_confirmed = Column(Boolean, default=False)
    is_checked_in = Column(Boolean, default=False)

    # Additional info
    skills = Column(ARRAY(String), default=[])
    experience_level = Column(String(50))
    bio = Column(Text)
    motivation = Column(Text)  # Why they want to participate

    # Metadata
    registered_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime)
    checked_in_at = Column(DateTime)

    # Relationships
    hackathon = relationship("Hackathon", back_populates="registrations")
    user = relationship("User", back_populates="hackathon_registrations")
    team = relationship("HackathonTeam")


class HackathonSubmission(Base):
    """Hackathon submission model"""
    __tablename__ = "hackathon_submissions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    hackathon_id = Column(PG_UUID(as_uuid=True), ForeignKey('hackathons.id', ondelete='CASCADE'), nullable=False)
    team_id = Column(PG_UUID(as_uuid=True), ForeignKey('hackathon_teams.id', ondelete='CASCADE'), nullable=False)

    # Submission details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    tagline = Column(String(500))

    # Links
    demo_url = Column(String(500))
    repository_url = Column(String(500))
    video_url = Column(String(500))
    presentation_url = Column(String(500))

    # Files
    attachments = Column(JSONB, default=[])  # [{"name": "...", "url": "...", "type": "..."}]

    # Technology
    tech_stack = Column(ARRAY(String), default=[])
    categories = Column(ARRAY(String), default=[])

    # Status
    status = Column(SQLEnum(SubmissionStatus), default=SubmissionStatus.DRAFT)

    # Judging
    scores = Column(JSONB, default=[])  # [{"judge_id": "...", "criteria": {...}, "total": 85}]
    total_score = Column(DECIMAL(5, 2), default=0)
    final_rank = Column(Integer)

    # Feedback
    feedback = Column(Text)
    judge_notes = Column(JSONB, default=[])

    # Metadata
    submitted_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    hackathon = relationship("Hackathon", back_populates="submissions")
    team = relationship("HackathonTeam", back_populates="submission")


class AptitudeTest(Base):
    """Aptitude test for pre-hackathon screening"""
    __tablename__ = "aptitude_tests"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    hackathon_id = Column(PG_UUID(as_uuid=True), ForeignKey('hackathons.id', ondelete='CASCADE'))

    # Test details
    title = Column(String(255), nullable=False)
    description = Column(Text)

    # Configuration
    duration_minutes = Column(Integer, default=60)
    passing_score = Column(Integer, default=70)
    total_questions = Column(Integer, default=20)

    # Questions
    questions = Column(JSONB, default=[])  # [{"question": "...", "options": [...], "correct": 0, "points": 5}]

    # Status
    is_active = Column(Boolean, default=True)
    is_required = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    results = relationship("TestResult", back_populates="test", cascade="all, delete-orphan")


class TestResult(Base):
    """Aptitude test result"""
    __tablename__ = "test_results"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    test_id = Column(PG_UUID(as_uuid=True), ForeignKey('aptitude_tests.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # Results
    score = Column(Integer, nullable=False)
    total_points = Column(Integer, nullable=False)
    percentage = Column(DECIMAL(5, 2))
    passed = Column(Boolean, default=False)

    # Answers
    answers = Column(JSONB, default=[])  # User's answers

    # Timing
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=False)
    time_taken_minutes = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    test = relationship("AptitudeTest", back_populates="results")
    user = relationship("User", back_populates="test_results")
