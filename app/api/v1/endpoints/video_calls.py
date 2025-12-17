"""
Video Call API Endpoints
Provides video conferencing capabilities for interviews and meetings
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.services.video_call_service import video_call_service

router = APIRouter()


# ==================== Schemas ====================

class CreateRoomRequest(BaseModel):
    """Request schema for creating a video room"""
    room_name: str = Field(..., description="Unique room name", min_length=1, max_length=100)
    room_type: str = Field("group", description="Room type: group, peer-to-peer, group-small")
    max_participants: Optional[int] = Field(None, description="Maximum participants (default: 50)")
    record: bool = Field(False, description="Record participants on connect")
    video_codecs: Optional[List[str]] = Field(None, description="Preferred video codecs (VP8, H264)")


class CreateInterviewRoomRequest(BaseModel):
    """Request schema for creating an interview room"""
    opportunity_id: str = Field(..., description="Opportunity ID")
    candidate_id: str = Field(..., description="Candidate user ID")
    scheduled_time: datetime = Field(..., description="Scheduled interview time")


class JoinRoomRequest(BaseModel):
    """Request schema for joining a room"""
    room_name: str = Field(..., description="Room name to join")
    duration_hours: int = Field(1, ge=1, le=24, description="Token validity in hours")


class RoomResponse(BaseModel):
    """Response schema for room details"""
    room_sid: str
    room_name: str
    room_type: str
    status: str
    max_participants: Optional[int]
    duration: Optional[int]
    created_at: Optional[str]
    ended_at: Optional[str] = None


class AccessTokenResponse(BaseModel):
    """Response schema for access token"""
    token: str
    room_name: str
    identity: str
    expires_in: int
    room_sid: Optional[str] = None


class ParticipantResponse(BaseModel):
    """Response schema for participant details"""
    participant_sid: str
    identity: str
    status: str
    duration: Optional[int]
    joined_at: Optional[str]
    left_at: Optional[str] = None


class RecordingResponse(BaseModel):
    """Response schema for recording details"""
    recording_sid: str
    room_sid: str
    status: str
    type: str
    duration: Optional[int]
    size: Optional[int]
    container_format: Optional[str]
    codec: Optional[str]
    media_url: Optional[str]
    created_at: Optional[str]


class InterviewRoomResponse(BaseModel):
    """Response schema for interview room"""
    room_sid: str
    room_name: str
    room_type: str
    status: str
    interviewer_token: str
    candidate_token: str
    expires_in: int
    created_at: Optional[str]


# ==================== Room Management Endpoints ====================

@router.post("/rooms", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    request: CreateRoomRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new video room

    Room types:
    - **group**: Large group calls (up to 50 participants)
    - **group-small**: Small group calls (up to 10 participants, better quality)
    - **peer-to-peer**: 1-on-1 calls (2 participants max, best quality)

    Features:
    - Optional recording
    - Configurable max participants
    - Video codec selection (VP8, H264)
    - Automatic room management

    Example:
    ```json
    {
      "room_name": "team_standup_20240115",
      "room_type": "group-small",
      "max_participants": 10,
      "record": true
    }
    ```
    """
    try:
        room = await video_call_service.create_room(
            room_name=request.room_name,
            room_type=request.room_type,
            max_participants=request.max_participants,
            record_participants_on_connect=request.record,
            video_codecs=request.video_codecs
        )

        return RoomResponse(**room)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create room: {str(e)}"
        )


@router.get("/rooms/{room_sid}", response_model=RoomResponse)
async def get_room(
    room_sid: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get details of a specific room by SID

    Returns:
    - Room metadata
    - Current status
    - Duration
    - Participant count limits
    """
    try:
        room = await video_call_service.get_room(room_sid)

        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Room not found: {room_sid}"
            )

        return RoomResponse(**room)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get room: {str(e)}"
        )


@router.get("/rooms/name/{room_name}", response_model=RoomResponse)
async def get_room_by_name(
    room_name: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get room details by unique room name

    Useful when you know the room name but not the SID
    """
    try:
        room = await video_call_service.get_room_by_name(room_name)

        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Room not found: {room_name}"
            )

        return RoomResponse(**room)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get room: {str(e)}"
        )


