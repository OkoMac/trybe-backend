"""
Video Call Service for Trybe Platform
Provides video conferencing capabilities using Twilio Programmable Video
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from twilio.rest import Client
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VideoGrant
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import os

from app.models.user import User

logger = logging.getLogger(__name__)


class VideoCallService:
    """Service for managing video calls using Twilio Programmable Video"""

    def __init__(self):
        """Initialize Twilio client"""
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.api_key = os.getenv("TWILIO_API_KEY")
        self.api_secret = os.getenv("TWILIO_API_SECRET")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")

        if not all([self.account_sid, self.api_key, self.api_secret, self.auth_token]):
            logger.warning("Twilio credentials not fully configured")
            self.client = None
        else:
            self.client = Client(self.account_sid, self.auth_token)

    def _ensure_client(self):
        """Ensure Twilio client is initialized"""
        if not self.client:
            raise ValueError("Twilio client not initialized. Check your credentials.")

    # ==================== Room Management ====================

    async def create_room(
        self,
        room_name: str,
        room_type: str = "group",  # "group", "peer-to-peer", "group-small"
        max_participants: Optional[int] = None,
        record_participants_on_connect: bool = False,
        video_codecs: Optional[List[str]] = None,
        status_callback: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a video room

        Args:
            room_name: Unique name for the room
            room_type: Type of room (group, peer-to-peer, group-small)
            max_participants: Maximum number of participants (default: 50 for group)
            record_participants_on_connect: Auto-record when participants join
            video_codecs: Preferred video codecs (VP8, H264)
            status_callback: Webhook URL for room events

        Returns:
            Dict with room details
        """
        self._ensure_client()

        try:
            # Room type mapping
            type_mapping = {
                "group": "group",
                "peer-to-peer": "peer-to-peer",
                "p2p": "peer-to-peer",
                "group-small": "group-small"
            }
            twilio_room_type = type_mapping.get(room_type.lower(), "group")

            # Create room
            create_params = {
                "unique_name": room_name,
                "type": twilio_room_type
            }

            if max_participants:
                create_params["max_participants"] = max_participants

            if record_participants_on_connect:
                create_params["record_participants_on_connect"] = True

            if video_codecs:
                create_params["video_codecs"] = video_codecs

            if status_callback:
                create_params["status_callback"] = status_callback
                create_params["status_callback_method"] = "POST"

            room = self.client.video.v1.rooms.create(**create_params)

            logger.info(f"Created video room: {room.sid} - {room_name}")

            return {
                "room_sid": room.sid,
                "room_name": room.unique_name,
                "room_type": room.type,
                "status": room.status,
                "max_participants": room.max_participants,
                "duration": room.duration,
                "created_at": room.date_created.isoformat() if room.date_created else None,
                "url": room.url
            }

        except Exception as e:
            logger.error(f"Failed to create room: {str(e)}")
            raise

    async def get_room(self, room_sid: str) -> Dict[str, Any]:
        """Get room details by SID"""
        self._ensure_client()

        try:
            room = self.client.video.v1.rooms(room_sid).fetch()

            return {
                "room_sid": room.sid,
                "room_name": room.unique_name,
                "room_type": room.type,
                "status": room.status,
                "max_participants": room.max_participants,
                "duration": room.duration,
                "created_at": room.date_created.isoformat() if room.date_created else None,
                "ended_at": room.date_updated.isoformat() if room.status == "completed" else None
            }

        except Exception as e:
            logger.error(f"Failed to get room {room_sid}: {str(e)}")
            raise

    async def get_room_by_name(self, room_name: str) -> Optional[Dict[str, Any]]:
        """Get room details by unique name"""
        self._ensure_client()

        try:
            rooms = self.client.video.v1.rooms.list(unique_name=room_name, limit=1)

            if not rooms:
                return None

            room = rooms[0]
            return {
                "room_sid": room.sid,
                "room_name": room.unique_name,
                "room_type": room.type,
                "status": room.status,
                "max_participants": room.max_participants,
                "duration": room.duration,
                "created_at": room.date_created.isoformat() if room.date_created else None
            }

        except Exception as e:
            logger.error(f"Failed to get room by name {room_name}: {str(e)}")
            raise

    async def list_rooms(
        self,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List video rooms

        Args:
            status: Filter by status (in-progress, completed)
            limit: Maximum number of rooms to return

        Returns:
            List of room details
        """
        self._ensure_client()

        try:
            list_params = {"limit": limit}
            if status:
                list_params["status"] = status

            rooms = self.client.video.v1.rooms.list(**list_params)

            return [
                {
                    "room_sid": room.sid,
                    "room_name": room.unique_name,
                    "room_type": room.type,
                    "status": room.status,
                    "duration": room.duration,
                    "created_at": room.date_created.isoformat() if room.date_created else None
                }
                for room in rooms
            ]

        except Exception as e:
            logger.error(f"Failed to list rooms: {str(e)}")
            raise

    async def end_room(self, room_sid: str) -> Dict[str, Any]:
        """
        End a video room

        This will disconnect all participants and mark the room as completed
        """
        self._ensure_client()

        try:
            room = self.client.video.v1.rooms(room_sid).update(status="completed")

            logger.info(f"Ended video room: {room.sid}")

            return {
                "room_sid": room.sid,
                "room_name": room.unique_name,
                "status": room.status,
                "duration": room.duration,
                "message": "Room ended successfully"
            }

        except Exception as e:
            logger.error(f"Failed to end room {room_sid}: {str(e)}")
            raise

    # ==================== Access Tokens ====================

    def generate_access_token(
        self,
        identity: str,
        room_name: str,
        ttl: int = 3600  # 1 hour default
    ) -> str:
        """
        Generate access token for a participant to join a room

        Args:
            identity: Unique identifier for the participant (e.g., user_id)
            room_name: Name of the room to join
            ttl: Token time-to-live in seconds (default: 1 hour)

        Returns:
            JWT access token string
        """
        if not all([self.account_sid, self.api_key, self.api_secret]):
            raise ValueError("Twilio credentials not configured")

        # Create access token
        token = AccessToken(
            self.account_sid,
            self.api_key,
            self.api_secret,
            identity=identity,
            ttl=ttl
        )

        # Create video grant
        video_grant = VideoGrant(room=room_name)

        # Add grant to token
        token.add_grant(video_grant)

        # Generate JWT
        jwt_token = token.to_jwt()

        logger.info(f"Generated access token for {identity} to join {room_name}")

        return jwt_token

    # ==================== Participants ====================

    async def get_participants(self, room_sid: str) -> List[Dict[str, Any]]:
        """
        Get list of participants in a room

        Args:
            room_sid: Room SID

        Returns:
            List of participant details
        """
        self._ensure_client()

        try:
            participants = self.client.video.v1.rooms(room_sid).participants.list()

            return [
                {
                    "participant_sid": p.sid,
                    "identity": p.identity,
                    "status": p.status,
                    "duration": p.duration,
                    "joined_at": p.start_time.isoformat() if p.start_time else None,
                    "left_at": p.end_time.isoformat() if p.end_time else None
                }
                for p in participants
            ]

        except Exception as e:
            logger.error(f"Failed to get participants for room {room_sid}: {str(e)}")
            raise

    async def get_participant(self, room_sid: str, participant_sid: str) -> Dict[str, Any]:
        """Get details of a specific participant"""
        self._ensure_client()

        try:
            participant = self.client.video.v1.rooms(room_sid).participants(participant_sid).fetch()

            return {
                "participant_sid": participant.sid,
                "identity": participant.identity,
                "status": participant.status,
                "duration": participant.duration,
                "joined_at": participant.start_time.isoformat() if participant.start_time else None,
                "left_at": participant.end_time.isoformat() if participant.end_time else None
            }

        except Exception as e:
            logger.error(f"Failed to get participant {participant_sid}: {str(e)}")
            raise

    async def remove_participant(self, room_sid: str, participant_sid: str) -> Dict[str, Any]:
        """
        Remove a participant from a room

        This will disconnect the participant from the video call
        """
        self._ensure_client()

        try:
            participant = self.client.video.v1.rooms(room_sid).participants(participant_sid).update(
                status="disconnected"
            )

            logger.info(f"Removed participant {participant_sid} from room {room_sid}")

            return {
                "participant_sid": participant.sid,
                "identity": participant.identity,
                "status": participant.status,
                "message": "Participant removed successfully"
            }

        except Exception as e:
            logger.error(f"Failed to remove participant {participant_sid}: {str(e)}")
            raise

    # ==================== Recordings ====================

    async def get_recordings(
        self,
        room_sid: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get list of recordings

        Args:
            room_sid: Filter by room SID (optional)
            status: Filter by status (processing, completed, deleted)
            limit: Maximum number of recordings

        Returns:
            List of recording details
        """
        self._ensure_client()

        try:
            list_params = {"limit": limit}

            if room_sid:
                # Get recordings for specific room
                recordings = self.client.video.v1.rooms(room_sid).recordings.list(**list_params)
            else:
                # Get all recordings
                recordings = self.client.video.v1.recordings.list(**list_params)

            return [
                {
                    "recording_sid": rec.sid,
                    "room_sid": rec.room_sid,
                    "status": rec.status,
                    "type": rec.type,
                    "duration": rec.duration,
                    "size": rec.size,
                    "container_format": rec.container_format,
                    "codec": rec.codec,
                    "media_url": rec.media_external_location if hasattr(rec, 'media_external_location') else None,
                    "created_at": rec.date_created.isoformat() if rec.date_created else None
                }
                for rec in recordings
            ]

        except Exception as e:
            logger.error(f"Failed to get recordings: {str(e)}")
            raise

    async def delete_recording(self, recording_sid: str) -> Dict[str, Any]:
        """Delete a recording"""
        self._ensure_client()

        try:
            self.client.video.v1.recordings(recording_sid).delete()

            logger.info(f"Deleted recording: {recording_sid}")

            return {
                "recording_sid": recording_sid,
                "message": "Recording deleted successfully"
            }

        except Exception as e:
            logger.error(f"Failed to delete recording {recording_sid}: {str(e)}")
            raise

    # ==================== Room Composition (Recording Layout) ====================

    async def create_composition(
        self,
        room_sid: str,
        video_layout: Optional[Dict[str, Any]] = None,
        audio_sources: Optional[List[str]] = None,
        resolution: str = "1280x720",
        format: str = "mp4"
    ) -> Dict[str, Any]:
        """
        Create a composition (combined recording) of a room

        Args:
            room_sid: Room SID
            video_layout: Layout configuration for video
            audio_sources: List of audio track SIDs to include
            resolution: Video resolution (e.g., "1280x720", "1920x1080")
            format: Output format (mp4, webm)

        Returns:
            Composition details
        """
        self._ensure_client()

        try:
            create_params = {
                "room_sid": room_sid,
                "resolution": resolution,
                "format": format
            }

            if video_layout:
                create_params["video_layout"] = video_layout

            if audio_sources:
                create_params["audio_sources"] = audio_sources

            composition = self.client.video.v1.compositions.create(**create_params)

            logger.info(f"Created composition: {composition.sid}")

            return {
                "composition_sid": composition.sid,
                "room_sid": composition.room_sid,
                "status": composition.status,
                "duration": composition.duration,
                "resolution": composition.resolution,
                "format": composition.format,
                "size": composition.size,
                "url": composition.url,
                "created_at": composition.date_created.isoformat() if composition.date_created else None
            }

        except Exception as e:
            logger.error(f"Failed to create composition: {str(e)}")
            raise

    # ==================== Helper Methods ====================

    async def create_interview_room(
        self,
        opportunity_id: str,
        interviewer_id: str,
        candidate_id: str,
        scheduled_time: datetime
    ) -> Dict[str, Any]:
        """
        Create a room for an interview session

        Args:
            opportunity_id: Opportunity ID
            interviewer_id: Interviewer user ID
            candidate_id: Candidate user ID
            scheduled_time: Scheduled interview time

        Returns:
            Room details with access tokens for both parties
        """
        # Generate unique room name
        room_name = f"interview_{opportunity_id}_{scheduled_time.strftime('%Y%m%d%H%M')}"

        # Create room
        room = await self.create_room(
            room_name=room_name,
            room_type="peer-to-peer",  # 1-on-1 interview
            max_participants=2,
            record_participants_on_connect=True  # Record interviews
        )

        # Generate access tokens (valid for 2 hours)
        interviewer_token = self.generate_access_token(
            identity=f"interviewer_{interviewer_id}",
            room_name=room_name,
            ttl=7200
        )

        candidate_token = self.generate_access_token(
            identity=f"candidate_{candidate_id}",
            room_name=room_name,
            ttl=7200
        )

        return {
            **room,
            "interviewer_token": interviewer_token,
            "candidate_token": candidate_token,
            "expires_in": 7200
        }

    async def create_group_call_room(
        self,
        room_name: str,
        max_participants: int = 10,
        record: bool = False
    ) -> Dict[str, Any]:
        """
        Create a room for group calls (team meetings, group interviews)

        Args:
            room_name: Unique room name
            max_participants: Maximum participants (default: 10)
            record: Whether to record the session

        Returns:
            Room details
        """
        return await self.create_room(
            room_name=room_name,
            room_type="group-small" if max_participants <= 10 else "group",
            max_participants=max_participants,
            record_participants_on_connect=record
        )

    def generate_room_token(
        self,
        user: User,
        room_name: str,
        duration_hours: int = 1
    ) -> str:
        """
        Generate access token for a user to join a room

        Args:
            user: User object
            room_name: Room name
            duration_hours: Token validity in hours

        Returns:
            Access token
        """
        identity = f"user_{user.id}_{user.username}"
        ttl = duration_hours * 3600

        return self.generate_access_token(
            identity=identity,
            room_name=room_name,
            ttl=ttl
        )

    async def get_room_stats(self, room_sid: str) -> Dict[str, Any]:
        """
        Get comprehensive statistics for a room

        Returns:
            Room stats including participants, duration, recordings, etc.
        """
        room = await self.get_room(room_sid)
        participants = await self.get_participants(room_sid)
        recordings = await self.get_recordings(room_sid=room_sid)

        return {
            "room": room,
            "participants": {
                "total": len(participants),
                "active": len([p for p in participants if p["status"] == "connected"]),
                "list": participants
            },
            "recordings": {
                "total": len(recordings),
                "list": recordings
            }
        }


# Global service instance
video_call_service = VideoCallService()
