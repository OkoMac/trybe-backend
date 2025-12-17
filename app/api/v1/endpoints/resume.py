"""Resume API endpoints - Upload, parse, and manage resumes"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_active_user
from app.models.user import User
from app.services.resume_parser_service import resume_parser_service


router = APIRouter()


# Schemas

class ResumeParseRequest(BaseModel):
    """Schema for resume parse request"""
    use_ai: bool = Field(True, description="Use AI for enhanced parsing")


class ContactInfo(BaseModel):
    """Contact information schema"""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None


class WorkExperience(BaseModel):
    """Work experience schema"""
    title: Optional[str] = None
    company: Optional[str] = None
    period: Optional[str] = None
    description: List[str] = []


class Education(BaseModel):
    """Education schema"""
    degree: str
    institution: Optional[str] = None
    year: Optional[str] = None


class ResumeParseResponse(BaseModel):
    """Schema for parsed resume data"""
    contact_info: ContactInfo
    summary: Optional[str] = None
    skills: List[str] = []
    experience: List[WorkExperience] = []
    education: List[Education] = []
    certifications: List[str] = []
    languages: Optional[List[str]] = None
    total_years_experience: Optional[int] = None
    parsing_method: Optional[str] = "rule_based"
    parsed_at: str
    raw_text: Optional[str] = None


class ResumeUploadResponse(BaseModel):
    """Schema for resume upload response"""
    success: bool
    message: str
    resume_id: Optional[str] = None
    parsed_data: Optional[Dict[str, Any]] = None


# Endpoints

@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_and_parse_resume(
    file: UploadFile = File(..., description="Resume file (PDF or DOCX)"),
    use_ai: bool = Query(True, description="Use AI for enhanced parsing"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload and parse a resume

    Supports:
    - PDF files (.pdf)
    - Microsoft Word documents (.docx, .doc)

    Features:
    - Automatic text extraction
    - Contact information parsing
    - Skills identification
    - Work experience extraction
    - Education details parsing
    - Certification detection
    - AI-enhanced parsing (optional)

    **File size limit**: 10 MB

    Returns parsed structured data including:
    - Contact info (name, email, phone, LinkedIn, GitHub)
    - Professional summary
    - Skills list
    - Work experience with dates
    - Education history
    - Certifications
    - Total years of experience (AI-powered)
    """
    # Validate file type
    allowed_extensions = ['.pdf', '.docx', '.doc']
    file_extension = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )

    # Validate file size (10 MB limit)
    file_content = await file.read()
    if len(file_content) > 10 * 1024 * 1024:  # 10 MB
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds 10 MB limit"
        )

    try:
        # Parse resume
        parsed_data = await resume_parser_service.parse_resume(
            file_content=file_content,
            filename=file.filename,
            use_ai=use_ai
        )

        # Store parsed data in user metadata (simplified)
        if not current_user.user_metadata:
            current_user.user_metadata = {}

        # Update user metadata with resume data
        current_user.user_metadata["resume"] = {
            "filename": file.filename,
            "uploaded_at": datetime.utcnow().isoformat(),
            "contact_info": parsed_data.get("contact_info"),
            "skills": parsed_data.get("skills", []),
            "summary": parsed_data.get("summary"),
            "total_years_experience": parsed_data.get("total_years_experience")
        }

        # Update user skills if not already set
        if not current_user.user_metadata.get("skills"):
            current_user.user_metadata["skills"] = parsed_data.get("skills", [])

        await db.commit()

        # Don't return full raw text in response (too large)
        response_data = {**parsed_data}
        response_data.pop("raw_text", None)

        return ResumeUploadResponse(
            success=True,
            message="Resume parsed successfully",
            resume_id=str(current_user.id),
            parsed_data=response_data
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error parsing resume: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse resume. Please try again."
        )


@router.post("/parse", response_model=ResumeParseResponse)
async def parse_resume_text(
    file: UploadFile = File(...),
    use_ai: bool = Query(True),
    current_user: User = Depends(get_current_active_user)
):
    """
    Parse resume without saving

    Same as upload endpoint but doesn't save to user profile.
    Useful for testing or preview before saving.
    """
    # Validate file type
    allowed_extensions = ['.pdf', '.docx', '.doc']
    file_extension = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )

    file_content = await file.read()

    try:
        parsed_data = await resume_parser_service.parse_resume(
            file_content=file_content,
            filename=file.filename,
            use_ai=use_ai
        )

        # Remove raw text from response
        parsed_data.pop("raw_text", None)

        return ResumeParseResponse(**parsed_data)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/my-resume")
