"""
Sub-Chapter Regeneration Service for Epic 6

Handles content regeneration with version management, allowing users to:
- Regenerate individual sub-chapters with new prompts/characters
- Bulk regenerate all sub-chapters in a chapter with a new character
- Maintain complete version history for rollback
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
import logging

from api.utils.supabase_client import get_supabase_client
from api.models.sub_chapter import (
    SubChapter,
    SubChapterVersion,
    SubChapterVersionListItem,
    RegenerateResponse,
    BulkRegenerateResponse
)

logger = logging.getLogger(__name__)


class SubChapterRegenerationService:
    """Handles content regeneration with version management"""

    def __init__(self):
        self.supabase = get_supabase_client()

    async def regenerate_sub_chapter(
        self,
        sub_chapter_id: UUID,
        user_id: UUID,
        new_character_id: Optional[UUID] = None,
        new_plot_points: Optional[str] = None,
        change_description: Optional[str] = None
    ) -> RegenerateResponse:
        """
        Regenerate sub-chapter content as a new version.

        Process:
        1. Get current sub-chapter and determine next version number
        2. If new character provided, update sub-chapter
        3. If new plot points provided, update sub-chapter
        4. Queue regeneration job
        5. Job creates new version in sub_chapter_versions
        6. Job updates sub_chapter.content and word_count on completion

        Args:
            sub_chapter_id: Sub-chapter to regenerate
            user_id: User triggering regeneration
            new_character_id: Optional new character perspective
            new_plot_points: Optional new plot points
            change_description: Optional description of why regenerating

        Returns:
            RegenerateResponse with job information

        Raises:
            ValueError: If sub-chapter not found or validation fails
        """
        try:
            # 1. Get current sub-chapter
            result = self.supabase.table("sub_chapters")\
                .select("*, chapter:chapters(id, book_id, book:books(id, trilogy_id))")\
                .eq("id", str(sub_chapter_id))\
                .execute()

            if not result.data:
                raise ValueError(f"Sub-chapter {sub_chapter_id} not found")

            sub_chapter = result.data[0]
            chapter = sub_chapter["chapter"]
            trilogy_id = chapter["book"]["trilogy_id"]

            # 2. Get next version number
            next_version = await self._get_next_version_number(sub_chapter_id)

            # 3. Update character if provided (and different from current)
            if new_character_id and str(new_character_id) != sub_chapter["character_id"]:
                # Verify character belongs to same trilogy
                await self._verify_character_ownership(new_character_id, trilogy_id, user_id)

                self.supabase.table("sub_chapters")\
                    .update({
                        "character_id": str(new_character_id),
                        "status": "needs_review",
                        "updated_at": datetime.utcnow().isoformat()
                    })\
                    .eq("id", str(sub_chapter_id))\
                    .execute()

                sub_chapter["character_id"] = str(new_character_id)

            # 4. Update plot points if provided
            if new_plot_points and new_plot_points != sub_chapter.get("plot_points"):
                self.supabase.table("sub_chapters")\
                    .update({
                        "plot_points": new_plot_points,
                        "updated_at": datetime.utcnow().isoformat()
                    })\
                    .eq("id", str(sub_chapter_id))\
                    .execute()

                sub_chapter["plot_points"] = new_plot_points

            # 5. Queue regeneration job (Epic 10: With job tracking)
            from api.services.task_queue import TaskQueue
            from api.services.generation_job_manager import GenerationJobManager

            # Epic 10: Enqueue Arq task
            arq_job_id = await TaskQueue.enqueue_sub_chapter_regeneration(
                sub_chapter_id=str(sub_chapter_id),
                version_number=next_version,
                chapter_id=chapter["id"],
                character_id=sub_chapter["character_id"],
                plot_points=sub_chapter.get("plot_points") or "",
                target_word_count=sub_chapter.get("target_word_count") or 2000,
                trilogy_id=trilogy_id,
                book_id=chapter["book"]["id"],  # Epic 5B: Required for world rule filtering
                change_description=change_description,
                user_id=str(user_id)
            )

            if not arq_job_id:
                raise Exception("Failed to enqueue regeneration job")

            # Epic 10: Create generation_jobs tracking record
            job_manager = GenerationJobManager()
            job = await job_manager.create_job(
                user_id=user_id,
                trilogy_id=UUID(trilogy_id),
                sub_chapter_id=sub_chapter_id,
                arq_job_id=arq_job_id,
                job_type="sub_chapter_regeneration",
                priority=0,
                target_word_count=sub_chapter.get("target_word_count") or 2000,
                generation_params={
                    "character_id": sub_chapter["character_id"],
                    "plot_points": sub_chapter.get("plot_points") or "",
                    "version_number": next_version,
                    "change_description": change_description
                }
            )

            # 6. Update status to in_progress
            self.supabase.table("sub_chapters")\
                .update({"status": "in_progress"})\
                .eq("id", str(sub_chapter_id))\
                .execute()

            logger.info(
                f"Queued regeneration for sub-chapter {sub_chapter_id}, "
                f"version {next_version}, job {job.id}"
            )

            return RegenerateResponse(
                sub_chapter_id=sub_chapter_id,
                new_version_number=next_version,
                generation_job_id=job.id,
                websocket_url=f"/api/generation-jobs/ws"  # Epic 10: User-specific WebSocket
            )

        except Exception as e:
            logger.error(f"Error regenerating sub-chapter {sub_chapter_id}: {e}")
            raise

    async def regenerate_chapter(
        self,
        chapter_id: UUID,
        new_character_id: UUID,
        user_id: UUID,
        change_description: Optional[str] = None
    ) -> BulkRegenerateResponse:
        """
        Bulk regenerate all sub-chapters in a chapter with a new character.

        The database trigger (propagate_chapter_character_change) automatically:
        - Updates all sub-chapter character_ids
        - Creates review flags for each sub-chapter

        Args:
            chapter_id: Chapter containing sub-chapters
            new_character_id: New character perspective for all sub-chapters
            user_id: User triggering regeneration
            change_description: Optional description of why regenerating

        Returns:
            BulkRegenerateResponse with jobs for all sub-chapters

        Raises:
            ValueError: If chapter not found or character invalid
        """
        try:
            # 1. Get chapter and verify ownership
            chapter_result = self.supabase.table("chapters")\
                .select("*, book:books(trilogy_id, trilogy:trilogy_projects(user_id))")\
                .eq("id", str(chapter_id))\
                .execute()

            if not chapter_result.data:
                raise ValueError(f"Chapter {chapter_id} not found")

            chapter = chapter_result.data[0]
            trilogy_id = chapter["book"]["trilogy_id"]

            # Verify ownership
            if str(chapter["book"]["trilogy"]["user_id"]) != str(user_id):
                raise ValueError("Access denied")

            # 2. Verify character belongs to same trilogy
            await self._verify_character_ownership(new_character_id, trilogy_id, user_id)

            # 3. Update chapter character_id (trigger propagates to sub-chapters)
            self.supabase.table("chapters")\
                .update({
                    "character_id": str(new_character_id),
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("id", str(chapter_id))\
                .execute()

            # 4. Get all sub-chapters (now updated with new character_id)
            sub_chapters_result = self.supabase.table("sub_chapters")\
                .select("*")\
                .eq("chapter_id", str(chapter_id))\
                .order("sub_chapter_number")\
                .execute()

            sub_chapters = sub_chapters_result.data or []

            # 5. Queue regeneration for each sub-chapter
            jobs = []
            for sc in sub_chapters:
                try:
                    response = await self.regenerate_sub_chapter(
                        sub_chapter_id=UUID(sc["id"]),
                        user_id=user_id,
                        change_description=change_description or f"Chapter character changed to {new_character_id}"
                    )
                    jobs.append(response)
                except Exception as e:
                    logger.error(f"Error queuing regeneration for sub-chapter {sc['id']}: {e}")

            logger.info(
                f"Queued bulk regeneration for chapter {chapter_id}, "
                f"{len(jobs)} sub-chapters"
            )

            return BulkRegenerateResponse(
                chapter_id=chapter_id,
                jobs=jobs,
                total_sub_chapters=len(sub_chapters)
            )

        except Exception as e:
            logger.error(f"Error bulk regenerating chapter {chapter_id}: {e}")
            raise

    async def get_version_history(
        self,
        sub_chapter_id: UUID,
        user_id: UUID
    ) -> List[SubChapterVersionListItem]:
        """
        Get version history for a sub-chapter.

        Args:
            sub_chapter_id: Sub-chapter identifier
            user_id: User requesting history

        Returns:
            List of version metadata, newest first
        """
        try:
            result = self.supabase.table("sub_chapter_versions")\
                .select("*")\
                .eq("sub_chapter_id", str(sub_chapter_id))\
                .order("version_number", desc=True)\
                .execute()

            versions = []
            for v in result.data:
                versions.append(SubChapterVersionListItem(
                    id=UUID(v["id"]),
                    version_number=v["version_number"],
                    word_count=v["word_count"],
                    change_description=v.get("change_description"),
                    is_ai_generated=v.get("is_ai_generated", False),
                    created_at=v["created_at"],
                    is_current=v.get("is_current", False)
                ))

            return versions

        except Exception as e:
            logger.error(f"Error fetching version history for {sub_chapter_id}: {e}")
            return []

    async def get_version(
        self,
        version_id: UUID,
        user_id: UUID
    ) -> Optional[SubChapterVersion]:
        """
        Get a specific version by ID.

        Args:
            version_id: Version identifier
            user_id: User requesting version

        Returns:
            SubChapterVersion or None if not found
        """
        try:
            result = self.supabase.table("sub_chapter_versions")\
                .select("*")\
                .eq("id", str(version_id))\
                .execute()

            if not result.data:
                return None

            return SubChapterVersion(**result.data[0])

        except Exception as e:
            logger.error(f"Error fetching version {version_id}: {e}")
            return None

    async def restore_version(
        self,
        version_id: UUID,
        user_id: UUID,
        create_new_version: bool = True
    ) -> SubChapter:
        """
        Restore a previous version as the current content.

        Args:
            version_id: Version to restore
            user_id: User performing the restore
            create_new_version: If True, creates a new version; if False, updates in place

        Returns:
            Updated SubChapter

        Raises:
            ValueError: If version not found
        """
        try:
            # 1. Get the version to restore
            version_result = self.supabase.table("sub_chapter_versions")\
                .select("*")\
                .eq("id", str(version_id))\
                .execute()

            if not version_result.data:
                raise ValueError(f"Version {version_id} not found")

            version = version_result.data[0]
            sub_chapter_id = UUID(version["sub_chapter_id"])

            # Set all versions to is_current = false
            self.supabase.table("sub_chapter_versions")\
                .update({"is_current": False})\
                .eq("sub_chapter_id", str(sub_chapter_id))\
                .execute()

            if create_new_version:
                # Create a new version with the restored content
                next_version = await self._get_next_version_number(sub_chapter_id)

                new_version_data = {
                    "sub_chapter_id": str(sub_chapter_id),
                    "version_number": next_version,
                    "content": version["content"],
                    "word_count": version["word_count"],
                    "snapshot_metadata": version.get("snapshot_metadata"),
                    "is_ai_generated": False,
                    "is_current": True,
                    "change_description": f"Restored from version {version['version_number']}",
                    "created_by_user_id": str(user_id)
                }

                self.supabase.table("sub_chapter_versions")\
                    .insert(new_version_data)\
                    .execute()
            else:
                # Just mark the restored version as current
                self.supabase.table("sub_chapter_versions")\
                    .update({"is_current": True})\
                    .eq("id", str(version_id))\
                    .execute()

            # 2. Update sub_chapter with restored content
            update_data = {
                "content": version["content"],
                "word_count": version["word_count"],
                "status": "completed",
                "updated_at": datetime.utcnow().isoformat()
            }

            result = self.supabase.table("sub_chapters")\
                .update(update_data)\
                .eq("id", str(sub_chapter_id))\
                .execute()

            if not result.data:
                raise Exception("Failed to restore version")

            logger.info(f"Restored version {version_id} for sub-chapter {sub_chapter_id}")

            return SubChapter(**result.data[0])

        except Exception as e:
            logger.error(f"Error restoring version {version_id}: {e}")
            raise

    # ========================================================================
    # Helper Methods
    # ========================================================================

    async def _get_next_version_number(self, sub_chapter_id: UUID) -> int:
        """
        Get the next version number for a sub-chapter.

        Args:
            sub_chapter_id: Sub-chapter identifier

        Returns:
            Next version number (1-indexed)
        """
        try:
            # Try using RPC function first
            try:
                result = self.supabase.rpc(
                    "get_next_version_number",
                    {"sub_chapter_uuid": str(sub_chapter_id)}
                ).execute()

                if result.data is not None:
                    return result.data
            except:
                pass  # Fall back to manual query

            # Fallback: query manually
            max_result = self.supabase.table("sub_chapter_versions")\
                .select("version_number")\
                .eq("sub_chapter_id", str(sub_chapter_id))\
                .order("version_number", desc=True)\
                .limit(1)\
                .execute()

            if max_result.data:
                return max_result.data[0]["version_number"] + 1

            return 1  # First version

        except Exception as e:
            logger.error(f"Error getting next version number: {e}")
            return 1

    async def _verify_character_ownership(
        self,
        character_id: UUID,
        trilogy_id: str,
        user_id: UUID
    ) -> None:
        """
        Verify that a character belongs to the specified trilogy.

        Args:
            character_id: Character identifier
            trilogy_id: Expected trilogy identifier
            user_id: User identifier (for RLS)

        Raises:
            ValueError: If character doesn't exist or doesn't belong to trilogy
        """
        try:
            result = self.supabase.table("characters")\
                .select("trilogy_id")\
                .eq("id", str(character_id))\
                .execute()

            if not result.data:
                raise ValueError(f"Character {character_id} not found")

            if result.data[0]["trilogy_id"] != trilogy_id:
                raise ValueError(f"Character {character_id} does not belong to trilogy {trilogy_id}")

        except Exception as e:
            logger.error(f"Error verifying character ownership: {e}")
            raise

    async def update_version_description(
        self,
        version_id: UUID,
        change_description: str,
        user_id: UUID
    ) -> Optional[SubChapterVersion]:
        """
        Update the change_description field for a specific version.

        Epic 7 Story 3: Allow users to document reasoning behind content changes.

        Args:
            version_id: Version identifier
            change_description: User's description of the change
            user_id: User making the update (for RLS verification)

        Returns:
            Updated SubChapterVersion or None if not found

        Raises:
            ValueError: If version not found or unauthorized
        """
        try:
            # Update the description (RLS will ensure user owns the version)
            result = self.supabase.table("sub_chapter_versions")\
                .update({
                    "change_description": change_description,
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("id", str(version_id))\
                .execute()

            if not result.data:
                return None

            version_data = result.data[0]

            # Get sub_chapter_id to check current version
            sub_chapter_result = self.supabase.table("sub_chapters")\
                .select("id, content")\
                .eq("id", version_data["sub_chapter_id"])\
                .execute()

            is_current = False
            if sub_chapter_result.data:
                # Check if this version's content matches current content
                is_current = (version_data["content"] == sub_chapter_result.data[0]["content"])

            return SubChapterVersion(
                id=version_data["id"],
                sub_chapter_id=version_data["sub_chapter_id"],
                version_number=version_data["version_number"],
                content=version_data["content"],
                word_count=version_data["word_count"],
                change_description=version_data.get("change_description"),
                snapshot_metadata=version_data.get("snapshot_metadata"),
                generated_by_model=version_data.get("generated_by_model"),
                generation_job_id=version_data.get("generation_job_id"),
                is_ai_generated=version_data.get("is_ai_generated", False),
                created_at=version_data["created_at"],
                created_by_user_id=version_data.get("created_by_user_id"),
                is_current=is_current
            )

        except Exception as e:
            logger.error(f"Error updating version description: {e}")
            raise
