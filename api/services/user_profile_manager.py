"""
UserProfileManager Service

Handles user profile CRUD operations.
"""

import logging
from typing import Optional
from api.models.user_profile import (
    UserProfileResponse,
    UpdateUserProfileRequest,
)
from api.utils.supabase_client import supabase
from postgrest.exceptions import APIError

logger = logging.getLogger(__name__)


class UserProfileError(Exception):
    """Raised when profile operations fail."""
    pass


class UserProfileManager:
    """
    Manages user profile operations.
    """

    def __init__(self, user_id: str):
        """
        Initialize UserProfileManager for a specific user.

        Args:
            user_id: UUID of the authenticated user (from JWT token)
        """
        self.user_id = user_id

    def get_profile(self) -> Optional[UserProfileResponse]:
        """
        Get the current user's profile.

        Returns:
            UserProfileResponse if profile exists, None otherwise

        Raises:
            UserProfileError: If database query fails
        """
        try:
            response = (
                supabase.table("user_profiles")
                .select("*")
                .eq("id", self.user_id)
                .execute()
            )

            if not response.data or len(response.data) == 0:
                return None

            return UserProfileResponse(**response.data[0])

        except APIError as e:
            raise UserProfileError(f"Failed to fetch profile: {str(e)}") from e

    def update_profile(
        self, request: UpdateUserProfileRequest
    ) -> UserProfileResponse:
        """
        Update the current user's profile.

        Args:
            request: Profile update request with fields to update

        Returns:
            Updated UserProfileResponse

        Raises:
            UserProfileError: If update fails or profile doesn't exist
        """
        try:
            # Build update dict with only provided fields
            update_dict = request.model_dump(exclude_none=True)

            if not update_dict:
                # Nothing to update, return current profile
                current = self.get_profile()
                if current is None:
                    raise UserProfileError("Profile not found")
                return current

            # Update the profile
            response = (
                supabase.table("user_profiles")
                .update(update_dict)
                .eq("id", self.user_id)
                .execute()
            )

            if not response.data or len(response.data) == 0:
                raise UserProfileError("Profile not found or update failed")

            return UserProfileResponse(**response.data[0])

        except APIError as e:
            raise UserProfileError(f"Failed to update profile: {str(e)}") from e

    def create_profile(self, name: str) -> UserProfileResponse:
        """
        Create a profile for the current user.

        This is a fallback in case auto-creation didn't work.

        Args:
            name: User's name

        Returns:
            Created UserProfileResponse

        Raises:
            UserProfileError: If creation fails
        """
        try:
            profile_data = {
                "id": self.user_id,
                "name": name,
            }

            response = (
                supabase.table("user_profiles")
                .insert(profile_data)
                .execute()
            )

            if not response.data or len(response.data) == 0:
                raise UserProfileError("Failed to create profile")

            return UserProfileResponse(**response.data[0])

        except APIError as e:
            raise UserProfileError(f"Failed to create profile: {str(e)}") from e
