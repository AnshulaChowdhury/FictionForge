"""
Character API Routes - Epic 2

Endpoints for managing characters within trilogy projects.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from api.models.character import (
    CharacterCreate,
    CharacterUpdate,
    CharacterResponse,
    CharacterListResponse,
    CharacterDeleteResponse,
)
from api.services.character_manager import (
    CharacterManager,
    CharacterCreationError,
    CharacterNotFoundError,
    CharacterUpdateError,
    CharacterDeletionError,
)
from api.middleware.auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/characters", tags=["characters"])


@router.post(
    "",
    response_model=CharacterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new character",
    description="""
    Create a new character for a trilogy project.

    Epic 2 Implementation:
    - Creates character with name, description, traits, and character arc
    - Associates character with a trilogy
    - Returns complete character data
    - Validates user ownership of the trilogy

    Authentication required.
    """,
)
async def create_character(
    request: CharacterCreate,
    user_id: str = Depends(get_current_user_id),
) -> CharacterResponse:
    """
    Create a new character.

    Request Body:
    - trilogy_id (required): UUID of the parent trilogy
    - name (required): Character name (max 100 chars)
    - description (optional): Character description (max 2000 chars)
    - traits (optional): Structured character traits (personality, speech patterns, etc.)
    - character_arc (optional): Character development arc (max 3000 chars)

    Returns:
    - Complete character data with ID and timestamps
    """
    logger.info(f"=== CREATE CHARACTER ENDPOINT CALLED ===")
    logger.info(f"User ID: {user_id}")
    logger.info(f"Character name: {request.name}, Trilogy: {request.trilogy_id}")

    try:
        manager = CharacterManager(user_id=user_id)
        response = await manager.create_character(request)
        logger.info(f"Character created successfully: {response.id}")
        return response

    except CharacterCreationError as e:
        logger.error(f"CharacterCreationError: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
    except CharacterNotFoundError as e:
        logger.error(f"Trilogy not found: {str(e)}", exc_info=True)
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
    "/trilogy/{trilogy_id}",
    response_model=CharacterListResponse,
    summary="List characters for a trilogy",
    description="""
    Get all characters for a specific trilogy.

    Results are sorted by creation date (oldest first).
    Row-Level Security ensures users only see characters from their own trilogies.

    Authentication required.
    """,
)
async def list_trilogy_characters(
    trilogy_id: str,
    user_id: str = Depends(get_current_user_id),
) -> CharacterListResponse:
    """
    Get all characters for a trilogy.

    Path Parameters:
    - trilogy_id: UUID of the trilogy

    Returns:
    - List of characters with total count
    """
    logger.info(f"=== LIST CHARACTERS ENDPOINT CALLED ===")
    logger.info(f"User ID: {user_id}, Trilogy: {trilogy_id}")

    try:
        manager = CharacterManager(user_id=user_id)
        response = await manager.get_trilogy_characters(trilogy_id)
        logger.info(f"Retrieved {response.total} characters")
        return response

    except CharacterNotFoundError as e:
        logger.error(f"Trilogy not found: {str(e)}", exc_info=True)
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
    response_model=CharacterListResponse,
    summary="List characters for a book",
    description="""
    Get all characters assigned to a specific book.

    Only returns characters that have been explicitly assigned to this book.
    Useful for filtering POV character selection in chapter creation.

    Authentication required.
    """,
)
async def list_book_characters(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
) -> CharacterListResponse:
    """
    Get all characters assigned to a book.

    Path Parameters:
    - book_id: UUID of the book

    Returns:
    - List of characters assigned to this book
    """
    logger.info(f"=== LIST BOOK CHARACTERS ENDPOINT CALLED ===")
    logger.info(f"User ID: {user_id}, Book: {book_id}")

    try:
        manager = CharacterManager(user_id=user_id)
        response = await manager.get_characters_by_book(book_id)
        logger.info(f"Retrieved {response.total} characters for book")
        return response

    except CharacterNotFoundError as e:
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
    "/{character_id}",
    response_model=CharacterResponse,
    summary="Get a single character",
    description="""
    Get detailed information for a specific character.

    Validates user ownership via the parent trilogy.

    Authentication required.
    """,
)
async def get_character(
    character_id: str,
    user_id: str = Depends(get_current_user_id),
) -> CharacterResponse:
    """
    Get a single character by ID.

    Path Parameters:
    - character_id: UUID of the character

    Returns:
    - Complete character data
    """
    logger.info(f"=== GET CHARACTER ENDPOINT CALLED ===")
    logger.info(f"User ID: {user_id}, Character ID: {character_id}")

    try:
        manager = CharacterManager(user_id=user_id)
        response = await manager.get_character(character_id)
        logger.info(f"Character retrieved: {response.name}")
        return response

    except CharacterNotFoundError as e:
        logger.error(f"Character not found: {str(e)}", exc_info=True)
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
    "/{character_id}",
    response_model=CharacterResponse,
    summary="Update a character",
    description="""
    Update an existing character's details.

    All fields are optional - only provided fields will be updated.
    Validates user ownership via the parent trilogy.

    Authentication required.
    """,
)
async def update_character(
    character_id: str,
    request: CharacterUpdate,
    user_id: str = Depends(get_current_user_id),
) -> CharacterResponse:
    """
    Update a character.

    Path Parameters:
    - character_id: UUID of the character to update

    Request Body (all optional):
    - name: Updated character name
    - description: Updated description
    - traits: Updated character traits
    - character_arc: Updated character arc

    Returns:
    - Updated character data
    """
    logger.info(f"=== UPDATE CHARACTER ENDPOINT CALLED ===")
    logger.info(f"User ID: {user_id}, Character ID: {character_id}")

    try:
        manager = CharacterManager(user_id=user_id)
        response = await manager.update_character(character_id, request)
        logger.info(f"Character updated: {response.name}")
        return response

    except CharacterNotFoundError as e:
        logger.error(f"Character not found: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except CharacterUpdateError as e:
        logger.error(f"CharacterUpdateError: {str(e)}", exc_info=True)
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
    "/{character_id}",
    response_model=CharacterDeleteResponse,
    summary="Delete a character",
    description="""
    Delete a character from the trilogy.

    WARNING: This will cascade delete all chapters and sub-chapters associated with this character.
    Validates user ownership via the parent trilogy.

    Authentication required.
    """,
)
async def delete_character(
    character_id: str,
    user_id: str = Depends(get_current_user_id),
) -> CharacterDeleteResponse:
    """
    Delete a character.

    Path Parameters:
    - character_id: UUID of the character to delete

    Returns:
    - Confirmation message with deleted character ID
    """
    logger.info(f"=== DELETE CHARACTER ENDPOINT CALLED ===")
    logger.info(f"User ID: {user_id}, Character ID: {character_id}")

    try:
        manager = CharacterManager(user_id=user_id)
        response = await manager.delete_character(character_id)
        logger.info(f"Character deleted: {character_id}")
        return response

    except CharacterNotFoundError as e:
        logger.error(f"Character not found: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except CharacterDeletionError as e:
        logger.error(f"CharacterDeletionError: {str(e)}", exc_info=True)
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
