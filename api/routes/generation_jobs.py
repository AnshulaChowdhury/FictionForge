"""
Generation Jobs API Routes for Epic 10

Provides endpoints for:
- Querying active and historical generation jobs
- Polling job status for long-running tasks
- Cancelling pending/in-progress jobs
- Managing user notification preferences
- Checking character vector store status
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse

from api.middleware.auth import get_current_user_id
from api.models.generation_job import (
    GenerationJobResponse,
    GenerationJobListResponse,
    GenerationJobStatusResponse,
    CancelJobResponse,
    NotificationPreferences,
    NotificationPreferencesUpdate,
    CharacterVectorStoreStatus,
    CharacterVectorStatus
)
from api.services.generation_job_manager import GenerationJobManager
from api.middleware.websocket_manager import get_connection_manager

router = APIRouter(prefix="/api/generation-jobs", tags=["generation-jobs"])


# ============================================================================
# Job Query Endpoints
# ============================================================================


@router.get("", response_model=GenerationJobListResponse)
async def get_generation_jobs(
    status: Optional[str] = Query(
        default=None,
        description="Filter by status: queued, in_progress, completed, failed, cancelled"
    ),
    limit: int = Query(default=50, ge=1, le=100),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get generation jobs for current user with optional status filtering.

    **Query Parameters:**
    - `status`: Filter by job status (optional). If not provided, returns ALL jobs.
      Valid values: queued, in_progress, completed, failed, cancelled
    - `limit`: Maximum number of jobs to return (default: 50)

    **Returns:**
    - List of jobs with enriched data (sub-chapter title, character name, etc.)
    - Cached flag and TTL for cache transparency
    - Total count of matching jobs
    - Jobs ordered by created_at DESC (newest first)

    **Caching:**
    - Results cached in Redis for 30 seconds when fetching all/active jobs
    - No caching for specific status queries
    - Cache automatically invalidated on job status changes
    """
    try:
        manager = GenerationJobManager()
        user_id_uuid = UUID(user_id)

        # Fetch jobs with optional status filter
        # If status is None, returns ALL jobs (active, completed, failed, cancelled)
        jobs = await manager.get_jobs(user_id_uuid, status=status, limit=limit)

        return GenerationJobListResponse(
            jobs=jobs,
            total_count=len(jobs),
            cached=False,  # TODO: Detect if from cache
            cache_ttl_seconds=30 if not status or status in ["queued", "in_progress"] else 0
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching generation jobs: {str(e)}"
        )


