"""
Chapter API Routes - Epic 4

Endpoints for managing chapters within books.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from api.models.chapter import (
    ChapterCreate,
    ChapterUpdate,
    ChapterResponse,
    ChapterListResponse,
    ChapterDeleteResponse,
    ChapterReorderRequest,
    ChapterProgressResponse,
    BookProgressResponse,
)
from api.services.chapter_manager import (
    ChapterManager,
    ChapterCreationError,
    ChapterNotFoundError,
    ChapterUpdateError,
    ChapterDeletionError,
    ChapterReorderError,
)
from api.middleware.auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chapters", tags=["chapters"])


@router.post(
    "",
    response_model=ChapterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chapter",
    description="""
    Create a new chapter for a book with automatic chapter number assignment.

    Epic 4 Implementation:
    - Creates chapter with POV character assignment
    - Auto-assigns next sequential chapter_number
    - Validates book and character ownership
    - Returns complete chapter data

    Authentication required.
    """,
)
async def create_chapter(
    request: ChapterCreate,
    user_id: str = Depends(get_current_user_id),
) -> ChapterResponse:
    """
    Create a new chapter.

    Request Body:
    - book_id (required): UUID of the parent book
    - character_id (required): UUID of POV character
    - title (required): Chapter title (max 255 chars)
    - description (optional): Plot notes (max 5000 chars)
    - target_word_count (optional): Target words for chapter

    Returns:
    - Complete chapter data with auto-assigned chapter_number
    """
    logger.info(f"=== CREATE CHAPTER ENDPOINT CALLED ===")
    logger.info(f"User ID: {user_id}")
    logger.info(f"Chapter title: {request.title}, Book: {request.book_id}")

    try:
        manager = ChapterManager(user_id=user_id)
        response = await manager.create_chapter(request)
        logger.info(f"Chapter created successfully: {response.id}")
        return response

    except ChapterCreationError as e:
        logger.error(f"ChapterCreationError: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
    except ChapterNotFoundError as e:
        logger.error(f"Book/Character not found: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        ) from e


@router.get(
    "/book/{book_id}",
    response_model=ChapterListResponse,
    summary="List chapters for a book",
    description="""
    Get all chapters for a specific book, ordered by chapter_number.

    Results are sorted sequentially (1, 2, 3...).
    Row-Level Security ensures users only see chapters from their own books.

    Authentication required.
    """,
)
async def list_book_chapters(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
) -> ChapterListResponse:
    """
    Get all chapters for a book.

    Path Parameters:
    - book_id: UUID of the book

    Returns:
    - List of chapters with total count
    """
    logger.info(f"=== LIST CHAPTERS ENDPOINT CALLED ===")
    logger.info(f"User ID: {user_id}, Book: {book_id}")

    try:
        manager = ChapterManager(user_id=user_id)
        response = await manager.get_book_chapters(book_id)
        logger.info(f"Retrieved {response.total} chapters")
        return response

    except ChapterNotFoundError as e:
        logger.error(f"Book not found: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        ) from e


@router.get(
    "/{chapter_id}",
    response_model=ChapterResponse,
    summary="Get a single chapter",
    description="""
    Get detailed information for a specific chapter.

    Validates user ownership via the parent book's trilogy.

    Authentication required.
    """,
)
async def get_chapter(
    chapter_id: str,
    user_id: str = Depends(get_current_user_id),
) -> ChapterResponse:
    """
    Get a single chapter by ID.

    Path Parameters:
    - chapter_id: UUID of the chapter

    Returns:
    - Complete chapter data
    """
    logger.info(f"=== GET CHAPTER ENDPOINT CALLED ===")
    logger.info(f"User ID: {user_id}, Chapter ID: {chapter_id}")

    try:
        manager = ChapterManager(user_id=user_id)
        response = await manager.get_chapter(chapter_id)
        logger.info(f"Chapter retrieved: {response.title}")
        return response

    except ChapterNotFoundError as e:
        logger.error(f"Chapter not found: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        ) from e


@router.put(
    "/{chapter_id}",
    response_model=ChapterResponse,
    summary="Update a chapter",
    description="""
    Update an existing chapter's details.

    All fields are optional - only provided fields will be updated.
    Validates user ownership via the parent book's trilogy.

    Authentication required.
    """,
)
async def update_chapter(
    chapter_id: str,
    request: ChapterUpdate,
    user_id: str = Depends(get_current_user_id),
) -> ChapterResponse:
    """
    Update a chapter.

    Path Parameters:
    - chapter_id: UUID of the chapter to update

    Request Body (all optional):
    - title: Updated chapter title
    - description: Updated plot notes
    - character_id: Updated POV character
    - target_word_count: Updated target

    Returns:
    - Updated chapter data
    """
    logger.info(f"=== UPDATE CHAPTER ENDPOINT CALLED ===")
    logger.info(f"User ID: {user_id}, Chapter ID: {chapter_id}")

    try:
        manager = ChapterManager(user_id=user_id)
        response = await manager.update_chapter(chapter_id, request)
        logger.info(f"Chapter updated: {response.title}")
        return response

    except ChapterNotFoundError as e:
        logger.error(f"Chapter not found: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ChapterUpdateError as e:
        logger.error(f"ChapterUpdateError: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        ) from e


@router.delete(
    "/{chapter_id}",
    response_model=ChapterDeleteResponse,
    summary="Delete a chapter",
    description="""
    Delete a chapter from the book.

    WARNING: This will CASCADE delete all sub-chapters associated with this chapter.
    Remaining chapters are automatically renumbered to maintain sequential order.
    Validates user ownership via the parent book's trilogy.

    Authentication required.
    """,
)
async def delete_chapter(
    chapter_id: str,
    user_id: str = Depends(get_current_user_id),
) -> ChapterDeleteResponse:
    """
    Delete a chapter.

    Path Parameters:
    - chapter_id: UUID of the chapter to delete

    Returns:
    - Confirmation message with deleted chapter ID
    """
    logger.info(f"=== DELETE CHAPTER ENDPOINT CALLED ===")
    logger.info(f"User ID: {user_id}, Chapter ID: {chapter_id}")

    try:
        manager = ChapterManager(user_id=user_id)
        response = await manager.delete_chapter(chapter_id)
        logger.info(f"Chapter deleted: {chapter_id}")
        return response

    except ChapterNotFoundError as e:
        logger.error(f"Chapter not found: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ChapterDeletionError as e:
        logger.error(f"ChapterDeletionError: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        ) from e


@router.post(
    "/{chapter_id}/reorder",
    response_model=ChapterListResponse,
    summary="Reorder a chapter",
    description="""
    Move a chapter to a new position within the book.

    All affected chapters are automatically renumbered to maintain sequential order.
    Chapter numbers always remain 1, 2, 3... with no gaps.

    Authentication required.
    """,
)
async def reorder_chapter(
    chapter_id: str,
    request: ChapterReorderRequest,
    user_id: str = Depends(get_current_user_id),
) -> ChapterListResponse:
    """
    Reorder a chapter to a new position.

    Path Parameters:
    - chapter_id: UUID of the chapter to move

    Request Body:
    - new_position: Target chapter_number (1-based index)

    Returns:
    - Complete list of chapters in new order
    """
    logger.info(f"=== REORDER CHAPTER ENDPOINT CALLED ===")
    logger.info(f"User ID: {user_id}, Chapter ID: {chapter_id}, New Position: {request.new_position}")

    try:
        manager = ChapterManager(user_id=user_id)
        response = await manager.reorder_chapter(chapter_id, request.new_position)
        logger.info(f"Chapter reordered successfully")
        return response

    except ChapterNotFoundError as e:
        logger.error(f"Chapter not found: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ChapterReorderError as e:
        logger.error(f"ChapterReorderError: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        ) from e


@router.get(
    "/{chapter_id}/progress",
    response_model=ChapterProgressResponse,
    summary="Get chapter progress",
    description="""
    Get word count progress for a chapter.

    Calculates completion percentage based on target word count.
    Status: not_started, in_progress, complete, over_target.

    Authentication required.
    """,
)
async def get_chapter_progress(
    chapter_id: str,
    user_id: str = Depends(get_current_user_id),
) -> ChapterProgressResponse:
    """
    Get chapter progress metrics.

    Path Parameters:
    - chapter_id: UUID of the chapter

    Returns:
    - Progress data with percentage and status
    """
    logger.info(f"=== GET CHAPTER PROGRESS ENDPOINT CALLED ===")
    logger.info(f"User ID: {user_id}, Chapter ID: {chapter_id}")

    try:
        manager = ChapterManager(user_id=user_id)
        response = await manager.get_chapter_progress(chapter_id)
        logger.info(f"Chapter progress: {response.percentage}% ({response.status})")
        return response

    except ChapterNotFoundError as e:
        logger.error(f"Chapter not found: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        ) from e


@router.get(
    "/book/{book_id}/progress",
    response_model=BookProgressResponse,
    summary="Get book progress summary",
    description="""
    Get aggregated progress for all chapters in a book.

    Provides book-level metrics and chapter status breakdown.

    Authentication required.
    """,
)
async def get_book_progress(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
) -> BookProgressResponse:
    """
    Get book-level progress summary.

    Path Parameters:
    - book_id: UUID of the book

    Returns:
    - Book progress with chapter status breakdown
    """
    logger.info(f"=== GET BOOK PROGRESS ENDPOINT CALLED ===")
    logger.info(f"User ID: {user_id}, Book ID: {book_id}")

    try:
        manager = ChapterManager(user_id=user_id)
        response = await manager.get_book_progress(book_id)
        logger.info(f"Book progress: {response.overall_percentage}%")
        return response

    except ChapterNotFoundError as e:
        logger.error(f"Book not found: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        ) from e
