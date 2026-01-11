"""
Trilogy API Routes - Epic 1

Endpoints for managing trilogy projects.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from api.models.trilogy import CreateTrilogyRequest, UpdateTrilogyRequest, CreateTrilogyResponse, TrilogyResponse, BookResponse, TrilogyStatsResponse
from api.services.trilogy_manager import TrilogyManager, TrilogyCreationError
from api.middleware.auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trilogy", tags=["trilogy"])


@router.post(
    "/create",
    response_model=CreateTrilogyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new trilogy project",
    description="""
    Create a new trilogy project with 3 auto-generated books.

    Epic 1 Implementation:
    - Validates required fields (title, author)
    - Creates trilogy record in database
    - Automatically generates 3 books (Book 1, Book 2, Book 3)
    - Returns complete trilogy + books data
    - Rolls back on any error

    Authentication required.
    """,
)
async def create_trilogy(
    request: CreateTrilogyRequest,
    user_id: str = Depends(get_current_user_id),
) -> CreateTrilogyResponse:
    """
    Create a new trilogy project.

    Request Body:
    - title (required): Trilogy title (max 100 chars)
    - description (optional): Trilogy description (max 2000 chars)
    - author (required): Author name (max 50 chars)
    - narrative_overview (optional): High-level narrative (max 2000 chars)

    Returns:
    - trilogy: Created trilogy metadata
    - books: Array of 3 auto-generated books
    - message: Success message
    """
    logger.info(f"=== CREATE TRILOGY ENDPOINT CALLED ===")
    logger.info(f"User ID: {user_id}")
    logger.info(f"Request data: title={request.title}, author={request.author}")

    try:
        logger.info("Creating TrilogyManager instance...")
        manager = TrilogyManager(user_id=user_id)
        logger.info("TrilogyManager created successfully")

        logger.info("Calling manager.create_project()...")
        response = await manager.create_project(request)
        logger.info(f"Trilogy created successfully: {response.trilogy.id}")

        return response

    except TrilogyCreationError as e:
        logger.error(f"TrilogyCreationError: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error in create_trilogy: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        ) from e


@router.get(
    "",
    response_model=list[TrilogyResponse],
    summary="List all user's trilogies",
    description="""
    Get all trilogy projects for the authenticated user.

    Results are sorted by creation date (newest first).
    Row-Level Security (RLS) ensures users only see their own trilogies.

    Authentication required.
    """,
)
async def list_trilogies(
    user_id: str = Depends(get_current_user_id),
) -> list[TrilogyResponse]:
    """
    Get all trilogies for the current user.

    Returns:
    - Array of trilogy metadata (empty array if none exist)
    """
    manager = TrilogyManager(user_id=user_id)

    try:
        trilogies = await manager.get_user_trilogies()
        return trilogies

    except TrilogyCreationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.get(
    "/active/stats",
    response_model=TrilogyStatsResponse,
    summary="Get active trilogy statistics",
    description="""
    Get comprehensive statistics for the user's most recently updated trilogy.

    Returns aggregated metrics including:
    - Total word count across all books
    - Estimated pages
    - Chapter completion status
    - Per-book progress percentages

    Used for the dashboard hero section.
    Returns 404 if user has no trilogies.

    Authentication required.
    """,
)
async def get_active_trilogy_stats(
    user_id: str = Depends(get_current_user_id),
) -> TrilogyStatsResponse:
    """
    Get statistics for the most recently updated trilogy.

    Returns:
    - Comprehensive trilogy statistics including word counts, pages, and progress

    Raises:
    - 404: If user has no trilogies
    """
    manager = TrilogyManager(user_id=user_id)

    try:
        stats = await manager.get_active_trilogy_stats()

        if stats is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No trilogies found for this user",
            )

        return stats

    except TrilogyCreationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.get(
    "/{trilogy_id}",
    response_model=TrilogyResponse,
    summary="Get a specific trilogy",
    description="""
    Get detailed information about a specific trilogy.

    RLS ensures users can only access their own trilogies.
    Returns 404 if trilogy doesn't exist or user doesn't have access.

    Authentication required.
    """,
)
async def get_trilogy(
    trilogy_id: str,
    user_id: str = Depends(get_current_user_id),
) -> TrilogyResponse:
    """
    Get a specific trilogy by ID.

    Path Parameters:
    - trilogy_id: UUID of the trilogy

    Returns:
    - Trilogy metadata

    Raises:
    - 404: If trilogy not found or user doesn't have access
    """
    manager = TrilogyManager(user_id=user_id)

    try:
        trilogy = await manager.get_trilogy_by_id(trilogy_id)

        if trilogy is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trilogy with ID {trilogy_id} not found or access denied",
            )

        return trilogy

    except TrilogyCreationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.get(
    "/{trilogy_id}/books",
    response_model=list[BookResponse],
    summary="Get books for a trilogy",
    description="""
    Get all books for a specific trilogy.

    Returns books sorted by book_number (1, 2, 3).
    RLS ensures users can only access books for their own trilogies.

    Authentication required.
    """,
)
async def get_trilogy_books(
    trilogy_id: str,
    user_id: str = Depends(get_current_user_id),
) -> list[BookResponse]:
    """
    Get all books for a specific trilogy.

    Path Parameters:
    - trilogy_id: UUID of the trilogy

    Returns:
    - Array of books (sorted by book_number)

    Raises:
    - 404: If trilogy not found or user doesn't have access
    """
    manager = TrilogyManager(user_id=user_id)

    try:
        # First verify user has access to this trilogy
        trilogy = await manager.get_trilogy_by_id(trilogy_id)
        if trilogy is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trilogy with ID {trilogy_id} not found or access denied",
            )

        # Fetch books for the trilogy
        books = await manager.get_trilogy_books(trilogy_id)
        return books

    except TrilogyCreationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.put(
    "/{trilogy_id}",
    response_model=TrilogyResponse,
    summary="Update a trilogy",
    description="""
    Update a trilogy's metadata.

    Only provided fields will be updated - unspecified fields remain unchanged.
    RLS ensures users can only update their own trilogies.

    Authentication required.
    """,
)
async def update_trilogy(
    trilogy_id: str,
    request: UpdateTrilogyRequest,
    user_id: str = Depends(get_current_user_id),
) -> TrilogyResponse:
    """
    Update a trilogy by ID.

    Path Parameters:
    - trilogy_id: UUID of the trilogy to update

    Request Body:
    - title (optional): New title
    - description (optional): New description
    - author (optional): New author name
    - narrative_overview (optional): New narrative overview

    Returns:
    - Updated trilogy metadata

    Raises:
    - 404: If trilogy not found or user doesn't have access
    - 500: If update fails
    """
    manager = TrilogyManager(user_id=user_id)

    try:
        updated_trilogy = await manager.update_trilogy(trilogy_id, request)

        if updated_trilogy is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trilogy with ID {trilogy_id} not found or access denied",
            )

        return updated_trilogy

    except TrilogyCreationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.patch(
    "/{trilogy_id}/set-primary",
    response_model=TrilogyResponse,
    summary="Set trilogy as primary",
    description="""
    Set this trilogy as the user's primary trilogy.

    Automatically unsets any other primary trilogy for this user.
    Only one trilogy can be primary at a time.

    The primary trilogy appears in the dashboard hero section.

    Authentication required.
    """,
)
async def set_primary_trilogy(
    trilogy_id: str,
    user_id: str = Depends(get_current_user_id),
) -> TrilogyResponse:
    """
    Set a trilogy as primary.

    Path Parameters:
    - trilogy_id: UUID of the trilogy to set as primary

    Returns:
    - Updated trilogy metadata

    Raises:
    - 404: If trilogy not found or user doesn't have access
    - 500: If update fails
    """
    manager = TrilogyManager(user_id=user_id)

    try:
        updated_trilogy = await manager.set_primary_trilogy(trilogy_id)

        if updated_trilogy is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trilogy with ID {trilogy_id} not found or access denied",
            )

        return updated_trilogy

    except TrilogyCreationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.patch(
    "/{trilogy_id}/unset-primary",
    response_model=TrilogyResponse,
    summary="Unset trilogy as primary",
    description="""
    Unset this trilogy as the user's primary trilogy.

    After this operation, no trilogy will be marked as primary,
    allowing the user to select a different primary trilogy.

    Authentication required.
    """,
)
async def unset_primary_trilogy(
    trilogy_id: str,
    user_id: str = Depends(get_current_user_id),
) -> TrilogyResponse:
    """
    Unset a trilogy as primary.

    Path Parameters:
    - trilogy_id: UUID of the trilogy to unset as primary

    Returns:
    - Updated trilogy metadata

    Raises:
    - 404: If trilogy not found or user doesn't have access
    - 500: If update fails
    """
    manager = TrilogyManager(user_id=user_id)

    try:
        updated_trilogy = await manager.unset_primary_trilogy(trilogy_id)

        if updated_trilogy is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trilogy with ID {trilogy_id} not found or access denied",
            )

        return updated_trilogy

    except TrilogyCreationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.delete(
    "/{trilogy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a trilogy",
    description="""
    Delete a trilogy and all associated data.

    This will CASCADE delete:
    - All books in the trilogy
    - All chapters and sub-chapters
    - All characters
    - All world rules
    - All other associated records

    This action cannot be undone.
    RLS ensures users can only delete their own trilogies.

    Authentication required.
    """,
)
async def delete_trilogy(
    trilogy_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """
    Delete a trilogy by ID.

    Path Parameters:
    - trilogy_id: UUID of the trilogy to delete

    Returns:
    - 204 No Content on success

    Raises:
    - 404: If trilogy not found or user doesn't have access
    - 500: If deletion fails
    """
    manager = TrilogyManager(user_id=user_id)

    try:
        await manager.delete_trilogy(trilogy_id)
        return None  # 204 No Content

    except TrilogyCreationError as e:
        if "not found or access denied" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            ) from e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
