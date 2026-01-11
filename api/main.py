"""
Consciousness Trilogy App - FastAPI Application

Main entry point for the backend API server.
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.config import settings
from api.routes import trilogy
from api.routes import world_rules
from api.routes import character
from api.routes import chapter
from api.routes import sub_chapter
from api.routes import books
from api.routes import generation_jobs
from api.routes import user_profile
from api.services.task_queue import close_redis_pool, start_worker, stop_worker
import logging
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Consciousness Trilogy API",
    description="""
    Backend API for the Consciousness Trilogy writing assistant.

    ## Features
    - **Epic 1**: Project foundation and trilogy creation
    - **Epic 3**: World Building & Rules Engine (CRUD + RAG)
    - **Epic 10**: Async Job Queue System with Real-Time Progress Tracking
    - **Authentication**: JWT-based authentication via Supabase
    - **Row-Level Security**: Users can only access their own data

    ## Architecture
    - **Database**: Supabase (PostgreSQL with RLS)
    - **Vector Store**: ChromaDB (embedded mode with DuckDB+Parquet)
    - **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
    - **Cache**: Redis (async job queue via Arq + progress tracking)
    - **LLM**: AWS Bedrock - Mistral 7B
    - **WebSocket**: Real-time job progress updates
    """,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["health"], summary="Health check endpoint")
async def health_check():
    """
    Health check endpoint to verify API is running.

    Returns:
    - status: "healthy"
    - environment: current environment (development/production)
    """
    return {
        "status": "healthy",
        "environment": settings.environment,
        "version": "0.1.0",
    }


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors.

    Logs the error and returns a generic 500 response.
    """
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred. Please try again later."
        },
    )


# Register routers
app.include_router(user_profile.router)
app.include_router(trilogy.router)
app.include_router(world_rules.router)
app.include_router(character.router)
app.include_router(chapter.router)
app.include_router(sub_chapter.router)
app.include_router(books.router)
app.include_router(generation_jobs.router)


# Startup event
@app.on_event("startup")
async def startup_event():
    """
    Application startup event.

    Logs startup information and verifies configuration.
    Starts the Arq worker for background task processing.
    """
    logger.info("=" * 60)
    logger.info("Consciousness Trilogy API - Starting Up")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug Mode: {settings.debug}")
    logger.info(f"Supabase URL: {settings.supabase_url}")
    logger.info(f"Frontend URL: {settings.frontend_url}")
    logger.info("=" * 60)

    # Start Arq worker for background task processing
    logger.info("Starting Arq worker for background tasks...")
    await start_worker()
    logger.info("Arq worker started successfully")
    logger.info("=" * 60)


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event.

    Cleanup operations (if needed).
    """
    logger.info("Consciousness Trilogy API - Shutting Down")

    # Stop Arq worker
    await stop_worker()
    logger.info("Stopped Arq worker")

    # Close Redis pool for task queue
    await close_redis_pool()
    logger.info("Closed Redis connection pool")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
