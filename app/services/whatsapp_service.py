"""WhatsApp Service using Twilio WhatsApp Business API"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

try:
    from twilio.rest import Client
    from twilio.base.exceptions import TwilioRestException
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logging.warning("Twilio SDK not installed. WhatsApp notifications disabled.")

from app.core.config import settings


logger = logging.getLogger(__name__)


class WhatsAppService:
    """
    WhatsApp Business API Service using Twilio

    Supports:
    - Text messages
    - Template messages
    - Media messages (images, documents)
    - Message status tracking
    - Webhook handling for incoming messages
    """

    def __init__(self):
        self.client = None
        self.whatsapp_number = None
        self.initialized = False

        if TWILIO_AVAILABLE:
            self._initialize_twilio()

    def _initialize_twilio(self):
        """Initialize Twilio client"""
        try:
            if not all([
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN,
                settings.TWILIO_WHATSAPP_NUMBER
            ]):
                logger.warning("Twilio WhatsApp credentials not configured. WhatsApp disabled.")
                return

            self.client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            self.whatsapp_number = settings.TWILIO_WHATSAPP_NUMBER
            self.initialized = True
            logger.info("Twilio WhatsApp initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Twilio WhatsApp: {e}")
            self.initialized = False

    def _format_whatsapp_number(self, phone_number: str) -> str:
        """
        Format phone number for WhatsApp

        Args:
            phone_number: Phone number (with or without country code)

        Returns:
            Formatted WhatsApp number (whatsapp:+1234567890)
        """
        # Remove any existing 'whatsapp:' prefix
        phone_number = phone_number.replace("whatsapp:", "")

        # Ensure it starts with '+'
        if not phone_number.startswith("+"):
            phone_number = "+" + phone_number

        return f"whatsapp:{phone_number}"

    async def send_text_message(
        self,
        to_phone: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Send a text message via WhatsApp

        Args:
            to_phone: Recipient's phone number (with country code)
            message: Message text

        Returns:
            Dictionary with success status and message details
        """
        if not self.initialized:
            logger.warning("WhatsApp not initialized. Skipping message.")
            return {
                "success": False,
                "error": "WhatsApp service not configured"
            }

        try:
            to_whatsapp = self._format_whatsapp_number(to_phone)
            from_whatsapp = self._format_whatsapp_number(self.whatsapp_number)

            message_obj = self.client.messages.create(
                body=message,
                from_=from_whatsapp,
                to=to_whatsapp
            )

            logger.info(f"WhatsApp message sent to {to_phone}: {message_obj.sid}")

            return {
                "success": True,
                "message_sid": message_obj.sid,
                "status": message_obj.status,
                "to": to_phone,
                "sent_at": datetime.utcnow().isoformat()
            }

        except TwilioRestException as e:
            logger.error(f"Twilio error sending WhatsApp to {to_phone}: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": e.code if hasattr(e, 'code') else None
            }
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message to {to_phone}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def send_template_message(
        self,
        to_phone: str,
        template_name: str,
        variables: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send a WhatsApp template message (pre-approved by WhatsApp)

        Template messages are required for business-initiated conversations
        outside the 24-hour customer service window.

        Args:
            to_phone: Recipient's phone number
            template_name: Approved template name
            variables: List of variables to insert into template

        Returns:
            Dictionary with success status and message details
        """
        if not self.initialized:
            logger.warning("WhatsApp not initialized. Skipping template message.")
            return {
                "success": False,
                "error": "WhatsApp service not configured"
            }

        try:
            to_whatsapp = self._format_whatsapp_number(to_phone)
            from_whatsapp = self._format_whatsapp_number(self.whatsapp_number)

            # Build template content
            content_sid = f"HX{template_name}"  # Twilio Content SID format

            message_params = {
                "from_": from_whatsapp,
                "to": to_whatsapp,
                "content_sid": content_sid
            }

            if variables:
                # Add template variables
                message_params["content_variables"] = {
                    str(i+1): var for i, var in enumerate(variables)
                }

            message_obj = self.client.messages.create(**message_params)

            logger.info(f"WhatsApp template sent to {to_phone}: {message_obj.sid}")

            return {
                "success": True,
                "message_sid": message_obj.sid,
                "status": message_obj.status,
                "template": template_name,
                "to": to_phone,
                "sent_at": datetime.utcnow().isoformat()
            }

        except TwilioRestException as e:
            logger.error(f"Twilio error sending template to {to_phone}: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": e.code if hasattr(e, 'code') else None
            }
        except Exception as e:
            logger.error(f"Failed to send WhatsApp template to {to_phone}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def send_media_message(
        self,
        to_phone: str,
        message: str,
        media_url: str
    ) -> Dict[str, Any]:
        """
        Send a WhatsApp message with media (image, document, etc.)

        Args:
            to_phone: Recipient's phone number
            message: Message text (caption)
            media_url: Public URL of the media file

        Returns:
            Dictionary with success status and message details
        """
        if not self.initialized:
            logger.warning("WhatsApp not initialized. Skipping media message.")
            return {
                "success": False,
                "error": "WhatsApp service not configured"
            }

        try:
            to_whatsapp = self._format_whatsapp_number(to_phone)
            from_whatsapp = self._format_whatsapp_number(self.whatsapp_number)

            message_obj = self.client.messages.create(
                body=message,
                from_=from_whatsapp,
                to=to_whatsapp,
                media_url=[media_url]
            )

            logger.info(f"WhatsApp media message sent to {to_phone}: {message_obj.sid}")

            return {
                "success": True,
                "message_sid": message_obj.sid,
                "status": message_obj.status,
                "to": to_phone,
                "media_url": media_url,
                "sent_at": datetime.utcnow().isoformat()
            }

        except TwilioRestException as e:
            logger.error(f"Twilio error sending media to {to_phone}: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": e.code if hasattr(e, 'code') else None
            }
        except Exception as e:
            logger.error(f"Failed to send WhatsApp media to {to_phone}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_message_status(self, message_sid: str) -> Dict[str, Any]:
        """
        Get the status of a sent message

        Statuses: queued, sending, sent, delivered, read, failed, undelivered

        Args:
            message_sid: Twilio message SID

        Returns:
            Dictionary with message status details
        """
        if not self.initialized:
            return {
                "success": False,
                "error": "WhatsApp service not configured"
            }

        try:
            message = self.client.messages(message_sid).fetch()

            return {
                "success": True,
                "message_sid": message.sid,
                "status": message.status,
                "to": message.to,
                "from": message.from_,
                "date_sent": message.date_sent.isoformat() if message.date_sent else None,
                "date_updated": message.date_updated.isoformat() if message.date_updated else None,
                "error_code": message.error_code,
                "error_message": message.error_message
            }

        except TwilioRestException as e:
            logger.error(f"Twilio error fetching message status {message_sid}: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": e.code if hasattr(e, 'code') else None
            }
        except Exception as e:
            logger.error(f"Failed to fetch message status {message_sid}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # Convenience methods for common notifications

    async def send_opportunity_notification(
        self,
        to_phone: str,
        opportunity_title: str,
        opportunity_id: str,
        user_name: str
    ) -> Dict[str, Any]:
        """Send WhatsApp notification for new opportunity match"""
        message = (
            f"🎯 New Opportunity Match!\n\n"
            f"Hi {user_name},\n\n"
            f"You have a new opportunity match: *{opportunity_title}*\n\n"
            f"Check it out on Trybe to learn more and apply.\n\n"
            f"Good luck! 🚀"
        )
        return await self.send_text_message(to_phone, message)

    async def send_application_accepted_notification(
        self,
        to_phone: str,
        opportunity_title: str,
        user_name: str
    ) -> Dict[str, Any]:
        """Send WhatsApp notification when application is accepted"""
        message = (
            f"🎉 Congratulations {user_name}!\n\n"
            f"Your application for *{opportunity_title}* has been accepted!\n\n"
            f"The opportunity provider will contact you soon with next steps.\n\n"
            f"Keep up the great work! 💪"
        )
        return await self.send_text_message(to_phone, message)

    async def send_message_notification(
        self,
        to_phone: str,
        sender_name: str,
        message_preview: str,
        user_name: str
    ) -> Dict[str, Any]:
        """Send WhatsApp notification for new message"""
        message = (
            f"💬 New Message on Trybe\n\n"
            f"Hi {user_name},\n\n"
            f"*{sender_name}* sent you a message:\n"
            f'"{message_preview[:100]}..."\n\n'
            f"Reply on Trybe to continue the conversation."
        )
        return await self.send_text_message(to_phone, message)

    async def send_payment_received_notification(
        self,
        to_phone: str,
        amount: float,
        from_user: str,
        user_name: str
    ) -> Dict[str, Any]:
        """Send WhatsApp notification for payment received"""
        message = (
            f"💰 Payment Received\n\n"
            f"Hi {user_name},\n\n"
            f"You received ${amount:.2f} from *{from_user}*\n\n"
            f"The funds are now in your Trybe wallet.\n\n"
            f"Thank you for using Trybe! ✨"
        )
        return await self.send_text_message(to_phone, message)

    async def send_verification_code(
        self,
        to_phone: str,
        code: str,
        user_name: str
    ) -> Dict[str, Any]:
        """Send WhatsApp verification code"""
        message = (
            f"🔐 Trybe Verification Code\n\n"
            f"Hi {user_name},\n\n"
            f"Your verification code is: *{code}*\n\n"
            f"This code will expire in 10 minutes.\n\n"
            f"If you didn't request this code, please ignore this message."
        )
        return await self.send_text_message(to_phone, message)

    def validate_webhook_signature(
        self,
        signature: str,
        url: str,
        params: Dict[str, str]
    ) -> bool:
        """
        Validate Twilio webhook signature for security

        Args:
            signature: X-Twilio-Signature header value
            url: Full URL of the webhook endpoint
            params: POST parameters from the webhook

        Returns:
            True if signature is valid, False otherwise
        """
        if not self.initialized:
            return False

        try:
            from twilio.request_validator import RequestValidator

            validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
            return validator.validate(url, params, signature)

        except Exception as e:
            logger.error(f"Failed to validate webhook signature: {e}")
            return False


# Global instance
whatsapp_service = WhatsAppService()
