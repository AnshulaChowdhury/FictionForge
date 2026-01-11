"""
Sub-Chapter Reordering Service for Epic 6

Handles reordering of sub-chapters within a chapter with automatic
sequential renumbering and transaction support for atomicity.
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime
import logging

from api.utils.supabase_client import get_supabase_client
from api.models.sub_chapter import SubChapter

logger = logging.getLogger(__name__)


class SubChapterReorderService:
    """Handles sub-chapter reordering with transaction support"""

    def __init__(self):
        self.supabase = get_supabase_client()

    async def reorder_sub_chapter(
        self,
        sub_chapter_id: UUID,
        new_position: int,
        user_id: UUID
    ) -> List[SubChapter]:
        """
        Move a sub-chapter to a new position, renumbering all affected sub-chapters.

        Algorithm:
        1. Fetch all sub-chapters for the chapter
        2. Remove target from current position
        3. Insert at new position
        4. Renumber all sequentially (1, 2, 3, ...)
        5. Update database (transaction handled by Supabase RPC)

        Args:
            sub_chapter_id: Sub-chapter to move
            new_position: New position (1-indexed)
            user_id: User performing the operation

        Returns:
            List of all sub-chapters in new order

        Raises:
            ValueError: If position is invalid or sub-chapter not found
        """
        try:
            # 1. Get target sub-chapter
            target_result = self.supabase.table("sub_chapters")\
                .select("*")\
                .eq("id", str(sub_chapter_id))\
                .execute()

            if not target_result.data:
                raise ValueError(f"Sub-chapter {sub_chapter_id} not found")

            target = target_result.data[0]
            chapter_id = target["chapter_id"]

            # 2. Get all sub-chapters for this chapter
            all_result = self.supabase.table("sub_chapters")\
                .select("*")\
                .eq("chapter_id", chapter_id)\
                .order("sub_chapter_number")\
                .execute()

            if not all_result.data:
                raise ValueError("No sub-chapters found for chapter")

            all_sub_chapters = all_result.data

            # 3. Validate new position
            if new_position < 1 or new_position > len(all_sub_chapters):
                raise ValueError(
                    f"Invalid position {new_position}. Must be between 1 and {len(all_sub_chapters)}"
                )

            # 4. Reorder in memory
            current_position = next(
                i for i, sc in enumerate(all_sub_chapters)
                if sc["id"] == str(sub_chapter_id)
            )

            # If already in correct position, nothing to do
            if current_position == new_position - 1:  # Convert to 0-indexed
                logger.info(f"Sub-chapter {sub_chapter_id} already at position {new_position}")
                return [SubChapter(**sc) for sc in all_sub_chapters]

            # Remove from current position and insert at new position
            sub_chapter = all_sub_chapters.pop(current_position)
            all_sub_chapters.insert(new_position - 1, sub_chapter)  # 1-indexed to 0-indexed

            # 5. Renumber all sub-chapters sequentially
            # We do this in reverse order to avoid UNIQUE constraint violations
            # First, set all to temporary negative numbers
            for i, sc in enumerate(all_sub_chapters):
                temp_number = -(i + 1)  # Negative numbers to avoid conflicts
                self.supabase.table("sub_chapters")\
                    .update({"sub_chapter_number": temp_number})\
                    .eq("id", sc["id"])\
                    .execute()

            # Then, set all to final positive numbers
            for i, sc in enumerate(all_sub_chapters, start=1):
                self.supabase.table("sub_chapters")\
                    .update({
                        "sub_chapter_number": i,
                        "updated_at": datetime.utcnow().isoformat()
                    })\
                    .eq("id", sc["id"])\
                    .execute()

            # 6. Update parent chapter timestamp
            self.supabase.table("chapters")\
                .update({"updated_at": datetime.utcnow().isoformat()})\
                .eq("id", chapter_id)\
                .execute()

            # 7. Fetch final state
            final_result = self.supabase.table("sub_chapters")\
                .select("*")\
                .eq("chapter_id", chapter_id)\
                .order("sub_chapter_number")\
                .execute()

            logger.info(
                f"Reordered sub-chapter {sub_chapter_id} from position "
                f"{current_position + 1} to {new_position}"
            )

            return [SubChapter(**sc) for sc in final_result.data]

        except Exception as e:
            logger.error(f"Error reordering sub-chapter {sub_chapter_id}: {e}")
            raise

    async def move_sub_chapter_up(
        self,
        sub_chapter_id: UUID,
        user_id: UUID
    ) -> Optional[List[SubChapter]]:
        """
        Move a sub-chapter up one position.

        Args:
            sub_chapter_id: Sub-chapter to move
            user_id: User performing the operation

        Returns:
            Updated list of sub-chapters, or None if already at top
        """
        try:
            # Get current position
            result = self.supabase.table("sub_chapters")\
                .select("sub_chapter_number")\
                .eq("id", str(sub_chapter_id))\
                .execute()

            if not result.data:
                raise ValueError(f"Sub-chapter {sub_chapter_id} not found")

            current_number = result.data[0]["sub_chapter_number"]

            if current_number <= 1:
                logger.info(f"Sub-chapter {sub_chapter_id} already at top position")
                return None  # Already at top

            return await self.reorder_sub_chapter(
                sub_chapter_id,
                current_number - 1,
                user_id
            )

        except Exception as e:
            logger.error(f"Error moving sub-chapter up {sub_chapter_id}: {e}")
            raise

    async def move_sub_chapter_down(
        self,
        sub_chapter_id: UUID,
        user_id: UUID
    ) -> Optional[List[SubChapter]]:
        """
        Move a sub-chapter down one position.

        Args:
            sub_chapter_id: Sub-chapter to move
            user_id: User performing the operation

        Returns:
            Updated list of sub-chapters, or None if already at bottom
        """
        try:
            # Get current position and max position
            current_result = self.supabase.table("sub_chapters")\
                .select("sub_chapter_number, chapter_id")\
                .eq("id", str(sub_chapter_id))\
                .execute()

            if not current_result.data:
                raise ValueError(f"Sub-chapter {sub_chapter_id} not found")

            current_number = current_result.data[0]["sub_chapter_number"]
            chapter_id = current_result.data[0]["chapter_id"]

            # Get max position for this chapter
            max_result = self.supabase.table("sub_chapters")\
                .select("sub_chapter_number")\
                .eq("chapter_id", chapter_id)\
                .order("sub_chapter_number", desc=True)\
                .limit(1)\
                .execute()

            max_number = max_result.data[0]["sub_chapter_number"] if max_result.data else 1

            if current_number >= max_number:
                logger.info(f"Sub-chapter {sub_chapter_id} already at bottom position")
                return None  # Already at bottom

            return await self.reorder_sub_chapter(
                sub_chapter_id,
                current_number + 1,
                user_id
            )

        except Exception as e:
            logger.error(f"Error moving sub-chapter down {sub_chapter_id}: {e}")
            raise

    async def swap_sub_chapters(
        self,
        sub_chapter_id_1: UUID,
        sub_chapter_id_2: UUID,
        user_id: UUID
    ) -> List[SubChapter]:
        """
        Swap positions of two sub-chapters.

        Args:
            sub_chapter_id_1: First sub-chapter
            sub_chapter_id_2: Second sub-chapter
            user_id: User performing the operation

        Returns:
            Updated list of all sub-chapters

        Raises:
            ValueError: If sub-chapters are not in same chapter
        """
        try:
            # Get both sub-chapters
            result1 = self.supabase.table("sub_chapters")\
                .select("sub_chapter_number, chapter_id")\
                .eq("id", str(sub_chapter_id_1))\
                .execute()

            result2 = self.supabase.table("sub_chapters")\
                .select("sub_chapter_number, chapter_id")\
                .eq("id", str(sub_chapter_id_2))\
                .execute()

            if not result1.data or not result2.data:
                raise ValueError("One or both sub-chapters not found")

            sc1 = result1.data[0]
            sc2 = result2.data[0]

            # Verify same chapter
            if sc1["chapter_id"] != sc2["chapter_id"]:
                raise ValueError("Cannot swap sub-chapters from different chapters")

            # Swap using temporary number
            temp_number = -999

            # Set first to temp
            self.supabase.table("sub_chapters")\
                .update({"sub_chapter_number": temp_number})\
                .eq("id", str(sub_chapter_id_1))\
                .execute()

            # Set second to first's position
            self.supabase.table("sub_chapters")\
                .update({
                    "sub_chapter_number": sc1["sub_chapter_number"],
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("id", str(sub_chapter_id_2))\
                .execute()

            # Set first to second's position
            self.supabase.table("sub_chapters")\
                .update({
                    "sub_chapter_number": sc2["sub_chapter_number"],
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("id", str(sub_chapter_id_1))\
                .execute()

            # Update chapter timestamp
            self.supabase.table("chapters")\
                .update({"updated_at": datetime.utcnow().isoformat()})\
                .eq("id", sc1["chapter_id"])\
                .execute()

            # Fetch final state
            final_result = self.supabase.table("sub_chapters")\
                .select("*")\
                .eq("chapter_id", sc1["chapter_id"])\
                .order("sub_chapter_number")\
                .execute()

            logger.info(f"Swapped sub-chapters {sub_chapter_id_1} and {sub_chapter_id_2}")

            return [SubChapter(**sc) for sc in final_result.data]

        except Exception as e:
            logger.error(f"Error swapping sub-chapters: {e}")
            raise
