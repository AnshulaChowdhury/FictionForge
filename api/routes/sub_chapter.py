"""
Sub-Chapter API Routes for Epic 6

Provides endpoints for:
- Creating and managing sub-chapters
- Updating plot points with automatic review flagging
- Reordering sub-chapters within chapters
- Tracking progress metrics
- Regenerating content with version control
- Managing content review flags
- Version history and restoration
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

from api.middleware.auth import get_current_user_id
from api.models.sub_chapter import (
    SubChapterCreate,
    SubChapterUpdate,
    SubChapterContentUpdate,
    SubChapter,
    SubChapterCreateResponse,
    SubChapterReorderRequest,
    SubChapterProgress,
    ChapterProgress,
    SubChapterRegenerateRequest,
    ChapterRegenerateRequest,
    RegenerateResponse,
    BulkRegenerateResponse,
    ContentReviewFlag,
    ContentReviewFlagResolve,
    SubChapterVersionListItem,
    SubChapterVersion,
    UpdateVersionDescriptionRequest
)
from api.services.sub_chapter_manager import SubChapterManager
from api.services.sub_chapter_update_service import SubChapterUpdateService
from api.services.sub_chapter_reorder_service import SubChapterReorderService
from api.services.progress_tracker import ProgressTracker
from api.services.sub_chapter_regeneration_service import SubChapterRegenerationService

router = APIRouter(prefix="/api/sub-chapters", tags=["sub-chapters"])


# ============================================================================
# Sub-Chapter CRUD Operations
# ============================================================================


@router.post("", response_model=SubChapterCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_sub_chapter(
    data: SubChapterCreate,
    user_id: str = Depends(get_current_user_id)
):
    """
    Create a new sub-chapter and optionally trigger content generation.

    The character_id is automatically inherited from the parent chapter via database trigger.

    **Process:**
    1. Creates sub-chapter stub with sequential sub_chapter_number
    2. Queues background job for content generation (if plot_points provided)
    3. Returns job_id for tracking progress via WebSocket

    **Returns:**
    - `sub_chapter_id`: Created sub-chapter identifier
    - `generation_job_id`: Job ID for tracking generation progress
    - `websocket_url`: WebSocket endpoint for real-time updates
    """
    try:
        manager = SubChapterManager()
        user_id_uuid = UUID(user_id)

        result = await manager.create_sub_chapter(
            data=data,
            user_id=user_id_uuid,
            trigger_generation=bool(data.plot_points)
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{sub_chapter_id}", response_model=SubChapter)
async def get_sub_chapter(
    sub_chapter_id: UUID,
    user_id: str = Depends(get_current_user_id)
):
    """Get a single sub-chapter by ID."""
    try:
        manager = SubChapterManager()
        user_id_uuid = UUID(user_id)

        sub_chapter = await manager.get_sub_chapter(sub_chapter_id, user_id_uuid)

        if not sub_chapter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sub-chapter {sub_chapter_id} not found"
            )

        return sub_chapter

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/chapter/{chapter_id}", response_model=List[SubChapter])
async def list_sub_chapters(
    chapter_id: UUID,
    user_id: str = Depends(get_current_user_id)
):
    """List all sub-chapters for a chapter, ordered by sub_chapter_number."""
    try:
        manager = SubChapterManager()
        user_id_uuid = UUID(user_id)

        sub_chapters = await manager.list_sub_chapters(chapter_id, user_id_uuid)

        return sub_chapters

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{sub_chapter_id}", response_model=SubChapter)
async def update_sub_chapter(
    sub_chapter_id: UUID,
    data: SubChapterUpdate,
    user_id: str = Depends(get_current_user_id)
):
    """
    Update sub-chapter metadata (title, plot_points, status).

    **Note:** This does NOT modify content or word_count. Use regeneration for that.

    If plot_points are significantly changed (< 70% similarity), a review flag will
    be created automatically.
    """
    try:
        manager = SubChapterManager()
        user_id_uuid = UUID(user_id)

        sub_chapter = await manager.update_sub_chapter(sub_chapter_id, data, user_id_uuid)

        if not sub_chapter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sub-chapter {sub_chapter_id} not found"
            )

        return sub_chapter

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{sub_chapter_id}/content", response_model=SubChapter)
async def update_sub_chapter_content(
    sub_chapter_id: UUID,
    data: SubChapterContentUpdate,
    user_id: str = Depends(get_current_user_id)
):
    """
    Manually update sub-chapter content and create a new version.

    This endpoint allows users to manually edit the content of a sub-chapter.
    Each edit creates a new version in the version history with is_ai_generated=false.

    **Process:**
    1. Validates the content
    2. Calculates word count
    3. Creates a new version in sub_chapter_versions
    4. Updates the main sub_chapter record

    **Returns:**
    - Updated SubChapter with new content and word_count
    """
    try:
        manager = SubChapterManager()
        user_id_uuid = UUID(user_id)

        sub_chapter = await manager.update_content(sub_chapter_id, data, user_id_uuid)

        if not sub_chapter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sub-chapter {sub_chapter_id} not found"
            )

        return sub_chapter

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{sub_chapter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sub_chapter(
    sub_chapter_id: UUID,
    user_id: str = Depends(get_current_user_id)
):
    """
    Delete a sub-chapter and all its versions.

    CASCADE deletion automatically removes:
    - All versions (sub_chapter_versions)
    - All review flags (content_review_flags)
    """
    try:
        manager = SubChapterManager()
        user_id_uuid = UUID(user_id)

        success = await manager.delete_sub_chapter(sub_chapter_id, user_id_uuid)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sub-chapter {sub_chapter_id} not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================================
# Plot Points & Review Flags
# ============================================================================


@router.put("/{sub_chapter_id}/plot-points")
async def update_plot_points(
    sub_chapter_id: UUID,
    new_title: Optional[str] = None,
    new_plot_points: Optional[str] = None,
    user_id: str = Depends(get_current_user_id)
):
    """
    Update plot points with automatic similarity detection and flagging.

    If plot points change significantly (< 70% similarity), a review flag is created
    to alert the user that content may need regeneration.

    **Returns:**
    - `sub_chapter`: Updated sub-chapter
    - `flagged`: Whether a review flag was created
    - `similarity_score`: Text similarity score (0.0 to 1.0)
    - `should_regenerate`: Recommendation to regenerate content
    """
    try:
        service = SubChapterUpdateService()
        user_id_uuid = UUID(user_id)

        result = await service.update_plot_points(
            sub_chapter_id, new_title, new_plot_points, user_id_uuid
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{sub_chapter_id}/flags", response_model=List[ContentReviewFlag])
async def get_content_flags(
    sub_chapter_id: UUID,
    unresolved_only: bool = True,
    user_id: str = Depends(get_current_user_id)
):
    """Get content review flags for a sub-chapter."""
    try:
        service = SubChapterUpdateService()
        user_id_uuid = UUID(user_id)

        flags = await service.get_content_flags(sub_chapter_id, user_id_uuid, unresolved_only)

        return flags

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/flags/{flag_id}/resolve", status_code=status.HTTP_204_NO_CONTENT)
async def resolve_flag(
    flag_id: UUID,
    data: ContentReviewFlagResolve,
    user_id: str = Depends(get_current_user_id)
):
    """Mark a content review flag as resolved."""
    try:
        service = SubChapterUpdateService()
        user_id_uuid = UUID(user_id)

        success = await service.resolve_flag(flag_id, user_id_uuid, data.resolution_notes)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Flag {flag_id} not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================================
# Reordering Operations
# ============================================================================


@router.post("/{sub_chapter_id}/reorder", response_model=List[SubChapter])
async def reorder_sub_chapter(
    sub_chapter_id: UUID,
    data: SubChapterReorderRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Move a sub-chapter to a new position with automatic renumbering.

    All sub-chapter_numbers remain sequential (1, 2, 3...) with no gaps.

    **Parameters:**
    - `new_position`: 1-indexed position (1 = first, 2 = second, etc.)

    **Returns:**
    - List of all sub-chapters in new order
    """
    try:
        service = SubChapterReorderService()
        user_id_uuid = UUID(user_id)

        result = await service.reorder_sub_chapter(sub_chapter_id, data.new_position, user_id_uuid)

        return result

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{sub_chapter_id}/move-up", response_model=List[SubChapter])
async def move_sub_chapter_up(
    sub_chapter_id: UUID,
    user_id: str = Depends(get_current_user_id)
):
    """Move a sub-chapter up one position. Returns None if already at top."""
    try:
        service = SubChapterReorderService()
        user_id_uuid = UUID(user_id)

        result = await service.move_sub_chapter_up(sub_chapter_id, user_id_uuid)

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sub-chapter is already at the top position"
            )

        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{sub_chapter_id}/move-down", response_model=List[SubChapter])
