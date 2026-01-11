"""
Progress Tracking Service for Epic 6

Calculates and tracks sub-chapter and chapter progress metrics
with real-time word count monitoring.
"""

from typing import Dict, Any, List
from uuid import UUID
import logging

from api.utils.supabase_client import get_supabase_client
from api.models.sub_chapter import (
    SubChapterProgress,
    ChapterProgress
)

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Calculates and tracks sub-chapter/chapter progress"""

    def __init__(self):
        self.supabase = get_supabase_client()

    async def calculate_sub_chapter_progress(
        self,
        sub_chapter_id: UUID,
        user_id: UUID
    ) -> SubChapterProgress:
        """
        Calculate progress metrics for a single sub-chapter.

        Progress status determined by:
        - not_started: 0 words
        - in_progress: 1-89% of target
        - near_complete: 90-99% of target
        - complete: >= 100% of target

        Args:
            sub_chapter_id: Sub-chapter identifier
            user_id: User requesting the progress

        Returns:
            SubChapterProgress with metrics

        Raises:
            ValueError: If sub-chapter not found
        """
        try:
            # Get sub-chapter with chapter info for target word count
            result = self.supabase.table("sub_chapters")\
                .select("*, chapter:chapters(target_word_count)")\
                .eq("id", str(sub_chapter_id))\
                .execute()

            if not result.data:
                raise ValueError(f"Sub-chapter {sub_chapter_id} not found")

            sub_chapter = result.data[0]

            # Get target word count (default to 2000 if not set)
            # Can be from sub_chapter, chapter, or default
            target_word_count = (
                sub_chapter.get("target_word_count") or
                (sub_chapter.get("chapter", {}).get("target_word_count") or 8000) // 4 or  # Divide chapter target by 4
                2000  # Default
            )

            actual_word_count = sub_chapter.get("word_count") or 0

            # Calculate percentage
            percentage = (actual_word_count / target_word_count * 100) if target_word_count > 0 else 0

            # Determine status
            if actual_word_count == 0:
                status = "not_started"
            elif percentage >= 100:
                status = "complete"
            elif percentage >= 90:
                status = "near_complete"
            else:
                status = "in_progress"

            return SubChapterProgress(
                sub_chapter_id=sub_chapter_id,
                actual_word_count=actual_word_count,
                target_word_count=target_word_count,
                percentage=round(percentage, 1),
                status=status,
                over_target=actual_word_count > target_word_count
            )

        except Exception as e:
            logger.error(f"Error calculating sub-chapter progress for {sub_chapter_id}: {e}")
            raise

    async def calculate_chapter_progress(
        self,
        chapter_id: UUID,
        user_id: UUID
    ) -> ChapterProgress:
        """
        Calculate aggregate progress for a chapter including all sub-chapters.

        Args:
            chapter_id: Chapter identifier
            user_id: User requesting the progress

        Returns:
            ChapterProgress with aggregate metrics

        Raises:
            ValueError: If chapter not found
        """
        try:
            # Get chapter info
            chapter_result = self.supabase.table("chapters")\
                .select("target_word_count, current_word_count")\
                .eq("id", str(chapter_id))\
                .execute()

            if not chapter_result.data:
                raise ValueError(f"Chapter {chapter_id} not found")

            chapter = chapter_result.data[0]

            # Get all sub-chapters
            sub_chapters_result = self.supabase.table("sub_chapters")\
                .select("*")\
                .eq("chapter_id", str(chapter_id))\
                .order("sub_chapter_number")\
                .execute()

            sub_chapters = sub_chapters_result.data or []

            # Calculate totals
            total_actual = chapter.get("current_word_count") or 0
            total_target = chapter.get("target_word_count") or 8000

            # If no explicit target, calculate from sub-chapters
            if not chapter.get("target_word_count") and sub_chapters:
                total_target = len(sub_chapters) * 2000  # Default 2000 per sub-chapter

            percentage = (total_actual / total_target * 100) if total_target > 0 else 0

            # Count completed sub-chapters (>= 100% of their target)
            sub_chapter_target = total_target // len(sub_chapters) if sub_chapters else 2000
            completed_count = sum(
                1 for sc in sub_chapters
                if (sc.get("word_count") or 0) >= sub_chapter_target
            )

            # Get detailed progress for each sub-chapter
            sub_chapter_progress_list = []
            for sc in sub_chapters:
                try:
                    progress = await self.calculate_sub_chapter_progress(
                        UUID(sc["id"]),
                        user_id
                    )
                    sub_chapter_progress_list.append(progress)
                except Exception as e:
                    logger.error(f"Error calculating progress for sub-chapter {sc['id']}: {e}")

            return ChapterProgress(
                chapter_id=chapter_id,
                total_actual=total_actual,
                total_target=total_target,
                percentage=round(percentage, 1),
                sub_chapters_total=len(sub_chapters),
                sub_chapters_completed=completed_count,
                sub_chapters=sub_chapter_progress_list
            )

        except Exception as e:
            logger.error(f"Error calculating chapter progress for {chapter_id}: {e}")
            raise

    async def get_book_progress(
        self,
        book_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Calculate aggregate progress for an entire book.

        Args:
            book_id: Book identifier
            user_id: User requesting the progress

        Returns:
            Dict with book-level progress metrics

        Raises:
            ValueError: If book not found
        """
        try:
            # Get book info
            book_result = self.supabase.table("books")\
                .select("target_word_count, current_word_count, title")\
                .eq("id", str(book_id))\
                .execute()

            if not book_result.data:
                raise ValueError(f"Book {book_id} not found")

            book = book_result.data[0]

            # Get all chapters
            chapters_result = self.supabase.table("chapters")\
                .select("id, title, current_word_count, target_word_count")\
                .eq("book_id", str(book_id))\
                .order("chapter_number")\
                .execute()

            chapters = chapters_result.data or []

            total_actual = book.get("current_word_count") or 0
            total_target = book.get("target_word_count") or 80000

            percentage = (total_actual / total_target * 100) if total_target > 0 else 0

            # Calculate chapter-level progress
            chapter_progress_list = []
            for chapter in chapters:
                chapter_target = chapter.get("target_word_count") or (total_target // len(chapters) if chapters else 8000)
                chapter_actual = chapter.get("current_word_count") or 0
                chapter_percentage = (chapter_actual / chapter_target * 100) if chapter_target > 0 else 0

                chapter_progress_list.append({
                    "chapter_id": chapter["id"],
                    "chapter_title": chapter["title"],
                    "actual_word_count": chapter_actual,
                    "target_word_count": chapter_target,
                    "percentage": round(chapter_percentage, 1),
                    "is_complete": chapter_actual >= chapter_target
                })

            completed_chapters = sum(1 for cp in chapter_progress_list if cp["is_complete"])

            return {
                "book_id": str(book_id),
                "book_title": book["title"],
                "total_actual": total_actual,
                "total_target": total_target,
                "percentage": round(percentage, 1),
                "chapters_total": len(chapters),
                "chapters_completed": completed_chapters,
                "chapters": chapter_progress_list
            }

        except Exception as e:
            logger.error(f"Error calculating book progress for {book_id}: {e}")
            raise

    async def get_trilogy_progress(
        self,
        trilogy_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Calculate aggregate progress for the entire trilogy.

        Args:
            trilogy_id: Trilogy identifier
            user_id: User requesting the progress

        Returns:
            Dict with trilogy-level progress metrics

        Raises:
            ValueError: If trilogy not found or user doesn't own it
        """
        try:
            # Get trilogy info
            trilogy_result = self.supabase.table("trilogy_projects")\
                .select("title")\
                .eq("id", str(trilogy_id))\
                .eq("user_id", str(user_id))\
                .execute()

            if not trilogy_result.data:
                raise ValueError(f"Trilogy {trilogy_id} not found or access denied")

            trilogy = trilogy_result.data[0]

            # Get all books
            books_result = self.supabase.table("books")\
                .select("id, title, book_number, current_word_count, target_word_count")\
                .eq("trilogy_id", str(trilogy_id))\
                .order("book_number")\
                .execute()

            books = books_result.data or []

            # Calculate totals
            total_actual = sum(book.get("current_word_count") or 0 for book in books)
            total_target = sum(book.get("target_word_count") or 80000 for book in books)

            percentage = (total_actual / total_target * 100) if total_target > 0 else 0

            # Get book progress
            book_progress_list = []
            for book in books:
                book_target = book.get("target_word_count") or 80000
                book_actual = book.get("current_word_count") or 0
                book_percentage = (book_actual / book_target * 100) if book_target > 0 else 0

                book_progress_list.append({
                    "book_id": book["id"],
                    "book_number": book["book_number"],
                    "book_title": book["title"],
                    "actual_word_count": book_actual,
                    "target_word_count": book_target,
                    "percentage": round(book_percentage, 1),
                    "is_complete": book_actual >= book_target
                })

            completed_books = sum(1 for bp in book_progress_list if bp["is_complete"])

            return {
                "trilogy_id": str(trilogy_id),
                "trilogy_title": trilogy["title"],
                "total_actual": total_actual,
                "total_target": total_target,
                "percentage": round(percentage, 1),
                "books_total": len(books),
                "books_completed": completed_books,
                "books": book_progress_list
            }

        except Exception as e:
            logger.error(f"Error calculating trilogy progress for {trilogy_id}: {e}")
            raise
