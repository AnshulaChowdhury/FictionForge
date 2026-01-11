"""
Async Task Queue Service using Arq (Redis-based).

Handles background tasks for:
- World rule embedding
- Rule re-embedding on updates
- Batch operations
"""

from typing import Optional, Dict, Any, List
from arq import create_pool, Worker
from arq.connections import RedisSettings, ArqRedis
from api.config import get_settings
# Lazy import RuleContextProvider to avoid ChromaDB import issues
# from api.services.rule_context_provider import RuleContextProvider
import logging
import asyncio

logger = logging.getLogger(__name__)

# Global pool instance
_redis_pool: Optional[ArqRedis] = None

# Global worker instance
_worker: Optional[Worker] = None
_worker_task: Optional[asyncio.Task] = None


async def get_redis_pool() -> ArqRedis:
    """
    Get or create Redis connection pool for Arq.

    Returns:
        ArqRedis connection pool
    """
    global _redis_pool

    if _redis_pool is None:
        settings = get_settings()

        # Parse Redis URL (format: redis://host:port or redis://host:port/db)
        redis_settings = RedisSettings.from_dsn(settings.redis_url)

        _redis_pool = await create_pool(redis_settings)
        logger.info("Created Arq Redis connection pool")

    return _redis_pool


async def close_redis_pool():
    """Close the Redis connection pool."""
    global _redis_pool

    if _redis_pool is not None:
        await _redis_pool.close()
        _redis_pool = None
        logger.info("Closed Arq Redis connection pool")


async def start_worker():
    """
    Start the Arq worker as a background task.

    The worker processes jobs from the Redis queue automatically.
    This is called during FastAPI startup.
    """
    global _worker, _worker_task

    if _worker is not None:
        logger.warning("Worker already running")
        return

    try:
        # Create worker instance
        _worker = Worker(
            functions=WorkerSettings.functions,
            redis_settings=WorkerSettings.redis_settings,
            max_jobs=WorkerSettings.max_jobs,
            job_timeout=WorkerSettings.job_timeout,
            keep_result=WorkerSettings.keep_result,
            handle_signals=False,  # Let FastAPI handle signals
        )

        # Run worker in background
        _worker_task = asyncio.create_task(_worker.async_run())

        logger.info(f"Arq worker started with {len(WorkerSettings.functions)} functions")
        logger.info(f"Max concurrent jobs: {WorkerSettings.max_jobs}")

    except Exception as e:
        logger.error(f"Failed to start Arq worker: {e}")
        _worker = None
        _worker_task = None
        raise


async def stop_worker():
    """
    Stop the Arq worker gracefully.

    This is called during FastAPI shutdown.
    """
    global _worker, _worker_task

    if _worker is None:
        return

    try:
        logger.info("Stopping Arq worker...")

        # Stop the worker
        await _worker.close()

        # Cancel the background task if it's still running
        if _worker_task and not _worker_task.done():
            _worker_task.cancel()
            try:
                await _worker_task
            except asyncio.CancelledError:
                pass

        _worker = None
        _worker_task = None

        logger.info("Arq worker stopped successfully")

    except Exception as e:
        logger.error(f"Error stopping Arq worker: {e}")


# ============================================================================
# Background Task Functions
# ============================================================================

async def _invalidate_rule_cache_for_trilogy(trilogy_id: str):
    """
    Invalidate all cached rule queries for a trilogy.

    This ensures that newly created or updated rules show up immediately
    in rule previews without waiting for the 15-minute cache expiration.

    Args:
        trilogy_id: Trilogy identifier
    """
    try:
        from api.utils.redis_client import redis_cache
        from api.utils.supabase_client import get_supabase_client

        # Get all books in this trilogy
        supabase = get_supabase_client()
        books_result = supabase.table('books').select('id').eq('trilogy_id', trilogy_id).execute()

        total_invalidated = 0
        if books_result.data:
            # Invalidate cache for each book in the trilogy
            for book in books_result.data:
                book_id = book['id']
                count = await redis_cache.invalidate_book_rules(book_id)
                total_invalidated += count

        logger.info(f"Invalidated {total_invalidated} cached rule queries for trilogy {trilogy_id}")

    except Exception as e:
        # Don't fail the embedding task if cache invalidation fails
        logger.warning(f"Failed to invalidate rule cache for trilogy {trilogy_id}: {e}")


