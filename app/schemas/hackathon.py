"""Hackathon Schemas"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal

from app.models.hackathon import HackathonStatus, DifficultyLevel, SubmissionStatus


# Prize schema
class Prize(BaseModel):
    """Prize information"""
    place: int
    amount: Decimal
    description: str
    currency: str = "USD"


# Judging criteria schema
class JudgingCriteria(BaseModel):
    """Judging criteria"""
    name: str
    description: str
    weight: int  # Percentage weight (e.g., 30 for 30%)


# Hackathon Schemas
class HackathonBase(BaseModel):
    """Base hackathon schema"""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)
    registration_start: datetime
    registration_end: datetime
    start_date: datetime
    end_date: datetime
    max_participants: Optional[int] = None
    max_team_size: int = 5
    min_team_size: int = 1
    is_team_required: bool = False
    difficulty_level: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    required_skills: List[str] = []
    categories: List[str] = []
    banner_url: Optional[str] = None
    logo_url: Optional[str] = None
    rules: Optional[str] = None
    submission_guidelines: Optional[str] = None
    is_public: bool = True


class HackathonCreate(HackathonBase):
    """Create hackathon schema"""
    prizes: List[Prize] = []
    judging_criteria: List[JudgingCriteria] = []


class HackathonUpdate(BaseModel):
    """Update hackathon schema"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)
    status: Optional[HackathonStatus] = None
    registration_start: Optional[datetime] = None
    registration_end: Optional[datetime] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    max_participants: Optional[int] = None
    max_team_size: Optional[int] = None
    min_team_size: Optional[int] = None
    is_team_required: Optional[bool] = None
    difficulty_level: Optional[DifficultyLevel] = None
    required_skills: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    prizes: Optional[List[Prize]] = None
    judging_criteria: Optional[List[JudgingCriteria]] = None
    banner_url: Optional[str] = None
    logo_url: Optional[str] = None
    rules: Optional[str] = None
    submission_guidelines: Optional[str] = None
    is_public: Optional[bool] = None
    is_featured: Optional[bool] = None


class HackathonResponse(HackathonBase):
    """Hackathon response schema"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organizer_id: UUID
    status: HackathonStatus
    prizes: List[dict] = []
    total_prize_pool: Optional[Decimal] = None
    judging_criteria: List[dict] = []
    is_featured: bool
    view_count: int
    participant_count: int
    created_at: datetime
    updated_at: datetime


# Team Schemas
class TeamBase(BaseModel):
    """Base team schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    logo_url: Optional[str] = None
    is_public: bool = True


class TeamCreate(TeamBase):
    """Create team schema"""
    hackathon_id: UUID
    max_members: int = 5


class TeamUpdate(BaseModel):
    """Update team schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    logo_url: Optional[str] = None
    is_public: Optional[bool] = None
    max_members: Optional[int] = None


class TeamMemberInfo(BaseModel):
    """Team member information"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    username: str
    avatar_url: Optional[str] = None


class TeamResponse(TeamBase):
    """Team response schema"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hackathon_id: UUID
    team_leader_id: UUID
    max_members: int
    member_count: int = 0
    created_at: datetime
    updated_at: datetime


class TeamDetailResponse(TeamResponse):
    """Detailed team response with members"""
    members: List[TeamMemberInfo] = []


# Registration Schemas
class RegistrationCreate(BaseModel):
    """Create registration schema"""
    hackathon_id: UUID
    team_id: Optional[UUID] = None
    skills: List[str] = []
    experience_level: Optional[str] = None
    bio: Optional[str] = None
    motivation: Optional[str] = None


class RegistrationUpdate(BaseModel):
    """Update registration schema"""
    team_id: Optional[UUID] = None
    skills: Optional[List[str]] = None
    experience_level: Optional[str] = None
    bio: Optional[str] = None
    motivation: Optional[str] = None


class RegistrationResponse(BaseModel):
    """Registration response schema"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hackathon_id: UUID
    user_id: UUID
    team_id: Optional[UUID] = None
    is_confirmed: bool
    is_checked_in: bool
    skills: List[str]
    experience_level: Optional[str] = None
    bio: Optional[str] = None
    motivation: Optional[str] = None
    registered_at: datetime
    confirmed_at: Optional[datetime] = None
    checked_in_at: Optional[datetime] = None


# Submission Schemas
class SubmissionBase(BaseModel):
    """Base submission schema"""
    title: str = Field(..., min_length=1, max_length=255)
    description: str
    tagline: Optional[str] = Field(None, max_length=500)
    demo_url: Optional[str] = None
    repository_url: Optional[str] = None
    video_url: Optional[str] = None
    presentation_url: Optional[str] = None
    tech_stack: List[str] = []
    categories: List[str] = []


class SubmissionCreate(SubmissionBase):
    """Create submission schema"""
    hackathon_id: UUID
    team_id: UUID


class SubmissionUpdate(BaseModel):
    """Update submission schema"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    tagline: Optional[str] = Field(None, max_length=500)
    demo_url: Optional[str] = None
    repository_url: Optional[str] = None
    video_url: Optional[str] = None
    presentation_url: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    status: Optional[SubmissionStatus] = None


class SubmissionResponse(SubmissionBase):
    """Submission response schema"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hackathon_id: UUID
    team_id: UUID
    status: SubmissionStatus
    attachments: List[dict] = []
    total_score: Decimal
    final_rank: Optional[int] = None
    submitted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# Score schema
class SubmissionScore(BaseModel):
    """Submission scoring schema"""
    submission_id: UUID
    criteria_scores: dict  # {"Innovation": 25, "Implementation": 20, ...}
    feedback: Optional[str] = None


# Aptitude Test Schemas
class TestQuestion(BaseModel):
    """Test question schema"""
    question: str
    options: List[str]
    correct: int  # Index of correct answer
    points: int = 5


class AptitudeTestCreate(BaseModel):
    """Create aptitude test schema"""
    hackathon_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    duration_minutes: int = 60
    passing_score: int = 70
    questions: List[TestQuestion]
    is_required: bool = False


class AptitudeTestResponse(BaseModel):
    """Aptitude test response schema"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hackathon_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    duration_minutes: int
    passing_score: int
    total_questions: int
    is_active: bool
    is_required: bool
    created_at: datetime


class TestAnswer(BaseModel):
    """Test answer schema"""
    question_index: int
    selected_option: int


class TestSubmission(BaseModel):
    """Test submission schema"""
    test_id: UUID
    answers: List[TestAnswer]


class TestResultResponse(BaseModel):
    """Test result response schema"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    test_id: UUID
    user_id: UUID
    score: int
    total_points: int
    percentage: Decimal
    passed: bool
    time_taken_minutes: int
    completed_at: datetime


# Statistics
class HackathonStats(BaseModel):
    """Hackathon statistics"""
    total_participants: int
    total_teams: int
    total_submissions: int
    submissions_by_status: dict
    average_team_size: float
    top_skills: List[dict]  # [{"skill": "Python", "count": 25}]


# Leaderboard
class LeaderboardEntry(BaseModel):
    """Leaderboard entry"""
    rank: int
    team_id: UUID
    team_name: str
    submission_title: str
    total_score: Decimal
    team_members: List[str]
