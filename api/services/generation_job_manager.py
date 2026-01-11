"""
Generation Job Manager Service for Epic 10

Handles CRUD operations, progress tracking, and status management for async generation jobs.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
import logging
import json

from api.utils.supabase_client import get_supabase_client
from api.models.generation_job import (
    GenerationJobResponse,
    GenerationJobListItem,
    GenerationJobUpdate,
    JobStatus,
    JobStage,
    ProgressUpdate
)

logger = logging.getLogger(__name__)


class GenerationJobManager:
    """Manages generation jobs with progress tracking and caching"""

    def __init__(self):
        self.supabase = get_supabase_client()

    async def create_job(
        self,
        user_id: UUID,
        trilogy_id: UUID,
        sub_chapter_id: UUID,
        arq_job_id: str,
        job_type: str = "sub_chapter_generation",
        priority: int = 0,
        target_word_count: int = 2000,
        generation_params: Optional[Dict[str, Any]] = None
    ) -> GenerationJobResponse:
        """
        Create a new generation job.

        Args:
            user_id: User creating the job
            trilogy_id: Trilogy identifier
            sub_chapter_id: Sub-chapter being generated
            arq_job_id: Arq task queue job ID
            job_type: Type of generation job
            priority: Job priority (0-10)
            target_word_count: Target word count for generation
            generation_params: Additional parameters (character_id, etc.)

        Returns:
            GenerationJobResponse with created job data

        Raises:
            ValueError: If validation fails or duplicate job exists
        """
        try:
            # Check for existing active job for this sub-chapter
            existing = self.supabase.table("generation_jobs")\
                .select("id, status")\
                .eq("sub_chapter_id", str(sub_chapter_id))\
                .in_("status", ["queued", "in_progress"])\
                .execute()

            if existing.data:
                raise ValueError(
                    f"Active generation job already exists for sub-chapter {sub_chapter_id}"
                )

            # Calculate estimated completion (avg 3 minutes for 2000 words)
            estimated_minutes = max(2, (target_word_count / 2000) * 3)
            estimated_completion = datetime.utcnow() + timedelta(minutes=estimated_minutes)

            # Create job record
            job_data = {
                "user_id": str(user_id),
                "trilogy_id": str(trilogy_id),
                "sub_chapter_id": str(sub_chapter_id),
                "arq_job_id": arq_job_id,
                "status": JobStatus.QUEUED.value,
                "job_type": job_type,
                "priority": priority,
                "stage": JobStage.INITIALIZING.value,
                "progress_percentage": 0,
                "estimated_completion": estimated_completion.isoformat(),
                "retry_count": 0,
                "generation_params": generation_params or {}
            }

            result = self.supabase.table("generation_jobs")\
                .insert(job_data)\
                .execute()

            if not result.data:
                raise Exception("Failed to create generation job")

            job = result.data[0]
            logger.info(f"Created generation job {job['id']} for sub-chapter {sub_chapter_id}")

            # Invalidate cache
            await self._invalidate_user_jobs_cache(user_id)

            return GenerationJobResponse(
                **job,
                can_cancel=True,
                time_remaining_seconds=int(estimated_minutes * 60)
            )

        except Exception as e:
            logger.error(f"Error creating generation job: {e}")
            raise

    async def get_job(self, job_id: UUID, user_id: UUID) -> Optional[GenerationJobResponse]:
        """
        Get a specific job by ID.

        Args:
            job_id: Job identifier
            user_id: User requesting the job (for RLS)

        Returns:
            GenerationJobResponse or None if not found
        """
        try:
            result = self.supabase.table("generation_jobs")\
                .select("*")\
                .eq("id", str(job_id))\
                .execute()

            if not result.data:
                return None

            job = result.data[0]
            time_remaining = self._calculate_time_remaining(job)

            return GenerationJobResponse(
                **job,
                can_cancel=job["status"] in ["queued", "in_progress"],
                time_remaining_seconds=time_remaining
            )

        except Exception as e:
            logger.error(f"Error fetching job {job_id}: {e}")
            return None

    async def update_job_progress(
        self,
        job_id: UUID,
        progress: ProgressUpdate,
        user_id: Optional[UUID] = None
    ) -> Optional[GenerationJobResponse]:
        """
        Update job progress.

        Args:
            job_id: Job identifier
            progress: Progress update data
            user_id: Optional user ID for RLS

        Returns:
            Updated GenerationJobResponse or None
        """
        try:
            update_data = {
                "stage": progress.stage.value,
                "progress_percentage": progress.progress_percentage,
                "updated_at": datetime.utcnow().isoformat()
            }

            # Calculate estimated completion if provided
            estimated_completion = progress.calculate_estimated_completion()
            if estimated_completion:
                update_data["estimated_completion"] = estimated_completion.isoformat()

            # Update status to in_progress if still queued
            result = self.supabase.table("generation_jobs")\
                .select("status")\
                .eq("id", str(job_id))\
                .execute()

            if result.data and result.data[0]["status"] == "queued":
                update_data["status"] = JobStatus.IN_PROGRESS.value

            # Perform update
            result = self.supabase.table("generation_jobs")\
                .update(update_data)\
                .eq("id", str(job_id))\
                .execute()

            if not result.data:
                logger.warning(f"No job found with id {job_id}")
                return None

            job = result.data[0]

            # Update Redis progress cache
            await self._cache_job_progress(job_id, job)

            # Invalidate user jobs cache
            if user_id:
                await self._invalidate_user_jobs_cache(user_id)

            logger.info(
                f"Updated job {job_id} progress: {progress.stage.value} "
                f"({progress.progress_percentage}%)"
            )

            return GenerationJobResponse(
                **job,
                can_cancel=True,
                time_remaining_seconds=progress.estimated_seconds_remaining
            )

        except Exception as e:
            logger.error(f"Error updating job progress: {e}")
            return None

    async def complete_job(
        self,
        job_id: UUID,
        word_count: int,
        version_id: UUID,
        version_number: int,
        model_used: Optional[str] = None,
        result_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[GenerationJobResponse]:
        """
        Mark job as completed with results.

        Args:
            job_id: Job identifier
            word_count: Generated word count
            version_id: Created version ID
            version_number: Created version number
            model_used: LLM model used
            result_metadata: Additional result data

        Returns:
            Updated GenerationJobResponse or None
        """
        try:
            update_data = {
                "status": JobStatus.COMPLETED.value,
                "stage": JobStage.COMPLETE.value,
                "progress_percentage": 100,
                "word_count": word_count,
                "version_id": str(version_id),
                "version_number": version_number,
                "completed_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            if model_used:
                update_data["model_used"] = model_used

            if result_metadata:
                update_data["result_metadata"] = result_metadata

            result = self.supabase.table("generation_jobs")\
                .update(update_data)\
                .eq("id", str(job_id))\
                .execute()

            if not result.data:
                return None

            job = result.data[0]

            # Get user_id for cache invalidation
            user_id = UUID(job["user_id"])

            # Delete Redis progress cache
            await self._delete_job_progress_cache(job_id)

            # Invalidate user jobs cache
            await self._invalidate_user_jobs_cache(user_id)

            logger.info(f"Completed job {job_id}: {word_count} words, version {version_number}")

            return GenerationJobResponse(**job, can_cancel=False, time_remaining_seconds=0)

        except Exception as e:
            logger.error(f"Error completing job {job_id}: {e}")
            return None

    async def fail_job(
        self,
        job_id: UUID,
        error_message: str,
        error_type: Optional[str] = None,
        increment_retry: bool = True
    ) -> Optional[GenerationJobResponse]:
        """
        Mark job as failed with error details.

        Args:
            job_id: Job identifier
            error_message: Error description
            error_type: Error type/category
            increment_retry: Whether to increment retry count

        Returns:
            Updated GenerationJobResponse or None
        """
        try:
            # Get current job to check retry count
            result = self.supabase.table("generation_jobs")\
                .select("retry_count, user_id")\
                .eq("id", str(job_id))\
                .execute()

            if not result.data:
                return None

            current_retry = result.data[0]["retry_count"]
            user_id = UUID(result.data[0]["user_id"])

            update_data = {
                "status": JobStatus.FAILED.value,
                "error_message": error_message,
                "completed_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            if increment_retry:
                update_data["retry_count"] = current_retry + 1

            if error_type:
                result_metadata = {"error_type": error_type}
                update_data["result_metadata"] = result_metadata

            result = self.supabase.table("generation_jobs")\
                .update(update_data)\
                .eq("id", str(job_id))\
                .execute()

            if not result.data:
                return None

            job = result.data[0]

            # Delete Redis progress cache
            await self._delete_job_progress_cache(job_id)

            # Invalidate user jobs cache
            await self._invalidate_user_jobs_cache(user_id)

            logger.error(f"Failed job {job_id}: {error_message}")

            return GenerationJobResponse(**job, can_cancel=False, time_remaining_seconds=0)

        except Exception as e:
            logger.error(f"Error failing job {job_id}: {e}")
            return None

    async def cancel_job(self, job_id: UUID, user_id: UUID) -> bool:
        """
        Cancel a pending or in-progress job.

        Args:
            job_id: Job identifier
            user_id: User requesting cancellation

        Returns:
            True if cancelled, False otherwise
        """
        try:
            # Check if job can be cancelled
            result = self.supabase.table("generation_jobs")\
                .select("status, arq_job_id")\
                .eq("id", str(job_id))\
                .execute()

            if not result.data:
                return False

            job = result.data[0]

            if job["status"] not in ["queued", "in_progress"]:
                logger.warning(f"Cannot cancel job {job_id} with status {job['status']}")
                return False

            # Update job status
            self.supabase.table("generation_jobs")\
                .update({
                    "status": JobStatus.CANCELLED.value,
                    "completed_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("id", str(job_id))\
                .execute()

            # TODO: Cancel the Arq job if it exists
            # arq_job_id = job["arq_job_id"]
            # await self._cancel_arq_job(arq_job_id)

            # Delete Redis progress cache
            await self._delete_job_progress_cache(job_id)

            # Invalidate user jobs cache
            await self._invalidate_user_jobs_cache(user_id)

            logger.info(f"Cancelled job {job_id}")
            return True

        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {e}")
            return False

    async def get_jobs(
        self,
        user_id: UUID,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[GenerationJobListItem]:
        """
        Get generation jobs for a user with optional status filtering.

        Args:
            user_id: User identifier
            status: Optional status filter (queued, in_progress, completed, failed, cancelled)
                   If None, returns all jobs
            limit: Maximum number of jobs to return

        Returns:
            List of GenerationJobListItem
        """
        try:
            # Only cache active jobs (status filtering may vary)
            if status is None or status in ["queued", "in_progress"]:
                cached_jobs = await self._get_cached_user_jobs(user_id)
                if cached_jobs is not None and status is None:
                    return cached_jobs

            # Build query - fetch jobs first without joins (FK relationships not defined)
            query = self.supabase.table("generation_jobs") \
                .select("*") \
                .eq("user_id", str(user_id)) \
                .order("created_at", desc=True) \
                .limit(limit)

            # Apply status filter if provided
            if status:
                query = query.eq("status", status)

            result = query.execute()

            if not result.data:
                return []

            # Extract unique sub_chapter_ids and character_ids for batch fetching
            sub_chapter_ids = list(set([job["sub_chapter_id"] for job in result.data if job.get("sub_chapter_id")]))

            # Get character_ids from generation_params
            character_ids = []
            for job in result.data:
                params = job.get("generation_params") or {}
                char_id = params.get("character_id")
                if char_id:
                    character_ids.append(char_id)
            character_ids = list(set(character_ids))

            # Batch fetch sub-chapters with their chapters
            sub_chapters_map = {}
            if sub_chapter_ids:
                sc_result = self.supabase.table("sub_chapters") \
                    .select("id, title, chapter_id, chapters(id, title, book_id)") \
                    .in_("id", sub_chapter_ids) \
                    .execute()

                for sc in sc_result.data or []:
                    sub_chapters_map[sc["id"]] = sc

            # Batch fetch characters
            characters_map = {}
            if character_ids:
                char_result = self.supabase.table("characters") \
                    .select("id, name") \
                    .in_("id", character_ids) \
                    .execute()

                for char in char_result.data or []:
                    characters_map[char["id"]] = char

            jobs = []
            for job_data in result.data or []:
                time_remaining = self._calculate_time_remaining(job_data)

                # Get sub-chapter data from map
                sub_chapter = sub_chapters_map.get(job_data.get("sub_chapter_id"))

                chapter = None
                chapter_id = None
                sub_chapter_title = None
                chapter_title = None

                if sub_chapter:
                    sub_chapter_title = sub_chapter.get("title")
                    chapter_id = sub_chapter.get("chapter_id")
                    chapters_data = sub_chapter.get("chapters")
                    # Handle both object and array
                    if isinstance(chapters_data, list) and len(chapters_data) > 0:
                        chapter = chapters_data[0]
                    elif isinstance(chapters_data, dict):
                        chapter = chapters_data

                    if chapter:
                        chapter_title = chapter.get("title")

                # Get character data from map
                params = job_data.get("generation_params") or {}
                char_id = params.get("character_id")
                character = characters_map.get(char_id) if char_id else None
                character_name = character.get("name") if character else None

                jobs.append(GenerationJobListItem(
                    id=job_data["id"],
                    trilogy_id=job_data["trilogy_id"],
                    sub_chapter_id=job_data["sub_chapter_id"],
                    chapter_id=chapter_id,
                    sub_chapter_title=sub_chapter_title,
                    chapter_title=chapter_title,
                    character_name=character_name,
                    status=job_data["status"],
                    stage=job_data.get("stage"),
                    progress_percentage=job_data.get("progress_percentage", 0),
                    estimated_completion=job_data.get("estimated_completion"),
                    created_at=job_data["created_at"],
                    started_at=job_data.get("started_at"),
                    word_count=job_data.get("word_count"),
                    can_cancel=job_data["status"] in ["queued", "in_progress"],
                    time_remaining_seconds=time_remaining,
                    queue_position=None  # TODO: Get from Arq if queued
                ))

            # Cache active jobs only
            if status is None or status in ["queued", "in_progress"]:
                await self._cache_user_jobs(user_id, jobs)

            return jobs

        except Exception as e:
            logger.error(f"Error fetching jobs for user {user_id}: {e}")
            return []

    async def get_active_jobs(
        self,
        user_id: UUID,
        limit: int = 50
    ) -> List[GenerationJobListItem]:
        """
        Get active jobs for a user (queued or in_progress).

        This is a convenience method that calls get_jobs with no status filter
        but only returns active jobs.

        Args:
            user_id: User identifier
            limit: Maximum number of jobs to return

        Returns:
            List of active GenerationJobListItem
        """
        all_jobs = await self.get_jobs(user_id, status=None, limit=limit)
        return [job for job in all_jobs if job.status in ["queued", "in_progress"]]

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _calculate_time_remaining(self, job: Dict[str, Any]) -> Optional[int]:
        """Calculate remaining seconds based on estimated completion"""
        if job.get("estimated_completion") and job["status"] in ["queued", "in_progress"]:
            try:
                est_completion = datetime.fromisoformat(
                    job["estimated_completion"].replace("Z", "+00:00")
                )
                remaining = (est_completion - datetime.utcnow()).total_seconds()
                return max(0, int(remaining))
            except:
                pass
        return None

    async def _cache_job_progress(self, job_id: UUID, job_data: Dict[str, Any]):
        """Cache job progress in Redis"""
        try:
            from api.utils.redis_client import get_redis_client
            redis = await get_redis_client()

            cache_key = f"job:progress:{job_id}"
            cache_data = {
                "job_id": str(job_id),
                "status": job_data["status"],
                "stage": job_data.get("stage"),
                "progress_percentage": job_data["progress_percentage"],
                "estimated_completion": job_data.get("estimated_completion"),
                "updated_at": job_data.get("updated_at", datetime.utcnow().isoformat())
            }

            await redis.setex(cache_key, 7200, json.dumps(cache_data))  # 2 hour TTL

        except Exception as e:
            logger.warning(f"Failed to cache job progress: {e}")

    async def _delete_job_progress_cache(self, job_id: UUID):
        """Delete job progress from Redis cache"""
        try:
            from api.utils.redis_client import get_redis_client
            redis = await get_redis_client()
            await redis.delete(f"job:progress:{job_id}")
        except Exception as e:
            logger.warning(f"Failed to delete job progress cache: {e}")

    async def _cache_user_jobs(self, user_id: UUID, jobs: List[GenerationJobListItem]):
        """Cache user's active jobs list"""
        try:
            from api.utils.redis_client import get_redis_client
            redis = await get_redis_client()

            cache_key = f"jobs:{user_id}:active"
            cache_data = [job.model_dump(mode='json') for job in jobs]

            await redis.setex(cache_key, 30, json.dumps(cache_data))  # 30 second TTL

        except Exception as e:
            logger.warning(f"Failed to cache user jobs: {e}")

    async def _get_cached_user_jobs(self, user_id: UUID) -> Optional[List[GenerationJobListItem]]:
        """Get cached user jobs from Redis"""
        try:
            from api.utils.redis_client import get_redis_client
            redis = await get_redis_client()

            cache_key = f"jobs:{user_id}:active"
            cached = await redis.get(cache_key)

            if cached:
                jobs_data = json.loads(cached)
                return [GenerationJobListItem(**job) for job in jobs_data]

        except Exception as e:
            logger.warning(f"Failed to get cached user jobs: {e}")

        return None

    async def _invalidate_user_jobs_cache(self, user_id: UUID):
        """Invalidate user's jobs cache"""
        try:
            from api.utils.redis_client import get_redis_client
            redis = await get_redis_client()
            await redis.delete(f"jobs:{user_id}:active")
        except Exception as e:
            logger.warning(f"Failed to invalidate user jobs cache: {e}")
