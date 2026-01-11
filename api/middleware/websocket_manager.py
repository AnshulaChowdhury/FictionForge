"""
WebSocket Manager for Epic 10

Manages WebSocket connections for real-time job progress updates, with support for
connection lifecycle, heartbeat, and message broadcasting.
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any
from uuid import UUID
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from collections import defaultdict

from api.models.generation_job import (
    WebSocketMessage,
    JobProgressMessage,
    JobCompletedMessage,
    JobFailedMessage,
    CharacterStatusMessage,
    HeartbeatMessage,
    ConnectedMessage
)

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.

    Supports:
    - Per-user connection tracking
    - Message broadcasting to specific users
    - Heartbeat/ping-pong for connection health
    - Automatic reconnection handling
    """

    def __init__(self):
        # user_id -> Set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = defaultdict(set)

        # WebSocket -> user_id mapping for cleanup
        self.connection_user_map: Dict[WebSocket, str] = {}

        # Heartbeat tasks
        self.heartbeat_tasks: Dict[WebSocket, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, user_id: UUID):
        """
        Accept a new WebSocket connection and register it.

        Args:
            websocket: WebSocket connection
            user_id: User identifier
        """
        await websocket.accept()

        user_id_str = str(user_id)
        self.active_connections[user_id_str].add(websocket)
        self.connection_user_map[websocket] = user_id_str

        logger.info(
            f"WebSocket connected for user {user_id}. "
            f"Total connections for user: {len(self.active_connections[user_id_str])}"
        )

        # Send connection confirmation
        await self.send_personal_message(
            ConnectedMessage(
                user_id=user_id,
                message="Real-time updates active"
            ),
            websocket
        )

        # Start heartbeat task
        heartbeat_task = asyncio.create_task(self._heartbeat_loop(websocket))
        self.heartbeat_tasks[websocket] = heartbeat_task

    async def disconnect(self, websocket: WebSocket):
        """
        Disconnect a WebSocket and clean up resources.

        Args:
            websocket: WebSocket connection to disconnect
        """
        # Cancel heartbeat task
        if websocket in self.heartbeat_tasks:
            self.heartbeat_tasks[websocket].cancel()
            del self.heartbeat_tasks[websocket]

        # Remove from active connections
        if websocket in self.connection_user_map:
            user_id = self.connection_user_map[websocket]

            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)

                # Clean up empty sets
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]

            del self.connection_user_map[websocket]

            logger.info(
                f"WebSocket disconnected for user {user_id}. "
                f"Remaining connections: {len(self.active_connections.get(user_id, []))}"
            )

    async def send_personal_message(self, message: WebSocketMessage, websocket: WebSocket):
        """
        Send a message to a specific WebSocket connection.

        Args:
            message: Message to send
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_json(message.model_dump(mode='json'))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            await self.disconnect(websocket)

    async def broadcast_to_user(self, message: WebSocketMessage, user_id: UUID):
        """
        Broadcast a message to all connections for a specific user.

        Args:
            message: Message to broadcast
            user_id: Target user ID
        """
        user_id_str = str(user_id)

        if user_id_str not in self.active_connections:
            logger.debug(f"No active connections for user {user_id}")
            return

        # Get a copy of the set to avoid modification during iteration
        connections = self.active_connections[user_id_str].copy()

        for connection in connections:
            try:
                await connection.send_json(message.model_dump(mode='json'))
            except Exception as e:
                logger.error(f"Error broadcasting to user {user_id}: {e}")
                await self.disconnect(connection)

    async def broadcast_job_progress(
        self,
        user_id: UUID,
        job_id: UUID,
        status: str,
        stage: Optional[str],
        progress_percentage: int,
        estimated_completion: Optional[datetime] = None,
        time_remaining_seconds: Optional[int] = None
    ):
        """
        Broadcast job progress update to user.

        Args:
            user_id: Target user
            job_id: Job identifier
            status: Job status
            stage: Current processing stage
            progress_percentage: Progress 0-100
            estimated_completion: Estimated completion time
            time_remaining_seconds: Seconds remaining
        """
        message = JobProgressMessage(
            job_id=job_id,
            status=status,
            stage=stage,
            progress_percentage=progress_percentage,
            estimated_completion=estimated_completion,
            time_remaining_seconds=time_remaining_seconds
        )

        await self.broadcast_to_user(message, user_id)

        logger.debug(
            f"Broadcast job progress: job={job_id}, user={user_id}, "
            f"progress={progress_percentage}%"
        )

    async def broadcast_job_completed(
        self,
        user_id: UUID,
        job_id: UUID,
        sub_chapter_id: UUID,
        word_count: int,
        version_id: UUID,
        version_number: int
    ):
        """
        Broadcast job completion notification to user.

        Args:
            user_id: Target user
            job_id: Job identifier
            sub_chapter_id: Generated sub-chapter ID
            word_count: Generated word count
            version_id: Created version ID
            version_number: Created version number
        """
        message = JobCompletedMessage(
            job_id=job_id,
            sub_chapter_id=sub_chapter_id,
            word_count=word_count,
            version_id=version_id,
            version_number=version_number,
            message=f"Content generated! {word_count:,} words",
            action_url=f"/sub-chapters/{sub_chapter_id}"
        )

        await self.broadcast_to_user(message, user_id)

        logger.info(
            f"Broadcast job completion: job={job_id}, user={user_id}, "
            f"words={word_count}"
        )

    async def broadcast_job_failed(
        self,
        user_id: UUID,
        job_id: UUID,
        error_message: str,
        error_type: Optional[str] = None,
        can_retry: bool = True
    ):
        """
        Broadcast job failure notification to user.

        Args:
            user_id: Target user
            job_id: Job identifier
            error_message: Error description
            error_type: Error type/category
            can_retry: Whether job can be retried
        """
        message = JobFailedMessage(
            job_id=job_id,
            error_message=error_message,
            error_type=error_type,
            can_retry=can_retry,
            message=f"Generation failed: {error_message}",
            action_url=f"/jobs/{job_id}/retry" if can_retry else None
        )

        await self.broadcast_to_user(message, user_id)

        logger.warning(
            f"Broadcast job failure: job={job_id}, user={user_id}, "
            f"error={error_message}"
        )

    async def broadcast_character_status(
        self,
        user_id: UUID,
        character_id: UUID,
        status: str,
        collection_name: Optional[str] = None,
        embedding_count: Optional[int] = None,
        can_generate: bool = False
    ):
        """
        Broadcast character vector store status update to user.

        Args:
            user_id: Target user
            character_id: Character identifier
            status: Vector store status
            collection_name: ChromaDB collection name
            embedding_count: Number of embeddings
            can_generate: Whether content generation is available
        """
        message = CharacterStatusMessage(
            character_id=character_id,
            status=status,
            collection_name=collection_name,
            embedding_count=embedding_count,
            can_generate=can_generate
        )

        await self.broadcast_to_user(message, user_id)

        logger.debug(
            f"Broadcast character status: character={character_id}, "
            f"user={user_id}, status={status}"
        )

    def is_user_connected(self, user_id: UUID) -> bool:
        """
        Check if user has any active WebSocket connections.

        Args:
            user_id: User identifier

        Returns:
            True if user has active connections, False otherwise
        """
        user_id_str = str(user_id)
        return user_id_str in self.active_connections and len(self.active_connections[user_id_str]) > 0

    def get_connection_count(self, user_id: Optional[UUID] = None) -> int:
        """
        Get connection count.

        Args:
            user_id: If provided, get count for specific user. Otherwise total.

        Returns:
            Number of active connections
        """
        if user_id:
            user_id_str = str(user_id)
            return len(self.active_connections.get(user_id_str, set()))

        return sum(len(conns) for conns in self.active_connections.values())

    async def _heartbeat_loop(self, websocket: WebSocket):
        """
        Send periodic heartbeat messages to keep connection alive.

        Args:
            websocket: WebSocket connection
        """
        try:
            while True:
                await asyncio.sleep(30)  # Heartbeat every 30 seconds

                try:
                    await websocket.send_json(
                        HeartbeatMessage().model_dump(mode='json')
                    )
                except Exception as e:
                    logger.error(f"Heartbeat failed: {e}")
                    break

        except asyncio.CancelledError:
            logger.debug("Heartbeat task cancelled")
        except Exception as e:
            logger.error(f"Error in heartbeat loop: {e}")


# Global connection manager instance
manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """
    Get the global ConnectionManager instance.

    Returns:
        ConnectionManager instance
    """
    return manager
