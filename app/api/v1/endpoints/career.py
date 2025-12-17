"""AI Career Assistant API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_active_user
from app.models.user import User
from app.services.career_assistant_service import career_assistant_service


router = APIRouter()


# Schemas

class ResumeAnalysisRequest(BaseModel):
    """Schema for resume analysis request"""
    resume_text: str = Field(..., min_length=100, max_length=50000, description="Full text of the resume")
    target_role: Optional[str] = Field(None, max_length=200, description="Target job role for tailored feedback")


class ResumeAnalysisResponse(BaseModel):
    """Schema for resume analysis response"""
    overall_score: int = Field(..., ge=0, le=100)
    strengths: List[str]
    weaknesses: List[str]
    technical_skills: List[str]
    soft_skills: List[str]
    experience_level: str
    recommendations: List[Dict[str, str]]
    ats_score: int = Field(..., ge=0, le=100)
    ats_tips: List[str]
    missing_sections: List[str]
    summary: str
    analyzed_at: str


class OpportunityRecommendationRequest(BaseModel):
    """Schema for opportunity recommendation request"""
    user_skills: List[str] = Field(..., min_items=1, description="User's skills")
    experience_level: str = Field(..., description="Experience level (entry, junior, mid, senior, lead)")
    preferences: Optional[Dict[str, Any]] = Field(None, description="Additional preferences")


class OpportunityRecommendation(BaseModel):
    """Schema for a single opportunity recommendation"""
    opportunity_id: str
    title: str
    company: Optional[str]
    match_score: float
    match_reason: str
    estimated_salary: Optional[float]
    location: Optional[Dict[str, Any]]
    opportunity_type: str
    required_skills: Optional[List[str]]
    missing_skills: List[str]


class SkillGapAnalysisRequest(BaseModel):
    """Schema for skill gap analysis request"""
    user_skills: List[str] = Field(..., min_items=1)
    target_role: str = Field(..., min_length=3, max_length=200)


class SkillGap(BaseModel):
    """Schema for a skill gap"""
    skill: str
    priority: str
    estimated_learning_time_weeks: int


class SkillGapAnalysisResponse(BaseModel):
    """Schema for skill gap analysis response"""
    target_role: str
    essential_skills: List[str]
    user_has: List[str]
    critical_gaps: List[SkillGap]
    nice_to_have: List[str]
    overall_readiness_percentage: int = Field(..., ge=0, le=100)
    learning_path: List[Dict[str, Any]]
    estimated_total_weeks: int
    recommended_courses: List[Dict[str, Any]]


class CareerRoadmapRequest(BaseModel):
    """Schema for career roadmap generation request"""
    current_role: str = Field(..., min_length=3, max_length=200)
    target_role: str = Field(..., min_length=3, max_length=200)
    user_skills: List[str] = Field(..., min_items=1)
    timeline_months: int = Field(12, ge=3, le=60, description="Timeline in months")


class QuarterMilestone(BaseModel):
    """Schema for quarterly milestone"""
    quarter: int
    focus: str
    skills_to_develop: List[str]
    projects: List[str]
    certifications: List[str]
    networking: List[str]
    success_metrics: List[str]


class CareerChallenge(BaseModel):
    """Schema for career challenge"""
    challenge: str
    solution: str


class CareerRoadmapResponse(BaseModel):
    """Schema for career roadmap response"""
    summary: str
    is_realistic: bool
    difficulty_level: str
    quarters: List[QuarterMilestone]
    key_challenges: List[CareerChallenge]
    success_probability: int = Field(..., ge=0, le=100)
    alternative_paths: List[str]


class ChatMessage(BaseModel):
    """Schema for chat message"""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class CareerChatRequest(BaseModel):
    """Schema for career chat request"""
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_history: Optional[List[ChatMessage]] = Field(None, max_items=20)
    include_user_context: bool = Field(True, description="Include user profile in context")


class CareerChatResponse(BaseModel):
    """Schema for career chat response"""
    message: str
    timestamp: str
    suggestions: List[str]


# Endpoints

@router.post("/analyze-resume", response_model=ResumeAnalysisResponse)
async def analyze_resume(
    request: ResumeAnalysisRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Analyze a resume and get detailed feedback

    Provides:
    - Overall score and assessment
    - Identified skills (technical and soft)
    - Experience level assessment
    - Specific improvement recommendations
    - ATS (Applicant Tracking System) optimization tips
    - Missing sections or information

    The AI analyzes resume structure, content, formatting, and keyword optimization.

    **Note:** This feature requires OpenAI or Anthropic API to be configured.
    """
    result = await career_assistant_service.analyze_resume(
        resume_text=request.resume_text,
        target_role=request.target_role
    )

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result["error"]
        )

    return ResumeAnalysisResponse(**result)


