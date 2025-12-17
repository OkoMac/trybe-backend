"""Enhanced Email Service with Professional Templates"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from app.core.config import settings
from app.services.email_templates import EmailTemplates

logger = logging.getLogger(__name__)


class EnhancedEmailService:
    """
    Enhanced email service with professional HTML templates

    Supports:
    - Opportunity match notifications
    - Application status updates
    - Payment receipts
    - Weekly digests
    - Marketing campaigns
    - Course enrollment
    - Profile completion reminders
    - Test results
    """

    def __init__(self):
        self.provider = getattr(settings, 'EMAIL_PROVIDER', 'smtp')
        self.from_email = getattr(settings, 'EMAIL_FROM', 'noreply@trybe.app')
        self.from_name = getattr(settings, 'EMAIL_FROM_NAME', 'Trybe Team')

        # SMTP settings
        self.smtp_host = getattr(settings, 'SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = getattr(settings, 'SMTP_PORT', 587)
        self.smtp_user = getattr(settings, 'SMTP_USER', '')
        self.smtp_password = getattr(settings, 'SMTP_PASSWORD', '')

        # SendGrid settings
        self.sendgrid_api_key = getattr(settings, 'SENDGRID_API_KEY', '')

    async def send_email(
        self,
        to: str | List[str],
        subject: str,
        html_body: str,
        plain_text: Optional[str] = None
    ) -> bool:
        """Send email with HTML template"""
        try:
            if self.provider == 'sendgrid':
                return await self._send_via_sendgrid(to, subject, plain_text or "Please view this email in HTML", html_body)
            else:
                return await self._send_via_smtp(to, subject, plain_text or "Please view this email in HTML", html_body)
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    async def _send_via_smtp(
        self,
        to: str | List[str],
        subject: str,
        body: str,
        html_body: str
    ) -> bool:
        """Send email via SMTP"""
        try:
            message = MIMEMultipart('alternative')
            message['From'] = f"{self.from_name} <{self.from_email}>"
            message['To'] = to if isinstance(to, str) else ', '.join(to)
            message['Subject'] = subject

            message.attach(MIMEText(body, 'plain'))
            message.attach(MIMEText(html_body, 'html'))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)

                recipients = [to] if isinstance(to, str) else to
                server.send_message(message, to_addrs=recipients)

            logger.info(f"Email sent successfully to {to}")
            return True

        except Exception as e:
            logger.error(f"SMTP error: {e}")
            return False

    async def _send_via_sendgrid(
        self,
        to: str | List[str],
        subject: str,
        body: str,
        html_body: str
    ) -> bool:
        """Send email via SendGrid"""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To, Content

            from_email = Email(self.from_email, self.from_name)
            to_emails = To(to) if isinstance(to, str) else [To(email) for email in to]
            content = Content("text/html", html_body)

            mail = Mail(from_email, to_emails, subject, content)

            sg = SendGridAPIClient(self.sendgrid_api_key)
            response = sg.send(mail)

            logger.info(f"SendGrid email sent: {response.status_code}")
            return response.status_code in [200, 201, 202]

        except ImportError:
            logger.error("SendGrid library not installed")
            return False
        except Exception as e:
            logger.error(f"SendGrid error: {e}")
            return False

    # Opportunity-related emails

    async def send_opportunity_match(
        self,
        user_email: str,
        user_name: str,
        opportunity_title: str,
        company_name: str,
        match_percentage: int,
        opportunity_type: str,
        budget: Optional[float],
        location: str,
        opportunity_url: str,
        required_skills: List[str]
    ) -> bool:
        """Send opportunity match notification"""
        html_body = EmailTemplates.opportunity_match(
            user_name=user_name,
            opportunity_title=opportunity_title,
            company_name=company_name,
            match_percentage=match_percentage,
            opportunity_type=opportunity_type,
            budget=budget,
            location=location,
            opportunity_url=opportunity_url,
            required_skills=required_skills,
            recipient_email=user_email
        )

        subject = f"🎯 New Match: {opportunity_title} ({match_percentage}% match)"

        return await self.send_email(
            to=user_email,
            subject=subject,
            html_body=html_body
        )

    async def send_application_status_update(
        self,
        user_email: str,
        user_name: str,
        opportunity_title: str,
        status: str,
        message: Optional[str],
        opportunity_url: str
    ) -> bool:
        """Send application status update"""
        html_body = EmailTemplates.application_status(
            user_name=user_name,
            opportunity_title=opportunity_title,
            status=status,
            message=message,
            opportunity_url=opportunity_url,
            recipient_email=user_email
        )

        status_subjects = {
            "accepted": f"🎉 Your application for {opportunity_title} was accepted!",
            "rejected": f"Application Update: {opportunity_title}",
            "interview": f"📅 Interview Request: {opportunity_title}",
            "shortlisted": f"⭐ You've been shortlisted for {opportunity_title}!"
        }

        subject = status_subjects.get(status, f"Application Update: {opportunity_title}")

        return await self.send_email(
            to=user_email,
            subject=subject,
            html_body=html_body
        )

    # Payment-related emails

    async def send_payment_receipt(
        self,
        user_email: str,
        user_name: str,
        transaction_id: str,
        amount: float,
        payment_method: str,
        description: str,
        transaction_date: Optional[datetime] = None,
        from_user: Optional[str] = None,
        to_user: Optional[str] = None
    ) -> bool:
        """Send payment receipt"""
        if not transaction_date:
            transaction_date = datetime.utcnow()

        html_body = EmailTemplates.payment_receipt(
            user_name=user_name,
            transaction_id=transaction_id,
            amount=amount,
            payment_method=payment_method,
            description=description,
            transaction_date=transaction_date,
            recipient_email=user_email,
            from_user=from_user,
            to_user=to_user
        )

        subject = f"💰 Payment Receipt: ${amount:,.2f}"

        return await self.send_email(
            to=user_email,
            subject=subject,
            html_body=html_body
        )

    # Engagement emails

    async def send_weekly_digest(
        self,
        user_email: str,
        user_name: str,
        stats: Dict[str, int],
        new_opportunities: List[Dict[str, Any]],
        achievements: List[str]
    ) -> bool:
        """Send weekly digest"""
        html_body = EmailTemplates.weekly_digest(
            user_name=user_name,
            stats=stats,
            new_opportunities=new_opportunities,
            achievements=achievements,
            recipient_email=user_email
        )

        subject = f"📊 Your Trybe Weekly Digest - {datetime.now().strftime('%B %d, %Y')}"

        return await self.send_email(
            to=user_email,
            subject=subject,
            html_body=html_body
        )

    async def send_marketing_campaign(
        self,
        user_email: str,
        user_name: str,
        campaign_title: str,
        campaign_message: str,
        cta_text: str,
        cta_url: str,
        image_url: Optional[str] = None
    ) -> bool:
        """Send marketing campaign email"""
        html_body = EmailTemplates.marketing_campaign(
            user_name=user_name,
            campaign_title=campaign_title,
            campaign_message=campaign_message,
            cta_text=cta_text,
            cta_url=cta_url,
            image_url=image_url,
            recipient_email=user_email
        )

        subject = campaign_title

        return await self.send_email(
            to=user_email,
            subject=subject,
            html_body=html_body
        )

    # Learning-related emails

    async def send_course_enrollment_confirmation(
        self,
        user_email: str,
        user_name: str,
        course_title: str,
        instructor_name: str,
        duration_hours: int,
        course_url: str
    ) -> bool:
        """Send course enrollment confirmation"""
        html_body = EmailTemplates.course_enrollment_confirmation(
            user_name=user_name,
            course_title=course_title,
            instructor_name=instructor_name,
            duration_hours=duration_hours,
            course_url=course_url,
            recipient_email=user_email
        )

        subject = f"📚 Enrolled: {course_title}"

        return await self.send_email(
            to=user_email,
            subject=subject,
            html_body=html_body
        )

    async def send_skill_test_result(
        self,
        user_email: str,
        user_name: str,
        test_name: str,
        score: int,
        passed: bool,
        certificate_url: Optional[str] = None
    ) -> bool:
        """Send skill test result"""
        html_body = EmailTemplates.skill_test_result(
            user_name=user_name,
            test_name=test_name,
            score=score,
            passed=passed,
            certificate_url=certificate_url,
            recipient_email=user_email
        )

        subject = f"📊 Test Results: {test_name} - {'Passed! 🎉' if passed else 'Keep Learning'}"

        return await self.send_email(
            to=user_email,
            subject=subject,
            html_body=html_body
        )

    # Profile-related emails

    async def send_profile_completion_reminder(
        self,
        user_email: str,
        user_name: str,
        completion_percentage: int,
        missing_items: List[str]
    ) -> bool:
        """Send profile completion reminder"""
        html_body = EmailTemplates.reminder_complete_profile(
            user_name=user_name,
            completion_percentage=completion_percentage,
            missing_items=missing_items,
            recipient_email=user_email
        )

        subject = f"✨ Complete Your Profile ({completion_percentage}% done)"

        return await self.send_email(
            to=user_email,
            subject=subject,
            html_body=html_body
        )

    # Batch email methods

    async def send_batch_opportunity_matches(
        self,
        matches: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Send opportunity match emails to multiple users

        Args:
            matches: List of match dictionaries with user and opportunity details

        Returns:
            Dictionary with success and failure counts
        """
        success_count = 0
        failure_count = 0

        for match in matches:
            try:
                success = await self.send_opportunity_match(
                    user_email=match['user_email'],
                    user_name=match['user_name'],
                    opportunity_title=match['opportunity_title'],
                    company_name=match['company_name'],
                    match_percentage=match['match_percentage'],
                    opportunity_type=match['opportunity_type'],
                    budget=match.get('budget'),
                    location=match['location'],
                    opportunity_url=match['opportunity_url'],
                    required_skills=match.get('required_skills', [])
                )

                if success:
                    success_count += 1
                else:
                    failure_count += 1

            except Exception as e:
                logger.error(f"Error sending match email to {match.get('user_email')}: {e}")
                failure_count += 1

        return {
            "success_count": success_count,
            "failure_count": failure_count,
            "total": len(matches)
        }

    async def send_batch_weekly_digests(
        self,
        digests: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Send weekly digests to multiple users"""
        success_count = 0
        failure_count = 0

        for digest in digests:
            try:
                success = await self.send_weekly_digest(
                    user_email=digest['user_email'],
                    user_name=digest['user_name'],
                    stats=digest['stats'],
                    new_opportunities=digest.get('new_opportunities', []),
                    achievements=digest.get('achievements', [])
                )

                if success:
                    success_count += 1
                else:
                    failure_count += 1

            except Exception as e:
                logger.error(f"Error sending digest to {digest.get('user_email')}: {e}")
                failure_count += 1

        return {
            "success_count": success_count,
            "failure_count": failure_count,
            "total": len(digests)
        }


# Global instance
enhanced_email_service = EnhancedEmailService()