async def embed_world_rule_task(
    ctx: Dict[str, Any],
    rule_id: str,
    rule_title: str,
    rule_description: str,
    rule_category: str,
    trilogy_id: str
) -> Dict[str, Any]:
    """
    Background task to embed a world rule in ChromaDB.

    Args:
        ctx: Arq context (injected automatically)
        rule_id: Rule identifier
        rule_title: Rule title
        rule_description: Rule description
        rule_category: Rule category
        trilogy_id: Trilogy identifier

    Returns:
        Task result dictionary
    """
    try:
        logger.info(f"Starting embedding task for rule {rule_id}")

        # Lazy import to avoid ChromaDB dependency on main app startup
        from api.services.rule_context_provider import RuleContextProvider
        provider = RuleContextProvider()

        success = await provider.embed_rule(
            rule_id=rule_id,
            rule_title=rule_title,
            rule_description=rule_description,
            rule_category=rule_category,
            trilogy_id=trilogy_id
        )

        if success:
            logger.info(f"Successfully embedded rule {rule_id}")

            # Invalidate cached rule queries so new rule appears immediately
            await _invalidate_rule_cache_for_trilogy(trilogy_id)

            return {"status": "success", "rule_id": rule_id}
        else:
            logger.error(f"Failed to embed rule {rule_id}")
            return {"status": "failed", "rule_id": rule_id, "error": "Embedding failed"}

    except Exception as e:
        logger.error(f"Error in embed_world_rule_task for {rule_id}: {e}")
        return {"status": "error", "rule_id": rule_id, "error": str(e)}


async def update_world_rule_embedding_task(
    ctx: Dict[str, Any],
    rule_id: str,
    rule_title: str,
    rule_description: str,
    rule_category: str,
    trilogy_id: str
) -> Dict[str, Any]:
    """
    Background task to update a world rule embedding in ChromaDB.

    Args:
        ctx: Arq context
        rule_id: Rule identifier
        rule_title: Updated rule title
        rule_description: Updated rule description
        rule_category: Updated rule category
        trilogy_id: Trilogy identifier

    Returns:
        Task result dictionary
    """
    try:
        logger.info(f"Starting embedding update task for rule {rule_id}")

        # Lazy import to avoid ChromaDB dependency on main app startup
        from api.services.rule_context_provider import RuleContextProvider
        provider = RuleContextProvider()

        success = await provider.update_rule_embedding(
            rule_id=rule_id,
            rule_title=rule_title,
            rule_description=rule_description,
            rule_category=rule_category,
            trilogy_id=trilogy_id
        )

        if success:
            logger.info(f"Successfully updated embedding for rule {rule_id}")

            # Invalidate cached rule queries so updated rule appears immediately
            await _invalidate_rule_cache_for_trilogy(trilogy_id)

            return {"status": "success", "rule_id": rule_id}
        else:
            logger.error(f"Failed to update embedding for rule {rule_id}")
            return {"status": "failed", "rule_id": rule_id, "error": "Update failed"}

    except Exception as e:
        logger.error(f"Error in update_world_rule_embedding_task for {rule_id}: {e}")
        return {"status": "error", "rule_id": rule_id, "error": str(e)}


async def delete_world_rule_embedding_task(
    ctx: Dict[str, Any],
    rule_id: str,
    trilogy_id: str
) -> Dict[str, Any]:
    """
    Background task to delete a world rule embedding from ChromaDB.

    Args:
        ctx: Arq context
        rule_id: Rule identifier
        trilogy_id: Trilogy identifier

    Returns:
        Task result dictionary
    """
    try:
        logger.info(f"Starting embedding deletion task for rule {rule_id}")

        provider = RuleContextProvider()

        success = await provider.delete_rule_embedding(
            rule_id=rule_id,
            trilogy_id=trilogy_id
        )

        if success:
            logger.info(f"Successfully deleted embedding for rule {rule_id}")

            # Invalidate cached rule queries so deleted rule disappears immediately
            await _invalidate_rule_cache_for_trilogy(trilogy_id)

            return {"status": "success", "rule_id": rule_id}
        else:
            logger.error(f"Failed to delete embedding for rule {rule_id}")
            return {"status": "failed", "rule_id": rule_id, "error": "Deletion failed"}

    except Exception as e:
        logger.error(f"Error in delete_world_rule_embedding_task for {rule_id}: {e}")
        return {"status": "error", "rule_id": rule_id, "error": str(e)}


