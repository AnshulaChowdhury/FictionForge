"""
World Rules API Routes (Epic 3).

Endpoints for managing world rules and contextual rule retrieval.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from api.models.world_rule import (
    WorldRuleCreate,
    WorldRuleUpdate,
    WorldRuleResponse,
    WorldRuleListResponse,
    CategoryListResponse,
    WorldRuleContextResponse,
    RulePreviewRequest,
    RulePreviewResponse,
)
from api.services.world_rule_manager import WorldRuleManager
from api.services.rule_context_provider import RuleContextProvider
from api.services.world_rule_rag_provider import WorldRuleRAGProvider
from api.services.task_queue import TaskQueue
from api.middleware.auth import get_current_user_id
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/world_rules", tags=["world_rules"])


# ============================================================================
# CRUD Endpoints
# ============================================================================

@router.post("", response_model=WorldRuleResponse, status_code=201)
async def create_world_rule(
    rule_data: WorldRuleCreate,
    user_id: str = Depends(get_current_user_id)
):
    """
    Create a new world rule with book associations.

    The rule will be automatically embedded in ChromaDB via background task.
    """
    try:
        manager = WorldRuleManager()
        rule = await manager.create_rule(rule_data, user_id)

        # Enqueue embedding task (fire-and-forget - don't block response)
        try:
            await TaskQueue.enqueue_rule_embedding(
                rule_id=rule.id,
                rule_title=rule.title,
                rule_description=rule.description,
                rule_category=rule.category,
                trilogy_id=rule.trilogy_id
            )
        except Exception as task_error:
            # Log but don't fail the request if background task fails
            logger.warning(f"Failed to enqueue embedding for rule {rule.id}: {task_error}")

        return rule

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating world rule: {e}")
        raise HTTPException(status_code=500, detail="Failed to create world rule")


@router.get("", response_model=WorldRuleListResponse)
async def list_world_rules(
    trilogy_id: str = Query(..., description="Trilogy to filter by"),
    category: Optional[str] = Query(None, description="Filter by category"),
    book_id: Optional[str] = Query(None, description="Filter by book"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Rules per page"),
    user_id: str = Depends(get_current_user_id)
):
    """
    List world rules for a trilogy with optional filtering.

    Supports filtering by category and book, with pagination.
    """
    try:
        manager = WorldRuleManager()
        rules = await manager.list_rules(
            trilogy_id=trilogy_id,
            user_id=user_id,
            category=category,
            book_id=book_id,
            page=page,
            page_size=page_size
        )
        return rules

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing world rules: {e}")
        raise HTTPException(status_code=500, detail="Failed to list world rules")


@router.get("/{rule_id}", response_model=WorldRuleResponse)
async def get_world_rule(
    rule_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get a single world rule by ID."""
    try:
        manager = WorldRuleManager()
        rule = await manager.get_rule_by_id(rule_id, user_id)
        return rule

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting world rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve world rule")


@router.put("/{rule_id}", response_model=WorldRuleResponse)
async def update_world_rule(
    rule_id: str,
    update_data: WorldRuleUpdate,
    user_id: str = Depends(get_current_user_id)
):
    """
    Update a world rule.

    If title, description, or category changes, the embedding will be updated
    via background task (with debouncing).
    """
    try:
        manager = WorldRuleManager()
        rule = await manager.update_rule(rule_id, update_data, user_id)

        # If content changed, enqueue re-embedding (with 2-second debounce)
        # This is fire-and-forget - don't block the response if task queue fails
        if any([
            update_data.title is not None,
            update_data.description is not None,
            update_data.category is not None
        ]):
            try:
                await TaskQueue.enqueue_rule_embedding_update(
                    rule_id=rule.id,
                    rule_title=rule.title,
                    rule_description=rule.description,
                    rule_category=rule.category,
                    trilogy_id=rule.trilogy_id,
                    delay=2  # 2-second debounce
                )
            except Exception as task_error:
                # Log but don't fail the request if background task fails
                logger.warning(f"Failed to enqueue embedding update for rule {rule_id}: {task_error}")

        return rule

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating world rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update world rule")


