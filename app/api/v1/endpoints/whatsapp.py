"""WhatsApp API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
import uuid
import re

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_active_user
from app.models.user import User
from app.services.whatsapp_service import whatsapp_service


router = APIRouter()


# Schemas

class WhatsAppMessageRequest(BaseModel):
    """Schema for sending a WhatsApp message"""
    to_phone: str = Field(..., description="Recipient's phone number with country code (e.g., +1234567890)")
    message: str = Field(..., min_length=1, max_length=1600, description="Message text")

    @validator('to_phone')
    def validate_phone(cls, v):
        # Remove spaces and dashes
        v = v.replace(" ", "").replace("-", "")

        # Check if it's a valid phone format
        if not re.match(r'^\+\d{10,15}$', v):
            raise ValueError('Phone number must be in format +1234567890 (10-15 digits with country code)')

        return v


class WhatsAppTemplateRequest(BaseModel):
    """Schema for sending a WhatsApp template message"""
    to_phone: str = Field(..., description="Recipient's phone number with country code")
    template_name: str = Field(..., description="Pre-approved template name")
    variables: Optional[List[str]] = Field(None, description="Template variables")

    @validator('to_phone')
    def validate_phone(cls, v):
        v = v.replace(" ", "").replace("-", "")
        if not re.match(r'^\+\d{10,15}$', v):
            raise ValueError('Phone number must be in format +1234567890')
        return v


class WhatsAppMediaRequest(BaseModel):
    """Schema for sending a WhatsApp media message"""
    to_phone: str = Field(..., description="Recipient's phone number with country code")
    message: str = Field(..., min_length=1, max_length=1600, description="Message text (caption)")
    media_url: str = Field(..., description="Public URL of the media file")

    @validator('to_phone')
    def validate_phone(cls, v):
        v = v.replace(" ", "").replace("-", "")
        if not re.match(r'^\+\d{10,15}$', v):
            raise ValueError('Phone number must be in format +1234567890')
        return v

    @validator('media_url')
    def validate_media_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Media URL must be a valid HTTP/HTTPS URL')
        return v


class WhatsAppMessageResponse(BaseModel):
    """Schema for WhatsApp message response"""
    success: bool
    message_sid: Optional[str] = None
    status: Optional[str] = None
    to: Optional[str] = None
    sent_at: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[int] = None


class WhatsAppStatusResponse(BaseModel):
    """Schema for WhatsApp message status"""
    success: bool
    message_sid: Optional[str] = None
    status: Optional[str] = None
    to: Optional[str] = None
    date_sent: Optional[str] = None
    date_updated: Optional[str] = None
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    error: Optional[str] = None


class WhatsAppWebhookEvent(BaseModel):
    """Schema for incoming WhatsApp webhook events"""
    MessageSid: str
    From: str
    To: str
    Body: Optional[str] = None
    MediaUrl0: Optional[str] = None
    MediaContentType0: Optional[str] = None
    SmsStatus: Optional[str] = None


# Endpoints

@router.post("/send", response_model=WhatsAppMessageResponse)
async def send_whatsapp_message(
    message_request: WhatsAppMessageRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Send a WhatsApp text message

    - **to_phone**: Recipient's phone number with country code (e.g., +1234567890)
    - **message**: Message text (max 1600 characters)

    Note: You can only send messages to users who have opted in to receive
    WhatsApp messages from your business.
    """
    result = await whatsapp_service.send_text_message(
        to_phone=message_request.to_phone,
        message=message_request.message
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to send WhatsApp message")
        )

    return WhatsAppMessageResponse(**result)