async def embed_all_trilogy_rules_task(
    ctx: Dict[str, Any],
    trilogy_id: str
) -> Dict[str, Any]:
    """
    Background task to embed all rules for a trilogy (batch operation).

    Useful for:
    - Initial setup
    - Re-indexing after major changes
    - Recovery from errors

    Args:
        ctx: Arq context
        trilogy_id: Trilogy identifier

    Returns:
        Task result with success/failure counts
    """
    try:
        logger.info(f"Starting batch embedding task for trilogy {trilogy_id}")

        provider = RuleContextProvider()

        result = await provider.embed_all_rules_for_trilogy(trilogy_id)

        logger.info(f"Batch embedding complete for trilogy {trilogy_id}: {result}")
        return {"status": "success", "trilogy_id": trilogy_id, **result}

    except Exception as e:
        logger.error(f"Error in embed_all_trilogy_rules_task for {trilogy_id}: {e}")
        return {"status": "error", "trilogy_id": trilogy_id, "error": str(e)}


async def embed_character_task(
    ctx: Dict[str, Any],
    character_id: str,
    trilogy_id: str,
    name: str,
    description: Optional[str] = None,
    traits: Optional[Dict[str, Any]] = None,
    character_arc: Optional[str] = None,
    consciousness_themes: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Background task to embed character profile into ChromaDB.

    Creates a dedicated collection for the character and embeds:
    - Character profile
    - Traits
    - Character arc
    - Consciousness themes

    Args:
        ctx: Arq context
        character_id: Character identifier
        trilogy_id: Trilogy identifier
        name: Character name
        description: Character description
        traits: Character traits
        character_arc: Character arc
        consciousness_themes: Consciousness themes

    Returns:
        Task result with status and collection info
    """
    try:
        logger.info(f"Starting character embedding for {character_id}")

        from api.services.character_embedding_service import CharacterEmbeddingService

        embedding_service = CharacterEmbeddingService()

        result = await embedding_service.embed_character(
            character_id=character_id,
            trilogy_id=trilogy_id,
            name=name,
            description=description,
            traits=traits,
            character_arc=character_arc,
            consciousness_themes=consciousness_themes
        )

        logger.info(f"Successfully embedded character {character_id}: {result}")

        return {"status": "success", **result}

    except Exception as e:
        logger.error(f"Error embedding character {character_id}: {e}")
        return {"status": "error", "character_id": character_id, "error": str(e)}


async def update_character_embedding_task(
    ctx: Dict[str, Any],
    character_id: str,
    trilogy_id: str,
    name: str,
    description: Optional[str] = None,
    traits: Optional[Dict[str, Any]] = None,
    character_arc: Optional[str] = None,
    consciousness_themes: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Background task to update character embedding in ChromaDB.

    Re-embeds character profile documents with updated data.

    Args:
        ctx: Arq context
        character_id: Character identifier
        trilogy_id: Trilogy identifier
        name: Character name
        description: Updated description
        traits: Updated traits
        character_arc: Updated arc
        consciousness_themes: Updated themes

    Returns:
        Task result with status
    """
    try:
        logger.info(f"Starting character embedding update for {character_id}")

        from api.services.character_embedding_service import CharacterEmbeddingService

        embedding_service = CharacterEmbeddingService()

        result = await embedding_service.update_character_embedding(
            character_id=character_id,
            trilogy_id=trilogy_id,
            name=name,
            description=description,
            traits=traits,
            character_arc=character_arc,
            consciousness_themes=consciousness_themes
        )

        logger.info(f"Successfully updated character embedding {character_id}")

        return {"status": "success", **result}

    except Exception as e:
        logger.error(f"Error updating character embedding {character_id}: {e}")
        return {"status": "error", "character_id": character_id, "error": str(e)}


async def generate_sub_chapter_content_task(
    ctx: Dict[str, Any],
    sub_chapter_id: str,
    chapter_id: str,
    character_id: str,
    plot_points: str,
    target_word_count: int,
    trilogy_id: str,
    book_id: str  # Epic 5B: Required for world rule filtering
) -> Dict[str, Any]:
    """
    Background task to generate sub-chapter content using Character RAG + World Rule RAG (Epic 5B).

    Epic 10: Now includes real-time progress tracking via WebSocket and generation_jobs table.

    Process:
    1. Retrieve character-specific context from ChromaDB (Epic 5A)
    2. Retrieve world rules context from ChromaDB (Epic 5B - NEW)
    3. Build enhanced prompt with plot points + both contexts
    4. Call LLM (AWS Bedrock Mistral 7B) via CharacterRAGGenerator
    5. Create version 1 in sub_chapter_versions
    6. Update sub_chapter.content and word_count
    7. Store generation metadata (which rules were used)
    8. Update character's ChromaDB collection with new content
    9. Update status to 'completed'

    Args:
        ctx: Arq context
        sub_chapter_id: Sub-chapter identifier
        chapter_id: Parent chapter identifier
        character_id: Character perspective
        plot_points: Plot points for this sub-chapter
        target_word_count: Target word count
        trilogy_id: Trilogy identifier
        book_id: Book identifier (for world rule filtering)

    Returns:
        Task result with generated content metadata
    """
    # Epic 10: Find generation job record
    job_id = None
    user_id = None

    try:
        from api.utils.supabase_client import get_supabase_client
        from api.services.generation_job_manager import GenerationJobManager
        from api.middleware.websocket_manager import get_connection_manager
        from api.models.generation_job import ProgressUpdate, JobStage
        from uuid import UUID

        supabase = get_supabase_client()
        job_manager = GenerationJobManager()
        ws_manager = get_connection_manager()

        # Epic 10: Get job record by arq_job_id
        arq_job_id = ctx.get("job_id")  # Arq provides this in context
        if arq_job_id:
            result = supabase.table("generation_jobs")\
                .select("id, user_id")\
                .eq("arq_job_id", arq_job_id)\
                .execute()

            if result.data:
                job_id = UUID(result.data[0]["id"])
                user_id = UUID(result.data[0]["user_id"])

        logger.info(f"Starting RAG content generation for sub-chapter {sub_chapter_id}, job {job_id}")

        # Epic 10: Stage 1 - Retrieving character context (5%)
        if job_id:
            await job_manager.update_job_progress(
                job_id,
                ProgressUpdate(
                    job_id=job_id,
                    stage=JobStage.RETRIEVING_CONTEXT,
                    progress_percentage=5,
                    estimated_seconds_remaining=165  # ~2.75 min remaining
                )
            )
            if user_id:
                await ws_manager.broadcast_job_progress(
                    user_id, job_id, "in_progress", JobStage.RETRIEVING_CONTEXT.value, 5, time_remaining_seconds=165
                )

        # Use CharacterRAGGenerator for actual generation
        from api.services.character_rag_generator import CharacterRAGGenerator

        rag_generator = CharacterRAGGenerator()

        # Epic 10: Stage 2 - Building prompt (15%)
        if job_id:
            await job_manager.update_job_progress(
                job_id,
                ProgressUpdate(
                    job_id=job_id,
                    stage=JobStage.BUILDING_PROMPT,
                    progress_percentage=15,
                    estimated_seconds_remaining=150
                )
            )
            if user_id:
                await ws_manager.broadcast_job_progress(
                    user_id, job_id, "in_progress", JobStage.BUILDING_PROMPT.value, 15, time_remaining_seconds=150
                )

        # Epic 10: Stage 3 - Generating content (20% -> 90%)
        if job_id:
            await job_manager.update_job_progress(
                job_id,
                ProgressUpdate(
                    job_id=job_id,
                    stage=JobStage.GENERATING_CONTENT,
                    progress_percentage=20,
                    estimated_seconds_remaining=120
                )
            )
            if user_id:
                await ws_manager.broadcast_job_progress(
                    user_id, job_id, "in_progress", JobStage.GENERATING_CONTENT.value, 20, time_remaining_seconds=120
                )

        # Generate content using RAG (Epic 5B: now includes world rules)
        result = await rag_generator.generate_content(
            sub_chapter_id=sub_chapter_id,
            character_id=character_id,
            writing_prompt=f"Write the following scene for this chapter.",
            plot_points=plot_points,
            target_word_count=target_word_count,
            trilogy_id=trilogy_id,
            book_id=book_id  # Epic 5B: Required for world rule filtering
        )

        # Epic 10: Stage 4 - Saving results (95%)
        if job_id:
            await job_manager.update_job_progress(
                job_id,
                ProgressUpdate(
                    job_id=job_id,
                    stage=JobStage.SAVING_RESULTS,
                    progress_percentage=95,
                    estimated_seconds_remaining=5
                )
            )
            if user_id:
                await ws_manager.broadcast_job_progress(
                    user_id, job_id, "in_progress", JobStage.SAVING_RESULTS.value, 95, time_remaining_seconds=5
                )

        logger.info(
            f"Successfully generated {result['word_count']} words "
            f"for sub-chapter {sub_chapter_id}"
        )

        # Epic 10: Mark job as completed
        if job_id:
            await job_manager.complete_job(
                job_id,
                word_count=result["word_count"],
                version_id=UUID(result["version_id"]),
                version_number=result["version_number"],
                model_used="Mistral-7B"
            )

            # Epic 10: Broadcast completion via WebSocket
            if user_id:
                await ws_manager.broadcast_job_completed(
                    user_id,
                    job_id,
                    UUID(sub_chapter_id),
                    result["word_count"],
                    UUID(result["version_id"]),
                    result["version_number"]
                )

        return {
            "status": "success",
            "sub_chapter_id": sub_chapter_id,
            "word_count": result["word_count"],
            "version_number": result["version_number"],
            "version_id": result["version_id"]
        }

    except Exception as e:
        logger.error(f"Error generating content for sub-chapter {sub_chapter_id}: {e}")

        # Epic 10: Mark job as failed
        if job_id:
            from api.services.generation_job_manager import GenerationJobManager
            from api.middleware.websocket_manager import get_connection_manager

            job_manager = GenerationJobManager()
            ws_manager = get_connection_manager()

            await job_manager.fail_job(
                job_id,
                error_message=str(e),
                error_type=type(e).__name__
            )

            # Epic 10: Broadcast failure via WebSocket
            if user_id:
                await ws_manager.broadcast_job_failed(
                    user_id,
                    job_id,
                    error_message=str(e),
                    error_type=type(e).__name__,
                    can_retry=True
                )

        # Update status to needs_review
        try:
            from api.utils.supabase_client import get_supabase_client
            from datetime import datetime

            supabase = get_supabase_client()
            supabase.table("sub_chapters").update({
                "status": "needs_review",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", sub_chapter_id).execute()
        except:
            pass

        return {"status": "error", "sub_chapter_id": sub_chapter_id, "error": str(e)}


async def regenerate_sub_chapter_content_task(
    ctx: Dict[str, Any],
    sub_chapter_id: str,
    version_number: int,
    chapter_id: str,
    character_id: str,
    plot_points: str,
    target_word_count: int,
    trilogy_id: str,
    book_id: str,  # Epic 5B: Required for world rule filtering
    change_description: Optional[str] = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Background task to regenerate sub-chapter content as a new version using RAG (Epic 5B).

    Epic 10: Now includes real-time progress tracking via WebSocket and generation_jobs table.

    Uses CharacterRAGGenerator to create version N+1 with updated context including world rules.

    Args:
        ctx: Arq context
        sub_chapter_id: Sub-chapter identifier
        version_number: Version number to create
        chapter_id: Parent chapter identifier
        character_id: Character perspective (may be different from original)
        plot_points: Plot points (may be updated)
        target_word_count: Target word count
        trilogy_id: Trilogy identifier
        book_id: Book identifier (for world rule filtering)
        change_description: Optional description of changes
        user_id: User who triggered regeneration

    Returns:
        Task result with regenerated content metadata
    """
    # Epic 10: Find generation job record
    job_id = None
    job_user_id = None

    try:
        from api.utils.supabase_client import get_supabase_client
        from api.services.generation_job_manager import GenerationJobManager
        from api.middleware.websocket_manager import get_connection_manager
        from api.models.generation_job import ProgressUpdate, JobStage
        from uuid import UUID

        supabase = get_supabase_client()
        job_manager = GenerationJobManager()
        ws_manager = get_connection_manager()

        # Epic 10: Get job record by arq_job_id
        arq_job_id = ctx.get("job_id")
        if arq_job_id:
            result = supabase.table("generation_jobs")\
                .select("id, user_id")\
                .eq("arq_job_id", arq_job_id)\
                .execute()

            if result.data:
                job_id = UUID(result.data[0]["id"])
                job_user_id = UUID(result.data[0]["user_id"])

        logger.info(
            f"Starting RAG regeneration for sub-chapter {sub_chapter_id}, version {version_number}, job {job_id}"
        )

        # Epic 10: Stage 1 - Retrieving context (5%)
        if job_id:
            await job_manager.update_job_progress(
                job_id,
                ProgressUpdate(
                    job_id=job_id,
                    stage=JobStage.RETRIEVING_CONTEXT,
                    progress_percentage=5,
                    estimated_seconds_remaining=165
                )
            )
            if job_user_id:
                await ws_manager.broadcast_job_progress(
                    job_user_id, job_id, "in_progress", JobStage.RETRIEVING_CONTEXT.value, 5, time_remaining_seconds=165
                )

        # Use CharacterRAGGenerator for regeneration
        from api.services.character_rag_generator import CharacterRAGGenerator
        from datetime import datetime

        rag_generator = CharacterRAGGenerator()

        # Epic 10: Stage 2 - Building prompt (15%)
        if job_id:
            await job_manager.update_job_progress(
                job_id,
                ProgressUpdate(
                    job_id=job_id,
                    stage=JobStage.BUILDING_PROMPT,
                    progress_percentage=15,
                    estimated_seconds_remaining=150
                )
            )
            if job_user_id:
                await ws_manager.broadcast_job_progress(
                    job_user_id, job_id, "in_progress", JobStage.BUILDING_PROMPT.value, 15, time_remaining_seconds=150
                )

        # Epic 10: Stage 3 - Generating content (20%)
        if job_id:
            await job_manager.update_job_progress(
                job_id,
                ProgressUpdate(
                    job_id=job_id,
                    stage=JobStage.GENERATING_CONTENT,
                    progress_percentage=20,
                    estimated_seconds_remaining=120
                )
            )
            if job_user_id:
                await ws_manager.broadcast_job_progress(
                    job_user_id, job_id, "in_progress", JobStage.GENERATING_CONTENT.value, 20, time_remaining_seconds=120
                )

        # Generate new content using RAG (Epic 5B: includes world rules)
        result = await rag_generator.generate_content(
            sub_chapter_id=sub_chapter_id,
            character_id=character_id,
            writing_prompt="Write this scene with the character's unique voice.",
            plot_points=plot_points,
            target_word_count=target_word_count,
            trilogy_id=trilogy_id,
            book_id=book_id  # Epic 5B: Required for world rule filtering
        )

        # Epic 10: Stage 4 - Saving results (95%)
        if job_id:
            await job_manager.update_job_progress(
                job_id,
                ProgressUpdate(
                    job_id=job_id,
                    stage=JobStage.SAVING_RESULTS,
                    progress_percentage=95,
                    estimated_seconds_remaining=5
                )
            )
            if job_user_id:
                await ws_manager.broadcast_job_progress(
                    job_user_id, job_id, "in_progress", JobStage.SAVING_RESULTS.value, 95, time_remaining_seconds=5
                )

        # Update the version's change description if provided
        if change_description:
            supabase.table("sub_chapter_versions").update({
                "change_description": change_description
            }).eq("id", result["version_id"]).execute()

        # Update created_by_user_id if provided
        if user_id:
            supabase.table("sub_chapter_versions").update({
                "created_by_user_id": user_id
            }).eq("id", result["version_id"]).execute()

        logger.info(
            f"Successfully regenerated sub-chapter {sub_chapter_id}, "
            f"version {result['version_number']}, {result['word_count']} words"
        )

        # Epic 10: Mark job as completed
        if job_id:
            await job_manager.complete_job(
                job_id,
                word_count=result["word_count"],
                version_id=UUID(result["version_id"]),
                version_number=result["version_number"],
                model_used="Mistral-7B"
            )

            # Epic 10: Broadcast completion via WebSocket
            if job_user_id:
                await ws_manager.broadcast_job_completed(
                    job_user_id,
                    job_id,
                    UUID(sub_chapter_id),
                    result["word_count"],
                    UUID(result["version_id"]),
                    result["version_number"]
                )

        return {
            "status": "success",
            "sub_chapter_id": sub_chapter_id,
            "version_number": result["version_number"],
            "version_id": result["version_id"],
            "word_count": result["word_count"]
        }

    except Exception as e:
        logger.error(f"Error regenerating sub-chapter {sub_chapter_id}: {e}")

        # Epic 10: Mark job as failed
        if job_id:
            await job_manager.fail_job(
                job_id,
                error_message=str(e),
                error_type=type(e).__name__
            )

            # Epic 10: Broadcast failure via WebSocket
            if job_user_id:
                await ws_manager.broadcast_job_failed(
                    job_user_id,
                    job_id,
                    error_message=str(e),
                    error_type=type(e).__name__,
                    can_retry=True
                )

        # Update status to needs_review
        try:
            from datetime import datetime

            supabase = get_supabase_client()
            supabase.table("sub_chapters").update({
                "status": "needs_review",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", sub_chapter_id).execute()
        except:
            pass

        return {
            "status": "error",
            "sub_chapter_id": sub_chapter_id,
            "version_number": version_number,
            "error": str(e)
        }


# ============================================================================
# Task Queue Client
# ============================================================================

class TaskQueue:
    """
    Client for enqueuing background tasks.

    This class provides a clean interface for adding tasks to the queue
    without dealing with Redis connection details.
    """

    @staticmethod
    async def enqueue_rule_embedding(
        rule_id: str,
        rule_title: str,
        rule_description: str,
        rule_category: str,
        trilogy_id: str,
        delay: Optional[int] = None
    ) -> Optional[str]:
        """
        Enqueue a task to embed a world rule.

        Args:
            rule_id: Rule identifier
            rule_title: Rule title
            rule_description: Rule description
            rule_category: Rule category
            trilogy_id: Trilogy identifier
            delay: Optional delay in seconds before processing

        Returns:
            Job ID if successful, None otherwise
        """
        try:
            pool = await get_redis_pool()

            job = await pool.enqueue_job(
                'embed_world_rule_task',
                rule_id,
                rule_title,
                rule_description,
                rule_category,
                trilogy_id,
                _defer_by=delay
            )

            logger.info(f"Enqueued embedding task for rule {rule_id}, job_id: {job.job_id}")
            return job.job_id

        except Exception as e:
            logger.error(f"Error enqueuing rule embedding task: {e}")
            return None

    @staticmethod
    async def enqueue_rule_embedding_update(
        rule_id: str,
        rule_title: str,
        rule_description: str,
        rule_category: str,
        trilogy_id: str,
        delay: Optional[int] = 2  # Default 2-second debounce
    ) -> Optional[str]:
        """
        Enqueue a task to update a rule embedding (with debouncing).

        Args:
            rule_id: Rule identifier
            rule_title: Updated rule title
            rule_description: Updated rule description
            rule_category: Updated rule category
            trilogy_id: Trilogy identifier
            delay: Delay in seconds (for debouncing rapid updates)

        Returns:
            Job ID if successful, None otherwise
        """
        try:
            pool = await get_redis_pool()

            job = await pool.enqueue_job(
                'update_world_rule_embedding_task',
                rule_id,
                rule_title,
                rule_description,
                rule_category,
                trilogy_id,
                _defer_by=delay,
                _job_id=f"update_rule_{rule_id}"  # Deduplicate rapid updates
            )

            logger.info(f"Enqueued update task for rule {rule_id}, job_id: {job.job_id}")
            return job.job_id

        except Exception as e:
            logger.error(f"Error enqueuing rule update task: {e}")
            return None

    @staticmethod
    async def enqueue_rule_embedding_deletion(
        rule_id: str,
        trilogy_id: str
    ) -> Optional[str]:
        """
        Enqueue a task to delete a rule embedding.

        Args:
            rule_id: Rule identifier
            trilogy_id: Trilogy identifier

        Returns:
            Job ID if successful, None otherwise
        """
        try:
            pool = await get_redis_pool()

            job = await pool.enqueue_job(
                'delete_world_rule_embedding_task',
                rule_id,
                trilogy_id
            )

            logger.info(f"Enqueued deletion task for rule {rule_id}, job_id: {job.job_id}")
            return job.job_id

        except Exception as e:
            logger.error(f"Error enqueuing rule deletion task: {e}")
            return None

    @staticmethod
    async def enqueue_batch_trilogy_embedding(
        trilogy_id: str
    ) -> Optional[str]:
        """
        Enqueue a task to embed all rules for a trilogy.

        Args:
            trilogy_id: Trilogy identifier

        Returns:
            Job ID if successful, None otherwise
        """
        try:
            pool = await get_redis_pool()

            job = await pool.enqueue_job(
                'embed_all_trilogy_rules_task',
                trilogy_id
            )

            logger.info(f"Enqueued batch embedding for trilogy {trilogy_id}, job_id: {job.job_id}")
            return job.job_id

        except Exception as e:
            logger.error(f"Error enqueuing batch embedding task: {e}")
            return None

    @staticmethod
    async def enqueue_character_embedding(
        character_id: str,
        trilogy_id: str,
        name: str,
        description: Optional[str] = None,
        traits: Optional[Dict[str, Any]] = None,
        character_arc: Optional[str] = None,
        consciousness_themes: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Enqueue a task to embed character profile.

        Args:
            character_id: Character identifier
            trilogy_id: Trilogy identifier
            name: Character name
            description: Character description
            traits: Character traits
            character_arc: Character arc
            consciousness_themes: Consciousness themes

        Returns:
            Job ID if successful, None otherwise
        """
        try:
            pool = await get_redis_pool()

            job = await pool.enqueue_job(
                'embed_character_task',
                character_id,
                trilogy_id,
                name,
                description,
                traits,
                character_arc,
                consciousness_themes
            )

            logger.info(f"Enqueued character embedding for {character_id}, job_id: {job.job_id}")
            return job.job_id

        except Exception as e:
            logger.error(f"Error enqueuing character embedding: {e}")
            return None

    @staticmethod
    async def enqueue_character_embedding_update(
        character_id: str,
        trilogy_id: str,
        name: str,
        description: Optional[str] = None,
        traits: Optional[Dict[str, Any]] = None,
        character_arc: Optional[str] = None,
        consciousness_themes: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Enqueue a task to update character embedding.

        Args:
            character_id: Character identifier
            trilogy_id: Trilogy identifier
            name: Character name
            description: Updated description
            traits: Updated traits
            character_arc: Updated arc
            consciousness_themes: Updated themes

        Returns:
            Job ID if successful, None otherwise
        """
        try:
            pool = await get_redis_pool()

            job = await pool.enqueue_job(
                'update_character_embedding_task',
                character_id,
                trilogy_id,
                name,
                description,
                traits,
                character_arc,
                consciousness_themes
            )

            logger.info(f"Enqueued character embedding update for {character_id}, job_id: {job.job_id}")
            return job.job_id

        except Exception as e:
            logger.error(f"Error enqueuing character embedding update: {e}")
            return None

    @staticmethod
    async def enqueue_sub_chapter_generation(
        sub_chapter_id: str,
        chapter_id: str,
        character_id: str,
        plot_points: str,
        target_word_count: int,
        trilogy_id: str,
        book_id: str  # Epic 5B: Required for world rule filtering
    ) -> Optional[str]:
        """
        Enqueue a task to generate sub-chapter content (Epic 5B: with world rules).

        Args:
            sub_chapter_id: Sub-chapter identifier
            chapter_id: Parent chapter identifier
            character_id: Character perspective
            plot_points: Plot points for content generation
            target_word_count: Target word count
            trilogy_id: Trilogy identifier
            book_id: Book identifier (for world rule filtering)

        Returns:
            Job ID if successful, None otherwise
        """
        try:
            pool = await get_redis_pool()

            job = await pool.enqueue_job(
                'generate_sub_chapter_content_task',
                sub_chapter_id,
                chapter_id,
                character_id,
                plot_points,
                target_word_count,
                trilogy_id,
                book_id  # Epic 5B
            )

            logger.info(
                f"Enqueued sub-chapter generation for {sub_chapter_id}, job_id: {job.job_id}"
            )
            return job.job_id

        except Exception as e:
            logger.error(f"Error enqueuing sub-chapter generation: {e}")
            return None

    @staticmethod
    async def enqueue_sub_chapter_regeneration(
        sub_chapter_id: str,
        version_number: int,
        chapter_id: str,
        character_id: str,
        plot_points: str,
        target_word_count: int,
        trilogy_id: str,
        book_id: str,  # Epic 5B: Required for world rule filtering
        change_description: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Enqueue a task to regenerate sub-chapter content as a new version (Epic 5B: with world rules).

        Args:
            sub_chapter_id: Sub-chapter identifier
            version_number: Version number to create
            chapter_id: Parent chapter identifier
            character_id: Character perspective
            plot_points: Plot points for content generation
            target_word_count: Target word count
            trilogy_id: Trilogy identifier
            book_id: Book identifier (for world rule filtering)
            change_description: Optional description of changes
            user_id: User who triggered regeneration

        Returns:
            Job ID if successful, None otherwise
        """
        try:
            pool = await get_redis_pool()

            job = await pool.enqueue_job(
                'regenerate_sub_chapter_content_task',
                sub_chapter_id,
                version_number,
                chapter_id,
                character_id,
                plot_points,
                target_word_count,
                trilogy_id,
                book_id,  # Epic 5B
                change_description,
                user_id
            )

            logger.info(
                f"Enqueued sub-chapter regeneration for {sub_chapter_id}, "
                f"version {version_number}, job_id: {job.job_id}"
            )
            return job.job_id

        except Exception as e:
            logger.error(f"Error enqueuing sub-chapter regeneration: {e}")
            return None


# ============================================================================
# Worker Configuration
# ============================================================================

class WorkerSettings:
    """
    Configuration for Arq worker.

    This defines which tasks the worker can process and how it connects to Redis.
    """

    functions = [
        # World Rules tasks
        embed_world_rule_task,
        update_world_rule_embedding_task,
        delete_world_rule_embedding_task,
        embed_all_trilogy_rules_task,
        # Character tasks (Epic 5A)
        embed_character_task,
        update_character_embedding_task,
        # Sub-Chapter tasks (Epic 6 + 5A)
        generate_sub_chapter_content_task,
        regenerate_sub_chapter_content_task,
    ]

    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)

    # Worker configuration
    max_jobs = 10  # Process up to 10 jobs concurrently
    job_timeout = 300  # 5 minutes per job (increased for LLM generation)
    keep_result = 3600  # Keep results for 1 hour