async def get_my_resume_data(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get stored resume data for current user

    Returns the last uploaded and parsed resume data
    from user's metadata.
    """
    if not current_user.user_metadata:
        return {
            "has_resume": False,
            "message": "No resume data found"
        }

    resume_data = current_user.user_metadata.get("resume")

    if not resume_data:
        return {
            "has_resume": False,
            "message": "No resume data found"
        }

    return {
        "has_resume": True,
        "resume_data": resume_data
    }


@router.delete("/my-resume", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_resume(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete stored resume data

    Removes resume data from user's metadata.
    Does not affect manually entered profile information.
    """
    if current_user.user_metadata and "resume" in current_user.user_metadata:
        del current_user.user_metadata["resume"]
        await db.commit()


@router.post("/extract-skills")
async def extract_skills_from_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """
    Extract only skills from resume

    Quick endpoint to extract skills list without full parsing.
    Useful for skill verification or profile enhancement.

    Returns:
    - Identified technical skills
    - Confidence scores (if AI-powered)
    - Skill categories
    """
    allowed_extensions = ['.pdf', '.docx', '.doc']
    file_extension = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type"
        )

    file_content = await file.read()

    try:
        parsed_data = await resume_parser_service.parse_resume(
            file_content=file_content,
            filename=file.filename,
            use_ai=False  # Use rule-based for faster extraction
        )

        skills = parsed_data.get("skills", [])

        # Categorize skills (simplified)
        categorized = {
            "programming_languages": [],
            "frameworks": [],
            "databases": [],
            "cloud_devops": [],
            "other": []
        }

        programming = ['python', 'javascript', 'java', 'c++', 'c#', 'ruby', 'php', 'go', 'rust']
        frameworks = ['react', 'angular', 'vue', 'django', 'flask', 'fastapi', 'spring', 'express']
        databases = ['sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch']
        cloud = ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'terraform']

        for skill in skills:
            skill_lower = skill.lower()
            if any(prog in skill_lower for prog in programming):
                categorized["programming_languages"].append(skill)
            elif any(fw in skill_lower for fw in frameworks):
                categorized["frameworks"].append(skill)
            elif any(db in skill_lower for db in databases):
                categorized["databases"].append(skill)
            elif any(cloud_kw in skill_lower for cloud_kw in cloud):
                categorized["cloud_devops"].append(skill)
            else:
                categorized["other"].append(skill)

        return {
            "total_skills": len(skills),
            "skills": skills,
            "categorized": categorized
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/compare-job")
async def compare_resume_with_job(
    file: UploadFile = File(...),
    job_description: str = Query(..., min_length=50, description="Job description text"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Compare resume with job description

    Analyzes how well the resume matches a job description.

    Returns:
    - Match percentage
    - Matching skills
    - Missing skills
    - Recommendations

    Requires AI to be configured for best results.
    """
    file_content = await file.read()

    try:
        # Parse resume
        parsed_data = await resume_parser_service.parse_resume(
            file_content=file_content,
            filename=file.filename,
            use_ai=True
        )

        resume_skills = set(s.lower() for s in parsed_data.get("skills", []))

        # Extract skills from job description (simplified)
        job_text = job_description.lower()
        job_skills_found = []

        skill_keywords = [
            'python', 'javascript', 'java', 'react', 'angular', 'vue',
            'sql', 'aws', 'docker', 'kubernetes', 'agile', 'scrum'
        ]

        for skill in skill_keywords:
            if skill in job_text:
                job_skills_found.append(skill)

        job_skills = set(job_skills_found)

        # Calculate match
        matching_skills = resume_skills & job_skills
        missing_skills = job_skills - resume_skills

        match_percentage = 0
        if job_skills:
            match_percentage = int((len(matching_skills) / len(job_skills)) * 100)

        return {
            "match_percentage": match_percentage,
            "matching_skills": list(matching_skills),
            "missing_skills": list(missing_skills),
            "resume_skills_count": len(resume_skills),
            "job_skills_count": len(job_skills),
            "recommendations": [
                f"Add {skill} to your resume" for skill in list(missing_skills)[:5]
            ] if missing_skills else ["Your resume matches well with this job!"]
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/supported-formats")
async def get_supported_formats():
    """
    Get list of supported resume formats

    Returns information about supported file types,
    size limits, and features.
    """
    return {
        "supported_formats": [
            {
                "format": "PDF",
                "extension": ".pdf",
                "max_size_mb": 10,
                "features": ["Text extraction", "Multi-page support"]
            },
            {
                "format": "Microsoft Word",
                "extensions": [".docx", ".doc"],
                "max_size_mb": 10,
                "features": ["Text extraction", "Formatting preserved"]
            }
        ],
        "parsing_features": {
            "contact_information": "Email, phone, LinkedIn, GitHub",
            "work_experience": "Job titles, companies, dates, descriptions",
            "education": "Degrees, institutions, years",
            "skills": "Technical and soft skills",
            "certifications": "Professional certifications",
            "ai_enhancement": "Optional AI-powered parsing for better accuracy"
        },
        "tips": [
            "Use standard section headers (Experience, Education, Skills)",
            "Include dates in clear formats (Jan 2020 - Dec 2023)",
            "List skills in a dedicated Skills section",
            "Keep formatting simple for best parsing results",
            "PDF format recommended for best compatibility"
        ]
    }


import logging
logger = logging.getLogger(__name__)
