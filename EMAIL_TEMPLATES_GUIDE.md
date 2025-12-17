# Email Templates Guide

Complete guide to the Trybe email notification system with professional HTML templates.

## Overview

The enhanced email system provides professionally designed, responsive HTML email templates for all platform communications. All templates feature:

- **Modern Design**: Gradient headers, clean typography, responsive layouts
- **Brand Consistency**: Trybe colors and styling throughout
- **Mobile Responsive**: Optimized for all screen sizes
- **Actionable**: Clear CTAs with button styles
- **Professional**: Statistics cards, info boxes, and formatted content

## Architecture

### Components

1. **EmailTemplates** (`app/services/email_templates.py`)
   - 8 professional HTML templates
   - Base template with Trybe branding
   - Responsive design with inline CSS
   - Social media links and footer

2. **EnhancedEmailService** (`app/services/enhanced_email_service.py`)
   - SMTP and SendGrid support
   - Async email sending
   - Background task integration
   - Batch email capabilities

3. **Email API** (`app/api/v1/endpoints/emails.py`)
   - 11 email sending endpoints
   - 2 batch endpoints
   - Background task integration
   - Template listing

## Available Email Templates

### 1. Opportunity Match Email

**Purpose**: Notify users about new opportunity matches

**Features**:
- Match percentage highlight
- Opportunity details in info box
- Required skills list
- Budget and location information
- Direct link to opportunity

**Endpoint**: `POST /api/v1/emails/send/opportunity-match`

**Example**:
```json
{
  "user_email": "user@example.com",
  "user_name": "John Doe",
  "opportunity_title": "Senior Full Stack Developer",
  "company_name": "Tech Innovations Inc",
  "match_percentage": 92,
  "opportunity_type": "full_time",
  "budget": 120000,
  "location": "Remote",
  "opportunity_url": "https://trybe.app/opportunities/123",
  "required_skills": ["Python", "React", "PostgreSQL", "Docker"]
}
```

---

### 2. Application Status Update

**Purpose**: Inform users about application status changes

**Status Types**:
- `accepted` - Application accepted (green, celebratory)
- `rejected` - Not selected (gray, respectful)
- `interview` - Interview request (blue, exciting)
- `shortlisted` - Shortlisted (orange, encouraging)

**Features**:
- Status-specific colors and emojis
- Optional message from employer
- Appropriate tone for each status
- Link to view details

**Endpoint**: `POST /api/v1/emails/send/application-status`

**Example**:
```json
{
  "user_email": "user@example.com",
  "user_name": "Jane Smith",
  "opportunity_title": "UX Designer",
  "status": "interview",
  "message": "We were impressed by your portfolio. Looking forward to meeting you!",
  "opportunity_url": "https://trybe.app/opportunities/456"
}
```

---

### 3. Payment Receipt

**Purpose**: Send transaction confirmations

**Features**:
- Large, prominent amount display
- Complete transaction details
- Transaction ID for reference
- From/To user information
- Link to transaction history

**Endpoint**: `POST /api/v1/emails/send/payment-receipt`

**Example**:
```json
{
  "user_email": "user@example.com",
  "user_name": "Alex Johnson",
  "transaction_id": "TXN-2025-001234",
  "amount": 2500.00,
  "payment_method": "Stripe",
  "description": "Payment for Full Stack Development Project",
  "from_user": "Tech Corp",
  "to_user": "Alex Johnson"
}
```

---

### 4. Weekly Digest

**Purpose**: Weekly engagement summary

**Features**:
- Statistics grid (4 metrics)
- New opportunity previews
- Achievement badges
- Activity summary
- Dashboard link

**Metrics Included**:
- Profile views
- New matches
- Applications submitted
- Messages received

**Endpoint**: `POST /api/v1/emails/send/weekly-digest`

**Example**:
```json
{
  "user_email": "user@example.com",
  "user_name": "Sarah Williams",
  "stats": {
    "profile_views": 47,
    "new_matches": 8,
    "applications": 3,
    "messages": 12
  },
  "new_opportunities": [
    {
      "title": "Backend Developer",
      "company": "StartupXYZ",
      "location": "Nairobi, Kenya"
    },
    {
      "title": "Data Analyst",
      "company": "DataCo",
      "location": "Lagos, Nigeria"
    }
  ],
  "achievements": [
    "Completed 5 courses this week",
    "Reached 1000 profile views",
    "Earned Python certification"
  ]
}
```

---

### 5. Marketing Campaign

**Purpose**: Custom marketing emails

