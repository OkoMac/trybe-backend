"""Email API endpoints for sending various types of emails"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.api.deps import get_current_user, get_current_active_user
from app.models.user import User
from app.services.enhanced_email_service import enhanced_email_service


router = APIRouter()


# Schemas

class OpportunityMatchEmailRequest(BaseModel):
    """Schema for opportunity match email"""
    user_email: EmailStr
    user_name: str
    opportunity_title: str
    company_name: str
    match_percentage: int = Field(..., ge=0, le=100)
    opportunity_type: str
    budget: Optional[float] = None
    location: str
    opportunity_url: str
    required_skills: List[str] = []


class ApplicationStatusEmailRequest(BaseModel):
    """Schema for application status email"""
    user_email: EmailStr
    user_name: str
    opportunity_title: str
    status: str = Field(..., pattern="^(accepted|rejected|interview|shortlisted)$")
    message: Optional[str] = None
    opportunity_url: str


class PaymentReceiptEmailRequest(BaseModel):
    """Schema for payment receipt email"""
    user_email: EmailStr
    user_name: str
    transaction_id: str
    amount: float = Field(..., gt=0)
    payment_method: str
    description: str
    from_user: Optional[str] = None
    to_user: Optional[str] = None


class WeeklyDigestEmailRequest(BaseModel):
    """Schema for weekly digest email"""
    user_email: EmailStr
    user_name: str
    stats: Dict[str, int]
    new_opportunities: List[Dict[str, Any]] = []
    achievements: List[str] = []


class MarketingCampaignEmailRequest(BaseModel):
    """Schema for marketing campaign email"""
    user_email: EmailStr
    user_name: str
    campaign_title: str
    campaign_message: str
    cta_text: str
    cta_url: str
    image_url: Optional[str] = None


class CourseEnrollmentEmailRequest(BaseModel):
    """Schema for course enrollment email"""
    user_email: EmailStr
    user_name: str
    course_title: str
    instructor_name: str
    duration_hours: int = Field(..., gt=0)
    course_url: str


class SkillTestResultEmailRequest(BaseModel):
    """Schema for skill test result email"""
    user_email: EmailStr
    user_name: str
    test_name: str
    score: int = Field(..., ge=0, le=100)
    passed: bool
    certificate_url: Optional[str] = None


class ProfileReminderEmailRequest(BaseModel):
    """Schema for profile completion reminder"""
    user_email: EmailStr
    user_name: str
    completion_percentage: int = Field(..., ge=0, le=100)
    missing_items: List[str]


class BatchEmailRequest(BaseModel):
    """Schema for batch email sending"""
    recipients: List[Dict[str, Any]]


# Endpoints

@router.post("/send/opportunity-match")
async def send_opportunity_match_email(
    request: OpportunityMatchEmailRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    """
    Send opportunity match notification email

    Sends a professionally designed email notifying a user about a new opportunity match.
    Includes match percentage, opportunity details, and required skills.

    **Note:** Email is sent in the background for better performance.
    """
    background_tasks.add_task(
        enhanced_email_service.send_opportunity_match,
        user_email=request.user_email,
        user_name=request.user_name,
        opportunity_title=request.opportunity_title,
        company_name=request.company_name,
        match_percentage=request.match_percentage,
        opportunity_type=request.opportunity_type,
        budget=request.budget,
        location=request.location,
        opportunity_url=request.opportunity_url,
        required_skills=request.required_skills
    )

    return {
        "success": True,
        "message": "Opportunity match email queued for sending"
    }


@router.post("/send/application-status")
async def send_application_status_email(
    request: ApplicationStatusEmailRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    """
    Send application status update email

    Notifies users about their application status (accepted, rejected, interview, shortlisted).
    Uses appropriate styling and messaging for each status type.
    """
    background_tasks.add_task(
        enhanced_email_service.send_application_status_update,
        user_email=request.user_email,
        user_name=request.user_name,
        opportunity_title=request.opportunity_title,
        status=request.status,
        message=request.message,
        opportunity_url=request.opportunity_url
    )

    return {
        "success": True,
        "message": "Application status email queued for sending"
    }


@router.post("/send/payment-receipt")
async def send_payment_receipt_email(
    request: PaymentReceiptEmailRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    """
    Send payment receipt email

    Sends a detailed payment receipt with transaction information.
    Includes transaction ID, amount, payment method, and description.
    """
    background_tasks.add_task(
        enhanced_email_service.send_payment_receipt,
        user_email=request.user_email,
        user_name=request.user_name,
        transaction_id=request.transaction_id,
        amount=request.amount,
        payment_method=request.payment_method,
        description=request.description,
        from_user=request.from_user,
        to_user=request.to_user
    )

    return {
        "success": True,
        "message": "Payment receipt email queued for sending"
    }


@router.post("/send/weekly-digest")
async def send_weekly_digest_email(
    request: WeeklyDigestEmailRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    """
    Send weekly digest email

    Sends a comprehensive weekly summary including:
    - Profile views and matches
    - New opportunities
    - User achievements
    - Activity statistics

    Great for keeping users engaged!
    """
    background_tasks.add_task(
        enhanced_email_service.send_weekly_digest,
        user_email=request.user_email,
        user_name=request.user_name,
        stats=request.stats,
        new_opportunities=request.new_opportunities,
        achievements=request.achievements
    )

    return {
        "success": True,
        "message": "Weekly digest email queued for sending"
    }


@router.post("/send/marketing-campaign")
async def send_marketing_campaign_email(
    request: MarketingCampaignEmailRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    """
    Send marketing campaign email

    Sends a custom marketing email with:
    - Campaign title and message
    - Call-to-action button
    - Optional hero image

    **Permissions:** Only admins can send marketing emails.
    """
    # TODO: Add admin permission check

    background_tasks.add_task(
        enhanced_email_service.send_marketing_campaign,
        user_email=request.user_email,
        user_name=request.user_name,
        campaign_title=request.campaign_title,
        campaign_message=request.campaign_message,
        cta_text=request.cta_text,
        cta_url=request.cta_url,
        image_url=request.image_url
    )

    return {
        "success": True,
        "message": "Marketing campaign email queued for sending"
    }


@router.post("/send/course-enrollment")
async def send_course_enrollment_email(
    request: CourseEnrollmentEmailRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    """
    Send course enrollment confirmation email

    Confirms course enrollment and provides:
    - Course details
    - Instructor information
    - Duration and learning tips
    - Direct link to start learning
    """
    background_tasks.add_task(
        enhanced_email_service.send_course_enrollment_confirmation,
        user_email=request.user_email,
        user_name=request.user_name,
        course_title=request.course_title,
        instructor_name=request.instructor_name,
        duration_hours=request.duration_hours,
        course_url=request.course_url
    )

    return {
        "success": True,
        "message": "Course enrollment email queued for sending"
    }


@router.post("/send/test-result")
async def send_test_result_email(
    request: SkillTestResultEmailRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    """
    Send skill test result email

    Sends test results with:
    - Score and pass/fail status
    - Certificate download link (if passed)
    - Encouragement and next steps
    """
    background_tasks.add_task(
        enhanced_email_service.send_skill_test_result,
        user_email=request.user_email,
        user_name=request.user_name,
        test_name=request.test_name,
        score=request.score,
        passed=request.passed,
        certificate_url=request.certificate_url
    )

    return {
        "success": True,
        "message": "Test result email queued for sending"
    }


@router.post("/send/profile-reminder")
async def send_profile_reminder_email(
    request: ProfileReminderEmailRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    """
    Send profile completion reminder

    Encourages users to complete their profile with:
    - Current completion percentage
    - List of missing items
    - Benefits of completing profile
    - Direct link to edit profile
    """
    background_tasks.add_task(
        enhanced_email_service.send_profile_completion_reminder,
        user_email=request.user_email,
        user_name=request.user_name,
        completion_percentage=request.completion_percentage,
        missing_items=request.missing_items
    )

    return {
        "success": True,
        "message": "Profile reminder email queued for sending"
    }


# Batch email endpoints

@router.post("/batch/opportunity-matches")
async def send_batch_opportunity_matches(
    request: BatchEmailRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    """
    Send opportunity match emails to multiple users

    Efficiently sends opportunity notifications to a batch of users.
    Each recipient gets a personalized email based on their match data.

    **Request format:**
    ```json
    {
        "recipients": [
            {
                "user_email": "user@example.com",
                "user_name": "John Doe",
                "opportunity_title": "Senior Developer",
                "company_name": "Tech Corp",
                "match_percentage": 85,
                ...
            }
        ]
    }
    ```
    """
    background_tasks.add_task(
        enhanced_email_service.send_batch_opportunity_matches,
        matches=request.recipients
    )

    return {
        "success": True,
        "message": f"Batch opportunity match emails queued for {len(request.recipients)} recipients"
    }


@router.post("/batch/weekly-digests")
async def send_batch_weekly_digests(
    request: BatchEmailRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    """
    Send weekly digest emails to multiple users

    Sends personalized weekly digests to all active users.
    Each digest includes user-specific stats and opportunities.

    **Permissions:** Only admins can trigger batch digest sending.
    """
    # TODO: Add admin permission check

    background_tasks.add_task(
        enhanced_email_service.send_batch_weekly_digests,
        digests=request.recipients
    )

    return {
        "success": True,
        "message": f"Batch weekly digest emails queued for {len(request.recipients)} recipients"
    }


@router.get("/templates")
async def list_email_templates(
    current_user: User = Depends(get_current_active_user)
):
    """
    List available email templates

    Returns information about all available email templates
    including their purpose and required fields.
    """
    templates = {
        "opportunity_match": {
            "name": "Opportunity Match",
            "description": "Notifies user about a new opportunity match",
            "required_fields": ["user_email", "user_name", "opportunity_title", "company_name", "match_percentage", "opportunity_type", "location", "opportunity_url"]
        },
        "application_status": {
            "name": "Application Status Update",
            "description": "Informs user about application status change",
            "required_fields": ["user_email", "user_name", "opportunity_title", "status", "opportunity_url"],
            "status_options": ["accepted", "rejected", "interview", "shortlisted"]
        },
        "payment_receipt": {
            "name": "Payment Receipt",
            "description": "Sends payment receipt with transaction details",
            "required_fields": ["user_email", "user_name", "transaction_id", "amount", "payment_method", "description"]
        },
        "weekly_digest": {
            "name": "Weekly Digest",
            "description": "Weekly summary of user activity and new opportunities",
            "required_fields": ["user_email", "user_name", "stats", "new_opportunities", "achievements"]
        },
        "marketing_campaign": {
            "name": "Marketing Campaign",
            "description": "Custom marketing email with CTA",
            "required_fields": ["user_email", "user_name", "campaign_title", "campaign_message", "cta_text", "cta_url"]
        },
        "course_enrollment": {
            "name": "Course Enrollment",
            "description": "Confirms course enrollment",
            "required_fields": ["user_email", "user_name", "course_title", "instructor_name", "duration_hours", "course_url"]
        },
        "test_result": {
            "name": "Test Result",
            "description": "Sends skill test results",
            "required_fields": ["user_email", "user_name", "test_name", "score", "passed"]
        },
        "profile_reminder": {
            "name": "Profile Completion Reminder",
            "description": "Reminds user to complete their profile",
            "required_fields": ["user_email", "user_name", "completion_percentage", "missing_items"]
        }
    }

    return {
        "total_templates": len(templates),
        "templates": templates
    }
