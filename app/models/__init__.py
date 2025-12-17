"""Database models"""

from app.models.user import User
from app.models.opportunity import Opportunity
from app.models.match import Swipe, Match
from app.models.payment import PaymentProposal, Transaction
from app.models.message import Conversation, Message
from app.models.notification import Notification, NotificationPreference
from app.models.learning import Course, Lesson, Enrollment, LessonProgress
from app.models.analytics import UserActivity, PlatformMetrics, SystemLog
from app.models.report import ReportTemplate, Report, ReportSchedule
from app.models.hackathon import (
    Hackathon,
    HackathonTeam,
    HackathonRegistration,
    HackathonSubmission,
    AptitudeTest,
    TestResult
)
from app.models.community import (
    CommunityPost,
    Comment,
    Reaction,
    CommunityGroup,
    Poll,
    PollVote,
    Feed
)
from app.models.solar import (
    SolarTrainingEnrollment,
    SolarOpportunity,
    SolarProject,
    SolarDevelopmentPlan,
    SolarResource
)
from app.models.review import (
    Review,
    ReviewHelpful,
    ReviewFlag,
    ReviewSummary
)
from app.models.device_token import (
    DeviceToken,
    NotificationLog
)

__all__ = [
    "User",
    "Opportunity",
    "Swipe",
    "Match",
    "PaymentProposal",
    "Transaction",
    "Conversation",
    "Message",
    "Notification",
    "NotificationPreference",
    "Course",
    "Lesson",
    "Enrollment",
    "LessonProgress",
    "UserActivity",
    "PlatformMetrics",
    "SystemLog",
    "ReportTemplate",
    "Report",
    "ReportSchedule",
    "Hackathon",
    "HackathonTeam",
    "HackathonRegistration",
    "HackathonSubmission",
    "AptitudeTest",
    "TestResult",
    "CommunityPost",
    "Comment",
    "Reaction",
    "CommunityGroup",
    "Poll",
    "PollVote",
    "Feed",
    "SolarTrainingEnrollment",
    "SolarOpportunity",
    "SolarProject",
    "SolarDevelopmentPlan",
    "SolarResource",
    "Review",
    "ReviewHelpful",
    "ReviewFlag",
    "ReviewSummary",
    "DeviceToken",
    "NotificationLog"
]
