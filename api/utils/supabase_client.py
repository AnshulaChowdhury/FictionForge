"""
Supabase client singleton for database operations.
"""

from supabase import create_client, Client
from functools import lru_cache
from api.config import settings


@lru_cache()
def get_supabase_client() -> Client:
    """
    Get cached Supabase client instance.
    Uses service role key for backend operations with full access.

    Returns:
        Client: Supabase client instance with service role privileges
    """
    return create_client(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_service_role_key,
    )


# Export singleton instance
supabase = get_supabase_client()