@router.delete("/{rule_id}")
async def delete_world_rule(
    rule_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Delete a world rule.

    Cascades to book associations and triggers embedding cleanup.
    """
    try:
        manager = WorldRuleManager()

        # Get rule details before deletion (for embedding cleanup)
        rule = await manager.get_rule_by_id(rule_id, user_id)

        # Delete from database
        result = await manager.delete_rule(rule_id, user_id)

        # Enqueue embedding deletion (fire-and-forget - don't block response)
        try:
            await TaskQueue.enqueue_rule_embedding_deletion(
                rule_id=rule_id,
                trilogy_id=rule.trilogy_id
            )
        except Exception as task_error:
            # Log but don't fail the request if background task fails
            logger.warning(f"Failed to enqueue embedding deletion for rule {rule_id}: {task_error}")

        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting world rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete world rule")


# ============================================================================
# Category Management
# ============================================================================

@router.get("/categories/list", response_model=CategoryListResponse)
async def get_categories(
    trilogy_id: str = Query(..., description="Trilogy to get categories for"),
    user_id: str = Depends(get_current_user_id)
):
    """Get all unique categories used in a trilogy's rules."""
    try:
        manager = WorldRuleManager()
        categories = await manager.get_categories(trilogy_id, user_id)
        return categories

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to get categories")


# ============================================================================
# Contextual Rule Retrieval (Epic 3 - Phase 3)
# ============================================================================

@router.get("/contextual/search")
async def get_contextual_rules(
    prompt: str = Query(..., description="Writing prompt"),
    book_id: str = Query(..., description="Current book"),
    trilogy_id: str = Query(..., description="Trilogy identifier"),
    similarity_threshold: float = Query(0.7, ge=0.0, le=1.0, description="Minimum similarity"),
    max_rules: int = Query(10, ge=1, le=20, description="Maximum rules to return"),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get contextually relevant rules for a writing prompt.

    Uses semantic search to find rules similar to the prompt,
    filtered by book applicability.
    """
    try:
        # Verify user has access to book/trilogy
        manager = WorldRuleManager()
        await manager.get_rules_for_book(book_id, user_id)

        # Get contextual rules
        provider = RuleContextProvider()
        rules = await provider.get_contextual_rules(
            prompt=prompt,
            book_id=book_id,
            trilogy_id=trilogy_id,
            similarity_threshold=similarity_threshold,
            max_rules=max_rules
        )

        return {"rules": rules, "count": len(rules)}

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting contextual rules: {e}")
        raise HTTPException(status_code=500, detail="Failed to get contextual rules")


# ============================================================================
# RAG Integration (Epic 5B Integration)
# ============================================================================

@router.post("/preview", response_model=RulePreviewResponse)
async def preview_rules_for_generation(
    request: RulePreviewRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Preview which rules will be used for content generation.

    Returns rules that would be included in the generation prompt,
    along with formatted text ready for LLM.
    """
    try:
        # Verify user has access
        manager = WorldRuleManager()
        await manager.get_rules_for_book(request.book_id, user_id)

        # Get preview
        rag_provider = WorldRuleRAGProvider()
        preview = await rag_provider.preview_rules(request)

        return preview

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error previewing rules: {e}")
        raise HTTPException(status_code=500, detail="Failed to preview rules")


@router.get("/category/{category}")
async def get_rules_by_category(
    category: str,
    trilogy_id: str = Query(..., description="Trilogy identifier"),
    book_id: str = Query(..., description="Current book"),
    max_rules: int = Query(10, ge=1, le=50),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get all rules in a specific category for a book.

    Useful for focused generation or rule review.
    """
    try:
        # Verify access
        manager = WorldRuleManager()
        await manager.get_rules_for_book(book_id, user_id)

        # Get rules by category
        rag_provider = WorldRuleRAGProvider()
        rules = await rag_provider.get_rules_by_category(
            trilogy_id=trilogy_id,
            book_id=book_id,
            category=category,
            max_rules=max_rules
        )

        return {"rules": rules, "category": category, "count": len(rules)}

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting rules by category: {e}")
        raise HTTPException(status_code=500, detail="Failed to get rules by category")


@router.get("/critical/list")
async def get_critical_rules(
    trilogy_id: str = Query(..., description="Trilogy identifier"),
    book_id: str = Query(..., description="Current book"),
    min_accuracy: float = Query(0.8, ge=0.0, le=1.0, description="Minimum accuracy rate"),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get high-accuracy "golden rules" for a book.

    These are rules that authors consistently follow.
    """
    try:
        # Verify access
        manager = WorldRuleManager()
        await manager.get_rules_for_book(book_id, user_id)

        # Get critical rules
        rag_provider = WorldRuleRAGProvider()
        rules = await rag_provider.get_critical_rules(
            trilogy_id=trilogy_id,
            book_id=book_id,
            min_accuracy=min_accuracy
        )

        return {"rules": rules, "count": len(rules)}

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting critical rules: {e}")
        raise HTTPException(status_code=500, detail="Failed to get critical rules")


# ============================================================================
# Batch Operations
# ============================================================================

@router.post("/batch/embed-trilogy")
async def embed_all_trilogy_rules(
    trilogy_id: str = Query(..., description="Trilogy to embed rules for"),
    user_id: str = Depends(get_current_user_id)
):
    """
    Trigger batch embedding for all rules in a trilogy.

    Useful for:
    - Initial setup
    - Re-indexing after major changes
    - Recovery from errors
    """
    try:
        # Verify trilogy access
        manager = WorldRuleManager()
        categories = await manager.get_categories(trilogy_id, user_id)

        # Enqueue batch embedding
        job_id = await TaskQueue.enqueue_batch_trilogy_embedding(trilogy_id)

        if job_id:
            return {
                "status": "enqueued",
                "job_id": job_id,
                "message": f"Batch embedding started for trilogy {trilogy_id}"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to enqueue batch embedding")

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error triggering batch embedding: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger batch embedding")


@router.post("/batch/embed-trilogy-dev")
async def embed_all_trilogy_rules_dev(
    trilogy_id: str = Query(..., description="Trilogy to embed rules for"),
    reset_collection: bool = Query(False, description="Delete and recreate ChromaDB collection")
):
    """
    DEV ONLY: Trigger batch embedding without authentication.

    WARNING: Remove this endpoint in production!

    Args:
        trilogy_id: ID of trilogy to embed rules for
        reset_collection: If true, deletes existing collection and recreates with cosine distance
    """
    try:
        from api.services.rule_context_provider import RuleContextProvider
        from api.utils.supabase_client import get_supabase_client
        from api.services.chromadb_client import chromadb_client

        supabase = get_supabase_client()

        # Delete old collection if requested (needed after changing distance metric)
        collection_name = f"{trilogy_id}_world_rules"
        if reset_collection:
            try:
                deleted = chromadb_client.delete_collection(collection_name)
                if deleted:
                    logger.info(f"Deleted old collection: {collection_name}")
            except Exception as e:
                logger.warning(f"Could not delete collection {collection_name}: {e}")

        # Get all world rules for the trilogy
        result = supabase.table('world_rules').select(
            'id, title, description, category, trilogy_id'
        ).eq('trilogy_id', trilogy_id).execute()

        rules = result.data
        logger.info(f"Found {len(rules)} rules to embed for trilogy {trilogy_id}")

        if not rules:
            return {
                "status": "no_rules",
                "count": 0,
                "message": f"No rules found for trilogy {trilogy_id}"
            }

        # Embed each rule synchronously
        provider = RuleContextProvider()
        success_count = 0
        failed_rules = []

        for rule in rules:
            try:
                success = await provider.embed_rule(
                    rule['id'],
                    rule['title'],
                    rule['description'],
                    rule['category'],
                    rule['trilogy_id']
                )
                if success:
                    success_count += 1
                    logger.info(f"Embedded rule: {rule['title']}")
                else:
                    failed_rules.append(rule['title'])
            except Exception as e:
                logger.error(f"Failed to embed rule {rule['id']}: {e}")
                failed_rules.append(rule['title'])

        return {
            "status": "completed",
            "total_rules": len(rules),
            "embedded": success_count,
            "failed": failed_rules,
            "collection_reset": reset_collection,
            "message": f"Embedded {success_count}/{len(rules)} rules for trilogy {trilogy_id}"
        }

    except Exception as e:
        logger.error(f"Error in dev batch embedding: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Analytics & Metrics (Epic 5B)
# ============================================================================

@router.get("/analytics/usage")
async def get_rule_usage_analytics(
    trilogy_id: str = Query(..., description="Trilogy to get analytics for"),
    book_id: Optional[str] = Query(None, description="Filter by specific book"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=200, description="Maximum rules to return"),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get rule usage analytics for a trilogy (Epic 5B).

    Returns:
    - Most flagged rules (times_flagged = usage count)
    - Rule accuracy rates
    - Violation statistics
    - Intentional break statistics
    """
    try:
        from api.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()

        # Verify trilogy access
        manager = WorldRuleManager()
        await manager.get_categories(trilogy_id, user_id)

        # Build base query - get all rules with their metrics
        select_fields = "id, title, category, times_flagged, times_true_violation, times_false_positive, times_intentional_break, times_checker_error, accuracy_rate"

        # If filtering by book, need to join with world_rule_books
        if book_id:
            # Query with book filter
            result = supabase.from_("world_rules")\
                .select(f"{select_fields}, world_rule_books!inner(book_id)")\
                .eq("trilogy_id", trilogy_id)\
                .eq("world_rule_books.book_id", book_id)\
                .execute()
        else:
            # Query without book filter
            result = supabase.from_("world_rules")\
                .select(select_fields)\
                .eq("trilogy_id", trilogy_id)\
                .execute()

        rules = result.data or []

        # Apply category filter if provided
        if category:
            rules = [r for r in rules if r.get('category') == category]

        # Sort by times_flagged (usage count) descending
        rules.sort(key=lambda x: x.get('times_flagged', 0), reverse=True)

        # Limit results
        rules = rules[:limit]

        # Format for response
        analytics = []
        for rule in rules:
            analytics.append({
                "rule_id": rule.get("id"),
                "title": rule.get("title"),
                "category": rule.get("category"),
                "times_flagged": rule.get("times_flagged", 0),  # Usage count
                "times_true_violation": rule.get("times_true_violation", 0),
                "times_false_positive": rule.get("times_false_positive", 0),
                "times_intentional_break": rule.get("times_intentional_break", 0),
                "times_checker_error": rule.get("times_checker_error", 0),
                "accuracy_rate": rule.get("accuracy_rate", 1.0)
            })

        # Calculate summary statistics
        total_rules = len(analytics)
        total_usage = sum(r["times_flagged"] for r in analytics)
        avg_accuracy = sum(r["accuracy_rate"] for r in analytics) / max(total_rules, 1)
        total_violations = sum(r["times_true_violation"] for r in analytics)
        total_intentional_breaks = sum(r["times_intentional_break"] for r in analytics)

        return {
            "trilogy_id": trilogy_id,
            "filters": {
                "book_id": book_id,
                "category": category
            },
            "summary": {
                "total_rules": total_rules,
                "total_times_flagged": total_usage,
                "total_violations": total_violations,
                "total_intentional_breaks": total_intentional_breaks,
                "average_accuracy_rate": round(avg_accuracy, 3)
            },
            "most_used_rules": analytics[:10],
            "all_rules": analytics
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting rule usage analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")


@router.get("/analytics/effectiveness")
async def get_rule_effectiveness_by_category(
    trilogy_id: str = Query(..., description="Trilogy to get analytics for"),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get rule effectiveness metrics by category (Epic 5B).

    Shows which categories of rules are most effective based on accuracy_rate.
    accuracy_rate is computed as: (times_true_violation + times_intentional_break) / times_flagged
    """
    try:
        from api.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()

        # Verify trilogy access
        manager = WorldRuleManager()
        await manager.get_categories(trilogy_id, user_id)

        # Query world_rules directly and aggregate by category
        result = supabase.from_("world_rules")\
            .select("category, accuracy_rate, times_flagged, times_true_violation, times_intentional_break, id")\
            .eq("trilogy_id", trilogy_id)\
            .execute()

        rules = result.data or []

        # Aggregate by category
        category_stats = {}
        for rule in rules:
            category = rule.get('category', 'uncategorized')

            if category not in category_stats:
                category_stats[category] = {
                    'category': category,
                    'trilogy_id': trilogy_id,
                    'total_rules': 0,
                    'rules_used': 0,  # Rules that have been flagged at least once
                    'avg_category_accuracy': 0.0,
                    'total_flags': 0,
                    'total_violations': 0,
                    'total_intentional_breaks': 0
                }

            stats = category_stats[category]
            stats['total_rules'] += 1

            times_flagged = rule.get('times_flagged', 0)
            if times_flagged > 0:
                stats['rules_used'] += 1
                stats['total_flags'] += times_flagged

            stats['total_violations'] += rule.get('times_true_violation', 0)
            stats['total_intentional_breaks'] += rule.get('times_intentional_break', 0)

        # Calculate average accuracy per category
        category_list = []
        for category, stats in category_stats.items():
            # Get all accuracy_rates for this category
            category_rules = [r for r in rules if r.get('category') == category]
            accuracy_rates = [r.get('accuracy_rate', 1.0) for r in category_rules]

            # Average accuracy across all rules in category
            if accuracy_rates:
                stats['avg_category_accuracy'] = sum(accuracy_rates) / len(accuracy_rates)

            category_list.append(stats)

        # Sort by average accuracy (highest first)
        category_list.sort(key=lambda x: x['avg_category_accuracy'], reverse=True)

        return {
            "trilogy_id": trilogy_id,
            "category_effectiveness": category_list
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting category effectiveness: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get category effectiveness: {str(e)}")


@router.get("/analytics/sub-chapter/{sub_chapter_id}")
async def get_sub_chapter_rule_usage(
    sub_chapter_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get which rules were used during a specific sub-chapter generation (Epic 5B).

    Shows:
    - Which rules were included in the generation prompt
    - Similarity scores for each rule
    - Whether each rule was followed or violated
    """
    try:
        from api.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()

        # Call the database function
        result = supabase.rpc(
            "get_generation_rule_usage",
            {"p_sub_chapter_id": sub_chapter_id}
        ).execute()

        return {
            "sub_chapter_id": sub_chapter_id,
            "rules_used": result.data or []
        }

    except Exception as e:
        logger.error(f"Error getting sub-chapter rule usage: {e}")
        raise HTTPException(status_code=500, detail="Failed to get rule usage")
