"""Notification Service - Helper functions for creating and managing notifications"""

import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.models.notification import Notification, NotificationPreference
from app.models.user import User
from app.core.websocket import manager

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for creating and managing notifications"""

    @staticmethod
    async def create_notification(
        db: AsyncSession,
        user_id: uuid.UUID,
        notification_type: str,
        title: str,
        message: str,
        priority: str = "medium",
        actor_id: Optional[uuid.UUID] = None,
        related_opportunity_id: Optional[uuid.UUID] = None,
        related_match_id: Optional[uuid.UUID] = None,
        related_message_id: Optional[uuid.UUID] = None,
        related_payment_id: Optional[uuid.UUID] = None,
        action_url: Optional[str] = None,
        notification_data: Optional[dict] = None
    ) -> Notification:
        """
        Create a new notification

        Args:
            db: Database session
            user_id: User to notify
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            priority: Priority level (low, medium, high, urgent)
            actor_id: User who triggered the notification
            related_*_id: Related entity IDs for deep linking
            action_url: Frontend URL to navigate to
            notification_data: Additional data

        Returns:
            Created notification
        """
        # Check user preferences
        preferences = await NotificationService.get_user_preferences(db, user_id)

        # Check if user wants this type of notification
        if not NotificationService._should_send_notification(notification_type, preferences):
            logger.info(f"Skipping notification {notification_type} for user {user_id} per preferences")
            return None

        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            priority=priority,
            title=title,
            message=message,
            actor_id=actor_id,
            related_opportunity_id=related_opportunity_id,
            related_match_id=related_match_id,
            related_message_id=related_message_id,
            related_payment_id=related_payment_id,
            action_url=action_url,
            notification_data=notification_data or {}
        )

        db.add(notification)
        await db.commit()
        await db.refresh(notification)

        # Send real-time notification via WebSocket if user is online
        if manager.is_user_online(user_id):
            await manager.send_personal_message(
                {
                    "event": "new_notification",
                    "data": {
                        "id": str(notification.id),
                        "type": notification_type,
                        "title": title,
                        "message": message,
                        "priority": priority,
                        "action_url": action_url,
                        "created_at": notification.created_at.isoformat()
                    }
                },
                user_id
            )

        logger.info(f"Created notification {notification.id} for user {user_id}")
        return notification

    @staticmethod
    async def get_user_preferences(
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> NotificationPreference:
        """Get or create user notification preferences"""
        result = await db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user_id
            )
        )
        preferences = result.scalar_one_or_none()

        if not preferences:
            # Create default preferences
            preferences = NotificationPreference(user_id=user_id)
            db.add(preferences)
            await db.commit()
            await db.refresh(preferences)

        return preferences

    @staticmethod
    def _should_send_notification(
        notification_type: str,
        preferences: NotificationPreference
    ) -> bool:
        """Check if notification should be sent based on user preferences"""
        if not preferences:
            return True  # Send by default if no preferences

        # Map notification types to preference flags
        type_mapping = {
            "new_match": preferences.enable_match_notifications,
            "match_accepted": preferences.enable_match_notifications,
            "new_message": preferences.enable_message_notifications,
            "payment_proposal_received": preferences.enable_payment_notifications,
            "payment_proposal_accepted": preferences.enable_payment_notifications,
            "payment_proposal_rejected": preferences.enable_payment_notifications,
            "payment_proposal_countered": preferences.enable_payment_notifications,
            "payment_received": preferences.enable_payment_notifications,
            "payment_sent": preferences.enable_payment_notifications,
            "opportunity_applied": preferences.enable_opportunity_notifications,
            "opportunity_filled": preferences.enable_opportunity_notifications,
            "opportunity_expiring": preferences.enable_opportunity_notifications,
            "system_announcement": preferences.enable_system_notifications,
            "account_verification": preferences.enable_system_notifications,
            "security_alert": True  # Always send security alerts
        }

        return type_mapping.get(notification_type, True)

    # ========================================================================
    # Specific notification creators for different events
    # ========================================================================

    @staticmethod
    async def notify_new_match(
        db: AsyncSession,
        user_id: uuid.UUID,
        match_id: uuid.UUID,
        opportunity_title: str,
        actor_id: uuid.UUID,
        actor_name: str
    ) -> Notification:
        """Notify user about a new match"""
        return await NotificationService.create_notification(
            db=db,
            user_id=user_id,
            notification_type="new_match",
            title="🎯 New Match!",
            message=f"You matched with {actor_name} for '{opportunity_title}'",
            priority="high",
            actor_id=actor_id,
            related_match_id=match_id,
            action_url=f"/matches/{match_id}"
        )

    @staticmethod
    async def notify_new_message(
        db: AsyncSession,
        user_id: uuid.UUID,
        message_id: uuid.UUID,
        conversation_id: uuid.UUID,
        sender_id: uuid.UUID,
        sender_name: str,
        message_preview: str
    ) -> Notification:
        """Notify user about a new message"""
        return await NotificationService.create_notification(
            db=db,
            user_id=user_id,
            notification_type="new_message",
            title=f"💬 New message from {sender_name}",
            message=message_preview[:100] + "..." if len(message_preview) > 100 else message_preview,
            priority="medium",
            actor_id=sender_id,
            related_message_id=message_id,
            action_url=f"/messages/{conversation_id}",
            notification_data={"conversation_id": str(conversation_id)}
        )

    @staticmethod
    async def notify_payment_proposal_received(
        db: AsyncSession,
        user_id: uuid.UUID,
        proposal_id: uuid.UUID,
        proposer_id: uuid.UUID,
        proposer_name: str,
        amount: float,
        currency: str
    ) -> Notification:
        """Notify user about a new payment proposal"""
        return await NotificationService.create_notification(
            db=db,
            user_id=user_id,
            notification_type="payment_proposal_received",
            title="💰 New Payment Proposal",
            message=f"{proposer_name} sent you a payment proposal for {currency} {amount:,.2f}",
            priority="high",
            actor_id=proposer_id,
            related_payment_id=proposal_id,
            action_url=f"/payments/proposals/{proposal_id}"
        )

    @staticmethod
    async def notify_payment_proposal_accepted(
        db: AsyncSession,
        user_id: uuid.UUID,
        proposal_id: uuid.UUID,
        acceptor_id: uuid.UUID,
        acceptor_name: str,
        amount: float,
        currency: str
    ) -> Notification:
        """Notify user that their payment proposal was accepted"""
        return await NotificationService.create_notification(
            db=db,
            user_id=user_id,
            notification_type="payment_proposal_accepted",
            title="✅ Payment Proposal Accepted",
            message=f"{acceptor_name} accepted your payment proposal of {currency} {amount:,.2f}",
            priority="high",
            actor_id=acceptor_id,
            related_payment_id=proposal_id,
            action_url=f"/payments/proposals/{proposal_id}"
        )

    @staticmethod
    async def notify_payment_proposal_countered(
        db: AsyncSession,
        user_id: uuid.UUID,
        proposal_id: uuid.UUID,
        counter_proposer_id: uuid.UUID,
        counter_proposer_name: str,
        new_amount: float,
        currency: str
    ) -> Notification:
        """Notify user about a counter proposal"""
        return await NotificationService.create_notification(
            db=db,
            user_id=user_id,
            notification_type="payment_proposal_countered",
            title="🔄 Payment Proposal Countered",
            message=f"{counter_proposer_name} countered with {currency} {new_amount:,.2f}",
            priority="high",
            actor_id=counter_proposer_id,
            related_payment_id=proposal_id,
            action_url=f"/payments/proposals/{proposal_id}"
        )

    @staticmethod
    async def notify_system_announcement(
        db: AsyncSession,
        user_id: uuid.UUID,
        title: str,
        message: str,
        action_url: Optional[str] = None
    ) -> Notification:
        """Send a system announcement to a user"""
        return await NotificationService.create_notification(
            db=db,
            user_id=user_id,
            notification_type="system_announcement",
            title=title,
            message=message,
            priority="medium",
            action_url=action_url
        )
