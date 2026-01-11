"""
Book API Routes

Simple endpoint for fetching individual book details.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from api.middleware.auth import get_current_user_id
from api.utils.supabase_client import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/books", tags=["books"])


class UpdateBookRequest(BaseModel):
    """Request model for updating book details."""
    title: str = Field(..., min_length=1, max_length=200, description="Book title")


@router.get(
    "/{book_id}",
    summary="Get a single book",
    description="""
    Get a book by ID with ownership verification.

    Validates user owns the book via the parent trilogy.

    Authentication required.
    """,
)
async def get_book(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """
    Get a single book by ID.

    Path Parameters:
    - book_id: UUID of the book

    Returns:
    - Book data with trilogy_id
    """
    logger.info(f"=== GET BOOK ENDPOINT CALLED ===")
    logger.info(f"User ID: {user_id}, Book ID: {book_id}")

    try:
        # Fetch book with trilogy to verify ownership
        response = (
            supabase.table("books")
            .select("*, trilogy_projects!inner(user_id)")
            .eq("id", book_id)
            .execute()
        )

        if not response.data or len(response.data) == 0:
            logger.warning(f"Book {book_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book {book_id} not found"
            )

        book_data = response.data[0]

        # Verify user ownership
        if book_data["trilogy_projects"]["user_id"] != user_id:
            logger.warning(f"User {user_id} doesn't own book {book_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book {book_id} not found"
            )

        # Remove nested trilogy data from response
        trilogy_id = book_data.get("trilogy_id")
        book_data.pop("trilogy_projects", None)

        logger.info(f"Book retrieved: {book_data.get('title')}")
        return book_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        ) from e


@router.put(
    "/{book_id}",
    summary="Update a book",
    description="""
    Update book details (currently supports title only).

    Validates user owns the book via the parent trilogy.

    Authentication required.
    """,
)
async def update_book(
    book_id: str,
    request: UpdateBookRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Update a book's details.

    Path Parameters:
    - book_id: UUID of the book

    Request Body:
    - title: New title for the book

    Returns:
    - Updated book data
    """
    logger.info(f"=== UPDATE BOOK ENDPOINT CALLED ===")
    logger.info(f"User ID: {user_id}, Book ID: {book_id}, New Title: {request.title}")

    try:
        # First, verify ownership
        verify_response = (
            supabase.table("books")
            .select("*, trilogy_projects!inner(user_id)")
            .eq("id", book_id)
            .execute()
        )

        if not verify_response.data or len(verify_response.data) == 0:
            logger.warning(f"Book {book_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book {book_id} not found"
            )

        book_data = verify_response.data[0]

        # Verify user ownership
        if book_data["trilogy_projects"]["user_id"] != user_id:
            logger.warning(f"User {user_id} doesn't own book {book_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this book"
            )

        # Update the book
        update_response = (
            supabase.table("books")
            .update({"title": request.title})
            .eq("id", book_id)
            .execute()
        )

        if not update_response.data or len(update_response.data) == 0:
            logger.error(f"Failed to update book {book_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update book"
            )

        updated_book = update_response.data[0]
        logger.info(f"Book updated successfully: {updated_book.get('title')}")
        return updated_book

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        ) from e
