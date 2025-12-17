"""Email HTML Templates for Trybe Platform"""

from typing import Dict, Any, List, Optional
from datetime import datetime


class EmailTemplates:
    """HTML email templates for various email types"""

    # Base template with Trybe branding
    BASE_TEMPLATE = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                   line-height: 1.6; color: #333; background-color: #f5f5f5; }}
            .email-wrapper {{ width: 100%; background-color: #f5f5f5; padding: 40px 20px; }}
            .email-container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff;
                               border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .email-header {{ background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                            padding: 40px 30px; text-align: center; }}
            .email-header h1 {{ color: #ffffff; font-size: 28px; margin: 0; font-weight: 700; }}
            .email-header p {{ color: #e0e7ff; margin-top: 10px; font-size: 14px; }}
            .email-content {{ padding: 40px 30px; }}
            .email-content h2 {{ color: #1f2937; font-size: 24px; margin-bottom: 20px; }}
            .email-content p {{ color: #4b5563; margin-bottom: 16px; line-height: 1.8; }}
            .email-content ul {{ margin-left: 20px; margin-bottom: 16px; }}
            .email-content li {{ color: #4b5563; margin-bottom: 8px; }}
            .button {{ display: inline-block; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                      color: #ffffff !important; padding: 14px 32px; text-decoration: none;
                      border-radius: 8px; margin: 20px 0; font-weight: 600; text-align: center;
                      transition: transform 0.2s; }}
            .button:hover {{ transform: translateY(-2px); }}
            .info-box {{ background-color: #f3f4f6; border-left: 4px solid #6366f1;
                        padding: 16px; margin: 20px 0; border-radius: 4px; }}
            .info-box p {{ margin: 0; color: #374151; }}
            .highlight {{ background-color: #fef3c7; padding: 2px 6px; border-radius: 3px; }}
            .email-footer {{ background-color: #f9fafb; padding: 30px; text-align: center;
                            border-top: 1px solid #e5e7eb; }}
            .email-footer p {{ color: #6b7280; font-size: 13px; margin-bottom: 8px; }}
            .social-links {{ margin: 20px 0; }}
            .social-links a {{ display: inline-block; margin: 0 10px; color: #6366f1; text-decoration: none; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin: 20px 0; }}
            .stat-card {{ background: #f9fafb; padding: 20px; border-radius: 8px; text-align: center; }}
            .stat-value {{ font-size: 28px; font-weight: 700; color: #6366f1; }}
            .stat-label {{ color: #6b7280; font-size: 14px; margin-top: 4px; }}
            @media only screen and (max-width: 600px) {{
                .email-header {{ padding: 30px 20px; }}
                .email-content {{ padding: 30px 20px; }}
                .stats-grid {{ grid-template-columns: 1fr; }}
            }}
        </style>
    </head>
    <body>
        <div class="email-wrapper">
            <div class="email-container">
                <div class="email-header">
                    <h1>🚀 Trybe</h1>
                    <p>{header_subtitle}</p>
                </div>
                <div class="email-content">
                    {content}
                </div>
                <div class="email-footer">
                    <div class="social-links">
                        <a href="https://twitter.com/trybeapp">Twitter</a>
                        <a href="https://linkedin.com/company/trybe">LinkedIn</a>
                        <a href="https://instagram.com/trybeapp">Instagram</a>
                    </div>
                    <p>&copy; 2025 Trybe People's Market. All rights reserved.</p>
                    <p>This email was sent to {recipient_email}</p>
                    <p><a href="{unsubscribe_url}" style="color: #6b7280;">Unsubscribe</a> |
                       <a href="https://trybe.app/privacy" style="color: #6b7280;">Privacy Policy</a></p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    @staticmethod
    def opportunity_match(
        user_name: str,
        opportunity_title: str,
        company_name: str,
        match_percentage: int,
        opportunity_type: str,
        budget: Optional[float],
        location: str,
        opportunity_url: str,
        required_skills: List[str],
        recipient_email: str
    ) -> str:
        """Email for new opportunity match"""
        skills_html = "".join([f"<li>{skill}</li>" for skill in required_skills[:5]])
        budget_text = f"${budget:,.0f}" if budget else "Negotiable"

        content = f"""
            <h2>🎯 New Opportunity Match!</h2>
            <p>Hi {user_name},</p>
            <p>Great news! We found an opportunity that matches your profile with a
               <span class="highlight">{match_percentage}% match</span>!</p>

            <div class="info-box">
                <h3 style="margin-bottom: 12px; color: #1f2937;">{opportunity_title}</h3>
                <p><strong>Company:</strong> {company_name}</p>
                <p><strong>Type:</strong> {opportunity_type.replace('_', ' ').title()}</p>
                <p><strong>Budget:</strong> {budget_text}</p>
                <p><strong>Location:</strong> {location}</p>
            </div>

            <p><strong>Required Skills:</strong></p>
            <ul>
                {skills_html}
            </ul>

            <p style="text-align: center;">
                <a href="{opportunity_url}" class="button">View Opportunity →</a>
            </p>

            <p>This opportunity matches your skills and preferences. Don't miss out!</p>
            <p>Best of luck,<br><strong>The Trybe Team</strong></p>
        """

        return EmailTemplates.BASE_TEMPLATE.format(
            title="New Opportunity Match",
            header_subtitle="You've got a new match!",
            content=content,
            recipient_email=recipient_email,
            unsubscribe_url=f"https://trybe.app/unsubscribe?email={recipient_email}"
        )

    @staticmethod
    def application_status(
        user_name: str,
        opportunity_title: str,
        status: str,
        message: Optional[str],
        opportunity_url: str,
        recipient_email: str
    ) -> str:
        """Email for application status update"""
        status_messages = {
            "accepted": {
                "emoji": "🎉",
                "title": "Application Accepted!",
                "color": "#10b981",
                "text": f"Congratulations! Your application for <strong>{opportunity_title}</strong> has been accepted!"
            },
            "rejected": {
                "emoji": "💼",
                "title": "Application Update",
                "color": "#6b7280",
                "text": f"Thank you for your interest in <strong>{opportunity_title}</strong>. Unfortunately, we've decided to move forward with other candidates."
            },
            "interview": {
                "emoji": "📅",
                "title": "Interview Request",
                "color": "#3b82f6",
                "text": f"Great news! The employer wants to interview you for <strong>{opportunity_title}</strong>!"
            },
            "shortlisted": {
                "emoji": "⭐",
                "title": "You've Been Shortlisted!",
                "color": "#f59e0b",
                "text": f"Your application for <strong>{opportunity_title}</strong> has been shortlisted!"
            }
        }

        status_info = status_messages.get(status, {
            "emoji": "📬",
            "title": "Application Update",
            "color": "#6366f1",
            "text": f"Your application for <strong>{opportunity_title}</strong> has been updated."
        })

        additional_message = f"<p><em>\"{message}\"</em></p>" if message else ""

        content = f"""
            <h2>{status_info['emoji']} {status_info['title']}</h2>
            <p>Hi {user_name},</p>

            <div class="info-box" style="border-left-color: {status_info['color']};">
                <p>{status_info['text']}</p>
            </div>

            {additional_message}

            <p style="text-align: center;">
                <a href="{opportunity_url}" class="button">View Details →</a>
            </p>

            <p>Keep up the great work and continue exploring opportunities on Trybe!</p>
            <p>Best regards,<br><strong>The Trybe Team</strong></p>
        """

        return EmailTemplates.BASE_TEMPLATE.format(
            title=status_info['title'],
            header_subtitle=f"Application Update: {opportunity_title}",
            content=content,
            recipient_email=recipient_email,
            unsubscribe_url=f"https://trybe.app/unsubscribe?email={recipient_email}"
        )

    @staticmethod
    def payment_receipt(
        user_name: str,
        transaction_id: str,
        amount: float,
        payment_method: str,
        description: str,
        transaction_date: datetime,
        recipient_email: str,
        from_user: Optional[str] = None,
        to_user: Optional[str] = None
    ) -> str:
        """Email for payment receipt"""
        content = f"""
            <h2>💰 Payment Receipt</h2>
            <p>Hi {user_name},</p>
            <p>This email confirms your recent payment on Trybe.</p>

            <div class="info-box">
                <h3 style="margin-bottom: 16px; color: #1f2937;">Transaction Details</h3>
                <p><strong>Transaction ID:</strong> {transaction_id}</p>
                <p><strong>Amount:</strong> <span style="font-size: 24px; color: #6366f1; font-weight: 700;">${amount:,.2f}</span></p>
                <p><strong>Payment Method:</strong> {payment_method}</p>
                <p><strong>Date:</strong> {transaction_date.strftime('%B %d, %Y at %I:%M %p')}</p>
                <p><strong>Description:</strong> {description}</p>
                {f'<p><strong>From:</strong> {from_user}</p>' if from_user else ''}
                {f'<p><strong>To:</strong> {to_user}</p>' if to_user else ''}
            </div>

            <p>You can view your complete transaction history in your Trybe account.</p>

            <p style="text-align: center;">
                <a href="https://trybe.app/transactions" class="button">View Transaction History →</a>
            </p>

            <p>If you have any questions about this transaction, please contact our support team.</p>
            <p>Thank you for using Trybe!<br><strong>The Trybe Team</strong></p>
        """

        return EmailTemplates.BASE_TEMPLATE.format(
            title="Payment Receipt",
            header_subtitle="Transaction Confirmation",
            content=content,
            recipient_email=recipient_email,
            unsubscribe_url=f"https://trybe.app/unsubscribe?email={recipient_email}"
        )

    @staticmethod
    def weekly_digest(
        user_name: str,
        stats: Dict[str, int],
        new_opportunities: List[Dict[str, Any]],
        achievements: List[str],
        recipient_email: str
    ) -> str:
        """Weekly digest email"""
        opportunities_html = ""
        for opp in new_opportunities[:3]:
            opportunities_html += f"""
                <div style="background: #f9fafb; padding: 16px; margin-bottom: 12px; border-radius: 8px;">
                    <h4 style="color: #1f2937; margin-bottom: 8px;">{opp['title']}</h4>
                    <p style="color: #6b7280; font-size: 14px; margin: 0;">{opp['company']} • {opp['location']}</p>
                </div>
            """

        achievements_html = "".join([f"<li>🏆 {achievement}</li>" for achievement in achievements])

        content = f"""
            <h2>📊 Your Weekly Digest</h2>
            <p>Hi {user_name},</p>
            <p>Here's what happened on your Trybe account this week:</p>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{stats.get('profile_views', 0)}</div>
                    <div class="stat-label">Profile Views</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{stats.get('new_matches', 0)}</div>
                    <div class="stat-label">New Matches</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{stats.get('applications', 0)}</div>
                    <div class="stat-label">Applications</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{stats.get('messages', 0)}</div>
                    <div class="stat-label">Messages</div>
                </div>
            </div>

            <h3 style="color: #1f2937; margin-top: 30px; margin-bottom: 16px;">🎯 New Opportunities for You</h3>
            {opportunities_html}

            {f'''
            <h3 style="color: #1f2937; margin-top: 30px; margin-bottom: 16px;">🌟 Your Achievements</h3>
            <ul style="list-style-type: none; padding-left: 0;">
                {achievements_html}
            </ul>
            ''' if achievements else ''}

            <p style="text-align: center; margin-top: 30px;">
                <a href="https://trybe.app/dashboard" class="button">Go to Dashboard →</a>
            </p>

            <p>Keep up the great work! We're here to support your journey.</p>
            <p>Best regards,<br><strong>The Trybe Team</strong></p>
        """

        return EmailTemplates.BASE_TEMPLATE.format(
            title="Your Weekly Digest",
            header_subtitle=f"Week of {datetime.now().strftime('%B %d, %Y')}",
            content=content,
            recipient_email=recipient_email,
            unsubscribe_url=f"https://trybe.app/unsubscribe?email={recipient_email}"
        )

    @staticmethod
    def marketing_campaign(
        user_name: str,
        campaign_title: str,
        campaign_message: str,
        cta_text: str,
        cta_url: str,
        image_url: Optional[str],
        recipient_email: str
    ) -> str:
        """Marketing campaign email"""
        image_html = f'<img src="{image_url}" alt="{campaign_title}" style="width: 100%; border-radius: 8px; margin: 20px 0;">' if image_url else ""

        content = f"""
            <h2>{campaign_title}</h2>
            <p>Hi {user_name},</p>

            {image_html}

            <div style="font-size: 16px; line-height: 1.8;">
                {campaign_message}
            </div>

            <p style="text-align: center; margin-top: 30px;">
                <a href="{cta_url}" class="button">{cta_text}</a>
            </p>

            <p>Questions? Reach out to our team anytime.</p>
            <p>Cheers,<br><strong>The Trybe Team</strong></p>
        """

        return EmailTemplates.BASE_TEMPLATE.format(
            title=campaign_title,
            header_subtitle="Exciting news from Trybe",
            content=content,
            recipient_email=recipient_email,
            unsubscribe_url=f"https://trybe.app/unsubscribe?email={recipient_email}"
        )

    @staticmethod
    def course_enrollment_confirmation(
        user_name: str,
        course_title: str,
        instructor_name: str,
        duration_hours: int,
        course_url: str,
        recipient_email: str
    ) -> str:
        """Course enrollment confirmation"""
        content = f"""
            <h2>📚 Course Enrollment Confirmed!</h2>
            <p>Hi {user_name},</p>
            <p>You're all set! You've successfully enrolled in:</p>

            <div class="info-box">
                <h3 style="margin-bottom: 12px; color: #1f2937;">{course_title}</h3>
                <p><strong>Instructor:</strong> {instructor_name}</p>
                <p><strong>Duration:</strong> {duration_hours} hours</p>
            </div>

            <p>Start learning at your own pace and unlock new skills!</p>

            <p style="text-align: center;">
                <a href="{course_url}" class="button">Start Learning →</a>
            </p>

            <p><strong>Pro Tips:</strong></p>
            <ul>
                <li>Set aside dedicated time each day for learning</li>
                <li>Take notes and complete practice exercises</li>
                <li>Join the course discussion forum</li>
                <li>Track your progress in your dashboard</li>
            </ul>

            <p>Happy learning!<br><strong>The Trybe Team</strong></p>
        """

        return EmailTemplates.BASE_TEMPLATE.format(
            title="Course Enrollment Confirmed",
            header_subtitle="Let's start learning!",
            content=content,
            recipient_email=recipient_email,
            unsubscribe_url=f"https://trybe.app/unsubscribe?email={recipient_email}"
        )

    @staticmethod
    def reminder_complete_profile(
        user_name: str,
        completion_percentage: int,
        missing_items: List[str],
        recipient_email: str
    ) -> str:
        """Reminder to complete profile"""
        missing_html = "".join([f"<li>{item}</li>" for item in missing_items])

        content = f"""
            <h2>✨ Complete Your Profile</h2>
            <p>Hi {user_name},</p>
            <p>Your Trybe profile is <strong>{completion_percentage}% complete</strong>.
               A complete profile helps you get better matches!</p>

            <div class="info-box">
                <p><strong>What's missing:</strong></p>
                <ul style="margin-top: 12px;">
                    {missing_html}
                </ul>
            </div>

            <p>Complete your profile to:</p>
            <ul>
                <li>Get 3x more profile views</li>
                <li>Receive better opportunity matches</li>
                <li>Build trust with employers</li>
                <li>Stand out from the competition</li>
            </ul>

            <p style="text-align: center;">
                <a href="https://trybe.app/profile/edit" class="button">Complete Profile →</a>
            </p>

            <p>It only takes 5 minutes!</p>
            <p>Best regards,<br><strong>The Trybe Team</strong></p>
        """

        return EmailTemplates.BASE_TEMPLATE.format(
            title="Complete Your Profile",
            header_subtitle="Stand out and get noticed",
            content=content,
            recipient_email=recipient_email,
            unsubscribe_url=f"https://trybe.app/unsubscribe?email={recipient_email}"
        )

    @staticmethod
    def skill_test_result(
        user_name: str,
        test_name: str,
        score: int,
        passed: bool,
        certificate_url: Optional[str],
        recipient_email: str
    ) -> str:
        """Skill test result notification"""
        if passed:
            result_html = f"""
                <div class="info-box" style="border-left-color: #10b981;">
                    <p style="font-size: 18px; color: #10b981; font-weight: 600;">✅ Congratulations! You passed!</p>
                    <p style="margin-top: 12px;">Your score: <strong>{score}%</strong></p>
                </div>
                {f'<p style="text-align: center;"><a href="{certificate_url}" class="button">Download Certificate →</a></p>' if certificate_url else ''}
            """
        else:
            result_html = f"""
                <div class="info-box" style="border-left-color: #f59e0b;">
                    <p style="font-size: 18px; color: #f59e0b; font-weight: 600;">Keep trying! You can retake the test.</p>
                    <p style="margin-top: 12px;">Your score: <strong>{score}%</strong></p>
                    <p>Required: <strong>70%</strong></p>
                </div>
            """

        content = f"""
            <h2>📊 Test Results: {test_name}</h2>
            <p>Hi {user_name},</p>
            <p>Your test results are ready!</p>

            {result_html}

            <p>{'Share your achievement on LinkedIn to showcase your skills!' if passed else 'Review the material and try again when you\'re ready.'}</p>

            <p style="text-align: center;">
                <a href="https://trybe.app/tests/results" class="button">View Detailed Results →</a>
            </p>

            <p>Keep learning and growing!<br><strong>The Trybe Team</strong></p>
        """

        return EmailTemplates.BASE_TEMPLATE.format(
            title="Test Results",
            header_subtitle=f"Results for {test_name}",
            content=content,
            recipient_email=recipient_email,
            unsubscribe_url=f"https://trybe.app/unsubscribe?email={recipient_email}"
        )
