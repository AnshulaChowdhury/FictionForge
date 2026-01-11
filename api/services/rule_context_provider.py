"""
Rule Context Provider Service (Epic 3 - Phase 3).

Provides semantic search for world rules during writing.
Retrieves contextually relevant rules based on writing prompts.
"""

from typing import List, Optional, Dict
from api.services.chromadb_client import chromadb_client
from api.services.embedding_service import embedding_service
from api.utils.supabase_client import get_supabase_client
from api.models.world_rule import WorldRuleContextResponse
import logging

logger = logging.getLogger(__name__)


class RuleContextProvider:
    """
    Retrieves contextually relevant world rules during writing.

    Uses semantic search in ChromaDB to find rules similar to the writing prompt.
    Filters results by book applicability and similarity threshold.
    """

    def __init__(self):
        self.chromadb = chromadb_client
        self.embedding_service = embedding_service
        self.supabase = get_supabase_client()

    async def get_contextual_rules(
        self,
        prompt: str,
        book_id: str,
        trilogy_id: str,
        similarity_threshold: float = 0.5,
        max_rules: int = 10
    ) -> List[WorldRuleContextResponse]:
        """
        Retrieve relevant rules via semantic search.

        Args:
            prompt: Writing prompt to find relevant rules for
            book_id: Current book being written
            trilogy_id: Trilogy identifier
            similarity_threshold: Minimum similarity score (0.0 to 1.0)
            max_rules: Maximum number of rules to return

        Returns:
            List of relevant rules with similarity scores
        """
        try:
            collection_name = f"{trilogy_id}_world_rules"

            # 1. Check if collection exists
            try:
                collection = self.chromadb.get_collection(collection_name)
            except Exception:
                logger.warning(f"ChromaDB collection {collection_name} not found")
                return []

            # Check if collection has documents
            if collection.count() == 0:
                logger.info(f"ChromaDB collection {collection_name} is empty")
                return []

            # 2. Embed the prompt
            prompt_embedding = self.embedding_service.embed_text(prompt)

            # 3. Query ChromaDB for similar rules
            results = collection.query(
                query_embeddings=[prompt_embedding],
                n_results=min(max_rules * 2, 50),  # Get extra for filtering
                include=['metadatas', 'distances']
            )

            if not results['ids'] or not results['ids'][0]:
                logger.info("No similar rules found in ChromaDB")
                return []

            # 4. Extract rule IDs and similarities
            rule_ids = results['ids'][0]
            distances = results['distances'][0]

            # Convert cosine distances to similarities
            # ChromaDB uses cosine distance: distance = 1 - cosine_similarity
            # Therefore: similarity = 1 - distance
            similarities = [1 - d for d in distances]

            # Apply +0.1 boost to account for title/category in embeddings
            # This helps near-exact matches score higher
            similarities = [min(s + 0.1, 1.0) for s in similarities]

            # 5. Filter by similarity threshold
            filtered_rules = [
                (rule_id, similarity)
                for rule_id, similarity in zip(rule_ids, similarities)
                if similarity >= similarity_threshold
            ]

            if not filtered_rules:
                logger.info(f"No rules above similarity threshold {similarity_threshold}")
                return []

            filtered_rule_ids = [r[0] for r in filtered_rules]
            similarity_map = {r[0]: r[1] for r in filtered_rules}

            # 6. Get rules that apply to this book from database
            book_rules_result = self.supabase.table('world_rule_books').select(
                'world_rule_id'
            ).eq('book_id', book_id).execute()

            applicable_rule_ids = [br['world_rule_id'] for br in book_rules_result.data]

            # Find intersection of similar rules and applicable rules
            relevant_rule_ids = list(set(filtered_rule_ids) & set(applicable_rule_ids))

            if not relevant_rule_ids:
                logger.info(f"No similar rules applicable to book {book_id}")
                return []

            # 7. Get full rule details from database
            rules_result = self.supabase.table('world_rules').select(
                'id, title, description, category, accuracy_rate, times_flagged'
            ).in_('id', relevant_rule_ids).execute()

            # 8. Build response with similarity scores
            contextual_rules = []
            for rule in rules_result.data:
                similarity = similarity_map[rule['id']]
                is_critical = similarity > 0.85

                # Weight down low-accuracy rules
                if rule.get('accuracy_rate', 1.0) < 0.5:
                    similarity *= 0.7

                relevance_reason = self._explain_relevance(
                    rule['title'],
                    rule['category'],
                    prompt,
                    similarity
                )

                contextual_rules.append(WorldRuleContextResponse(
                    id=rule['id'],
                    title=rule['title'],
                    description=rule['description'],
                    category=rule['category'],
                    similarity=similarity,
                    relevance_reason=relevance_reason,
                    is_critical=is_critical,
                    accuracy_rate=rule.get('accuracy_rate', 1.0)
                ))

            # 9. Sort by adjusted similarity and limit
            contextual_rules.sort(key=lambda x: x.similarity, reverse=True)
            contextual_rules = contextual_rules[:max_rules]

            logger.info(f"Found {len(contextual_rules)} contextual rules for book {book_id}")
            return contextual_rules

        except Exception as e:
            logger.error(f"Error getting contextual rules: {e}")
            # Graceful degradation - return empty list
            return []

    def _explain_relevance(
        self,
        rule_title: str,
        rule_category: str,
        prompt: str,
        similarity: float
    ) -> str:
        """
        Generate human-readable explanation of why rule is relevant.

        Args:
            rule_title: Title of the rule
            rule_category: Category of the rule
            prompt: Writing prompt
            similarity: Similarity score

        Returns:
            Relevance explanation
        """
        prompt_lower = prompt.lower()

        # Check for keyword matches
        keywords = (rule_title.lower().split() +
                    rule_category.lower().split())
        matched = [kw for kw in keywords if len(kw) > 3 and kw in prompt_lower]

        if matched:
            # Show up to 3 matched keywords
            return f"Matched keywords: {', '.join(matched[:3])}"

        if similarity > 0.9:
            return "Very high semantic similarity to scene"
        elif similarity > 0.8:
            return "High semantic similarity to scene"
        elif similarity > 0.7:
            return "Moderate semantic similarity to scene"
        else:
            return "Semantic similarity to scene context"

    async def embed_rule(
        self,
        rule_id: str,
        rule_title: str,
        rule_description: str,
        rule_category: str,
        trilogy_id: str
    ) -> bool:
        """
        Embed a single rule into ChromaDB.

        Args:
            rule_id: Rule identifier
            rule_title: Rule title
            rule_description: Rule description
            rule_category: Rule category
            trilogy_id: Trilogy identifier

        Returns:
            True if embedding successful, False otherwise
        """
        try:
            collection_name = f"{trilogy_id}_world_rules"

            # Get or create collection
            collection = self.chromadb.get_or_create_collection(
                collection_name,
                metadata={"trilogy_id": trilogy_id, "type": "world_rules"}
            )

            # Combine title, category, and description for embedding
            text_to_embed = f"{rule_title} ({rule_category}): {rule_description}"

            # Generate embedding
            embedding = self.embedding_service.embed_text(text_to_embed)

            # Add to ChromaDB
            collection.add(
                ids=[rule_id],
                embeddings=[embedding],
                metadatas=[{
                    "rule_id": rule_id,
                    "title": rule_title,
                    "category": rule_category,
                    "trilogy_id": trilogy_id
                }]
            )

            logger.info(f"Embedded rule {rule_id} in collection {collection_name}")
            return True

        except Exception as e:
            logger.error(f"Error embedding rule {rule_id}: {e}")
            return False

    async def delete_rule_embedding(
        self,
        rule_id: str,
        trilogy_id: str
    ) -> bool:
        """
        Delete a rule's embedding from ChromaDB.

        Args:
            rule_id: Rule to delete
            trilogy_id: Trilogy identifier

        Returns:
            True if deletion successful, False otherwise
        """
        try:
            collection_name = f"{trilogy_id}_world_rules"

            # Get collection
            collection = self.chromadb.get_collection(collection_name)

            # Delete rule
            collection.delete(ids=[rule_id])

            logger.info(f"Deleted embedding for rule {rule_id} from {collection_name}")
            return True

        except Exception as e:
            logger.error(f"Error deleting rule embedding {rule_id}: {e}")
            return False

    async def update_rule_embedding(
        self,
        rule_id: str,
        rule_title: str,
        rule_description: str,
        rule_category: str,
        trilogy_id: str
    ) -> bool:
        """
        Update a rule's embedding in ChromaDB.

        This is done by deleting the old embedding and adding a new one.

        Args:
            rule_id: Rule identifier
            rule_title: Updated rule title
            rule_description: Updated rule description
            rule_category: Updated rule category
            trilogy_id: Trilogy identifier

        Returns:
            True if update successful, False otherwise
        """
        try:
            # Delete old embedding
            await self.delete_rule_embedding(rule_id, trilogy_id)

            # Add new embedding
            success = await self.embed_rule(
                rule_id=rule_id,
                rule_title=rule_title,
                rule_description=rule_description,
                rule_category=rule_category,
                trilogy_id=trilogy_id
            )

            return success

        except Exception as e:
            logger.error(f"Error updating rule embedding {rule_id}: {e}")
            return False

    async def embed_all_rules_for_trilogy(
        self,
        trilogy_id: str
    ) -> Dict[str, int]:
        """
        Embed all rules for a trilogy (useful for initial setup or re-indexing).

        Args:
            trilogy_id: Trilogy to embed rules for

        Returns:
            Dictionary with success/failure counts
        """
        try:
            # Get all rules for trilogy
            rules_result = self.supabase.table('world_rules').select(
                'id, title, description, category'
            ).eq('trilogy_id', trilogy_id).execute()

            total = len(rules_result.data)
            successful = 0
            failed = 0

            for rule in rules_result.data:
                success = await self.embed_rule(
                    rule_id=rule['id'],
                    rule_title=rule['title'],
                    rule_description=rule['description'],
                    rule_category=rule['category'],
                    trilogy_id=trilogy_id
                )

                if success:
                    successful += 1
                else:
                    failed += 1

            logger.info(f"Embedded {successful}/{total} rules for trilogy {trilogy_id}")

            return {
                "total": total,
                "successful": successful,
                "failed": failed
            }

        except Exception as e:
            logger.error(f"Error embedding rules for trilogy {trilogy_id}: {e}")
            return {"total": 0, "successful": 0, "failed": 0}