@router.get("/{job_id}", response_model=GenerationJobResponse)
async def get_generation_job(
    job_id: UUID,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get details of a specific generation job.

    **Returns:**
    - Complete job details including progress, status, and timing information
    - Calculated time remaining based on estimated completion

    **HTTP Status Codes:**
    - 200: Job found and returned
    - 404: Job not found
    - 500: Server error
    """
    try:
        manager = GenerationJobManager()
        user_id_uuid = UUID(user_id)

        job = await manager.get_job(job_id, user_id_uuid)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Generation job {job_id} not found"
            )

        return job

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching job: {str(e)}"
        )


# ============================================================================
# Job Status Polling (202 Accepted Pattern)
# ============================================================================


@router.get("/{job_id}/status", response_class=JSONResponse)
async def get_job_status(
    job_id: UUID,
    user_id: str = Depends(get_current_user_id)
):
    """
    Poll job status for long-running tasks (Epic 10 Story 2).

    **HTTP Status Codes:**
    - **202 Accepted**: Job still processing (continue polling)
    - **200 OK**: Job completed successfully
    - **500 Internal Server Error**: Job failed

    **Polling Strategy:**
    - Poll every 5 seconds for jobs in progress
    - WebSocket provides faster updates (<5s) when available
    - Use this endpoint as fallback when WebSocket disconnected

    **202 Accepted Response:**
    ```json
    {
      "job_id": "uuid",
      "status": "in_progress",
      "stage": "Generating content",
      "progress_percentage": 75,
      "estimated_completion": "2025-11-03T10:32:00Z",
      "poll_after_seconds": 5,
      "message": "Generation in progress"
    }
    ```

    **200 OK Response:**
    ```json
    {
      "job_id": "uuid",
      "status": "completed",
      "result": {
        "sub_chapter_id": "uuid",
        "word_count": 1987,
        "version_id": "uuid"
      },
      "completed_at": "2025-11-03T10:35:12Z"
    }
    ```
    """
    try:
        manager = GenerationJobManager()
        user_id_uuid = UUID(user_id)

        job = await manager.get_job(job_id, user_id_uuid)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        # Job still in progress -> 202 Accepted
        if job.status in ["queued", "in_progress"]:
            response = GenerationJobStatusResponse(
                job_id=job.id,
                status=job.status,
                stage=job.stage,
                progress_percentage=job.progress_percentage,
                estimated_completion=job.estimated_completion,
                poll_after_seconds=5,
                message="Generation in progress"
            )
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content=response.model_dump(mode='json')
            )

        # Job completed -> 200 OK
        elif job.status == "completed":
            response = GenerationJobStatusResponse(
                job_id=job.id,
                status=job.status,
                progress_percentage=100,
                result={
                    "sub_chapter_id": str(job.sub_chapter_id),
                    "word_count": job.word_count,
                    "version_id": str(job.version_id) if job.version_id else None,
                    "version_number": job.version_number
                },
                completed_at=job.completed_at,
                message="Generation completed successfully"
            )
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=response.model_dump(mode='json')
            )

        # Job failed -> 500 Internal Server Error
        elif job.status == "failed":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=job.error_message or "Generation failed"
            )

        # Job cancelled -> 409 Conflict
        elif job.status == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Job was cancelled"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking job status: {str(e)}"
        )


# ============================================================================
# Job Cancellation
# ============================================================================


@router.post("/{job_id}/cancel", response_model=CancelJobResponse)
async def cancel_job(
    job_id: UUID,
    user_id: str = Depends(get_current_user_id)
):
    """
    Cancel a pending or in-progress generation job.

    **Requirements:**
    - Job must be in `queued` or `in_progress` status
    - User must own the job (enforced by RLS)

    **HTTP Status Codes:**
    - 200: Job cancelled successfully
    - 400: Job cannot be cancelled (already completed/failed)
    - 404: Job not found
    - 500: Server error
    """
    try:
        manager = GenerationJobManager()
        user_id_uuid = UUID(user_id)

        # Check if job exists and can be cancelled
        job = await manager.get_job(job_id, user_id_uuid)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        if job.status not in ["queued", "in_progress"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel job with status '{job.status}'"
            )

        # Perform cancellation
        success = await manager.cancel_job(job_id, user_id_uuid)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel job"
            )

        return CancelJobResponse(
            job_id=job_id,
            status="cancelled",
            cancelled_at=job.updated_at,
            message="Job cancelled successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cancelling job: {str(e)}"
        )


# ============================================================================
# WebSocket Connection (Real-time Updates)
# ============================================================================


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT auth token")
):
    """
    WebSocket endpoint for real-time job updates.

    **Connection URL:**
    ```
    ws://localhost:8000/api/generation-jobs/ws?token={jwt_token}
    ```

    **Message Types:**
    1. **connected**: Connection confirmation
    2. **heartbeat**: Periodic keep-alive (every 30s)
    3. **job_progress**: Progress updates during generation
    4. **job_completed**: Job completion notification
    5. **job_failed**: Job failure notification
    6. **character_status_update**: Character vector store status

    **Client Requirements:**
    - Send heartbeat response to prevent timeout
    - Implement exponential backoff reconnection (1s, 2s, 4s, 8s, 16s, max 30s)
    - Handle message types appropriately in UI

    **Connection Lifecycle:**
    1. Client connects with JWT token
    2. Server validates token and accepts connection
    3. Server sends `connected` message
    4. Server broadcasts updates for user's jobs
    5. Heartbeat every 30 seconds
    6. Connection closes on error or client disconnect
    """
    from api.middleware.auth import validate_token

    manager = get_connection_manager()

    try:
        # Validate JWT token and extract user_id
        user_id_str = await validate_token(token)

        if not user_id_str:
            logger.warning("WebSocket connection rejected: invalid token")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid authentication token")
            return

        user_id = UUID(user_id_str)
        logger.info(f"WebSocket connecting for user {user_id}")

        await manager.connect(websocket, user_id)

        try:
            while True:
                # Wait for client messages (heartbeat responses, etc.)
                data = await websocket.receive_text()

                # Client can send heartbeat acks, but we don't require them
                # The server's heartbeat loop keeps connection alive

        except WebSocketDisconnect:
            logger.info(f"WebSocket client disconnected for user {user_id}")
            await manager.disconnect(websocket)

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await manager.disconnect(websocket)
        except Exception:
            pass  # Already disconnected


# ============================================================================
# Notification Preferences
# ============================================================================


@router.get("/preferences/notifications", response_model=NotificationPreferences)
async def get_notification_preferences(
    user_id: str = Depends(get_current_user_id)
):
    """
    Get current user's notification preferences (Epic 10 Story 4).

    **Returns:**
    - Email and toast notification settings
    - Notification email address
    - Success/failure/long-task notification flags

    **Defaults (if not set):**
    - All notifications enabled
    - Uses user's primary email from auth.users
    """
    try:
        from api.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        user_id_uuid = UUID(user_id)

        result = supabase.table("user_notification_preferences")\
            .select("*")\
            .eq("user_id", str(user_id_uuid))\
            .execute()

        if result.data:
            return NotificationPreferences(**result.data[0])

        # Return defaults if not set
        return NotificationPreferences(
            user_id=user_id_uuid,
            email_notifications_enabled=True,
            toast_notifications_enabled=True,
            notify_on_success=True,
            notify_on_failure=True,
            notify_on_long_tasks=True
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching notification preferences: {str(e)}"
        )


@router.put("/preferences/notifications", response_model=NotificationPreferences)
async def update_notification_preferences(
    preferences: NotificationPreferencesUpdate,
    user_id: str = Depends(get_current_user_id)
):
    """
    Update user's notification preferences.

    **Request Body:**
    ```json
    {
      "email_notifications_enabled": true,
      "toast_notifications_enabled": true,
      "notification_email": "user@example.com",
      "notify_on_success": true,
      "notify_on_failure": true,
      "notify_on_long_tasks": true
    }
    ```

    **HTTP Status Codes:**
    - 200: Preferences updated successfully
    - 500: Server error
    """
    try:
        from api.utils.supabase_client import get_supabase_client
        from datetime import datetime
        supabase = get_supabase_client()
        user_id_uuid = UUID(user_id)

        # Build update data (only include provided fields)
        update_data = preferences.model_dump(exclude_none=True)

        # Upsert preferences
        result = supabase.table("user_notification_preferences")\
            .upsert({
                "user_id": str(user_id_uuid),
                **update_data
            })\
            .execute()

        if not result.data:
            raise Exception("Failed to update preferences")

        return NotificationPreferences(**result.data[0])

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating notification preferences: {str(e)}"
        )


# ============================================================================
# Character Vector Store Status (Epic 10 Story 3)
# ============================================================================


@router.get("/characters/{character_id}/vector-status", response_model=CharacterVectorStoreStatus)
async def get_character_vector_status(
    character_id: UUID,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get character vector store initialization status (Epic 10 Story 3).

    **Status Values:**
    - `not_initialized`: Character has no vector store yet
    - `initializing`: Background job is creating ChromaDB collection
    - `ready`: Vector store ready for content generation
    - `updating`: Adding new content to vector store (non-blocking)
    - `failed`: Initialization or update failed

    **Returns:**
    - Current status
    - ChromaDB collection name (if initialized)
    - Number of embeddings/documents
    - Whether content generation is available

    **Redis Caching:**
    - In-progress status (`initializing`, `updating`) cached for 1 hour
    - Deleted when initialization complete
    """
    try:
        from api.utils.supabase_client import get_supabase_client
        from api.utils.redis_client import get_redis_client
        import json

        supabase = get_supabase_client()
        redis = await get_redis_client()

        # Check Redis for in-progress status
        cache_key = f"character:vector_status:{character_id}"
        cached_status = await redis.get(cache_key)

        if cached_status:
            status_data = json.loads(cached_status)
            return CharacterVectorStoreStatus(
                character_id=character_id,
                status=CharacterVectorStatus(status_data["status"]),
                collection_name=status_data.get("collection_name"),
                embedding_count=status_data.get("embedding_count"),
                can_generate=status_data.get("status") == "ready",
                error_message=status_data.get("error_message")
            )

        # Check database for persisted status
        result = supabase.table("characters")\
            .select("vector_store_collection, vector_store_initialized_at, vector_store_initialization_failed_at")\
            .eq("id", str(character_id))\
            .execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Character {character_id} not found"
            )

        char = result.data[0]

        # Determine status
        if char["vector_store_initialization_failed_at"]:
            vector_status = CharacterVectorStatus.FAILED
            can_generate = False
        elif char["vector_store_collection"] and char["vector_store_initialized_at"]:
            vector_status = CharacterVectorStatus.READY
            can_generate = True
        else:
            vector_status = CharacterVectorStatus.NOT_INITIALIZED
            can_generate = False

        # TODO: Get actual embedding count from ChromaDB if ready

        return CharacterVectorStoreStatus(
            character_id=character_id,
            status=vector_status,
            collection_name=char["vector_store_collection"],
            embedding_count=None,  # TODO: Query ChromaDB
            can_generate=can_generate,
            initialized_at=char.get("vector_store_initialized_at")
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching character vector status: {str(e)}"
        )


import logging
logger = logging.getLogger(__name__)
