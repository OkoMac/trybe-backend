"""Push Notification Service using Firebase Cloud Messaging (FCM)"""

import logging
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import json
import uuid

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logging.warning("Firebase Admin SDK not installed. Push notifications disabled.")

from app.core.config import settings


logger = logging.getLogger(__name__)


class PushNotificationService:
    """
    Push Notification Service for sending notifications to mobile devices

    Supports:
    - Firebase Cloud Messaging (FCM)
    - Topic-based notifications
    - Token-based notifications
    - Batch notifications
    - Notification analytics
    """

    def __init__(self):
        self.firebase_initialized = False

        if FIREBASE_AVAILABLE:
            self._initialize_firebase()

    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            # Check if already initialized
            if firebase_admin._apps:
                self.firebase_initialized = True
                logger.info("Firebase already initialized")
                return

            # Initialize Firebase with service account
            if hasattr(settings, 'FIREBASE_CREDENTIALS_PATH') and settings.FIREBASE_CREDENTIALS_PATH:
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                firebase_admin.initialize_app(cred)
                self.firebase_initialized = True
                logger.info("Firebase initialized successfully")
            elif hasattr(settings, 'FIREBASE_CREDENTIALS_JSON') and settings.FIREBASE_CREDENTIALS_JSON:
                # Initialize from JSON string (environment variable)
                cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                self.firebase_initialized = True
                logger.info("Firebase initialized from JSON credentials")
            else:
                logger.warning("Firebase credentials not configured. Push notifications disabled.")

        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            self.firebase_initialized = False

    async def send_notification(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None,
        click_action: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Send push notification to a single device

        Args:
            token: FCM device token
            title: Notification title
            body: Notification body
            data: Additional data payload
            image_url: Optional image URL
            click_action: Optional deep link or action

        Returns:
            Tuple of (success, message_id_or_error)
        """
        if not self.firebase_initialized:
            logger.warning("Firebase not initialized. Skipping notification.")
            return False, "Firebase not configured"

        try:
            # Build notification
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url if image_url else None
            )

            # Build Android config
            android_config = messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    click_action=click_action if click_action else None,
                    sound='default',
                    channel_id='trybe_notifications'
                )
            )

            # Build iOS config
            apns_config = messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound='default',
                        badge=1,
                        category=click_action if click_action else None
                    )
                )
            )

            # Build message
            message = messaging.Message(
                token=token,
                notification=notification,
                data=data if data else {},
                android=android_config,
                apns=apns_config
            )

            # Send message
            response = messaging.send(message)

            logger.info(f"Successfully sent notification to {token}: {response}")
            return True, response

        except Exception as e:
            logger.error(f"Failed to send notification to {token}: {e}")
            return False, str(e)

    async def send_batch_notifications(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send push notifications to multiple devices

        Args:
            tokens: List of FCM device tokens
            title: Notification title
            body: Notification body
            data: Additional data payload
            image_url: Optional image URL

        Returns:
            Dictionary with success/failure counts and details
        """
        if not self.firebase_initialized:
            logger.warning("Firebase not initialized. Skipping batch notification.")
            return {
                "success_count": 0,
                "failure_count": len(tokens),
                "results": []
            }

        if not tokens:
            return {
                "success_count": 0,
                "failure_count": 0,
                "results": []
            }

        try:
            # Build messages
            messages = []
            for token in tokens:
                notification = messaging.Notification(
                    title=title,
                    body=body,
                    image=image_url if image_url else None
                )

                message = messaging.Message(
                    token=token,
                    notification=notification,
                    data=data if data else {}
                )
                messages.append(message)

            # Send batch
            response = messaging.send_each(messages)

            logger.info(
                f"Batch notification sent: "
                f"{response.success_count} success, "
                f"{response.failure_count} failures"
            )

            return {
                "success_count": response.success_count,
                "failure_count": response.failure_count,
                "results": [
                    {
                        "success": r.success,
                        "message_id": r.message_id if r.success else None,
                        "error": str(r.exception) if r.exception else None
                    }
                    for r in response.responses
                ]
            }

        except Exception as e:
            logger.error(f"Failed to send batch notifications: {e}")
            return {
                "success_count": 0,
                "failure_count": len(tokens),
                "error": str(e),
                "results": []
            }

    async def send_topic_notification(
        self,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Send push notification to a topic (group of devices)

        Topics examples:
        - "all_users"
        - "new_opportunities"
        - "hackathon_updates"

        Args:
            topic: Topic name (subscribers receive the notification)
            title: Notification title
            body: Notification body
            data: Additional data payload
            image_url: Optional image URL

        Returns:
            Tuple of (success, message_id_or_error)
        """
        if not self.firebase_initialized:
            logger.warning("Firebase not initialized. Skipping topic notification.")
            return False, "Firebase not configured"

        try:
            # Build notification
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url if image_url else None
            )

            # Build message
            message = messaging.Message(
                topic=topic,
                notification=notification,
                data=data if data else {}
            )

            # Send message
            response = messaging.send(message)

            logger.info(f"Successfully sent notification to topic {topic}: {response}")
            return True, response

        except Exception as e:
            logger.error(f"Failed to send notification to topic {topic}: {e}")
            return False, str(e)

    async def subscribe_to_topic(
        self,
        tokens: List[str],
        topic: str
    ) -> Dict[str, int]:
        """
        Subscribe devices to a topic

        Args:
            tokens: List of FCM device tokens
            topic: Topic name

        Returns:
            Dictionary with success/failure counts
        """
        if not self.firebase_initialized:
            logger.warning("Firebase not initialized. Skipping topic subscription.")
            return {"success_count": 0, "failure_count": len(tokens)}

        try:
            response = messaging.subscribe_to_topic(tokens, topic)

            logger.info(
                f"Topic subscription: {response.success_count} success, "
                f"{response.failure_count} failures for topic '{topic}'"
            )

            return {
                "success_count": response.success_count,
                "failure_count": response.failure_count
            }

        except Exception as e:
            logger.error(f"Failed to subscribe to topic {topic}: {e}")
            return {"success_count": 0, "failure_count": len(tokens), "error": str(e)}

    async def unsubscribe_from_topic(
        self,
        tokens: List[str],
        topic: str
    ) -> Dict[str, int]:
        """
        Unsubscribe devices from a topic

        Args:
            tokens: List of FCM device tokens
            topic: Topic name

        Returns:
            Dictionary with success/failure counts
        """
        if not self.firebase_initialized:
            logger.warning("Firebase not initialized. Skipping topic unsubscription.")
            return {"success_count": 0, "failure_count": len(tokens)}

        try:
            response = messaging.unsubscribe_from_topic(tokens, topic)

            logger.info(
                f"Topic unsubscription: {response.success_count} success, "
                f"{response.failure_count} failures for topic '{topic}'"
            )

            return {
                "success_count": response.success_count,
                "failure_count": response.failure_count
            }

        except Exception as e:
            logger.error(f"Failed to unsubscribe from topic {topic}: {e}")
            return {"success_count": 0, "failure_count": len(tokens), "error": str(e)}

    # Convenience methods for common notifications

    async def send_new_opportunity_notification(
        self,
        token: str,
        opportunity_title: str,
        opportunity_id: str
    ) -> Tuple[bool, Optional[str]]:
        """Send notification for new opportunity match"""
        return await self.send_notification(
            token=token,
            title="New Opportunity Match!",
            body=f"Check out: {opportunity_title}",
            data={
                "type": "new_opportunity",
                "opportunity_id": opportunity_id,
                "click_action": f"/opportunities/{opportunity_id}"
            },
            click_action=f"OPEN_OPPORTUNITY_{opportunity_id}"
        )

    async def send_message_notification(
        self,
        token: str,
        sender_name: str,
        message_preview: str,
        conversation_id: str
    ) -> Tuple[bool, Optional[str]]:
        """Send notification for new message"""
        return await self.send_notification(
            token=token,
            title=f"New message from {sender_name}",
            body=message_preview[:100],
            data={
                "type": "new_message",
                "conversation_id": conversation_id,
                "click_action": f"/messages/{conversation_id}"
            },
            click_action=f"OPEN_CONVERSATION_{conversation_id}"
        )

    async def send_application_status_notification(
        self,
        token: str,
        opportunity_title: str,
        status: str,
        opportunity_id: str
    ) -> Tuple[bool, Optional[str]]:
        """Send notification for application status change"""
        status_messages = {
            "accepted": f"Congratulations! Your application for {opportunity_title} was accepted!",
            "rejected": f"Your application for {opportunity_title} was not accepted this time.",
            "review": f"Your application for {opportunity_title} is under review."
        }

        return await self.send_notification(
            token=token,
            title="Application Update",
            body=status_messages.get(status, f"Application status: {status}"),
            data={
                "type": "application_status",
                "opportunity_id": opportunity_id,
                "status": status,
                "click_action": f"/opportunities/{opportunity_id}"
            },
            click_action=f"OPEN_OPPORTUNITY_{opportunity_id}"
        )

    async def send_payment_notification(
        self,
        token: str,
        amount: float,
        payment_type: str,
        payment_id: str
    ) -> Tuple[bool, Optional[str]]:
        """Send notification for payment events"""
        payment_messages = {
            "received": f"You received ${amount:.2f}",
            "sent": f"Payment of ${amount:.2f} sent successfully",
            "pending": f"Payment of ${amount:.2f} is pending"
        }

        return await self.send_notification(
            token=token,
            title="Payment Update",
            body=payment_messages.get(payment_type, f"Payment: ${amount:.2f}"),
            data={
                "type": "payment",
                "payment_id": payment_id,
                "amount": str(amount),
                "payment_type": payment_type,
                "click_action": f"/payments/{payment_id}"
            },
            click_action=f"OPEN_PAYMENT_{payment_id}"
        )

    async def send_review_notification(
        self,
        token: str,
        reviewer_name: str,
        rating: int,
        review_id: str
    ) -> Tuple[bool, Optional[str]]:
        """Send notification for new review"""
        stars = "⭐" * rating

        return await self.send_notification(
            token=token,
            title="New Review",
            body=f"{reviewer_name} left you a {rating}-star review {stars}",
            data={
                "type": "new_review",
                "review_id": review_id,
                "rating": str(rating),
                "click_action": f"/reviews/{review_id}"
            },
            click_action=f"OPEN_REVIEW_{review_id}"
        )


# Global instance
push_notification_service = PushNotificationService()