**Features**:
- Custom title and message
- Optional hero image
- Customizable CTA button
- Full HTML message support
- Unsubscribe link

**Endpoint**: `POST /api/v1/emails/send/marketing-campaign`

**Permissions**: Admin only

**Example**:
```json
{
  "user_email": "user@example.com",
  "user_name": "Michael Chen",
  "campaign_title": "🎉 New Feature Launch: AI Career Assistant",
  "campaign_message": "<p>We're excited to announce our new AI Career Assistant!</p><p>Get personalized career advice, skill gap analysis, and career roadmaps powered by AI.</p>",
  "cta_text": "Try AI Career Assistant",
  "cta_url": "https://trybe.app/career",
  "image_url": "https://trybe.app/images/ai-career-banner.jpg"
}
```

---

### 6. Course Enrollment Confirmation

**Purpose**: Confirm course enrollments

**Features**:
- Course details
- Instructor information
- Duration estimate
- Learning tips
- Direct start link

**Endpoint**: `POST /api/v1/emails/send/course-enrollment`

**Example**:
```json
{
  "user_email": "user@example.com",
  "user_name": "Emma Davis",
  "course_title": "Advanced Python Programming",
  "instructor_name": "Dr. James Wilson",
  "duration_hours": 24,
  "course_url": "https://trybe.app/courses/python-advanced"
}
```

---

### 7. Skill Test Result

**Purpose**: Share test results

**Features**:
- Pass/fail status with color coding
- Score display
- Certificate download (if passed)
- Encouragement message
- Detailed results link

**Endpoint**: `POST /api/v1/emails/send/test-result`

**Example**:
```json
{
  "user_email": "user@example.com",
  "user_name": "David Brown",
  "test_name": "JavaScript Fundamentals",
  "score": 88,
  "passed": true,
  "certificate_url": "https://trybe.app/certificates/js-fund-001.pdf"
}
```

---

### 8. Profile Completion Reminder

**Purpose**: Encourage profile completion

**Features**:
- Completion percentage
- Missing items list
- Benefits of completion
- Profile edit link
- Engagement statistics

**Endpoint**: `POST /api/v1/emails/send/profile-reminder`

**Example**:
```json
{
  "user_email": "user@example.com",
  "user_name": "Lisa Anderson",
  "completion_percentage": 65,
  "missing_items": [
    "Professional photo",
    "Portfolio links",
    "Skills assessment",
    "Work experience details"
  ]
}
```

---

## Batch Email Endpoints

### Batch Opportunity Matches

Send opportunity notifications to multiple users efficiently.

**Endpoint**: `POST /api/v1/emails/batch/opportunity-matches`

**Example**:
```json
{
  "recipients": [
    {
      "user_email": "user1@example.com",
      "user_name": "User One",
      "opportunity_title": "Developer",
      "company_name": "Company A",
      "match_percentage": 85,
      "opportunity_type": "full_time",
      "location": "Remote",
      "opportunity_url": "https://trybe.app/opp/1",
      "required_skills": ["Python", "React"]
    },
    {
      "user_email": "user2@example.com",
      "user_name": "User Two",
      ...
    }
  ]
}
```

### Batch Weekly Digests

Send personalized weekly digests to all active users.

**Endpoint**: `POST /api/v1/emails/batch/weekly-digests`

**Permissions**: Admin only

---

## Technical Implementation

### Email Service Configuration

Configure in `.env`:

```env
# Email Provider ('smtp' or 'sendgrid')
EMAIL_PROVIDER=smtp
EMAIL_FROM=noreply@trybe.app
EMAIL_FROM_NAME=Trybe Team

# SMTP Settings
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# SendGrid (alternative)
SENDGRID_API_KEY=your-sendgrid-api-key
```

### Background Tasks

All emails are sent using FastAPI's `BackgroundTasks` for better performance:

```python
from fastapi import BackgroundTasks

@router.post("/send-email")
async def send_email(background_tasks: BackgroundTasks):
    background_tasks.add_task(
        enhanced_email_service.send_opportunity_match,
        ...
    )
    return {"message": "Email queued"}
```

### Template Customization

Templates use inline CSS for maximum email client compatibility:

```python
# All styles are inline for email client compatibility
style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
       color: #ffffff; padding: 40px 30px; text-align: center;"
```

### Responsive Design

Templates adapt to mobile screens:

```css
@media only screen and (max-width: 600px) {
    .email-header { padding: 30px 20px; }
    .email-content { padding: 30px 20px; }
    .stats-grid { grid-template-columns: 1fr; }
}
```

---

## Best Practices

