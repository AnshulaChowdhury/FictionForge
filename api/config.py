"""
Application configuration management using Pydantic Settings.
Loads environment variables from .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path
import os

# Get the api directory (same directory as this file)
API_DIR = Path(__file__).parent
ENV_FILE = API_DIR / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True
    environment: str = "development"
    frontend_url: str = "http://localhost:5173"

    # Supabase Configuration
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    # ChromaDB Configuration
    # Note: Using embedded mode (DuckDB+Parquet) - no HTTP server needed
    chromadb_persist_dir: str = "./chromadb_data"

    # Redis Configuration (for future epics)
    redis_url: str = "redis://localhost:6379"
    redis_ttl_seconds: int = 900

    # Embeddings Configuration
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_cache_dir: str = "./models/embeddings"
    embedding_dimension: int = 384

    # AWS Bedrock Configuration
    aws_api_gateway_url: str = ""
    aws_bedrock_timeout: int = 120
    aws_region: str = "ca-central-1"

    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Using lru_cache ensures settings are only loaded once.
    """
    return Settings()


# Export settings instance for convenience
settings = get_settings()
