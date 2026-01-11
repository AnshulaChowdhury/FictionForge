"""
CharacterManager Service - Epic 2

Handles character CRUD operations for trilogy projects.
Characters are the core entities with unique voices and perspectives.
"""

import logging
from typing import List, Optional
from api.models.character import (
    CharacterCreate,
    CharacterUpdate,
    CharacterResponse,
    CharacterListResponse,
    CharacterDeleteResponse,
    CharacterTraits,
)
from api.utils.supabase_client import supabase
from postgrest.exceptions import APIError

logger = logging.getLogger(__name__)


class CharacterNotFoundError(Exception):
    """Raised when a character is not found."""
    pass


class CharacterCreationError(Exception):
    """Raised when character creation fails."""
    pass


class CharacterUpdateError(Exception):
    """Raised when character update fails."""
    pass


class CharacterDeletionError(Exception):
    """Raised when character deletion fails."""
    pass


class CharacterManager:
    """
    Manages character operations for trilogy projects.

    Epic 2: Full CRUD operations for characters.
    """

    def __init__(self, user_id: str):
        """
        Initialize CharacterManager for a specific user.

        Args:
            user_id: UUID of the authenticated user (from JWT token)
        """
        self.user_id = user_id

    async def create_character(
        self, request: CharacterCreate
    ) -> CharacterResponse:
        """
        Create a new character in a trilogy.

        Args:
            request: Validated character creation request

        Returns:
            CharacterResponse with created character data

        Raises:
            CharacterCreationError: If creation fails
        """
        logger.info("=== CharacterManager.create_character START ===")
        logger.info(f"User ID: {self.user_id}")
        logger.info(f"Character: {request.name} for trilogy {request.trilogy_id}")

        try:
            # Verify user owns the trilogy
            await self._verify_trilogy_ownership(request.trilogy_id)

            # Prepare character data
            character_data = {
                "trilogy_id": request.trilogy_id,
                "name": request.name,
                "gender": request.gender.value if request.gender else None,
                "description": request.description,
                "character_arc": request.character_arc,
                "traits": request.traits.model_dump() if request.traits else None,
            }

            logger.info("Inserting character into database...")
            response = (
                supabase.table("characters")
                .insert(character_data)
                .execute()
            )

            if not response.data or len(response.data) == 0:
                logger.error("No data returned from character insert")
                raise CharacterCreationError(
                    "Failed to create character: No data returned from database"
                )

            character_record = response.data[0]
            logger.info(f"Character created successfully with ID: {character_record['id']}")

            # Save book assignments
            if request.book_ids:
                await self._set_character_book_ids(character_record['id'], request.book_ids)
            character_record["book_ids"] = request.book_ids or []

            # Queue character embedding task (Epic 5A)
            try:
                from api.services.task_queue import TaskQueue

                embedding_job_id = await TaskQueue.enqueue_character_embedding(
                    character_id=character_record['id'],
                    trilogy_id=request.trilogy_id,
                    name=request.name,
                    description=request.description,
                    traits=request.traits.model_dump() if request.traits else None,
                    character_arc=request.character_arc,
                    consciousness_themes=request.consciousness_themes
                )

                if embedding_job_id:
                    logger.info(f"Character embedding queued with job ID: {embedding_job_id}")
                else:
                    logger.warning("Failed to queue character embedding task")

            except Exception as e:
                # Don't fail character creation if embedding fails
                logger.error(f"Error queuing character embedding: {e}")

            # Convert traits back to CharacterTraits model
            if character_record.get("traits"):
                character_record["traits"] = CharacterTraits(**character_record["traits"])

            logger.info("=== CharacterManager.create_character SUCCESS ===")
            return CharacterResponse(**character_record)

        except APIError as e:
            logger.error(f"Database error during character creation: {str(e)}", exc_info=True)
            raise CharacterCreationError(f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during character creation: {str(e)}", exc_info=True)
            raise CharacterCreationError(f"Failed to create character: {str(e)}")

    async def get_trilogy_characters(
        self, trilogy_id: str
    ) -> CharacterListResponse:
        """
        Get all characters for a trilogy.

        Args:
            trilogy_id: UUID of the trilogy

        Returns:
            CharacterListResponse with list of characters

        Raises:
            CharacterNotFoundError: If trilogy not found or user doesn't own it
        """
        logger.info(f"=== CharacterManager.get_trilogy_characters for trilogy {trilogy_id} ===")

        try:
            # Verify user owns the trilogy
            await self._verify_trilogy_ownership(trilogy_id)

            # Fetch all characters for this trilogy
            response = (
                supabase.table("characters")
                .select("*")
                .eq("trilogy_id", trilogy_id)
                .order("created_at", desc=False)
                .execute()
            )

            characters_data = response.data if response.data else []

            # Convert traits to CharacterTraits model and fetch book_ids
            characters = []
            for char_data in characters_data:
                if char_data.get("traits"):
                    char_data["traits"] = CharacterTraits(**char_data["traits"])
                # Fetch book_ids for this character
                char_data["book_ids"] = await self._get_character_book_ids(char_data["id"])
                characters.append(CharacterResponse(**char_data))

            logger.info(f"Retrieved {len(characters)} characters")
            return CharacterListResponse(
                characters=characters,
                total=len(characters)
            )

        except APIError as e:
            logger.error(f"Database error fetching characters: {str(e)}", exc_info=True)
            raise CharacterNotFoundError(f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error fetching characters: {str(e)}", exc_info=True)
            raise CharacterNotFoundError(f"Failed to fetch characters: {str(e)}")

    async def get_character(self, character_id: str) -> CharacterResponse:
        """
        Get a single character by ID.

        Args:
            character_id: UUID of the character

        Returns:
            CharacterResponse with character data

        Raises:
            CharacterNotFoundError: If character not found or user doesn't own it
        """
        logger.info(f"=== CharacterManager.get_character {character_id} ===")

        try:
            # Fetch character and verify ownership via trilogy
            response = (
                supabase.table("characters")
                .select("*, trilogy_projects!inner(user_id)")
                .eq("id", character_id)
                .execute()
            )

            if not response.data or len(response.data) == 0:
                logger.warning(f"Character {character_id} not found")
                raise CharacterNotFoundError(f"Character {character_id} not found")

            character_data = response.data[0]

            # Verify user ownership
            if character_data["trilogy_projects"]["user_id"] != self.user_id:
                logger.warning(f"User {self.user_id} doesn't own character {character_id}")
                raise CharacterNotFoundError(f"Character {character_id} not found")

            # Remove nested trilogy data and convert traits
            character_data.pop("trilogy_projects", None)
            if character_data.get("traits"):
                character_data["traits"] = CharacterTraits(**character_data["traits"])

            # Fetch book_ids
            character_data["book_ids"] = await self._get_character_book_ids(character_id)

            logger.info(f"Character {character_id} retrieved successfully")
            return CharacterResponse(**character_data)

        except CharacterNotFoundError:
            raise
        except APIError as e:
            logger.error(f"Database error fetching character: {str(e)}", exc_info=True)
            raise CharacterNotFoundError(f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error fetching character: {str(e)}", exc_info=True)
            raise CharacterNotFoundError(f"Failed to fetch character: {str(e)}")

    async def update_character(
        self, character_id: str, request: CharacterUpdate
    ) -> CharacterResponse:
        """
        Update an existing character.

        Args:
            character_id: UUID of the character to update
            request: Validated character update request

        Returns:
            CharacterResponse with updated character data

        Raises:
            CharacterNotFoundError: If character not found
            CharacterUpdateError: If update fails
        """
        logger.info(f"=== CharacterManager.update_character {character_id} ===")

        try:
            # Verify character exists and user owns it
            await self.get_character(character_id)

            # Prepare update data (only include fields that are set)
            update_data = {}
            if request.name is not None:
                update_data["name"] = request.name
            if request.gender is not None:
                update_data["gender"] = request.gender.value
            if request.description is not None:
                update_data["description"] = request.description
            if request.character_arc is not None:
                update_data["character_arc"] = request.character_arc
            if request.traits is not None:
                update_data["traits"] = request.traits.model_dump()

            # Handle book_ids separately (not stored in characters table)
            if request.book_ids is not None:
                await self._set_character_book_ids(character_id, request.book_ids)

            if not update_data:
                logger.warning("No fields to update (only book_ids changed)")
                # Return the current character with updated book_ids
                return await self.get_character(character_id)

            logger.info(f"Updating character with data: {list(update_data.keys())}")
            response = (
                supabase.table("characters")
                .update(update_data)
                .eq("id", character_id)
                .execute()
            )

            if not response.data or len(response.data) == 0:
                logger.error("No data returned from character update")
                raise CharacterUpdateError("Failed to update character")

            character_data = response.data[0]
            if character_data.get("traits"):
                character_data["traits"] = CharacterTraits(**character_data["traits"])

            # Fetch current book_ids
            character_data["book_ids"] = await self._get_character_book_ids(character_id)

            logger.info(f"Character {character_id} updated successfully")
            return CharacterResponse(**character_data)

        except CharacterNotFoundError:
            raise
        except APIError as e:
            logger.error(f"Database error updating character: {str(e)}", exc_info=True)
            raise CharacterUpdateError(f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error updating character: {str(e)}", exc_info=True)
            raise CharacterUpdateError(f"Failed to update character: {str(e)}")

    async def delete_character(
        self, character_id: str
    ) -> CharacterDeleteResponse:
        """
        Delete a character.

        Args:
            character_id: UUID of the character to delete

        Returns:
            CharacterDeleteResponse confirming deletion

        Raises:
            CharacterNotFoundError: If character not found
            CharacterDeletionError: If deletion fails
        """
        logger.info(f"=== CharacterManager.delete_character {character_id} ===")

        try:
            # Verify character exists and user owns it
            await self.get_character(character_id)

            # Delete the character
            logger.info(f"Deleting character {character_id}...")
            response = (
                supabase.table("characters")
                .delete()
                .eq("id", character_id)
                .execute()
            )

            if not response.data or len(response.data) == 0:
                logger.error("No data returned from character delete")
                raise CharacterDeletionError("Failed to delete character")

            logger.info(f"Character {character_id} deleted successfully")
            return CharacterDeleteResponse(
                id=character_id,
                message="Character deleted successfully"
            )

        except CharacterNotFoundError:
            raise
        except APIError as e:
            logger.error(f"Database error deleting character: {str(e)}", exc_info=True)
            raise CharacterDeletionError(f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error deleting character: {str(e)}", exc_info=True)
            raise CharacterDeletionError(f"Failed to delete character: {str(e)}")

    async def _verify_trilogy_ownership(self, trilogy_id: str) -> None:
        """
        Verify that the current user owns the specified trilogy.

        Args:
            trilogy_id: UUID of the trilogy to verify

        Raises:
            CharacterNotFoundError: If trilogy not found or user doesn't own it
        """
        logger.debug(f"Verifying trilogy ownership: {trilogy_id} for user {self.user_id}")

        try:
            response = (
                supabase.table("trilogy_projects")
                .select("id, user_id")
                .eq("id", trilogy_id)
                .execute()
            )

            if not response.data or len(response.data) == 0:
                logger.warning(f"Trilogy {trilogy_id} not found")
                raise CharacterNotFoundError(f"Trilogy {trilogy_id} not found")

            trilogy = response.data[0]
            if trilogy["user_id"] != self.user_id:
                logger.warning(f"User {self.user_id} doesn't own trilogy {trilogy_id}")
                raise CharacterNotFoundError(f"Trilogy {trilogy_id} not found")

            logger.debug(f"Trilogy ownership verified")

        except CharacterNotFoundError:
            raise
        except APIError as e:
            logger.error(f"Database error verifying trilogy ownership: {str(e)}", exc_info=True)
            raise CharacterNotFoundError(f"Database error: {str(e)}")

    async def _get_character_book_ids(self, character_id: str) -> List[str]:
        """
        Get the list of book IDs a character is assigned to.

        Args:
            character_id: UUID of the character

        Returns:
            List of book IDs
        """
        try:
            response = (
                supabase.table("character_book_assignments")
                .select("book_id")
                .eq("character_id", character_id)
                .execute()
            )
            return [r["book_id"] for r in (response.data or [])]
        except Exception as e:
            logger.warning(f"Error fetching book assignments for character {character_id}: {e}")
            return []

    async def _set_character_book_ids(self, character_id: str, book_ids: List[str]) -> None:
        """
        Set the book assignments for a character (replaces existing assignments).

        Args:
            character_id: UUID of the character
            book_ids: List of book IDs to assign
        """
        try:
            # Delete existing assignments
            supabase.table("character_book_assignments").delete().eq(
                "character_id", character_id
            ).execute()

            # Insert new assignments
            if book_ids:
                assignments = [
                    {"character_id": character_id, "book_id": book_id}
                    for book_id in book_ids
                ]
                supabase.table("character_book_assignments").insert(assignments).execute()
                logger.info(f"Set {len(book_ids)} book assignments for character {character_id}")
        except Exception as e:
            logger.error(f"Error setting book assignments for character {character_id}: {e}")
            # Don't fail the main operation if book assignments fail

    async def get_characters_by_book(self, book_id: str) -> CharacterListResponse:
        """
        Get all characters assigned to a specific book.

        Args:
            book_id: UUID of the book

        Returns:
            CharacterListResponse with list of characters for this book
        """
        logger.info(f"=== CharacterManager.get_characters_by_book {book_id} ===")

        try:
            # Verify user owns the book via trilogy
            book_response = (
                supabase.table("books")
                .select("trilogy_id, trilogy_projects!inner(user_id)")
                .eq("id", book_id)
                .execute()
            )

            if not book_response.data:
                raise CharacterNotFoundError(f"Book {book_id} not found")

            if book_response.data[0]["trilogy_projects"]["user_id"] != self.user_id:
                raise CharacterNotFoundError(f"Book {book_id} not found")

            # Fetch characters assigned to this book
            response = (
                supabase.table("character_book_assignments")
                .select("character_id, characters(*)")
                .eq("book_id", book_id)
                .execute()
            )

            characters = []
            for assignment in (response.data or []):
                char_data = assignment.get("characters")
                if char_data:
                    if char_data.get("traits"):
                        char_data["traits"] = CharacterTraits(**char_data["traits"])
                    # Fetch book_ids for this character
                    char_data["book_ids"] = await self._get_character_book_ids(char_data["id"])
                    characters.append(CharacterResponse(**char_data))

            logger.info(f"Retrieved {len(characters)} characters for book {book_id}")
            return CharacterListResponse(characters=characters, total=len(characters))

        except CharacterNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error fetching characters for book {book_id}: {e}")
            raise CharacterNotFoundError(f"Failed to fetch characters: {str(e)}")
