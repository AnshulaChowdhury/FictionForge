"""
Sub-Chapter Management Service for Epic 6

Handles creation, updating, and management of sub-chapters with
automatic character inheritance and integration with generation jobs.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
import logging

from api.utils.supabase_client import get_supabase_client
from api.models.sub_chapter import (
    SubChapter,
    SubChapterCreate,
    SubChapterUpdate,
    SubChapterContentUpdate,
    SubChapterCreateResponse,
    SubChapterStatus,
    SubChapterWithProgress
)

logger = logging.getLogger(__name__)


class SubChapterManager:
    """Handles sub-chapter creation and management operations"""

    def __init__(self):
        self.supabase = get_supabase_client()

    async def create_sub_chapter(
        self,
        data: SubChapterCreate,
        user_id: UUID,
        trigger_generation: bool = True
    ) -> SubChapterCreateResponse:
        """
        Create a new sub-chapter and optionally trigger content generation.

        The character_id is automatically populated from the parent chapter
        via database trigger (copy_character_from_chapter).

        Args:
            data: Sub-chapter creation data
            user_id: User creating the sub-chapter
            trigger_generation: Whether to queue content generation job

        Returns:
            SubChapterCreateResponse with job information

        Raises:
            ValueError: If chapter doesn't exist or user doesn't own it
        """
        try:
            # 1. Verify chapter exists and user owns it
            chapter = await self._get_chapter_with_ownership(data.chapter_id, user_id)
            if not chapter:
                raise ValueError(f"Chapter {data.chapter_id} not found or access denied")

            # 2. Get next sub_chapter_number
            next_number = await self._get_next_sub_chapter_number(data.chapter_id)

            # 3. Create sub-chapter stub
            # Note: character_id will be auto-populated by DB trigger
            # Note: target_word_count is not stored in DB, only used for generation
            sub_chapter_data = {
                "chapter_id": str(data.chapter_id),
                "sub_chapter_number": next_number,
                "title": data.title,
                "plot_points": data.plot_points,
                "status": SubChapterStatus.DRAFT,
                "word_count": 0,
                "content": None
            }

            result = self.supabase.table("sub_chapters").insert(sub_chapter_data).execute()

            if not result.data:
                raise Exception("Failed to create sub-chapter")

            sub_chapter = result.data[0]
            sub_chapter_id = UUID(sub_chapter["id"])

            # 4. Queue generation job if requested (Epic 10: With job tracking)
            generation_job_id = None
            websocket_url = None

            if trigger_generation and data.plot_points:
                from api.services.task_queue import TaskQueue
                from api.services.generation_job_manager import GenerationJobManager

                # Epic 10: Enqueue Arq task
                arq_job_id = await TaskQueue.enqueue_sub_chapter_generation(
                    sub_chapter_id=str(sub_chapter_id),
                    chapter_id=str(data.chapter_id),
                    character_id=sub_chapter["character_id"],
                    plot_points=data.plot_points,
                    target_word_count=data.target_word_count or 2000,
                    trilogy_id=chapter["book"]["trilogy_id"],
                    book_id=chapter["book"]["id"]  # Epic 5B: Required for world rule filtering
                )

                if arq_job_id:
                    # Epic 10: Create generation_jobs tracking record
                    job_manager = GenerationJobManager()
                    job = await job_manager.create_job(
                        user_id=user_id,
                        trilogy_id=UUID(chapter["book"]["trilogy_id"]),
                        sub_chapter_id=sub_chapter_id,
                        arq_job_id=arq_job_id,
                        job_type="sub_chapter_generation",
                        priority=0,
                        target_word_count=data.target_word_count or 2000,
                        generation_params={
                            "character_id": sub_chapter["character_id"],
                            "plot_points": data.plot_points
                        }
                    )

                    generation_job_id = str(job.id)

                    # Update status to in_progress
                    self.supabase.table("sub_chapters").update({
                        "status": SubChapterStatus.IN_PROGRESS
                    }).eq("id", str(sub_chapter_id)).execute()

                    websocket_url = f"/api/generation-jobs/ws"  # Epic 10: User-specific WebSocket

            logger.info(f"Created sub-chapter {sub_chapter_id} for chapter {data.chapter_id}")

            return SubChapterCreateResponse(
                sub_chapter_id=sub_chapter_id,
                generation_job_id=UUID(generation_job_id) if generation_job_id else None,
                status=SubChapterStatus.IN_PROGRESS if generation_job_id else SubChapterStatus.DRAFT,
                websocket_url=websocket_url
            )

        except Exception as e:
            logger.error(f"Error creating sub-chapter: {e}")
            raise

    async def get_sub_chapter(
        self,
        sub_chapter_id: UUID,
        user_id: UUID
    ) -> Optional[SubChapter]:
        """
        Get a single sub-chapter by ID.

        Args:
            sub_chapter_id: Sub-chapter identifier
            user_id: User requesting the sub-chapter

        Returns:
            SubChapter or None if not found
        """
        try:
            # Query with RLS automatically enforcing ownership
            result = self.supabase.table("sub_chapters")\
                .select("*")\
                .eq("id", str(sub_chapter_id))\
                .execute()

            if not result.data:
                return None

            return SubChapter(**result.data[0])

        except Exception as e:
            logger.error(f"Error fetching sub-chapter {sub_chapter_id}: {e}")
            return None

    async def list_sub_chapters(
        self,
        chapter_id: UUID,
        user_id: UUID
    ) -> List[SubChapter]:
        """
        List all sub-chapters for a chapter, ordered by sub_chapter_number.

        Args:
            chapter_id: Chapter identifier
            user_id: User requesting the list

        Returns:
            List of sub-chapters
        """
        try:
            result = self.supabase.table("sub_chapters")\
                .select("*")\
                .eq("chapter_id", str(chapter_id))\
                .order("sub_chapter_number")\
                .execute()

            return [SubChapter(**sc) for sc in result.data]

        except Exception as e:
            logger.error(f"Error listing sub-chapters for chapter {chapter_id}: {e}")
            return []

    async def update_sub_chapter(
        self,
        sub_chapter_id: UUID,
        data: SubChapterUpdate,
        user_id: UUID
    ) -> Optional[SubChapter]:
        """
        Update sub-chapter metadata (title, plot_points, status).

        Note: This does NOT modify content or word_count. Use versioning for that.

        Args:
            sub_chapter_id: Sub-chapter identifier
            data: Update data
            user_id: User performing the update

        Returns:
            Updated SubChapter or None if not found

        Raises:
            ValueError: If validation fails
        """
        try:
            # Build update dict (only non-None values)
            update_data = {}
            if data.title is not None:
                update_data["title"] = data.title
            if data.plot_points is not None:
                update_data["plot_points"] = data.plot_points
            if data.status is not None:
                update_data["status"] = data.status

            if not update_data:
                # Nothing to update, just fetch current
                return await self.get_sub_chapter(sub_chapter_id, user_id)

            update_data["updated_at"] = datetime.utcnow().isoformat()

            result = self.supabase.table("sub_chapters")\
                .update(update_data)\
                .eq("id", str(sub_chapter_id))\
                .execute()

            if not result.data:
                return None

            logger.info(f"Updated sub-chapter {sub_chapter_id}")
            return SubChapter(**result.data[0])

        except Exception as e:
            logger.error(f"Error updating sub-chapter {sub_chapter_id}: {e}")
            raise

    async def update_content(
        self,
        sub_chapter_id: UUID,
        data: SubChapterContentUpdate,
        user_id: UUID
    ) -> Optional[SubChapter]:
        """
        Manually update sub-chapter content and create a new version.

        Creates a new version in sub_chapter_versions with is_ai_generated=false,
        then updates the main sub_chapter record.

        Args:
            sub_chapter_id: Sub-chapter identifier
            data: Content update data
            user_id: User performing the update

        Returns:
            Updated SubChapter or None if not found

        Raises:
            ValueError: If validation fails or sub-chapter not found
        """
        try:
            # 1. Verify sub-chapter exists and user has access
            sub_chapter = await self.get_sub_chapter(sub_chapter_id, user_id)
            if not sub_chapter:
                raise ValueError(f"Sub-chapter {sub_chapter_id} not found or access denied")

            # 2. Calculate word count
            word_count = len(data.content.split())

            # 3. Get next version number
            version_result = self.supabase.table("sub_chapter_versions")\
                .select("version_number")\
                .eq("sub_chapter_id", str(sub_chapter_id))\
                .order("version_number", desc=True)\
                .limit(1)\
                .execute()

            next_version = 1
            if version_result.data:
                next_version = version_result.data[0]["version_number"] + 1

            # 4. Set all existing versions to is_current = false
            self.supabase.table("sub_chapter_versions")\
                .update({"is_current": False})\
                .eq("sub_chapter_id", str(sub_chapter_id))\
                .execute()

            # 5. Create version record with is_current = true
            version_data = {
                "sub_chapter_id": str(sub_chapter_id),
                "version_number": next_version,
                "content": data.content,
                "word_count": word_count,
                "is_ai_generated": False,
                "is_current": True,
                "created_by_user_id": str(user_id),
                "change_description": data.change_description or f"Manual edit (version {next_version})"
            }

            version_insert = self.supabase.table("sub_chapter_versions")\
                .insert(version_data)\
                .execute()

            if not version_insert.data:
                raise Exception("Failed to create version record")

            # 6. Update sub_chapter record
            update_result = self.supabase.table("sub_chapters")\
                .update({
                    "content": data.content,
                    "word_count": word_count,
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("id", str(sub_chapter_id))\
                .execute()

            if not update_result.data:
                raise Exception("Failed to update sub-chapter")

            logger.info(
                f"Updated content for sub-chapter {sub_chapter_id}, "
                f"created version {next_version}, {word_count} words"
            )
            return SubChapter(**update_result.data[0])

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error updating content for sub-chapter {sub_chapter_id}: {e}")
            raise

    async def delete_sub_chapter(
        self,
        sub_chapter_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Delete a sub-chapter and all its versions.

        CASCADE deletion will automatically remove:
        - All versions (sub_chapter_versions)
        - All review flags (content_review_flags)

        Args:
            sub_chapter_id: Sub-chapter identifier
            user_id: User performing the deletion

        Returns:
            True if deleted, False otherwise
        """
        try:
            result = self.supabase.table("sub_chapters")\
                .delete()\
                .eq("id", str(sub_chapter_id))\
                .execute()

            if result.data:
                logger.info(f"Deleted sub-chapter {sub_chapter_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error deleting sub-chapter {sub_chapter_id}: {e}")
            return False

    # ========================================================================
    # Helper Methods
    # ========================================================================

    async def _get_next_sub_chapter_number(self, chapter_id: UUID) -> int:
        """
        Get the next sequential sub_chapter_number for a chapter.

        Args:
            chapter_id: Chapter identifier

        Returns:
            Next available sub_chapter_number (1-indexed)
        """
        # Query for the maximum sub_chapter_number for this chapter
        max_result = self.supabase.table("sub_chapters")\
            .select("sub_chapter_number")\
            .eq("chapter_id", str(chapter_id))\
            .order("sub_chapter_number", desc=True)\
            .limit(1)\
            .execute()

        if max_result.data and len(max_result.data) > 0:
            next_number = max_result.data[0]["sub_chapter_number"] + 1
            logger.info(f"Next sub-chapter number for chapter {chapter_id}: {next_number}")
            return next_number

        # No sub-chapters exist yet, start with 1
        logger.info(f"First sub-chapter for chapter {chapter_id}, using number 1")
        return 1

    async def _get_chapter_with_ownership(
        self,
        chapter_id: UUID,
        user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get chapter and verify user ownership via trilogy.

        Args:
            chapter_id: Chapter identifier
            user_id: User identifier

        Returns:
            Chapter data with book/trilogy info, or None if not found/no access
        """
        try:
            result = self.supabase.table("chapters")\
                .select("*, book:books(id, trilogy_id, trilogy:trilogy_projects(user_id))")\
                .eq("id", str(chapter_id))\
                .execute()

            if not result.data:
                return None

            chapter = result.data[0]

            # Verify ownership through RLS or explicit check
            # RLS should handle this automatically, but we can double-check
            if chapter.get("book") and chapter["book"].get("trilogy"):
                if str(chapter["book"]["trilogy"]["user_id"]) != str(user_id):
                    return None

            return chapter

        except Exception as e:
            logger.error(f"Error fetching chapter with ownership: {e}")
            return None