async def move_sub_chapter_down(
    sub_chapter_id: UUID,
    user_id: str = Depends(get_current_user_id)
):
    """Move a sub-chapter down one position. Returns None if already at bottom."""
    try:
        service = SubChapterReorderService()
        user_id_uuid = UUID(user_id)

        result = await service.move_sub_chapter_down(sub_chapter_id, user_id_uuid)

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sub-chapter is already at the bottom position"
            )

        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================================
# Progress Tracking
# ============================================================================


@router.get("/{sub_chapter_id}/progress", response_model=SubChapterProgress)
async def get_sub_chapter_progress(
    sub_chapter_id: UUID,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get progress metrics for a sub-chapter.

    **Returns:**
    - `actual_word_count`: Current word count
    - `target_word_count`: Target word count
    - `percentage`: Progress percentage
    - `status`: not_started, in_progress, near_complete, or complete
    - `over_target`: Whether word count exceeds target
    """
    try:
        tracker = ProgressTracker()
        user_id_uuid = UUID(user_id)

        progress = await tracker.calculate_sub_chapter_progress(sub_chapter_id, user_id_uuid)

        return progress

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/chapter/{chapter_id}/progress", response_model=ChapterProgress)
async def get_chapter_progress(
    chapter_id: UUID,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get aggregate progress for a chapter including all sub-chapters.

    **Returns:**
    - Chapter-level progress metrics
    - List of all sub-chapter progress metrics
    - Completion counts
    """
    try:
        tracker = ProgressTracker()
        user_id_uuid = UUID(user_id)

        progress = await tracker.calculate_chapter_progress(chapter_id, user_id_uuid)

        return progress

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================================
# Content Regeneration
# ============================================================================


@router.post("/{sub_chapter_id}/regenerate", response_model=RegenerateResponse)
async def regenerate_sub_chapter(
    sub_chapter_id: UUID,
    data: SubChapterRegenerateRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Regenerate sub-chapter content as a new version.

    Allows changing character perspective and/or plot points before regeneration.
    All previous versions are preserved for rollback.

    **Process:**
    1. Updates character/plot points if provided
    2. Gets next version number
    3. Queues regeneration job
    4. Returns job_id for tracking via WebSocket

    **Returns:**
    - `sub_chapter_id`: Sub-chapter identifier
    - `new_version_number`: Version number being created
    - `generation_job_id`: Job ID for tracking
    - `websocket_url`: WebSocket endpoint for real-time updates
    """
    try:
        service = SubChapterRegenerationService()
        user_id_uuid = UUID(user_id)

        result = await service.regenerate_sub_chapter(
            sub_chapter_id=sub_chapter_id,
            user_id=user_id_uuid,
            new_character_id=data.new_character_id,
            new_plot_points=data.new_plot_points,
            change_description=data.change_description
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/chapter/{chapter_id}/regenerate", response_model=BulkRegenerateResponse)
async def regenerate_chapter(
    chapter_id: UUID,
    data: ChapterRegenerateRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Bulk regenerate all sub-chapters in a chapter with a new character.

    Useful for switching the entire chapter to a different character's perspective.

    The database trigger automatically:
    - Updates all sub-chapter character_ids
    - Creates review flags for each sub-chapter

    **Returns:**
    - `chapter_id`: Chapter identifier
    - `jobs`: List of regeneration jobs for each sub-chapter
    - `total_sub_chapters`: Total count of sub-chapters being regenerated
    """
    try:
        service = SubChapterRegenerationService()
        user_id_uuid = UUID(user_id)

        result = await service.regenerate_chapter(
            chapter_id=chapter_id,
            new_character_id=data.new_character_id,
            user_id=user_id_uuid,
            change_description=data.change_description
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================================
# Version Management
# ============================================================================


@router.get("/{sub_chapter_id}/versions", response_model=List[SubChapterVersionListItem])
async def get_version_history(
    sub_chapter_id: UUID,
    user_id: str = Depends(get_current_user_id)
):
    """Get version history for a sub-chapter, ordered by version number (newest first)."""
    try:
        service = SubChapterRegenerationService()
        user_id_uuid = UUID(user_id)

        versions = await service.get_version_history(sub_chapter_id, user_id_uuid)

        return versions

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/versions/{version_id}", response_model=SubChapterVersion)
async def get_version(
    version_id: UUID,
    user_id: str = Depends(get_current_user_id)
):
    """Get a specific version by ID, including full content."""
    try:
        service = SubChapterRegenerationService()
        user_id_uuid = UUID(user_id)

        version = await service.get_version(version_id, user_id_uuid)

        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {version_id} not found"
            )

        return version

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/versions/{version_id}/restore", response_model=SubChapter)
async def restore_version(
    version_id: UUID,
    create_new_version: bool = True,
    user_id: str = Depends(get_current_user_id)
):
    """
    Restore a previous version as the current content.

    **Parameters:**
    - `create_new_version`: If True, creates a new version entry; if False, updates in place

    **Returns:**
    - Updated SubChapter with restored content
    """
    try:
        service = SubChapterRegenerationService()
        user_id_uuid = UUID(user_id)

        sub_chapter = await service.restore_version(version_id, user_id_uuid, create_new_version)

        return sub_chapter

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/versions/{version_id}/description", response_model=SubChapterVersion)
async def update_version_description(
    version_id: UUID,
    data: UpdateVersionDescriptionRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Update the change_description field for a specific version.

    Epic 7 Story 3: Allow users to document reasoning behind content changes.

    **Parameters:**
    - `change_description`: User's description of the change (max 1000 chars)

    **Returns:**
    - Updated SubChapterVersion with new description
    """
    try:
        service = SubChapterRegenerationService()
        user_id_uuid = UUID(user_id)

        version = await service.update_version_description(
            version_id, data.change_description, user_id_uuid
        )

        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {version_id} not found"
            )

        return version

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
