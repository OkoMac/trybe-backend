"""WebSocket Connection Manager - Real-time messaging"""

import json
import logging
from typing import Dict, List, Set
from fastapi import WebSocket
import uuid

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time messaging"""

    def __init__(self):
        # Map of user_id -> list of WebSocket connections (users can have multiple devices)
        self.active_connections: Dict[str, List[WebSocket]] = {}

        # Map of user_id -> set of conversation_ids they're currently viewing
        self.user_active_conversations: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: uuid.UUID):
        """
        Connect a user's WebSocket

        Args:
            websocket: The WebSocket connection
            user_id: The user's UUID
        """
        await websocket.accept()
        user_id_str = str(user_id)

        if user_id_str not in self.active_connections:
            self.active_connections[user_id_str] = []

        self.active_connections[user_id_str].append(websocket)

        # Initialize active conversations set
        if user_id_str not in self.user_active_conversations:
            self.user_active_conversations[user_id_str] = set()

        logger.info(f"User {user_id} connected. Total connections: {len(self.active_connections[user_id_str])}")

        # Notify other users that this user is online
        await self.broadcast_user_status(user_id, "online")

    async def disconnect(self, websocket: WebSocket, user_id: uuid.UUID):
        """
        Disconnect a user's WebSocket

        Args:
            websocket: The WebSocket connection
            user_id: The user's UUID
        """
        user_id_str = str(user_id)

        if user_id_str in self.active_connections:
            if websocket in self.active_connections[user_id_str]:
                self.active_connections[user_id_str].remove(websocket)

            # If user has no more connections, remove from dict and notify offline
            if len(self.active_connections[user_id_str]) == 0:
                del self.active_connections[user_id_str]
                if user_id_str in self.user_active_conversations:
                    del self.user_active_conversations[user_id_str]

                logger.info(f"User {user_id} disconnected (all devices)")
                await self.broadcast_user_status(user_id, "offline")
            else:
                logger.info(f"User {user_id} disconnected one device. Remaining: {len(self.active_connections[user_id_str])}")

    def is_user_online(self, user_id: uuid.UUID) -> bool:
        """Check if a user has any active connections"""
        return str(user_id) in self.active_connections

    async def send_personal_message(self, message: dict, user_id: uuid.UUID):
        """
        Send a message to a specific user (all their connected devices)

        Args:
            message: The message dict to send
            user_id: The recipient user's UUID
        """
        user_id_str = str(user_id)

        if user_id_str in self.active_connections:
            message_json = json.dumps(message)

            # Send to all user's connections
            disconnected = []
            for connection in self.active_connections[user_id_str]:
                try:
                    await connection.send_text(message_json)
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    disconnected.append(connection)

            # Clean up disconnected websockets
            for connection in disconnected:
                await self.disconnect(connection, user_id)

    async def send_conversation_message(
        self,
        message: dict,
        conversation_id: uuid.UUID,
        sender_id: uuid.UUID,
        recipient_id: uuid.UUID
    ):
        """
        Send a message in a conversation to both participants

        Args:
            message: The message dict to send
            conversation_id: The conversation UUID
            sender_id: The sender's UUID
            recipient_id: The recipient's UUID
        """
        message_data = {
            "event": "new_message",
            "conversation_id": str(conversation_id),
            "data": message
        }

        # Send to both sender and recipient
        await self.send_personal_message(message_data, sender_id)
        await self.send_personal_message(message_data, recipient_id)

    async def broadcast_typing_indicator(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        recipient_id: uuid.UUID,
        is_typing: bool
    ):
        """
        Broadcast typing indicator to the other participant

        Args:
            conversation_id: The conversation UUID
            user_id: The user who is typing
            recipient_id: The other participant
            is_typing: Whether user is typing
        """
        typing_data = {
            "event": "typing",
            "conversation_id": str(conversation_id),
            "data": {
                "user_id": str(user_id),
                "is_typing": is_typing
            }
        }

        await self.send_personal_message(typing_data, recipient_id)

    async def broadcast_message_read(
        self,
        conversation_id: uuid.UUID,
        message_id: uuid.UUID,
        sender_id: uuid.UUID,
        reader_id: uuid.UUID
    ):
        """
        Notify sender that their message was read

        Args:
            conversation_id: The conversation UUID
            message_id: The message UUID that was read
            sender_id: The original sender to notify
            reader_id: Who read the message
        """
        read_data = {
            "event": "message_read",
            "conversation_id": str(conversation_id),
            "data": {
                "message_id": str(message_id),
                "read_by": str(reader_id)
            }
        }

        await self.send_personal_message(read_data, sender_id)

    async def broadcast_user_status(self, user_id: uuid.UUID, status: str):
        """
        Broadcast user's online/offline status to all connected users

        Args:
            user_id: The user whose status changed
            status: "online" or "offline"
        """
        status_data = {
            "event": f"user_{status}",
            "data": {
                "user_id": str(user_id)
            }
        }

        # Broadcast to all connected users
        for connected_user_id, connections in self.active_connections.items():
            if connected_user_id != str(user_id):  # Don't send to the user themselves
                await self.send_personal_message(status_data, uuid.UUID(connected_user_id))

    def set_user_active_conversation(self, user_id: uuid.UUID, conversation_id: uuid.UUID):
        """Mark that a user is currently viewing a conversation"""
        user_id_str = str(user_id)
        conversation_id_str = str(conversation_id)

        if user_id_str not in self.user_active_conversations:
            self.user_active_conversations[user_id_str] = set()

        self.user_active_conversations[user_id_str].add(conversation_id_str)

    def unset_user_active_conversation(self, user_id: uuid.UUID, conversation_id: uuid.UUID):
        """Mark that a user is no longer viewing a conversation"""
        user_id_str = str(user_id)
        conversation_id_str = str(conversation_id)

        if user_id_str in self.user_active_conversations:
            self.user_active_conversations[user_id_str].discard(conversation_id_str)

    def is_user_viewing_conversation(self, user_id: uuid.UUID, conversation_id: uuid.UUID) -> bool:
        """Check if a user is currently viewing a conversation"""
        user_id_str = str(user_id)
        conversation_id_str = str(conversation_id)

        return (
            user_id_str in self.user_active_conversations and
            conversation_id_str in self.user_active_conversations[user_id_str]
        )


# Global connection manager instance
manager = ConnectionManager()
