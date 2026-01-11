"""
World Rule RAG Provider Service (Epic 3 + Epic 5B Integration).

Retrieves and formats world rules for inclusion in content generation prompts.
Integrates with Character RAG to provide comprehensive generation context.
"""

from typing import List, Dict, Optional
from api.services.chromadb_client import chromadb_client
from api.services.embedding_service import embedding_service
from api.utils.supabase_client import get_supabase_client
from api.utils.redis_client import redis_cache
from api.models.world_rule import (
    WorldRuleContextResponse,
    RulePreviewRequest,
    RulePreviewResponse
)
import logging
import hashlib

logger = logging.getLogger(__name__)


class WorldRuleRAGProvider:
    """
    Retrieves and formats world rules for inclusion in content generation prompts.

    Key Features:
    - Semantic search for relevant rules
    - Book-specific filtering
    - Priority weighting based on similarity and accuracy
    - Formatted output ready for LLM prompts
    - Redis caching for performance (15-min TTL)
    """

    def __init__(self):
        self.chromadb = chromadb_client
        self.embedding_service = embedding_service
        self.supabase = get_supabase_client()
        self.cache = redis_cache

    async def get_rules_for_generation(
        self,
        prompt: str,
        plot_points: str,
        book_id: str,
        trilogy_id: str,
        max_rules: int = 10,
        similarity_threshold: float = 0.5
    ) -> List[WorldRuleContextResponse]:
        """
        Retrieve relevant world rules for content generation.

        Args:
            prompt: User's writing prompt
            plot_points: Key plot points for the sub-chapter
            book_id: Current book being written
            trilogy_id: Trilogy identifier
            max_rules: Maximum number of rules to return
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            List of world rules with similarity scores, sorted by relevance
        """
        try:
            # 1. Combine prompt and plot points for comprehensive search
            search_text = f"{prompt}\n\n{plot_points}"

            # 2. Check cache first
            cache_key = self._generate_cache_key(book_id, search_text)
            cached = await self.cache.get(cache_key)
            if cached:
                logger.info(f"Cache hit for book {book_id}")
                # Deserialize cached rules back to WorldRuleContextResponse objects
                return [WorldRuleContextResponse(**rule) for rule in cached]

            # 3. Semantic search in ChromaDB
            collection_name = f"{trilogy_id}_world_rules"

            try:
                collection = self.chromadb.get_collection(collection_name)
            except Exception:
                logger.warning(f"ChromaDB collection {collection_name} not found")
                return []

            if collection.count() == 0:
                logger.info(f"ChromaDB collection {collection_name} is empty")
                return []

            # Embed search text
            search_embedding = self.embedding_service.embed_text(search_text)

            # Query ChromaDB
            results = collection.query(
                query_embeddings=[search_embedding],
                n_results=max_rules * 2,  # Get extra for filtering
                include=['metadatas', 'distances']
            )

            if not results['ids'] or not results['ids'][0]:
                logger.info("No similar rules found")
                return []

            # 4. Filter to rules applicable to this book
            rule_ids = results['ids'][0]
            distances = results['distances'][0]

            # Convert cosine distances to similarities
            # ChromaDB uses cosine distance: distance = 1 - cosine_similarity
            # Therefore: similarity = 1 - distance
            similarities = [1 - d for d in distances]

            # Apply +0.1 boost to account for title/category in embeddings
            # This helps near-exact matches score higher
            similarities = [min(s + 0.1, 1.0) for s in similarities]

            # Log all similarity scores for debugging
            logger.info(f"Found {len(similarities)} rules with similarities (boosted): {[f'{s:.3f}' for s in similarities[:5]]}")

            # Filter by similarity threshold
            filtered = [
                (rid, sim) for rid, sim in zip(rule_ids, similarities)
                if sim >= similarity_threshold
            ]

            if not filtered:
                logger.info(f"No rules above threshold {similarity_threshold}. Best score: {max(similarities) if similarities else 0:.3f}")
                return []

            filtered_rule_ids = [r[0] for r in filtered]
            similarity_map = {r[0]: r[1] for r in filtered}

            # 5. Get rules that apply to this book
            rules = await self._get_rules_for_book_filtered(
                book_id,
                filtered_rule_ids,
                max_rules
            )

            # 6. Enhance with similarity scores and accuracy weighting
            enhanced_rules = []
            for rule in rules:
                similarity = similarity_map.get(rule['id'], 0.0)

                # Weight down low-accuracy rules
                if rule.get('accuracy_rate', 1.0) < 0.5:
                    similarity *= 0.7

                relevance_reason = self._explain_relevance(
                    rule['title'],
                    rule['category'],
                    search_text,
                    similarity
                )

                enhanced_rules.append(WorldRuleContextResponse(
                    id=rule['id'],
                    title=rule['title'],
                    description=rule['description'],
                    category=rule['category'],
                    similarity=similarity,
                    relevance_reason=relevance_reason,
                    is_critical=similarity > 0.85,
                    accuracy_rate=rule.get('accuracy_rate', 1.0)
                ))

            # 7. Sort by adjusted similarity
            enhanced_rules.sort(key=lambda x: x.similarity, reverse=True)
            enhanced_rules = enhanced_rules[:max_rules]

            # 8. Cache results (15 minutes TTL)
            # Serialize to dict for caching
            serialized_rules = [rule.model_dump() for rule in enhanced_rules]
            await self.cache.set(cache_key, serialized_rules, ttl=900)

            logger.info(f"Retrieved {len(enhanced_rules)} rules for generation (cached)")
            return enhanced_rules

        except Exception as e:
            logger.error(f"Error getting rules for generation: {e}")
            # Graceful degradation
            return []

    async def _get_rules_for_book_filtered(
        self,
        book_id: str,
        rule_ids: List[str],
        max_rules: int
    ) -> List[Dict]:
        """
        Get rules that apply to this book, from the provided rule IDs.

        Args:
            book_id: Book to filter by
            rule_ids: Candidate rule IDs from semantic search
            max_rules: Maximum rules to return

        Returns:
            List of rule dictionaries
        """
        try:
            # Get applicable rule IDs for this book
            book_rules_result = self.supabase.table('world_rule_books').select(
                'world_rule_id'
            ).eq('book_id', book_id).in_('world_rule_id', rule_ids).execute()

            applicable_rule_ids = [br['world_rule_id'] for br in book_rules_result.data]

            if not applicable_rule_ids:
                return []

            # Get full rule details, ordered by accuracy
            rules_result = self.supabase.table('world_rules').select(
                'id, title, description, category, accuracy_rate, times_flagged'
            ).in_('id', applicable_rule_ids).order(
                'accuracy_rate', desc=True
            ).limit(max_rules).execute()

            return rules_result.data

        except Exception as e:
            logger.error(f"Error filtering rules for book {book_id}: {e}")
            return []

    def format_rules_for_prompt(
        self,
        rules: List[WorldRuleContextResponse]
    ) -> str:
        """
        Format rules for inclusion in LLM generation prompt.

        Args:
            rules: Rules to format

        Returns:
            Formatted string ready to insert into prompt
        """
        if not rules:
            return ""

        formatted = "WORLD RULES TO RESPECT:\n\n"

        for i, rule in enumerate(rules, 1):
            formatted += f"{i}. [{rule.category}] {rule.title}\n"
            formatted += f"   {rule.description}\n"

            # Add relevance note for high-similarity rules
            if rule.is_critical:
                formatted += f"   ⚠️ Highly relevant to this scene (similarity: {rule.similarity:.2f})\n"

            formatted += "\n"

        formatted += "NOTE: These rules should guide but not constrain creative storytelling. "
        formatted += "Intentional rule breaks are acceptable when they serve the narrative.\n"

        return formatted

    def _explain_relevance(
        self,
        rule_title: str,
        rule_category: str,
        search_text: str,
        similarity: float
    ) -> str:
        """
        Generate human-readable explanation of why rule is relevant.

        Args:
            rule_title: Rule title
            rule_category: Rule category
            search_text: Combined prompt and plot points
            similarity: Similarity score

        Returns:
            Relevance explanation
        """
        search_lower = search_text.lower()

        # Simple keyword matching for explanation
        keywords = rule_title.lower().split() + rule_category.lower().split()
        matched = [kw for kw in keywords if len(kw) > 3 and kw in search_lower]

        if matched:
            return f"Matched keywords: {', '.join(matched[:3])}"

        # Fallback based on similarity
        if similarity > 0.9:
            return "Very high semantic similarity"
        elif similarity > 0.8:
            return "High semantic similarity"
        elif similarity > 0.7:
            return "Moderate semantic similarity"
        else:
            return "Semantic similarity to scene context"

    def _generate_cache_key(self, book_id: str, search_text: str) -> str:
        """
        Generate cache key for rule retrieval.

        Args:
            book_id: Book identifier
            search_text: Combined prompt and plot points

        Returns:
            Cache key string
        """
        text_hash = hashlib.md5(search_text.encode()).hexdigest()
        return f"rules:{book_id}:{text_hash}"

    async def preview_rules(
        self,
        request: RulePreviewRequest
    ) -> RulePreviewResponse:
        """
        Preview which rules will be used for generation.

        This endpoint allows authors to see which rules will be included
        before generating content.

        Args:
            request: Preview request with prompt and parameters

        Returns:
            Rules that would be used, with formatted prompt section
        """
        try:
            rules = await self.get_rules_for_generation(
                prompt=request.prompt,
                plot_points=request.plot_points,
                book_id=request.book_id,
                trilogy_id=request.trilogy_id,
                max_rules=request.max_rules,
                similarity_threshold=request.similarity_threshold
            )

            formatted_section = self.format_rules_for_prompt(rules)

            return RulePreviewResponse(
                rules=rules,
                formatted_prompt_section=formatted_section,
                cache_hit=False  # TODO: Set based on actual cache status
            )

        except Exception as e:
            logger.error(f"Error previewing rules: {e}")
            # Return empty response on error
            return RulePreviewResponse(
                rules=[],
                formatted_prompt_section="",
                cache_hit=False
            )

    async def get_rules_by_category(
        self,
        trilogy_id: str,
        book_id: str,
        category: str,
        max_rules: int = 10
    ) -> List[WorldRuleContextResponse]:
        """
        Get all rules in a specific category for a book.

        Useful for focused generation tasks (e.g., "show me all physics rules").

        Args:
            trilogy_id: Trilogy identifier
            book_id: Current book
            category: Category to filter by
            max_rules: Maximum rules to return

        Returns:
            List of rules in the category
        """
        try:
            # Get applicable rule IDs for this book
            book_rules_result = self.supabase.table('world_rule_books').select(
                'world_rule_id'
            ).eq('book_id', book_id).execute()

            applicable_rule_ids = [br['world_rule_id'] for br in book_rules_result.data]

            if not applicable_rule_ids:
                return []

            # Get rules in category
            rules_result = self.supabase.table('world_rules').select(
                'id, title, description, category, accuracy_rate'
            ).eq('category', category).in_(
                'id', applicable_rule_ids
            ).order('title').limit(max_rules).execute()

            return [
                WorldRuleContextResponse(
                    id=rule['id'],
                    title=rule['title'],
                    description=rule['description'],
                    category=rule['category'],
                    similarity=1.0,  # Not from semantic search
                    relevance_reason=f"Category: {category}",
                    is_critical=False,
                    accuracy_rate=rule.get('accuracy_rate', 1.0)
                )
                for rule in rules_result.data
            ]

        except Exception as e:
            logger.error(f"Error getting rules by category: {e}")
            return []

    async def get_critical_rules(
        self,
        trilogy_id: str,
        book_id: str,
        min_accuracy: float = 0.8
    ) -> List[WorldRuleContextResponse]:
        """
        Get all high-accuracy rules for a book (rules that are consistently followed).

        These are "golden rules" that authors rarely break.

        Args:
            trilogy_id: Trilogy identifier
            book_id: Current book
            min_accuracy: Minimum accuracy rate (default 0.8)

        Returns:
            List of high-accuracy rules
        """
        try:
            # Get applicable rule IDs for this book
            book_rules_result = self.supabase.table('world_rule_books').select(
                'world_rule_id'
            ).eq('book_id', book_id).execute()

            applicable_rule_ids = [br['world_rule_id'] for br in book_rules_result.data]

            if not applicable_rule_ids:
                return []

            # Get high-accuracy rules
            rules_result = self.supabase.table('world_rules').select(
                'id, title, description, category, accuracy_rate, times_flagged'
            ).in_('id', applicable_rule_ids).gte(
                'accuracy_rate', min_accuracy
            ).gte('times_flagged', 5).order(  # Only rules tested at least 5 times
                'accuracy_rate', desc=True
            ).execute()

            return [
                WorldRuleContextResponse(
                    id=rule['id'],
                    title=rule['title'],
                    description=rule['description'],
                    category=rule['category'],
                    similarity=1.0,
                    relevance_reason=f"High accuracy rule ({rule['accuracy_rate']:.1%})",
                    is_critical=True,
                    accuracy_rate=rule['accuracy_rate']
                )
                for rule in rules_result.data
            ]

        except Exception as e:
            logger.error(f"Error getting critical rules: {e}")
            return []