@router.post("/recommend-opportunities", response_model=List[OpportunityRecommendation])
async def recommend_opportunities(
    request: OpportunityRecommendationRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get AI-powered opportunity recommendations

    Analyzes user skills and preferences to recommend the best-matching opportunities
    from the platform.

    Factors considered:
    - Skills match percentage
    - Experience level fit
    - Location/remote preferences
    - Salary requirements
    - Industry preferences

    Each recommendation includes:
    - Match score (0-100)
    - Detailed reasoning
    - Missing skills that would improve the match
    - Estimated salary and other opportunity details
    """
    recommendations = await career_assistant_service.recommend_opportunities(
        db=db,
        user_skills=request.user_skills,
        experience_level=request.experience_level,
        preferences=request.preferences,
        limit=20
    )

    return [OpportunityRecommendation(**rec) for rec in recommendations]


@router.post("/skill-gap-analysis", response_model=SkillGapAnalysisResponse)
async def analyze_skill_gaps(
    request: SkillGapAnalysisRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze skill gaps for a target role

    Provides comprehensive analysis of:
    - Essential skills required for the target role
    - Skills you already have that are relevant
    - Critical skills you're missing (prioritized by importance)
    - Nice-to-have skills that would be beneficial
    - Estimated time to acquire missing skills
    - Personalized learning path with specific courses and resources

    The AI considers industry standards and current job market requirements
    to provide accurate skill gap analysis.

    **Note:** This feature requires OpenAI or Anthropic API to be configured.
    """
    result = await career_assistant_service.analyze_skill_gaps(
        user_skills=request.user_skills,
        target_role=request.target_role,
        db=db
    )

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result["error"]
        )

    return SkillGapAnalysisResponse(**result)


@router.post("/career-roadmap", response_model=CareerRoadmapResponse)
async def generate_career_roadmap(
    request: CareerRoadmapRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate a detailed career roadmap

    Creates a comprehensive, actionable plan for career transition with:
    - Quarterly milestones and objectives
    - Skills to develop each quarter
    - Specific projects to complete
    - Networking and community activities
    - Certifications to pursue
    - Expected challenges and solutions
    - Success probability assessment
    - Alternative career paths

    The roadmap is personalized based on your:
    - Current role and experience
    - Target role aspirations
    - Existing skills
    - Desired timeline

    **Timeline:** Can be customized from 3 to 60 months.

    **Note:** This feature requires OpenAI or Anthropic API to be configured.
    """
    result = await career_assistant_service.generate_career_roadmap(
        current_role=request.current_role,
        target_role=request.target_role,
        user_skills=request.user_skills,
        timeline_months=request.timeline_months
    )

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result["error"]
        )

    return CareerRoadmapResponse(**result)


@router.post("/chat", response_model=CareerChatResponse)
async def chat_with_career_assistant(
    request: CareerChatRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Chat with AI career assistant

    Have a natural conversation with an AI career counselor that can help with:
    - Career planning and goal setting
    - Resume and interview preparation
    - Skill development strategies
    - Job search tactics
    - Work-life balance and career satisfaction
    - Salary negotiation advice
    - Career transitions and pivots

    The assistant maintains conversation context and can reference your
    profile (skills, experience, goals) to provide personalized advice.

    **Features:**
    - Natural language understanding
    - Context-aware responses
    - Actionable suggestions extracted from responses
    - Supportive and encouraging tone

    **Conversation History:** Include up to 20 previous messages for context.

    **Note:** This feature requires OpenAI or Anthropic API to be configured.
    """
    # Build user context
    user_context = None
    if request.include_user_context:
        # Get user skills from metadata (simplified)
        user_skills = current_user.user_metadata.get("skills", []) if current_user.user_metadata else []
        experience_level = current_user.user_metadata.get("experience_level", "unknown") if current_user.user_metadata else "unknown"
        career_goal = current_user.user_metadata.get("career_goal") if current_user.user_metadata else None

        user_context = {
            "skills": user_skills,
            "experience_level": experience_level,
            "career_goal": career_goal
        }

    # Convert conversation history
    conversation_history = None
    if request.conversation_history:
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.conversation_history
        ]

    result = await career_assistant_service.chat_with_assistant(
        user_message=request.message,
        conversation_history=conversation_history,
        user_context=user_context
    )

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result["error"]
        )

    return CareerChatResponse(**result)