@router.get("/rooms", response_model=List[RoomResponse])
async def list_rooms(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
    current_user: User = Depends(get_current_active_user)
):
    """
    List video rooms

    Filters:
    - **status**: in-progress, completed
    - **limit**: Maximum number of results (1-100)

    Returns:
    - List of rooms with metadata
    """
    try:
        rooms = await video_call_service.list_rooms(
            status=status_filter,
            limit=limit
        )

        return [RoomResponse(**room) for room in rooms]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list rooms: {str(e)}"
        )


@router.delete("/rooms/{room_sid}", status_code=status.HTTP_200_OK)
async def end_room(
    room_sid: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    End a video room

    Actions:
    - Disconnects all participants
    - Marks room as completed
    - Finalizes any recordings

    Note: This cannot be undone
    """
    try:
        result = await video_call_service.end_room(room_sid)
        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end room: {str(e)}"
        )


# ==================== Access Token Endpoints ====================

@router.post("/rooms/join", response_model=AccessTokenResponse)
async def join_room(
    request: JoinRoomRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Join a video room (get access token)

    Returns an access token that allows the user to connect to the video room.
    This token should be used on the client side to initialize the Twilio Video SDK.

    The token is valid for the specified duration (default: 1 hour).

    Example response:
    ```json
    {
      "token": "eyJhbGci...",
      "room_name": "interview_123",
      "identity": "user_456_john",
      "expires_in": 3600
    }
    ```

    Client-side usage (JavaScript):
    ```javascript
    const { connect } = require('twilio-video');

    const room = await connect(token, {
      name: roomName,
      audio: true,
      video: { width: 640 }
    });
    ```
    """
    try:
        # Generate access token
        token = video_call_service.generate_room_token(
            user=current_user,
            room_name=request.room_name,
            duration_hours=request.duration_hours
        )

        # Get room details if exists
        room = await video_call_service.get_room_by_name(request.room_name)

        identity = f"user_{current_user.id}_{current_user.username}"

        return AccessTokenResponse(
            token=token,
            room_name=request.room_name,
            identity=identity,
            expires_in=request.duration_hours * 3600,
            room_sid=room["room_sid"] if room else None
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate access token: {str(e)}"
        )


@router.post("/rooms/{room_sid}/token", response_model=AccessTokenResponse)
async def get_room_token(
    room_sid: str,
    duration_hours: int = Query(1, ge=1, le=24),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get access token for a specific room by SID

    Alternative to /rooms/join when you have the room SID
    """
    try:
        # Get room details
        room = await video_call_service.get_room(room_sid)

        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Room not found: {room_sid}"
            )

        # Generate token
        token = video_call_service.generate_room_token(
            user=current_user,
            room_name=room["room_name"],
            duration_hours=duration_hours
        )

        identity = f"user_{current_user.id}_{current_user.username}"

        return AccessTokenResponse(
            token=token,
            room_name=room["room_name"],
            identity=identity,
            expires_in=duration_hours * 3600,
            room_sid=room_sid
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate token: {str(e)}"
        )


# ==================== Participant Management ====================

@router.get("/rooms/{room_sid}/participants", response_model=List[ParticipantResponse])
async def get_participants(
    room_sid: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get list of participants in a room

    Returns:
    - Active participants
    - Historical participants (who left)
    - Join/leave times
    - Duration of participation
    """
    try:
        participants = await video_call_service.get_participants(room_sid)
        return [ParticipantResponse(**p) for p in participants]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get participants: {str(e)}"
        )


@router.get("/rooms/{room_sid}/participants/{participant_sid}", response_model=ParticipantResponse)
async def get_participant(
    room_sid: str,
    participant_sid: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get details of a specific participant"""
    try:
        participant = await video_call_service.get_participant(room_sid, participant_sid)
        return ParticipantResponse(**participant)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get participant: {str(e)}"
        )


@router.delete("/rooms/{room_sid}/participants/{participant_sid}")
async def remove_participant(
    room_sid: str,
    participant_sid: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Remove a participant from a room

    Use cases:
    - Moderator removing disruptive participant
    - Ending someone's access to the call
    - Managing room capacity

    Note: Only room owners or admins should have access to this endpoint
    """
    # TODO: Add authorization check (only room owner or admin)
    try:
        result = await video_call_service.remove_participant(room_sid, participant_sid)
        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove participant: {str(e)}"
        )


# ==================== Recording Endpoints ====================

@router.get("/recordings", response_model=List[RecordingResponse])
async def list_recordings(
    room_sid: Optional[str] = Query(None, description="Filter by room SID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """
    List video recordings

    Filters:
    - **room_sid**: Get recordings for a specific room
    - **status**: processing, completed, deleted
    - **limit**: Maximum results (1-100)

    Recordings are automatically created when:
    - Room is created with record=True
    - Recording is started manually during a call
    """
    try:
        recordings = await video_call_service.get_recordings(
            room_sid=room_sid,
            status=status_filter,
            limit=limit
        )

        return [RecordingResponse(**rec) for rec in recordings]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recordings: {str(e)}"
        )


@router.delete("/recordings/{recording_sid}")
async def delete_recording(
    recording_sid: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a recording

    Warning: This permanently deletes the recording and cannot be undone.

    Use cases:
    - GDPR compliance (right to be forgotten)
    - Storage management
    - Removing sensitive content
    """
    # TODO: Add authorization check (only recording owner or admin)
    try:
        result = await video_call_service.delete_recording(recording_sid)
        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete recording: {str(e)}"
        )


# ==================== Interview-Specific Endpoints ====================

@router.post("/interviews", response_model=InterviewRoomResponse, status_code=status.HTTP_201_CREATED)
async def create_interview_room(
    request: CreateInterviewRoomRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a dedicated interview room

    Creates a 1-on-1 video room specifically for interviews with:
    - Peer-to-peer connection (best quality)
    - Automatic recording
    - Pre-generated access tokens for both parties
    - 2-hour validity

    Returns:
    - Room details
    - Interviewer access token
    - Candidate access token

    Usage:
    1. Interviewer receives `interviewer_token`
    2. Candidate receives `candidate_token`
    3. Both parties use their tokens to connect to the same room
    4. Session is automatically recorded

    Example:
    ```json
    {
      "opportunity_id": "uuid-here",
      "candidate_id": "candidate-uuid",
      "scheduled_time": "2024-01-15T14:00:00Z"
    }
    ```
    """
    try:
        # Verify the current user is authorized (interviewer or admin)
        # TODO: Add proper authorization logic

        room = await video_call_service.create_interview_room(
            opportunity_id=request.opportunity_id,
            interviewer_id=str(current_user.id),
            candidate_id=request.candidate_id,
            scheduled_time=request.scheduled_time
        )

        return InterviewRoomResponse(**room)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create interview room: {str(e)}"
        )


@router.post("/group-calls", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_group_call(
    room_name: str = Body(..., embed=True),
    max_participants: int = Body(10, embed=True, ge=2, le=50),
    record: bool = Body(False, embed=True),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a group call room

    Optimized for:
    - Team meetings
    - Group interviews
    - Panel discussions
    - Collaborative sessions

    Features:
    - Configurable participant limit (2-50)
    - Optional recording
    - Optimized video quality based on participant count
      - 2-10 participants: group-small (better quality)
      - 11+ participants: group (optimized for scale)
    """
    try:
        room = await video_call_service.create_group_call_room(
            room_name=room_name,
            max_participants=max_participants,
            record=record
        )

        return RoomResponse(**room)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create group call: {str(e)}"
        )


# ==================== Statistics & Analytics ====================

@router.get("/rooms/{room_sid}/stats")
async def get_room_stats(
    room_sid: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get comprehensive statistics for a room

    Returns:
    - Room metadata
    - Participant statistics (total, active, list)
    - Recording information
    - Duration and usage metrics

    Useful for:
    - Analytics dashboards
    - Billing and usage tracking
    - Quality monitoring
    - Attendance tracking
    """
    try:
        stats = await video_call_service.get_room_stats(room_sid)
        return stats

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get room stats: {str(e)}"
        )


# ==================== Health Check ====================

@router.get("/health")
async def video_health_check():
    """
    Check video service health

    Returns:
    - Service status
    - Twilio connection status
    - Configuration status
    """
    try:
        # Check if Twilio client is initialized
        is_configured = video_call_service.client is not None

        return {
            "status": "healthy" if is_configured else "not_configured",
            "service": "Twilio Programmable Video",
            "configured": is_configured,
            "message": "Video call service is ready" if is_configured else "Twilio credentials not configured"
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
