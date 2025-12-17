"""Email service for sending transactional emails"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from pathlib import Path
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    Email service using SMTP or SendGrid

    Supports:
    - Transactional emails
    - HTML templates
    - Multiple recipients
    - Attachments
    """

    def __init__(self):
        self.provider = getattr(settings, 'EMAIL_PROVIDER', 'smtp')  # 'smtp' or 'sendgrid'
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
        body: str,
        html_body: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """
        Send email

        Args:
            to: Recipient email(s)
            subject: Email subject
            body: Plain text body
            html_body: HTML body (optional)
            cc: CC recipients
            bcc: BCC recipients

        Returns:
            True if sent successfully
        """
        try:
            if self.provider == 'sendgrid':
                return await self._send_via_sendgrid(to, subject, body, html_body)
            else:
                return await self._send_via_smtp(to, subject, body, html_body, cc, bcc)
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    async def _send_via_smtp(
        self,
        to: str | List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """Send email via SMTP"""
        # Create message
        message = MIMEMultipart('alternative')
        message['From'] = f"{self.from_name} <{self.from_email}>"
        message['To'] = to if isinstance(to, str) else ', '.join(to)
        message['Subject'] = subject

        if cc:
            message['Cc'] = ', '.join(cc)

        # Add plain text part
        message.attach(MIMEText(body, 'plain'))

        # Add HTML part if provided
        if html_body:
            message.attach(MIMEText(html_body, 'html'))

        # Send email
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)

                # Get all recipients
                recipients = []
                if isinstance(to, list):
                    recipients.extend(to)
                else:
                    recipients.append(to)
                if cc:
                    recipients.extend(cc)
                if bcc:
                    recipients.extend(bcc)

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
        html_body: Optional[str] = None
    ) -> bool:
        """
        Send email via SendGrid API

        Requires: pip install sendgrid
        """
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To, Content

            # Create message
            from_email = Email(self.from_email, self.from_name)
            to_emails = To(to) if isinstance(to, str) else [To(email) for email in to]
            content = Content("text/html", html_body) if html_body else Content("text/plain", body)

            mail = Mail(from_email, to_emails, subject, content)

            # Send
            sg = SendGridAPIClient(self.sendgrid_api_key)
            response = sg.send(mail)

            logger.info(f"SendGrid email sent: {response.status_code}")
            return response.status_code in [200, 201, 202]

        except ImportError:
            logger.error("SendGrid library not installed. Install with: pip install sendgrid")
            return False
        except Exception as e:
            logger.error(f"SendGrid error: {e}")
            return False

    async def send_welcome_email(self, user_email: str, user_name: str) -> bool:
        """Send welcome email to new user"""
        subject = "Welcome to Trybe! 🎉"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                           color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #667eea; color: white;
                          padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to Trybe!</h1>
                </div>
                <div class="content">
                    <p>Hi {user_name},</p>
                    <p>Thank you for joining Trybe People's Market! We're excited to have you as part of our community.</p>
                    <p>Trybe is your platform to:</p>
                    <ul>
                        <li>Discover amazing opportunities</li>
                        <li>Connect with talented professionals</li>
                        <li>Learn new skills</li>
                        <li>Grow your career</li>
                    </ul>
                    <p>
                        <a href="https://trybe.app/discover" class="button">Start Exploring</a>
                    </p>
                    <p>If you have any questions, feel free to reach out to our support team.</p>
                    <p>Best regards,<br>The Trybe Team</p>
                </div>
                <div class="footer">
                    <p>© 2025 Trybe. All rights reserved.</p>
                    <p>This email was sent to {user_email}</p>
                </div>
            </div>
        </body>
        </html>
        """

        body = f"""
        Hi {user_name},

        Thank you for joining Trybe People's Market! We're excited to have you as part of our community.

        Trybe is your platform to:
        - Discover amazing opportunities
        - Connect with talented professionals
        - Learn new skills
        - Grow your career

        Visit https://trybe.app/discover to start exploring!

        Best regards,
        The Trybe Team
        """

        return await self.send_email(
            to=user_email,
            subject=subject,
            body=body,
            html_body=html_body
        )

    async def send_password_reset_email(
        self,
        user_email: str,
        user_name: str,
        reset_token: str
    ) -> bool:
        """Send password reset email"""
        reset_url = f"https://trybe.app/reset-password?token={reset_token}"

        subject = "Reset Your Trybe Password"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2>Password Reset Request</h2>
                <p>Hi {user_name},</p>
                <p>We received a request to reset your password. Click the button below to create a new password:</p>
                <p>
                    <a href="{reset_url}" style="display: inline-block; background: #667eea; color: white;
                       padding: 12px 30px; text-decoration: none; border-radius: 5px;">
                        Reset Password
                    </a>
                </p>
                <p>This link will expire in 1 hour.</p>
                <p>If you didn't request this, please ignore this email.</p>
                <p>Best regards,<br>The Trybe Team</p>
            </div>
        </body>
        </html>
        """

        body = f"""
        Hi {user_name},

        We received a request to reset your password.

        Click here to reset: {reset_url}

        This link will expire in 1 hour.

        If you didn't request this, please ignore this email.

        Best regards,
        The Trybe Team
        """

        return await self.send_email(
            to=user_email,
            subject=subject,
            body=body,
            html_body=html_body
        )

    async def send_verification_email(
        self,
        user_email: str,
        user_name: str,
        verification_token: str
    ) -> bool:
        """Send email verification"""
        verification_url = f"https://trybe.app/verify-email?token={verification_token}"

        subject = "Verify Your Trybe Email"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2>Verify Your Email</h2>
                <p>Hi {user_name},</p>
                <p>Please verify your email address to activate your Trybe account:</p>
                <p>
                    <a href="{verification_url}" style="display: inline-block; background: #667eea; color: white;
                       padding: 12px 30px; text-decoration: none; border-radius: 5px;">
                        Verify Email
                    </a>
                </p>
                <p>Best regards,<br>The Trybe Team</p>
            </div>
        </body>
        </html>
        """

        body = f"""
        Hi {user_name},

        Please verify your email address: {verification_url}

        Best regards,
        The Trybe Team
        """

        return await self.send_email(
            to=user_email,
            subject=subject,
            body=body,
            html_body=html_body
        )


# Global instance
email_service = EmailService()