### 1. Email Content

- **Subject Lines**: Keep under 50 characters, use emojis sparingly
- **Preview Text**: First 140 characters should be engaging
- **CTA Buttons**: One primary action per email
- **Personalization**: Always use user's name

### 2. Sending Strategy

- **Timing**: Send digests on Sunday evenings
- **Frequency**: Limit marketing to 1-2 per week
- **Segmentation**: Target specific user groups
- **A/B Testing**: Test subject lines and CTAs

### 3. Deliverability

- **SPF/DKIM**: Configure sender authentication
- **Unsubscribe**: Always include unsubscribe link
- **Clean Lists**: Remove bounced addresses
- **Warm Up**: Gradually increase sending volume

### 4. Metrics to Track

- **Open Rate**: Target 20-30%
- **Click Rate**: Target 3-5%
- **Unsubscribe Rate**: Keep below 0.5%
- **Bounce Rate**: Keep below 2%

---

## Integration Examples

### Trigger on Opportunity Match

```python
from app.services.enhanced_email_service import enhanced_email_service

async def create_match(user_id, opportunity_id):
    # Create match in database
    match = await create_match_record(user_id, opportunity_id)

    # Send email notification
    await enhanced_email_service.send_opportunity_match(
        user_email=user.email,
        user_name=user.full_name,
        opportunity_title=opportunity.title,
        company_name=opportunity.company,
        match_percentage=match.score,
        ...
    )
```

### Weekly Digest Cron Job

```python
from app.services.enhanced_email_service import enhanced_email_service

async def send_weekly_digests():
    """Run every Sunday at 6 PM"""
    active_users = await get_active_users()

    digests = []
    for user in active_users:
        stats = await calculate_weekly_stats(user.id)
        opportunities = await get_new_opportunities(user.id)
        achievements = await get_user_achievements(user.id)

        digests.append({
            "user_email": user.email,
            "user_name": user.full_name,
            "stats": stats,
            "new_opportunities": opportunities,
            "achievements": achievements
        })

    # Send batch
    await enhanced_email_service.send_batch_weekly_digests(digests)
```

---

## Email Template Reference

### Base Template Structure

```html
<!DOCTYPE html>
<html>
  <head>
    <style>/* Inline CSS */</style>
  </head>
  <body>
    <div class="email-wrapper">
      <div class="email-container">
        <!-- Header with gradient -->
        <div class="email-header">
          <h1>🚀 Trybe</h1>
        </div>

        <!-- Main content -->
        <div class="email-content">
          {content}
        </div>

        <!-- Footer with social links -->
        <div class="email-footer">
          <p>© 2025 Trybe</p>
          <p>Unsubscribe | Privacy</p>
        </div>
      </div>
    </div>
  </body>
</html>
```

### Color Palette

- **Primary**: `#6366f1` (Indigo)
- **Secondary**: `#8b5cf6` (Purple)
- **Success**: `#10b981` (Green)
- **Warning**: `#f59e0b` (Orange)
- **Info**: `#3b82f6` (Blue)
- **Text**: `#1f2937` (Dark Gray)
- **Muted**: `#6b7280` (Gray)

---

## Testing

### Test Email Sending

```bash
# Test SMTP connection
python -c "
from app.services.enhanced_email_service import enhanced_email_service
import asyncio

async def test():
    result = await enhanced_email_service.send_opportunity_match(
        user_email='test@example.com',
        user_name='Test User',
        ...
    )
    print(f'Email sent: {result}')

asyncio.run(test())
"
```

### Preview Templates

Use the `/api/v1/emails/templates` endpoint to list all available templates and their required fields.

---

## Troubleshooting

### Common Issues

**Problem**: Emails not sending
- Check SMTP credentials
- Verify firewall allows SMTP port
- Check email service logs

**Problem**: Emails in spam
- Configure SPF/DKIM records
- Warm up IP address
- Reduce sending frequency

**Problem**: Broken images
- Use full URLs for images
- Host images on CDN
- Test with different clients

**Problem**: Poor mobile rendering
- Test on actual devices
- Use inline CSS
- Keep width under 600px

---

## Future Enhancements

- [ ] A/B testing framework
- [ ] Template builder UI
- [ ] Email analytics dashboard
- [ ] Automated drip campaigns
- [ ] SMS fallback integration
- [ ] Multi-language support
- [ ] Dynamic content blocks
- [ ] Email preference center

---

**Total Email Templates**: 8
**API Endpoints**: 13
**Batch Operations**: 2
**Email Providers**: 2 (SMTP, SendGrid)
