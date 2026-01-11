"""
Sub-Chapter Update Service for Epic 6

Handles plot point updates with automatic flagging for review
when significant changes are detected.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
import logging
from difflib import SequenceMatcher

from api.utils.supabase_client import get_supabase_client
from api.models.sub_chapter import (
    SubChapter,
    SubChapterUpdate,
    ContentReviewFlag,
    FlagType
)

logger = logging.getLogger(__name__)


class SubChapterUpdateService:
    """Handles sub-chapter updates with automatic consistency flagging"""

    def __init__(self):
        self.supabase = get_supabase_client()
        self.similarity_threshold = 0.7  # 70% similarity to avoid flagging

    async def update_plot_points(
        self,
        sub_chapter_id: UUID,
        new_title: Optional[str],
        new_plot_points: Optional[str],
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Update sub-chapter plot points and flag for review if significantly changed.

        Uses text similarity analysis to detect significant changes that warrant
        content review/regeneration.

        Args:
            sub_chapter_id: Sub-chapter identifier
            new_title: Updated title (optional)
            new_plot_points: Updated plot points (optional)
            user_id: User performing the update

        Returns:
            Dict with updated sub-chapter and flagging information

        Raises:
            ValueError: If sub-chapter not found
        """
        try:
            # 1. Get current sub-chapter
            result = self.supabase.table("sub_chapters")\
                .select("*")\
                .eq("id", str(sub_chapter_id))\
                .execute()

            if not result.data:
                raise ValueError(f"Sub-chapter {sub_chapter_id} not found")

            current = result.data[0]
            flagged = False
            similarity_score = 1.0

            # 2. Detect significant plot point changes
            if new_plot_points and new_plot_points != current.get("plot_points"):
                similarity_score = self._calculate_text_similarity(
                    current.get("plot_points") or "",
                    new_plot_points
                )

                # If less than 70% similar, flag for review
                if similarity_score < self.similarity_threshold:
                    await self._create_review_flag(
                        sub_chapter_id=sub_chapter_id,
                        flag_type=FlagType.USER_MARKED,
                        reason=f"Plot points significantly modified (similarity: {similarity_score:.0%})",
                        user_id=user_id
                    )
                    flagged = True

            # 3. Update sub-chapter
            update_data = {}
            if new_title is not None:
                update_data["title"] = new_title
            if new_plot_points is not None:
                update_data["plot_points"] = new_plot_points

            if update_data:
                update_data["updated_at"] = datetime.utcnow().isoformat()

                updated_result = self.supabase.table("sub_chapters")\
                    .update(update_data)\
                    .eq("id", str(sub_chapter_id))\
                    .execute()

                updated_sub_chapter = updated_result.data[0] if updated_result.data else current
            else:
                updated_sub_chapter = current

            logger.info(
                f"Updated sub-chapter {sub_chapter_id} plot points "
                f"(similarity: {similarity_score:.2f}, flagged: {flagged})"
            )

            return {
                "sub_chapter": SubChapter(**updated_sub_chapter),
                "flagged": flagged,
                "similarity_score": similarity_score,
                "should_regenerate": flagged  # Suggest regeneration if significantly changed
            }

        except Exception as e:
            logger.error(f"Error updating plot points for {sub_chapter_id}: {e}")
            raise

    async def get_content_flags(
        self,
        sub_chapter_id: UUID,
        user_id: UUID,
        unresolved_only: bool = True
    ) -> List[ContentReviewFlag]:
        """
        Get content review flags for a sub-chapter.

        Args:
            sub_chapter_id: Sub-chapter identifier
            user_id: User requesting flags
            unresolved_only: Only return unresolved flags

        Returns:
            List of content review flags
        """
        try:
            query = self.supabase.table("content_review_flags")\
                .select("*")\
                .eq("sub_chapter_id", str(sub_chapter_id))\
                .order("created_at", desc=True)

            if unresolved_only:
                query = query.is_("resolved_at", "null")

            result = query.execute()

            return [ContentReviewFlag(**flag) for flag in result.data]

        except Exception as e:
            logger.error(f"Error fetching content flags for {sub_chapter_id}: {e}")
            return []

    async def resolve_flag(
        self,
        flag_id: UUID,
        user_id: UUID,
        resolution_notes: Optional[str] = None
    ) -> bool:
        """
        Mark a content review flag as resolved.

        Args:
            flag_id: Flag identifier
            user_id: User resolving the flag
            resolution_notes: Optional notes about resolution

        Returns:
            True if successful
        """
        try:
            update_data = {
                "resolved_at": datetime.utcnow().isoformat(),
                "resolved_by_user_id": str(user_id)
            }

            result = self.supabase.table("content_review_flags")\
                .update(update_data)\
                .eq("id", str(flag_id))\
                .execute()

            if result.data:
                logger.info(f"Resolved content review flag {flag_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error resolving flag {flag_id}: {e}")
            return False

    async def bulk_resolve_flags(
        self,
        sub_chapter_id: UUID,
        user_id: UUID
    ) -> int:
        """
        Resolve all unresolved flags for a sub-chapter.

        Useful after regenerating content to clear all pending flags.

        Args:
            sub_chapter_id: Sub-chapter identifier
            user_id: User resolving flags

        Returns:
            Number of flags resolved
        """
        try:
            update_data = {
                "resolved_at": datetime.utcnow().isoformat(),
                "resolved_by_user_id": str(user_id)
            }

            result = self.supabase.table("content_review_flags")\
                .update(update_data)\
                .eq("sub_chapter_id", str(sub_chapter_id))\
                .is_("resolved_at", "null")\
                .execute()

            count = len(result.data) if result.data else 0
            logger.info(f"Resolved {count} flags for sub-chapter {sub_chapter_id}")
            return count

        except Exception as e:
            logger.error(f"Error bulk resolving flags for {sub_chapter_id}: {e}")
            return 0

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two text strings using SequenceMatcher.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0.0 to 1.0)
        """
        if not text1 and not text2:
            return 1.0
        if not text1 or not text2:
            return 0.0

        # Normalize whitespace for better comparison
        text1_normalized = " ".join(text1.split())
        text2_normalized = " ".join(text2.split())

        matcher = SequenceMatcher(None, text1_normalized, text2_normalized)
        return matcher.ratio()

    async def _create_review_flag(
        self,
        sub_chapter_id: UUID,
        flag_type: str,
        reason: str,
        user_id: UUID
    ) -> UUID:
        """
        Create a content review flag.

        Args:
            sub_chapter_id: Sub-chapter identifier
            flag_type: Type of flag
            reason: Reason for flagging
            user_id: User who triggered the flag

        Returns:
            Flag ID
        """
        try:
            flag_data = {
                "sub_chapter_id": str(sub_chapter_id),
                "flag_type": flag_type,
                "reason": reason,
                "flagged_at": datetime.utcnow().isoformat()
            }

            result = self.supabase.table("content_review_flags")\
                .insert(flag_data)\
                .execute()

            if result.data:
                flag_id = UUID(result.data[0]["id"])
                logger.info(f"Created review flag {flag_id} for sub-chapter {sub_chapter_id}")
                return flag_id

            raise Exception("Failed to create review flag")

        except Exception as e:
            logger.error(f"Error creating review flag: {e}")
            raise