@router.get("/quick-tips")
async def get_career_quick_tips(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get quick career tips and insights

    Returns bite-sized career advice, tips, and best practices.

    Categories:
    - Resume writing
    - Interview preparation
    - Networking
    - Skill development
    - Job search strategies
    """
    tips = {
        "resume": [
            "Use action verbs to start bullet points (e.g., 'Led', 'Developed', 'Achieved')",
            "Quantify achievements with numbers and metrics whenever possible",
            "Tailor your resume for each application, highlighting relevant skills",
            "Keep your resume to 1-2 pages maximum",
            "Use keywords from the job description to pass ATS screening"
        ],
        "interview": [
            "Research the company thoroughly before the interview",
            "Prepare STAR (Situation, Task, Action, Result) stories for common questions",
            "Prepare thoughtful questions to ask the interviewer",
            "Practice your answers out loud, not just in your head",
            "Follow up with a thank-you email within 24 hours"
        ],
        "networking": [
            "Connect with people on LinkedIn with personalized messages",
            "Attend industry events and conferences regularly",
            "Offer value first before asking for favors",
            "Follow up with new connections within a week",
            "Join relevant professional communities and contribute actively"
        ],
        "skill_development": [
            "Focus on learning skills that are in high demand in your industry",
            "Build a portfolio of projects showcasing your skills",
            "Dedicate at least 5 hours per week to learning",
            "Learn by doing - theory alone isn't enough",
            "Share your learning journey publicly to build credibility"
        ],
        "job_search": [
            "Apply to jobs even if you don't meet 100% of requirements",
            "Use your network to get referrals - they dramatically increase success rates",
            "Follow up on applications after 1-2 weeks",
            "Keep a spreadsheet tracking all applications and follow-ups",
            "Don't put all your eggs in one basket - apply to multiple opportunities"
        ]
    }

    return {
        "tips": tips,
        "tip_of_the_day": "The best time to start building your professional network is before you need it. Start connecting and building relationships today."
    }


@router.get("/salary-insights")
async def get_salary_insights(
    role: str,
    location: Optional[str] = None,
    experience_level: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get salary insights for a specific role

    Provides indicative salary ranges based on:
    - Job role/title
    - Location
    - Experience level

    **Note:** This is a simplified implementation. In production, integrate with
    salary data APIs like Glassdoor, PayScale, or local job market data.
    """
    # Simplified salary data (in production, use real data sources)
    base_salaries = {
        "software engineer": {"entry": 60000, "junior": 75000, "mid": 95000, "senior": 130000, "lead": 160000},
        "data scientist": {"entry": 70000, "junior": 85000, "mid": 110000, "senior": 145000, "lead": 180000},
        "product manager": {"entry": 65000, "junior": 80000, "mid": 105000, "senior": 140000, "lead": 175000},
        "designer": {"entry": 50000, "junior": 65000, "mid": 85000, "senior": 115000, "lead": 145000},
        "marketing manager": {"entry": 55000, "junior": 70000, "mid": 90000, "senior": 120000, "lead": 150000},
        "default": {"entry": 50000, "junior": 65000, "mid": 85000, "senior": 115000, "lead": 145000}
    }

    # Get salary data
    role_lower = role.lower()
    salary_data = base_salaries.get(role_lower, base_salaries["default"])

    # Adjust for experience level
    exp_level = experience_level.lower() if experience_level else "mid"
    base_salary = salary_data.get(exp_level, salary_data["mid"])

    # Location adjustment (simplified)
    location_multiplier = 1.0
    if location:
        location_lower = location.lower()
        if any(city in location_lower for city in ["san francisco", "new york", "seattle", "boston"]):
            location_multiplier = 1.4
        elif any(city in location_lower for city in ["austin", "denver", "chicago", "los angeles"]):
            location_multiplier = 1.2
        elif any(city in location_lower for city in ["nairobi", "lagos", "accra", "cape town"]):
            location_multiplier = 0.4

    adjusted_salary = base_salary * location_multiplier

    return {
        "role": role,
        "location": location or "General",
        "experience_level": exp_level,
        "currency": "USD",
        "salary_range": {
            "min": int(adjusted_salary * 0.85),
            "median": int(adjusted_salary),
            "max": int(adjusted_salary * 1.25)
        },
        "percentiles": {
            "25th": int(adjusted_salary * 0.9),
            "50th": int(adjusted_salary),
            "75th": int(adjusted_salary * 1.15)
        },
        "market_trend": "stable",
        "note": "Salary data is indicative and based on market averages. Actual salaries may vary based on company size, industry, and individual qualifications."
    }
