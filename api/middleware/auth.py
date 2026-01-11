"""
Authentication middleware and dependencies.

Handles JWT token validation with Supabase Auth.
"""

import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from api.utils.supabase_client import supabase
from typing import Optional

logger = logging.getLogger(__name__)

# Security scheme for Bearer token
security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    Extract and validate user ID from JWT token.

    This dependency can be used in route functions to ensure authentication
    and get the current user's ID.

    Args:
        credentials: HTTP Bearer token from Authorization header

    Returns:
        str: User ID (UUID) from the validated JWT token

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    try:
        # Verify JWT token with Supabase
        user_response = supabase.auth.get_user(token)

        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user_response.user.id

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_optional_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> Optional[str]:
    """
    Extract user ID from JWT token if provided (optional authentication).

    Use this for endpoints that work both with and without authentication.

    Args:
        credentials: Optional HTTP Bearer token

    Returns:
        str: User ID if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        user_response = supabase.auth.get_user(credentials.credentials)
        if user_response and user_response.user:
            return user_response.user.id
    except Exception:
        pass

    return None


async def validate_token(token: str) -> Optional[str]:
    """
    Validate a JWT token and extract user ID.

    For use in WebSocket connections and other contexts where Depends() cannot be used.

    Args:
        token: JWT token string

    Returns:
        str: User ID if valid, None if invalid
    """
    try:
        user_response = supabase.auth.get_user(token)
        if user_response and user_response.user:
            return user_response.user.id
    except Exception as e:
        return None

    return None
