"""
User Profile API Routes

Endpoints for managing user profile data.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from api.models.user_profile import (
    UserProfileResponse,
    UpdateUserProfileRequest,
)
from api.services.user_profile_manager import (
    UserProfileManager,
    UserProfileError,
)
from api.middleware.auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get(
    "",
    response_model=UserProfileResponse,
    summary="Get current user's profile",
    description="""
    Get the authenticated user's profile information.

    Returns profile data including name, bio, and avatar.
    Returns 404 if profile doesn't exist (shouldn't happen with auto-creation).

    Authentication required.
    """,
)
async def get_profile(
    user_id: str = Depends(get_current_user_id),
) -> UserProfileResponse:
    """
    Get current user's profile.

    Returns:
    - User profile data

    Raises:
    - 404: If profile not found
    """
    logger.info(f"=== GET PROFILE ENDPOINT CALLED ===")
    logger.info(f"User ID: {user_id}")

    try:
        manager = UserProfileManager(user_id=user_id)
        profile = manager.get_profile()

        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found",
            )

        logger.info(f"Profile retrieved for user: {profile.name}")
        return profile

    except HTTPException:
        # Re-raise HTTP exceptions as-is (don't convert to 500)
        raise
    except UserProfileError as e:
        logger.error(f"UserProfileError: {str(e)}", exc_info=True)
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
    "",
    response_model=UserProfileResponse,
    summary="Create current user's profile",
    status_code=status.HTTP_201_CREATED,
    description="""
    Create a profile for the authenticated user.

    This is a fallback in case auto-creation didn't work.

    Authentication required.
    """,
)
async def create_profile(
    name: str,
    user_id: str = Depends(get_current_user_id),
) -> UserProfileResponse:
    """
    Create current user's profile.

    Returns:
    - Created profile data

    Raises:
    - 409: If profile already exists
    """
    logger.info(f"=== CREATE PROFILE ENDPOINT CALLED ===")
    logger.info(f"User ID: {user_id}")

    try:
        manager = UserProfileManager(user_id=user_id)

        # Check if profile already exists
        existing = manager.get_profile()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Profile already exists",
            )

        new_profile = manager.create_profile(name=name)
        logger.info(f"Profile created for user: {new_profile.name}")
        return new_profile

    except HTTPException:
        raise
    except UserProfileError as e:
        logger.error(f"UserProfileError: {str(e)}", exc_info=True)
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


@router.put(
    "",
    response_model=UserProfileResponse,
    summary="Update current user's profile",
    description="""
    Update the authenticated user's profile information.

    All fields are optional - only provided fields will be updated.

    Authentication required.
    """,
)
async def update_profile(
    request: UpdateUserProfileRequest,
    user_id: str = Depends(get_current_user_id),
) -> UserProfileResponse:
    """
    Update current user's profile.

    Request Body (all optional):
    - name: Updated name
    - bio: Updated bio/about
    - avatar_url: Updated avatar URL

    Returns:
    - Updated profile data

    Raises:
    - 404: If profile not found
    """
    logger.info(f"=== UPDATE PROFILE ENDPOINT CALLED ===")
    logger.info(f"User ID: {user_id}")

    try:
        manager = UserProfileManager(user_id=user_id)
        updated_profile = manager.update_profile(request)

        logger.info(f"Profile updated for user: {updated_profile.name}")
        return updated_profile

    except UserProfileError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            ) from e
        logger.error(f"UserProfileError: {str(e)}", exc_info=True)
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
