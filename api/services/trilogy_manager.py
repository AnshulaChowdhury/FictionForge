"""
TrilogyManager Service - Epic 1

Handles trilogy project creation with automatic book generation.
Implements transaction-like behavior with rollback on failure.
"""

import logging
from typing import Optional
from api.models.trilogy import (
    CreateTrilogyRequest,
    UpdateTrilogyRequest,
    TrilogyResponse,
    BookResponse,
    CreateTrilogyResponse,
    TrilogyStatsResponse,
)
from api.utils.supabase_client import supabase
from postgrest.exceptions import APIError

logger = logging.getLogger(__name__)


class TrilogyCreationError(Exception):
    """Raised when trilogy creation fails."""

    pass


class TrilogyManager:
    """
    Manages trilogy project operations.

    Epic 1: Create trilogy with automatic 3-book generation.
    """

    DEFAULT_BOOK_WORD_COUNT = 80000

    def __init__(self, user_id: str):
        """
        Initialize TrilogyManager for a specific user.

        Args:
            user_id: UUID of the authenticated user (from JWT token)
        """
        self.user_id = user_id

    async def create_project(
        self, request: CreateTrilogyRequest
    ) -> CreateTrilogyResponse:
        """
        Create a new trilogy project with 3 auto-generated books.

        This method implements the Epic 1 user flow:
        1. Validate input data (handled by Pydantic)
        2. Insert trilogy record into database
        3. Loop: Create 3 books (book_number 1-3)
        4. Rollback all changes if any step fails
        5. Return complete trilogy + books data

        Args:
            request: Validated trilogy creation request

        Returns:
            CreateTrilogyResponse with trilogy and 3 books

        Raises:
            TrilogyCreationError: If creation fails at any step
        """
        logger.info("=== TrilogyManager.create_project START ===")
        logger.info(f"User ID: {self.user_id}")
        logger.info(f"Request: {request.title} by {request.author}")

        trilogy_id: Optional[str] = None

        try:
            # Step 1: Create trilogy record
            logger.info("Step 1: Preparing trilogy data...")
            trilogy_data = {
                "user_id": self.user_id,
                "title": request.title,
                "description": request.description,
                "author": request.author,
                "narrative_overview": request.narrative_overview,
            }
            logger.info(f"Trilogy data prepared: {trilogy_data}")

            logger.info("Inserting trilogy into database...")
            trilogy_response = (
                supabase.table("trilogy_projects")
                .insert(trilogy_data)
                .execute()
            )
            logger.info(f"Database response received, data length: {len(trilogy_response.data) if trilogy_response.data else 0}")

            if not trilogy_response.data or len(trilogy_response.data) == 0:
                logger.error("No data returned from trilogy insert")
                raise TrilogyCreationError(
                    "Failed to create trilogy: No data returned from database"
                )

            trilogy_record = trilogy_response.data[0]
            trilogy_id = trilogy_record["id"]
            logger.info(f"Trilogy created successfully with ID: {trilogy_id}")

            # Step 2: Create 3 books
            logger.info("Step 2: Preparing books data...")
            books_data = []
            for book_number in range(1, 4):
                book_data = {
                    "trilogy_id": trilogy_id,
                    "book_number": book_number,
                    "title": f"Book {book_number}",
                    "description": None,
                    "target_word_count": self.DEFAULT_BOOK_WORD_COUNT,
                    "current_word_count": 0,
                }
                books_data.append(book_data)
            logger.info(f"Books data prepared: {len(books_data)} books")

            # Insert all 3 books in a single batch operation
            logger.info("Inserting books into database...")
            books_response = (
                supabase.table("books")
                .insert(books_data)
                .execute()
            )
            logger.info(f"Books inserted, data length: {len(books_response.data) if books_response.data else 0}")

            if not books_response.data or len(books_response.data) != 3:
                logger.error(f"Book creation failed. Expected 3, got {len(books_response.data) if books_response.data else 0}")
                raise TrilogyCreationError(
                    f"Failed to create all 3 books. Expected 3, got {len(books_response.data) if books_response.data else 0}"
                )

            # Step 3: Format and return response
            logger.info("Step 3: Formatting response...")
            trilogy = TrilogyResponse(**trilogy_record)
            books = [BookResponse(**book) for book in books_response.data]
            logger.info("Response formatted successfully")

            logger.info("=== TrilogyManager.create_project SUCCESS ===")
            return CreateTrilogyResponse(
                trilogy=trilogy,
                books=books,
                message="Project created successfully!",
            )

        except APIError as e:
            # Database error occurred - attempt rollback
            logger.error(f"APIError occurred: {str(e)}", exc_info=True)
            logger.info(f"Attempting rollback for trilogy_id: {trilogy_id}")
            await self._rollback_trilogy(trilogy_id)
            error_msg = f"Database error during trilogy creation: {str(e)}"
            logger.error(f"Raising TrilogyCreationError: {error_msg}")
            raise TrilogyCreationError(error_msg) from e

        except Exception as e:
            # Unexpected error - attempt rollback
            logger.error(f"Unexpected exception occurred: {str(e)}", exc_info=True)
            logger.info(f"Attempting rollback for trilogy_id: {trilogy_id}")
            await self._rollback_trilogy(trilogy_id)
            error_msg = f"Unexpected error during trilogy creation: {str(e)}"
            logger.error(f"Raising TrilogyCreationError: {error_msg}")
            raise TrilogyCreationError(error_msg) from e

    async def _rollback_trilogy(self, trilogy_id: Optional[str]) -> None:
        """
        Rollback trilogy creation by deleting the trilogy record.

        Due to CASCADE delete constraints, this will automatically delete:
        - All associated books
        - All child records (chapters, sub-chapters, etc.)

        Args:
            trilogy_id: UUID of the trilogy to delete, or None if not created yet
        """
        if trilogy_id is None:
            # Trilogy was never created, nothing to rollback
            return

        try:
            supabase.table("trilogy_projects").delete().eq("id", trilogy_id).execute()
        except Exception as e:
            # Log the rollback failure but don't raise
            # (we're already handling an error, don't want to mask it)
            print(f"Warning: Failed to rollback trilogy {trilogy_id}: {str(e)}")

    async def get_user_trilogies(self) -> list[TrilogyResponse]:
        """
        Get all trilogies for the current user.

        Returns:
            List of trilogy responses (RLS ensures only user's trilogies)

        Raises:
            TrilogyCreationError: If database query fails
        """
        try:
            response = (
                supabase.table("trilogy_projects")
                .select("*")
                .eq("user_id", self.user_id)
                .order("created_at", desc=True)
                .execute()
            )

            if not response.data:
                return []

            return [TrilogyResponse(**trilogy) for trilogy in response.data]

        except APIError as e:
            raise TrilogyCreationError(
                f"Failed to fetch trilogies: {str(e)}"
            ) from e

    async def get_trilogy_by_id(self, trilogy_id: str) -> Optional[TrilogyResponse]:
        """
        Get a specific trilogy by ID.

        Args:
            trilogy_id: UUID of the trilogy

        Returns:
            TrilogyResponse if found and user has access, None otherwise

        Raises:
            TrilogyCreationError: If database query fails
        """
        try:
            response = (
                supabase.table("trilogy_projects")
                .select("*")
                .eq("id", trilogy_id)
                .eq("user_id", self.user_id)  # RLS enforcement
                .execute()
            )

            if not response.data or len(response.data) == 0:
                return None

            return TrilogyResponse(**response.data[0])

        except APIError as e:
            raise TrilogyCreationError(
                f"Failed to fetch trilogy: {str(e)}"
            ) from e

    async def get_trilogy_books(self, trilogy_id: str) -> list[BookResponse]:
        """
        Get all books for a specific trilogy.

        Args:
            trilogy_id: UUID of the trilogy

        Returns:
            List of books sorted by book_number

        Raises:
            TrilogyCreationError: If database query fails
        """
        try:
            response = (
                supabase.table("books")
                .select("*")
                .eq("trilogy_id", trilogy_id)
                .order("book_number")
                .execute()
            )

            if not response.data:
                return []

            return [BookResponse(**book) for book in response.data]

        except APIError as e:
            raise TrilogyCreationError(
                f"Failed to fetch books: {str(e)}"
            ) from e

    async def update_trilogy(
        self, trilogy_id: str, update_data: "UpdateTrilogyRequest"
    ) -> Optional[TrilogyResponse]:
        """
        Update a trilogy's metadata.

        Args:
            trilogy_id: UUID of the trilogy
            update_data: Fields to update (only non-None fields are updated)

        Returns:
            Updated TrilogyResponse if successful, None if trilogy not found

        Raises:
            TrilogyCreationError: If database update fails
        """
        try:
            # Build update dict with only provided fields
            update_dict = update_data.model_dump(exclude_none=True)

            if not update_dict:
                # Nothing to update, just return current state
                return await self.get_trilogy_by_id(trilogy_id)

            # Update the trilogy
            response = (
                supabase.table("trilogy_projects")
                .update(update_dict)
                .eq("id", trilogy_id)
                .eq("user_id", self.user_id)  # RLS enforcement
                .execute()
            )

            if not response.data or len(response.data) == 0:
                return None

            return TrilogyResponse(**response.data[0])

        except APIError as e:
            raise TrilogyCreationError(
                f"Failed to update trilogy: {str(e)}"
            ) from e

    async def get_active_trilogy_stats(self) -> Optional[TrilogyStatsResponse]:
        """
        Get comprehensive stats for the user's primary trilogy.
        Falls back to most recently updated trilogy if no primary is set.

        Returns:
            TrilogyStatsResponse with aggregated metrics, or None if no trilogies exist

        Raises:
            TrilogyCreationError: If database query fails
        """
        try:
            # Try to get primary trilogy first
            trilogy_response = (
                supabase.table("trilogy_projects")
                .select("*")
                .eq("user_id", self.user_id)
                .eq("is_primary", True)
                .limit(1)
                .execute()
            )

            # If no primary trilogy, fall back to most recently updated
            if not trilogy_response.data or len(trilogy_response.data) == 0:
                trilogy_response = (
                    supabase.table("trilogy_projects")
                    .select("*")
                    .eq("user_id", self.user_id)
                    .order("updated_at", desc=True)
                    .limit(1)
                    .execute()
                )

            if not trilogy_response.data or len(trilogy_response.data) == 0:
                return None

            trilogy_data = trilogy_response.data[0]
            trilogy = TrilogyResponse(**trilogy_data)
            trilogy_id = trilogy.id

            # Get all books for this trilogy
            books_response = (
                supabase.table("books")
                .select("*")
                .eq("trilogy_id", trilogy_id)
                .order("book_number")
                .execute()
            )

            books = books_response.data or []

            # Calculate total word count and per-book progress
            total_word_count = 0
            books_progress = []

            for book in books:
                current_words = book.get("current_word_count") or 0
                target_words = book.get("target_word_count") or 80000
                total_word_count += current_words

                completion_percentage = (
                    (current_words / target_words * 100) if target_words > 0 else 0
                )

                books_progress.append(
                    {
                        "book_number": book.get("book_number"),
                        "title": book.get("title"),
                        "completion_percentage": round(completion_percentage, 1),
                        "current_word_count": current_words,
                        "target_word_count": target_words,
                    }
                )

            # Get all chapters across all books
            book_ids = [book["id"] for book in books]
            chapters_response = (
                supabase.table("chapters")
                .select("*")
                .in_("book_id", book_ids)
                .execute()
            )

            chapters = chapters_response.data or []
            total_chapters = len(chapters)

            # Calculate chapter status counts
            chapters_completed = 0
            chapters_in_progress = 0
            chapters_not_started = 0

            for chapter in chapters:
                current_words = chapter.get("current_word_count") or 0
                target_words = chapter.get("target_word_count") or 0

                if target_words > 0:
                    percentage = (current_words / target_words) * 100
                    if percentage >= 100:
                        chapters_completed += 1
                    elif percentage > 0:
                        chapters_in_progress += 1
                    else:
                        chapters_not_started += 1
                else:
                    # No target set, count as not started if no words
                    if current_words > 0:
                        chapters_in_progress += 1
                    else:
                        chapters_not_started += 1

            # Calculate estimated pages (250 words/page is industry standard)
            estimated_pages = round(total_word_count / 250)

            return TrilogyStatsResponse(
                trilogy=trilogy,
                total_word_count=total_word_count,
                estimated_pages=estimated_pages,
                total_chapters=total_chapters,
                chapters_completed=chapters_completed,
                chapters_in_progress=chapters_in_progress,
                chapters_not_started=chapters_not_started,
                books_progress=books_progress,
            )

        except APIError as e:
            raise TrilogyCreationError(
                f"Failed to fetch trilogy stats: {str(e)}"
            ) from e

    async def set_primary_trilogy(self, trilogy_id: str) -> Optional[TrilogyResponse]:
        """
        Set a trilogy as the user's primary trilogy.
        Automatically unsets any other primary trilogy for this user.

        Args:
            trilogy_id: UUID of the trilogy to set as primary

        Returns:
            Updated trilogy response or None if not found

        Raises:
            TrilogyCreationError: If database operation fails
        """
        try:
            # Step 1: Verify user owns this trilogy
            verify_response = (
                supabase.table("trilogy_projects")
                .select("id")
                .eq("id", trilogy_id)
                .eq("user_id", self.user_id)
                .execute()
            )

            if not verify_response.data:
                return None

            # Step 2: Unset all primary trilogies for this user
            supabase.table("trilogy_projects").update({
                "is_primary": False
            }).eq("user_id", self.user_id).execute()

            # Step 3: Set this trilogy as primary
            response = (
                supabase.table("trilogy_projects")
                .update({"is_primary": True})
                .eq("id", trilogy_id)
                .eq("user_id", self.user_id)
                .execute()
            )

            if response.data:
                return TrilogyResponse(**response.data[0])
            return None

        except APIError as e:
            logger.error(f"Database error setting primary trilogy: {e}")
            raise TrilogyCreationError(f"Failed to set primary trilogy: {e}") from e

    async def unset_primary_trilogy(self, trilogy_id: str) -> Optional[TrilogyResponse]:
        """
        Unset a trilogy as the user's primary trilogy.
        After this, no trilogy will be marked as primary for this user.

        Args:
            trilogy_id: UUID of the trilogy to unset as primary

        Returns:
            Updated trilogy response or None if not found

        Raises:
            TrilogyCreationError: If database operation fails
        """
        try:
            # Verify user owns this trilogy and it is currently primary
            verify_response = (
                supabase.table("trilogy_projects")
                .select("id, is_primary")
                .eq("id", trilogy_id)
                .eq("user_id", self.user_id)
                .execute()
            )

            if not verify_response.data:
                return None

            # Only unset if it's currently primary
            if not verify_response.data[0].get("is_primary", False):
                # Already not primary, just return current state
                return await self.get_trilogy_by_id(trilogy_id)

            # Unset this trilogy as primary
            response = (
                supabase.table("trilogy_projects")
                .update({"is_primary": False})
                .eq("id", trilogy_id)
                .eq("user_id", self.user_id)
                .execute()
            )

            if response.data:
                return TrilogyResponse(**response.data[0])
            return None

        except APIError as e:
            logger.error(f"Database error unsetting primary trilogy: {e}")
            raise TrilogyCreationError(f"Failed to unset primary trilogy: {e}") from e

    async def delete_trilogy(self, trilogy_id: str) -> bool:
        """
        Delete a trilogy and all associated data.

        Manually deletes all related records in the correct order:
        - Sub-chapters
        - Chapters
        - Books
        - Characters
        - World rules
        - Generation jobs
        - Trilogy

        Args:
            trilogy_id: UUID of the trilogy to delete

        Returns:
            True if deletion was successful

        Raises:
            TrilogyCreationError: If database operation fails
        """
        try:
            # First verify the trilogy exists and belongs to the user
            trilogy = await self.get_trilogy_by_id(trilogy_id)
            if trilogy is None:
                raise TrilogyCreationError(
                    f"Trilogy {trilogy_id} not found or access denied"
                )

            logger.info(f"Starting deletion of trilogy {trilogy_id}")

            # Get all books for this trilogy
            books_response = (
                supabase.table("books")
                .select("id")
                .eq("trilogy_id", trilogy_id)
                .execute()
            )
            book_ids = [book["id"] for book in books_response.data] if books_response.data else []
            logger.info(f"Found {len(book_ids)} books to delete")

            # Get all chapters for these books
            if book_ids:
                chapters_response = (
                    supabase.table("chapters")
                    .select("id")
                    .in_("book_id", book_ids)
                    .execute()
                )
                chapter_ids = [chapter["id"] for chapter in chapters_response.data] if chapters_response.data else []
                logger.info(f"Found {len(chapter_ids)} chapters to delete")

                # Delete sub-chapters first
                if chapter_ids:
                    logger.info("Deleting sub-chapters...")
                    supabase.table("sub_chapters").delete().in_("chapter_id", chapter_ids).execute()

                # Delete chapters
                logger.info("Deleting chapters...")
                supabase.table("chapters").delete().in_("book_id", book_ids).execute()

            # Delete books
            if book_ids:
                logger.info("Deleting books...")
                supabase.table("books").delete().eq("trilogy_id", trilogy_id).execute()

            # Delete characters
            logger.info("Deleting characters...")
            supabase.table("characters").delete().eq("trilogy_id", trilogy_id).execute()

            # Delete world rules
            logger.info("Deleting world rules...")
            supabase.table("world_rules").delete().eq("trilogy_id", trilogy_id).execute()

            # Delete generation jobs
            logger.info("Deleting generation jobs...")
            supabase.table("generation_jobs").delete().eq("trilogy_id", trilogy_id).execute()

            # Finally, delete the trilogy itself
            logger.info("Deleting trilogy...")
            response = (
                supabase.table("trilogy_projects")
                .delete()
                .eq("id", trilogy_id)
                .eq("user_id", self.user_id)  # Extra safety check
                .execute()
            )

            logger.info(f"Trilogy {trilogy_id} deleted successfully")
            return True

        except APIError as e:
            raise TrilogyCreationError(
                f"Failed to delete trilogy: {str(e)}"
            ) from e
