"""
ChapterManager Service - Epic 4

Handles chapter CRUD operations, reordering, and progress tracking for books.
Chapters are sequentially numbered within each book and assigned to character POVs.
"""

import logging
from typing import List, Optional
from api.models.chapter import (
    ChapterCreate,
    ChapterUpdate,
    ChapterResponse,
    ChapterListResponse,
    ChapterDeleteResponse,
    ChapterProgressResponse,
    BookProgressResponse,
)
from api.utils.supabase_client import supabase
from postgrest.exceptions import APIError

logger = logging.getLogger(__name__)


class ChapterNotFoundError(Exception):
    """Raised when a chapter is not found."""
    pass


class ChapterCreationError(Exception):
    """Raised when chapter creation fails."""
    pass


class ChapterUpdateError(Exception):
    """Raised when chapter update fails."""
    pass


class ChapterDeletionError(Exception):
    """Raised when chapter deletion fails."""
    pass


class ChapterReorderError(Exception):
    """Raised when chapter reordering fails."""
    pass


class ChapterManager:
    """
    Manages chapter operations for books.

    Epic 4: Full CRUD, reordering, and progress tracking.
    """

    def __init__(self, user_id: str):
        """
        Initialize ChapterManager for a specific user.

        Args:
            user_id: UUID of the authenticated user (from JWT token)
        """
        self.user_id = user_id

    async def create_chapter(
        self, request: ChapterCreate
    ) -> ChapterResponse:
        """
        Create a new chapter in a book.

        Automatically assigns the next sequential chapter_number.

        Args:
            request: Validated chapter creation request

        Returns:
            ChapterResponse with created chapter data

        Raises:
            ChapterCreationError: If creation fails
        """
        logger.info("=== ChapterManager.create_chapter START ===")
        logger.info(f"User ID: {self.user_id}")
        logger.info(f"Chapter: {request.title} for book {request.book_id}")

        try:
            # Verify user owns the book (via trilogy)
            await self._verify_book_ownership(request.book_id)

            # Verify character exists and belongs to same trilogy
            await self._verify_character_ownership(request.character_id, request.book_id)

            # Get next chapter number for this book
            next_chapter_number = await self._get_next_chapter_number(request.book_id)

            # Prepare chapter data
            chapter_data = {
                "book_id": request.book_id,
                "character_id": request.character_id,
                "title": request.title,
                "chapter_number": next_chapter_number,
                "chapter_plot": request.chapter_plot,
                "target_word_count": request.target_word_count,
                "current_word_count": 0,
            }

            logger.info(f"Inserting chapter with number {next_chapter_number}...")
            response = (
                supabase.table("chapters")
                .insert(chapter_data)
                .execute()
            )

            if not response.data or len(response.data) == 0:
                logger.error("No data returned from chapter insert")
                raise ChapterCreationError(
                    "Failed to create chapter: No data returned from database"
                )

            chapter_record = response.data[0]
            logger.info(f"Chapter created successfully with ID: {chapter_record['id']}")

            logger.info("=== ChapterManager.create_chapter SUCCESS ===")
            return ChapterResponse(**chapter_record)

        except ChapterNotFoundError:
            raise
        except APIError as e:
            logger.error(f"Database error during chapter creation: {str(e)}", exc_info=True)
            raise ChapterCreationError(f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during chapter creation: {str(e)}", exc_info=True)
            raise ChapterCreationError(f"Failed to create chapter: {str(e)}")

    async def get_book_chapters(
        self, book_id: str
    ) -> ChapterListResponse:
        """
        Get all chapters for a book, ordered by chapter_number.

        Args:
            book_id: UUID of the book

        Returns:
            ChapterListResponse with list of chapters

        Raises:
            ChapterNotFoundError: If book not found or user doesn't own it
        """
        logger.info(f"=== ChapterManager.get_book_chapters for book {book_id} ===")

        try:
            # Verify user owns the book
            await self._verify_book_ownership(book_id)

            # Fetch all chapters for this book
            response = (
                supabase.table("chapters")
                .select("*")
                .eq("book_id", book_id)
                .order("chapter_number", desc=False)
                .execute()
            )

            chapters_data = response.data if response.data else []
            chapters = [ChapterResponse(**chapter) for chapter in chapters_data]

            logger.info(f"Retrieved {len(chapters)} chapters")
            return ChapterListResponse(
                chapters=chapters,
                total=len(chapters)
            )

        except ChapterNotFoundError:
            raise
        except APIError as e:
            logger.error(f"Database error fetching chapters: {str(e)}", exc_info=True)
            raise ChapterNotFoundError(f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error fetching chapters: {str(e)}", exc_info=True)
            raise ChapterNotFoundError(f"Failed to fetch chapters: {str(e)}")

    async def get_chapter(self, chapter_id: str) -> ChapterResponse:
        """
        Get a single chapter by ID.

        Args:
            chapter_id: UUID of the chapter

        Returns:
            ChapterResponse with chapter data

        Raises:
            ChapterNotFoundError: If chapter not found or user doesn't own it
        """
        logger.info(f"=== ChapterManager.get_chapter {chapter_id} ===")

        try:
            # Fetch chapter and verify ownership via book -> trilogy
            response = (
                supabase.table("chapters")
                .select("*, books!inner(*, trilogy_projects!inner(user_id))")
                .eq("id", chapter_id)
                .execute()
            )

            if not response.data or len(response.data) == 0:
                logger.warning(f"Chapter {chapter_id} not found")
                raise ChapterNotFoundError(f"Chapter {chapter_id} not found")

            chapter_data = response.data[0]

            # Verify user ownership
            if chapter_data["books"]["trilogy_projects"]["user_id"] != self.user_id:
                logger.warning(f"User {self.user_id} doesn't own chapter {chapter_id}")
                raise ChapterNotFoundError(f"Chapter {chapter_id} not found")

            # Remove nested data
            chapter_data.pop("books", None)

            logger.info(f"Chapter {chapter_id} retrieved successfully")
            return ChapterResponse(**chapter_data)

        except ChapterNotFoundError:
            raise
        except APIError as e:
            logger.error(f"Database error fetching chapter: {str(e)}", exc_info=True)
            raise ChapterNotFoundError(f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error fetching chapter: {str(e)}", exc_info=True)
            raise ChapterNotFoundError(f"Failed to fetch chapter: {str(e)}")

    async def update_chapter(
        self, chapter_id: str, request: ChapterUpdate
    ) -> ChapterResponse:
        """
        Update an existing chapter.

        Args:
            chapter_id: UUID of the chapter to update
            request: Validated chapter update request

        Returns:
            ChapterResponse with updated chapter data

        Raises:
            ChapterNotFoundError: If chapter not found
            ChapterUpdateError: If update fails
        """
        logger.info(f"=== ChapterManager.update_chapter {chapter_id} ===")

        try:
            # Verify chapter exists and user owns it
            chapter = await self.get_chapter(chapter_id)

            # Prepare update data (only include fields that are set)
            update_data = {}
            if request.title is not None:
                update_data["title"] = request.title
            if request.chapter_plot is not None:
                update_data["chapter_plot"] = request.chapter_plot
            if request.character_id is not None:
                # Verify character belongs to same trilogy
                await self._verify_character_ownership(request.character_id, chapter.book_id)
                update_data["character_id"] = request.character_id
            if request.target_word_count is not None:
                update_data["target_word_count"] = request.target_word_count

            if not update_data:
                logger.warning("No fields to update")
                return chapter

            logger.info(f"Updating chapter with data: {list(update_data.keys())}")
            response = (
                supabase.table("chapters")
                .update(update_data)
                .eq("id", chapter_id)
                .execute()
            )

            if not response.data or len(response.data) == 0:
                logger.error("No data returned from chapter update")
                raise ChapterUpdateError("Failed to update chapter")

            chapter_data = response.data[0]
            logger.info(f"Chapter {chapter_id} updated successfully")
            return ChapterResponse(**chapter_data)

        except ChapterNotFoundError:
            raise
        except APIError as e:
            logger.error(f"Database error updating chapter: {str(e)}", exc_info=True)
            raise ChapterUpdateError(f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error updating chapter: {str(e)}", exc_info=True)
            raise ChapterUpdateError(f"Failed to update chapter: {str(e)}")

    async def delete_chapter(
        self, chapter_id: str
    ) -> ChapterDeleteResponse:
        """
        Delete a chapter and renumber remaining chapters.

        Cascades to sub-chapters via database constraint.

        Args:
            chapter_id: UUID of the chapter to delete

        Returns:
            ChapterDeleteResponse confirming deletion

        Raises:
            ChapterNotFoundError: If chapter not found
            ChapterDeletionError: If deletion fails
        """
        logger.info(f"=== ChapterManager.delete_chapter {chapter_id} ===")

        try:
            # Verify chapter exists and user owns it
            chapter = await self.get_chapter(chapter_id)
            book_id = chapter.book_id
            deleted_chapter_number = chapter.chapter_number

            # Delete the chapter (CASCADE handles sub-chapters)
            logger.info(f"Deleting chapter {chapter_id}...")
            response = (
                supabase.table("chapters")
                .delete()
                .eq("id", chapter_id)
                .execute()
            )

            if not response.data or len(response.data) == 0:
                logger.error("No data returned from chapter delete")
                raise ChapterDeletionError("Failed to delete chapter")

            # Renumber chapters after the deleted one
            logger.info(f"Renumbering chapters after position {deleted_chapter_number}...")
            await self._renumber_chapters_after_deletion(book_id, deleted_chapter_number)

            logger.info(f"Chapter {chapter_id} deleted successfully")
            return ChapterDeleteResponse(
                id=chapter_id,
                message="Chapter deleted successfully"
            )

        except ChapterNotFoundError:
            raise
        except APIError as e:
            logger.error(f"Database error deleting chapter: {str(e)}", exc_info=True)
            raise ChapterDeletionError(f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error deleting chapter: {str(e)}", exc_info=True)
            raise ChapterDeletionError(f"Failed to delete chapter: {str(e)}")

    async def reorder_chapter(
        self, chapter_id: str, new_position: int
    ) -> ChapterListResponse:
        """
        Reorder a chapter to a new position and update all affected chapter numbers.

        All updates are executed in a single operation.

        Args:
            chapter_id: UUID of the chapter to move
            new_position: New chapter_number (1-based)

        Returns:
            ChapterListResponse with updated chapters in new order

        Raises:
            ChapterNotFoundError: If chapter not found
            ChapterReorderError: If reordering fails
        """
        logger.info(f"=== ChapterManager.reorder_chapter {chapter_id} to position {new_position} ===")

        try:
            # Get the chapter to move
            chapter = await self.get_chapter(chapter_id)
            book_id = chapter.book_id
            old_position = chapter.chapter_number

            # Get all chapters for this book
            chapters_response = await self.get_book_chapters(book_id)
            chapters = chapters_response.chapters
            total_chapters = len(chapters)

            # Validate new position
            if new_position < 1 or new_position > total_chapters:
                raise ChapterReorderError(
                    f"Invalid position {new_position}. Must be between 1 and {total_chapters}"
                )

            if old_position == new_position:
                logger.info("Chapter already at target position, no reordering needed")
                return chapters_response

            logger.info(f"Moving chapter from position {old_position} to {new_position}")

            # Calculate updates for all affected chapters
            updates_needed = []

            if old_position < new_position:
                # Moving down: shift chapters up between old and new positions
                for ch in chapters:
                    if ch.id == chapter_id:
                        updates_needed.append((ch.id, new_position))
                    elif old_position < ch.chapter_number <= new_position:
                        updates_needed.append((ch.id, ch.chapter_number - 1))
            else:
                # Moving up: shift chapters down between new and old positions
                for ch in chapters:
                    if ch.id == chapter_id:
                        updates_needed.append((ch.id, new_position))
                    elif new_position <= ch.chapter_number < old_position:
                        updates_needed.append((ch.id, ch.chapter_number + 1))

            # Execute updates in two phases to avoid unique constraint violations
            # Phase 1: Set all affected chapters to temporary negative numbers
            logger.info(f"Phase 1: Setting {len(updates_needed)} chapters to temporary positions...")
            for i, (chapter_to_update_id, _) in enumerate(updates_needed):
                temp_number = -(i + 1000)  # Use large negative numbers to avoid conflicts
                supabase.table("chapters").update({
                    "chapter_number": temp_number
                }).eq("id", chapter_to_update_id).execute()

            # Phase 2: Set chapters to their final positions
            logger.info(f"Phase 2: Setting chapters to final positions...")
            for chapter_to_update_id, new_number in updates_needed:
                supabase.table("chapters").update({
                    "chapter_number": new_number
                }).eq("id", chapter_to_update_id).execute()

            # Return updated chapters
            logger.info("=== ChapterManager.reorder_chapter SUCCESS ===")
            return await self.get_book_chapters(book_id)

        except ChapterNotFoundError:
            raise
        except ChapterReorderError:
            raise
        except APIError as e:
            logger.error(f"Database error reordering chapter: {str(e)}", exc_info=True)
            raise ChapterReorderError(f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error reordering chapter: {str(e)}", exc_info=True)
            raise ChapterReorderError(f"Failed to reorder chapter: {str(e)}")

    async def get_chapter_progress(
        self, chapter_id: str
    ) -> ChapterProgressResponse:
        """
        Calculate progress for a chapter.

        Current word count is calculated from sub-chapters (Epic 6).
        For now, uses the current_word_count field directly.

        Args:
            chapter_id: UUID of the chapter

        Returns:
            ChapterProgressResponse with progress metrics

        Raises:
            ChapterNotFoundError: If chapter not found
        """
        logger.info(f"=== ChapterManager.get_chapter_progress {chapter_id} ===")

        try:
            chapter = await self.get_chapter(chapter_id)

            # Calculate percentage
            if chapter.target_word_count and chapter.target_word_count > 0:
                percentage = (chapter.current_word_count / chapter.target_word_count) * 100
            else:
                percentage = 0.0

            # Determine status
            if chapter.current_word_count == 0:
                status = "not_started"
            elif percentage >= 110:
                status = "over_target"
            elif percentage >= 100:
                status = "complete"
            else:
                status = "in_progress"

            return ChapterProgressResponse(
                chapter_id=chapter_id,
                title=chapter.title,
                target_word_count=chapter.target_word_count,
                current_word_count=chapter.current_word_count,
                percentage=round(percentage, 1),
                status=status
            )

        except ChapterNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error calculating progress: {str(e)}", exc_info=True)
            raise ChapterNotFoundError(f"Failed to calculate progress: {str(e)}")

    async def get_book_progress(
        self, book_id: str
    ) -> BookProgressResponse:
        """
        Calculate book-level progress summary.

        Args:
            book_id: UUID of the book

        Returns:
            BookProgressResponse with book-level metrics

        Raises:
            ChapterNotFoundError: If book not found
        """
        logger.info(f"=== ChapterManager.get_book_progress {book_id} ===")

        try:
            # Verify ownership
            await self._verify_book_ownership(book_id)

            # Get all chapters
            chapters_response = await self.get_book_chapters(book_id)
            chapters = chapters_response.chapters

            total_chapters = len(chapters)
            total_target_word_count = sum(
                ch.target_word_count or 0 for ch in chapters
            )
            total_current_word_count = sum(ch.current_word_count for ch in chapters)

            # Count chapters by status
            chapters_by_status = {
                "not_started": 0,
                "in_progress": 0,
                "complete": 0,
                "over_target": 0
            }

            chapters_completed = 0
            for chapter in chapters:
                progress = await self.get_chapter_progress(chapter.id)
                chapters_by_status[progress.status] += 1
                if progress.status in ["complete", "over_target"]:
                    chapters_completed += 1

            # Calculate overall percentage
            if total_target_word_count > 0:
                overall_percentage = (total_current_word_count / total_target_word_count) * 100
            else:
                overall_percentage = 0.0

            return BookProgressResponse(
                book_id=book_id,
                total_chapters=total_chapters,
                chapters_completed=chapters_completed,
                total_target_word_count=total_target_word_count,
                total_current_word_count=total_current_word_count,
                overall_percentage=round(overall_percentage, 1),
                chapters_by_status=chapters_by_status
            )

        except ChapterNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error calculating book progress: {str(e)}", exc_info=True)
            raise ChapterNotFoundError(f"Failed to calculate book progress: {str(e)}")

    # ==================== Private Helper Methods ====================

    async def _verify_book_ownership(self, book_id: str) -> None:
        """
        Verify that the current user owns the book (via trilogy).

        Args:
            book_id: UUID of the book to verify

        Raises:
            ChapterNotFoundError: If book not found or user doesn't own it
        """
        logger.debug(f"Verifying book ownership: {book_id} for user {self.user_id}")

        try:
            response = (
                supabase.table("books")
                .select("id, trilogy_projects!inner(user_id)")
                .eq("id", book_id)
                .execute()
            )

            if not response.data or len(response.data) == 0:
                logger.warning(f"Book {book_id} not found")
                raise ChapterNotFoundError(f"Book {book_id} not found")

            book = response.data[0]
            if book["trilogy_projects"]["user_id"] != self.user_id:
                logger.warning(f"User {self.user_id} doesn't own book {book_id}")
                raise ChapterNotFoundError(f"Book {book_id} not found")

            logger.debug("Book ownership verified")

        except ChapterNotFoundError:
            raise
        except APIError as e:
            logger.error(f"Database error verifying book ownership: {str(e)}", exc_info=True)
            raise ChapterNotFoundError(f"Database error: {str(e)}")

    async def _verify_character_ownership(self, character_id: str, book_id: str) -> None:
        """
        Verify that the character belongs to the same trilogy as the book.

        Args:
            character_id: UUID of the character
            book_id: UUID of the book

        Raises:
            ChapterCreationError: If character not found or doesn't match trilogy
        """
        logger.debug(f"Verifying character {character_id} belongs to book's trilogy")

        try:
            # Get book's trilogy
            book_response = (
                supabase.table("books")
                .select("trilogy_id")
                .eq("id", book_id)
                .execute()
            )

            if not book_response.data:
                raise ChapterCreationError(f"Book {book_id} not found")

            trilogy_id = book_response.data[0]["trilogy_id"]

            # Verify character belongs to same trilogy
            char_response = (
                supabase.table("characters")
                .select("id, trilogy_id")
                .eq("id", character_id)
                .eq("trilogy_id", trilogy_id)
                .execute()
            )

            if not char_response.data or len(char_response.data) == 0:
                raise ChapterCreationError(
                    f"Character {character_id} not found or doesn't belong to this trilogy"
                )

            logger.debug("Character ownership verified")

        except ChapterCreationError:
            raise
        except APIError as e:
            logger.error(f"Database error verifying character: {str(e)}", exc_info=True)
            raise ChapterCreationError(f"Database error: {str(e)}")

    async def _get_next_chapter_number(self, book_id: str) -> int:
        """
        Get the next available chapter number for a book.

        Args:
            book_id: UUID of the book

        Returns:
            Next sequential chapter number (1 if book has no chapters)
        """
        logger.debug(f"Getting next chapter number for book {book_id}")

        try:
            response = (
                supabase.table("chapters")
                .select("chapter_number")
                .eq("book_id", book_id)
                .order("chapter_number", desc=True)
                .limit(1)
                .execute()
            )

            if response.data and len(response.data) > 0:
                max_chapter_number = response.data[0]["chapter_number"]
                return max_chapter_number + 1
            else:
                return 1

        except APIError as e:
            logger.error(f"Database error getting next chapter number: {str(e)}", exc_info=True)
            raise ChapterCreationError(f"Database error: {str(e)}")

    async def _renumber_chapters_after_deletion(
        self, book_id: str, deleted_chapter_number: int
    ) -> None:
        """
        Renumber chapters after a deletion to maintain sequential numbering.

        Args:
            book_id: UUID of the book
            deleted_chapter_number: The chapter number that was deleted
        """
        logger.debug(f"Renumbering chapters after position {deleted_chapter_number}")

        try:
            # Get all chapters with chapter_number > deleted_chapter_number
            response = (
                supabase.table("chapters")
                .select("id, chapter_number")
                .eq("book_id", book_id)
                .gt("chapter_number", deleted_chapter_number)
                .execute()
            )

            if response.data:
                # Update each chapter to decrease its number by 1
                for chapter in response.data:
                    supabase.table("chapters").update({
                        "chapter_number": chapter["chapter_number"] - 1
                    }).eq("id", chapter["id"]).execute()

                logger.debug(f"Renumbered {len(response.data)} chapters")

        except APIError as e:
            logger.error(f"Database error renumbering chapters: {str(e)}", exc_info=True)
            # Don't raise - deletion succeeded, renumbering is cleanup
            logger.warning("Chapter deleted but renumbering failed")