@router.post("/send-template", response_model=WhatsAppMessageResponse)
async def send_whatsapp_template(
    template_request: WhatsAppTemplateRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Send a WhatsApp template message

    Template messages are pre-approved by WhatsApp and can be used to initiate
    conversations outside the 24-hour customer service window.

    - **to_phone**: Recipient's phone number
    - **template_name**: Name of the approved template
    - **variables**: List of variables to substitute in the template

    Example:
    ```json
    {
        "to_phone": "+1234567890",
        "template_name": "welcome_message",
        "variables": ["John", "Trybe"]
    }
    ```
    """
    result = await whatsapp_service.send_template_message(
        to_phone=template_request.to_phone,
        template_name=template_request.template_name,
        variables=template_request.variables
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to send WhatsApp template")
        )

    return WhatsAppMessageResponse(**result)


@router.post("/send-media", response_model=WhatsAppMessageResponse)
async def send_whatsapp_media(
    media_request: WhatsAppMediaRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Send a WhatsApp message with media attachment

    Supported media types:
    - Images: JPEG, PNG
    - Documents: PDF
    - Videos: MP4
    - Audio: MP3, OGG

    - **to_phone**: Recipient's phone number
    - **message**: Caption text for the media
    - **media_url**: Public HTTPS URL of the media file

    Note: The media URL must be publicly accessible and use HTTPS.
    """
    result = await whatsapp_service.send_media_message(
        to_phone=media_request.to_phone,
        message=media_request.message,
        media_url=media_request.media_url
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to send WhatsApp media")
        )

    return WhatsAppMessageResponse(**result)


@router.get("/status/{message_sid}", response_model=WhatsAppStatusResponse)
async def get_whatsapp_message_status(
    message_sid: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the delivery status of a WhatsApp message

    Possible statuses:
    - **queued**: Message is queued for sending
    - **sending**: Message is being sent
    - **sent**: Message has been sent to WhatsApp
    - **delivered**: Message was delivered to recipient
    - **read**: Message was read by recipient
    - **failed**: Message failed to send
    - **undelivered**: Message could not be delivered

    Returns detailed information about the message including timestamps
    and any error information.
    """
    result = await whatsapp_service.get_message_status(message_sid)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error", "Message not found")
        )

    return WhatsAppStatusResponse(**result)


@router.post("/webhook", include_in_schema=False)
async def whatsapp_webhook(
    request: Request,
    x_twilio_signature: Optional[str] = Header(None)
):
    """
    Webhook endpoint for receiving WhatsApp events from Twilio

    This endpoint receives:
    - Incoming messages from users
    - Message status updates (delivered, read, failed)
    - Media messages

    Note: This endpoint validates the Twilio signature for security.
    Configure this URL in your Twilio console:
    https://yourdomain.com/api/v1/whatsapp/webhook
    """
    # Get webhook data
    form_data = await request.form()
    params = dict(form_data)

    # Validate signature
    url = str(request.url)
    if x_twilio_signature:
        is_valid = whatsapp_service.validate_webhook_signature(
            signature=x_twilio_signature,
            url=url,
            params=params
        )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid webhook signature"
            )

    # Process webhook event
    event = WhatsAppWebhookEvent(**params)

    # Log the event
    print(f"WhatsApp webhook received: {event.MessageSid}")
    print(f"From: {event.From}, To: {event.To}")
    print(f"Body: {event.Body}")
    print(f"Status: {event.SmsStatus}")

    # TODO: Implement webhook processing logic
    # - Store incoming messages in database
    # - Update message status
    # - Trigger notifications
    # - Auto-reply logic

    return {"status": "received", "message_sid": event.MessageSid}


# Convenience endpoints for common notifications

@router.post("/notify/opportunity-match")
async def notify_opportunity_match(
    to_phone: str,
    opportunity_title: str,
    opportunity_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send WhatsApp notification for a new opportunity match

    This is a convenience endpoint that sends a pre-formatted message
    about a new opportunity match.
    """
    result = await whatsapp_service.send_opportunity_notification(
        to_phone=to_phone,
        opportunity_title=opportunity_title,
        opportunity_id=opportunity_id,
        user_name=current_user.full_name or current_user.email.split('@')[0]
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to send notification")
        )

    return result


@router.post("/notify/application-accepted")
async def notify_application_accepted(
    to_phone: str,
    opportunity_title: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Send WhatsApp notification when an application is accepted

    This is a convenience endpoint for application acceptance notifications.
    """
    result = await whatsapp_service.send_application_accepted_notification(
        to_phone=to_phone,
        opportunity_title=opportunity_title,
        user_name=current_user.full_name or current_user.email.split('@')[0]
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to send notification")
        )

    return result


@router.post("/notify/new-message")
async def notify_new_message(
    to_phone: str,
    sender_name: str,
    message_preview: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Send WhatsApp notification for a new message

    This is a convenience endpoint for new message notifications.
    """
    result = await whatsapp_service.send_message_notification(
        to_phone=to_phone,
        sender_name=sender_name,
        message_preview=message_preview,
        user_name=current_user.full_name or current_user.email.split('@')[0]
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to send notification")
        )

    return result


@router.post("/notify/payment-received")
async def notify_payment_received(
    to_phone: str,
    amount: float,
    from_user: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Send WhatsApp notification for payment received

    This is a convenience endpoint for payment notifications.
    """
    result = await whatsapp_service.send_payment_received_notification(
        to_phone=to_phone,
        amount=amount,
        from_user=from_user,
        user_name=current_user.full_name or current_user.email.split('@')[0]
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to send notification")
        )

    return result


@router.post("/send-verification-code")
async def send_verification_code(
    to_phone: str,
    code: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Send WhatsApp verification code

    This is a convenience endpoint for sending verification codes.
    """
    result = await whatsapp_service.send_verification_code(
        to_phone=to_phone,
        code=code,
        user_name=current_user.full_name or current_user.email.split('@')[0]
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to send verification code")
        )

    return result
