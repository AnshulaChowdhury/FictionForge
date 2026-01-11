"""
Character RAG Generator for Epic 5A

Core service for generating character-specific content using retrieval-augmented
generation. Retrieves character context from ChromaDB, builds enhanced prompts,
generates content via LLM, and manages versioning.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID

from api.services.chromadb_client import get_chromadb_client
from api.services.llm_client import get_llm_client, LLMError
from api.services.character_embedding_service import CharacterEmbeddingService
from api.services.world_rule_rag_provider import WorldRuleRAGProvider
from api.utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class RAGGenerationError(Exception):
    """Raised when RAG generation fails"""
    pass


class CharacterRAGGenerator:
    """Core service for generating character-specific content using RAG (Epic 5A + 5B)"""

    def __init__(self):
        self.chromadb = get_chromadb_client()
        self.llm = get_llm_client()
        self.embedding_service = CharacterEmbeddingService()
        self.world_rule_rag = WorldRuleRAGProvider()  # Epic 5B integration
        self.supabase = get_supabase_client()

    async def generate_content(
        self,
        sub_chapter_id: str,
        character_id: str,
        writing_prompt: str,
        plot_points: str,
        target_word_count: int,
        trilogy_id: str,
        book_id: str  # Epic 5B: Required for world rule filtering
    ) -> Dict[str, Any]:
        """
        Generate character-specific content using RAG (Epic 5A + 5B).

        Process:
        1. Retrieve character context from ChromaDB (Epic 5A)
        2. Retrieve world rules context from ChromaDB (Epic 5B - NEW)
        3. Identify most recent sub-chapters for voice consistency
        4. Build enhanced prompt with all context
        5. Generate content using LLM
        6. Save as new version
        7. Store generation metadata (which rules were used)
        8. Update character ChromaDB with new content

        Args:
            sub_chapter_id: Sub-chapter identifier
            character_id: Character identifier
            writing_prompt: User's writing prompt
            plot_points: Plot points to incorporate
            target_word_count: Target word count
            trilogy_id: Trilogy identifier
            book_id: Book identifier (for world rule filtering)

        Returns:
            Dict with version_id, version_number, word_count, content, and rules_used

        Raises:
            RAGGenerationError: If generation fails
        """
        try:
            logger.info(f"Starting RAG generation for sub-chapter {sub_chapter_id}")

            # Step 1 & 2: Fetch character context and world rules in parallel (Epic 5B)
            logger.info("Fetching character context and world rules in parallel...")

            import asyncio

            # Parallel retrieval for performance
            character_context_task = self._fetch_character_context(
                character_id=character_id,
                trilogy_id=trilogy_id,
                writing_prompt=writing_prompt,
                plot_points=plot_points
            )

            world_rules_task = self.world_rule_rag.get_rules_for_generation(
                prompt=writing_prompt,
                plot_points=plot_points,
                book_id=book_id,
                trilogy_id=trilogy_id,
                max_rules=10,
                similarity_threshold=0.65
            )

            # Wait for both to complete
            character_context, world_rules = await asyncio.gather(
                character_context_task,
                world_rules_task
            )

            logger.info(f"Retrieved {len(world_rules)} world rules for generation")

            # Step 3: Build enhanced prompt with both character and world rule context
            logger.info("Building comprehensive prompt...")
            enhanced_prompt = self._build_enhanced_prompt(
                character_context=character_context,
                world_rules=world_rules,
                writing_prompt=writing_prompt,
                plot_points=plot_points,
                target_word_count=target_word_count
            )

            # Step 3: Generate content using LLM
            logger.info(f"Generating content (target: {target_word_count} words)...")
            generated_content = await self.llm.generate(
                prompt=enhanced_prompt,
                max_tokens=int(target_word_count * 1.5),  # Allow some buffer
                temperature=0.7
            )

            # Step 4: Calculate word count
            word_count = len(generated_content.split())
            logger.info(f"Generated {word_count} words")

            # Step 5: Save as version
            version = await self._save_as_version(
                sub_chapter_id=sub_chapter_id,
                content=generated_content,
                word_count=word_count
            )

            # Step 6: Store generation metadata (Epic 5B)
            logger.info("Storing generation metadata...")
            await self._store_generation_metadata(
                sub_chapter_id=sub_chapter_id,
                world_rules=world_rules,
                character_id=character_id,
                character_context_chunks=len(character_context.get("relevant_context", {}).get("documents", [[]])[0]),
                model_used="mistral-7b-instruct",
                prompt_token_count=len(enhanced_prompt.split()),  # Rough estimate
                generation_token_count=word_count
            )

            # Step 7: Update character ChromaDB
            logger.info("Updating character context in ChromaDB...")
            await self.embedding_service.add_generated_content(
                character_id=character_id,
                trilogy_id=trilogy_id,
                sub_chapter_id=sub_chapter_id,
                content=generated_content,
                version_number=version["version_number"]
            )

            logger.info(f"Successfully completed RAG generation for sub-chapter {sub_chapter_id}")

            return {
                "version_id": version["id"],
                "version_number": version["version_number"],
                "word_count": word_count,
                "content": generated_content,
                "rules_used": [rule.id for rule in world_rules]  # Epic 5B metadata
            }

        except LLMError as e:
            logger.error(f"LLM error during generation: {e}")
            raise RAGGenerationError(f"LLM generation failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error during RAG generation: {e}")
            raise RAGGenerationError(f"Generation failed: {str(e)}")

    async def _fetch_character_context(
        self,
        character_id: str,
        trilogy_id: str,
        writing_prompt: str,
        plot_points: str
    ) -> Dict[str, Any]:
        """
        Fetch character context using semantic search and recent chapters.

        Args:
            character_id: Character identifier
            trilogy_id: Trilogy identifier
            writing_prompt: Writing prompt
            plot_points: Plot points

        Returns:
            Dict with character, relevant_context, recent_chapters, and is_first_generation
        """
        # Get character data from database
        character_result = self.supabase.table("characters")\
            .select("*")\
            .eq("id", character_id)\
            .execute()

        if not character_result.data:
            raise RAGGenerationError(f"Character {character_id} not found")

        character = character_result.data[0]

        # Get character's ChromaDB collection
        collection_name = self.embedding_service.get_collection_name(trilogy_id, character_id)

        try:
            collection = self.chromadb.get_collection(collection_name)

            # Semantic search for relevant context
            query_text = f"{writing_prompt}\n{plot_points}"
            results = collection.query(
                query_texts=[query_text],
                n_results=5,
                where={"type": {"$in": ["profile", "traits", "arc", "themes", "generated_content"]}}
            )

            relevant_context = results

        except Exception as e:
            logger.warning(f"Error querying ChromaDB: {e}. Using empty context.")
            relevant_context = {"documents": [[]], "metadatas": [[]], "distances": [[]]}

        # Get most recent sub-chapters by this character
        recent_chapters_result = self.supabase.table("sub_chapters")\
            .select("id, title, content, word_count, created_at")\
            .eq("character_id", character_id)\
            .not_.is_("content", "null")\
            .order("created_at", desc=True)\
            .limit(3)\
            .execute()

        recent_chapters = recent_chapters_result.data or []

        return {
            "character": character,
            "relevant_context": relevant_context,
            "recent_chapters": recent_chapters,
            "is_first_generation": len(recent_chapters) == 0
        }

    def _build_enhanced_prompt(
        self,
        character_context: Dict[str, Any],
        world_rules: List[Any],  # List[WorldRuleContextResponse]
        writing_prompt: str,
        plot_points: str,
        target_word_count: int
    ) -> str:
        """
        Build comprehensive prompt with character voice and world rules context (Epic 5B).

        Prompt Structure:
        1. Character Profile & Traits
        2. World Rules to Respect (Epic 5B - NEW)
        3. Previous Chapter Examples (if exist)
        4. Scene Setup (plot points)
        5. Writing Instructions (prompt)
        6. Technical Requirements (word count, POV)

        Args:
            character_context: Character context from fetch
            world_rules: World rules from WorldRuleRAGProvider
            writing_prompt: User's writing prompt
            plot_points: Plot points to incorporate
            target_word_count: Target word count

        Returns:
            Enhanced prompt string
        """
        character = character_context["character"]
        is_first = character_context["is_first_generation"]

        # Section 1: Character Foundation
        traits_json = json.dumps(character.get("traits") or {}, indent=2)
        themes_list = ', '.join(character.get("consciousness_themes") or [])

        profile_section = f"""CHARACTER PROFILE:
Name: {character['name']}
Description: {character.get('description', 'No description provided')}

Traits:
{traits_json}

Character Arc: {character.get('character_arc', 'No arc defined')}

Consciousness Themes: {themes_list if themes_list else 'None specified'}
"""

        # Section 2: World Rules (Epic 5B - NEW)
        world_rules_section = ""
        if world_rules:
            world_rules_section = "\n" + self.world_rule_rag.format_rules_for_prompt(world_rules)

        # Section 3: Voice Examples (if available)
        voice_section = ""
        if not is_first:
            recent_chapters = character_context["recent_chapters"]
            if recent_chapters:
                voice_section = "\nPREVIOUS WRITING SAMPLES (for voice consistency):\n"

                for i, chapter in enumerate(recent_chapters[:2], 1):
                    # Include first 500 words of each recent chapter
                    content = chapter.get("content", "")
                    sample = ' '.join(content.split()[:500])
                    voice_section += f"\nSample {i} ({chapter.get('title', 'Untitled')}):\n{sample}...\n"

                voice_section += "\nPlease maintain the same voice, tone, and perspective as shown above.\n"

        # Section 3: Scene Setup
        scene_section = f"""
CURRENT SCENE:
Plot Points: {plot_points}

Writing Prompt: {writing_prompt}
"""

        # Section 4: Instructions
        first_time_instruction = "This is the first chapter for this character - establish their voice clearly and consistently."
        continue_instruction = "Continue the established narrative voice and character consistency."

        instructions = f"""
WRITING INSTRUCTIONS:
1. Write from {character['name']}'s perspective
2. Maintain the established voice and character traits
3. Target word count: approximately {target_word_count} words
4. Incorporate the plot points naturally into the narrative
5. Stay true to the character's consciousness themes and arc
6. {first_time_instruction if is_first else continue_instruction}
7. Write engaging, descriptive prose that advances the plot
8. Use vivid sensory details and internal character thoughts

Please write the complete scene now:
"""

        # Combine all sections (Epic 5B: world_rules_section added)
        full_prompt = f"{profile_section}{world_rules_section}\n{voice_section}\n{scene_section}\n{instructions}"

        return full_prompt

    async def _save_as_version(
        self,
        sub_chapter_id: str,
        content: str,
        word_count: int
    ) -> Dict[str, Any]:
        """
        Save generated content as a new version in sub_chapter_versions.

        Also updates the sub_chapter record with the content and status.

        Args:
            sub_chapter_id: Sub-chapter identifier
            content: Generated content
            word_count: Word count

        Returns:
            Version record
        """
        # Get next version number
        version_result = self.supabase.table("sub_chapter_versions")\
            .select("version_number")\
            .eq("sub_chapter_id", sub_chapter_id)\
            .order("version_number", desc=True)\
            .limit(1)\
            .execute()

        next_version = 1
        if version_result.data:
            next_version = version_result.data[0]["version_number"] + 1

        # Set all existing versions to is_current = false
        self.supabase.table("sub_chapter_versions")\
            .update({"is_current": False})\
            .eq("sub_chapter_id", sub_chapter_id)\
            .execute()

        # Create version record with is_current = true
        version_data = {
            "sub_chapter_id": sub_chapter_id,
            "version_number": next_version,
            "content": content,
            "word_count": word_count,
            "generated_by_model": "mistral-7b-instruct",
            "is_ai_generated": True,
            "is_current": True,
            "change_description": f"AI-generated content (version {next_version})"
        }

        version_insert = self.supabase.table("sub_chapter_versions")\
            .insert(version_data)\
            .execute()

        if not version_insert.data:
            raise RAGGenerationError("Failed to create version")

        version = version_insert.data[0]

        # Update sub_chapter record
        self.supabase.table("sub_chapters")\
            .update({
                "content": content,
                "word_count": word_count,
                "status": "completed",
                "updated_at": datetime.utcnow().isoformat()
            })\
            .eq("id", sub_chapter_id)\
            .execute()

        return version

    async def _store_generation_metadata(
        self,
        sub_chapter_id: str,
        world_rules: List[Any],  # List[WorldRuleContextResponse]
        character_id: str,
        character_context_chunks: int,
        model_used: str,
        prompt_token_count: int,
        generation_token_count: int
    ):
        """
        Store generation metadata for analytics and learning (Epic 5B).

        Args:
            sub_chapter_id: Sub-chapter identifier
            world_rules: World rules used in generation
            character_id: Character identifier
            character_context_chunks: Number of context chunks used
            model_used: LLM model identifier
            prompt_token_count: Approximate prompt token count
            generation_token_count: Approximate generation token count
        """
        try:
            # Extract rule IDs and similarities
            world_rule_ids = [str(rule.id) for rule in world_rules]
            world_rule_similarities = {
                str(rule.id): rule.similarity
                for rule in world_rules
            }

            # Insert metadata
            metadata = {
                "sub_chapter_id": sub_chapter_id,
                "world_rule_ids": world_rule_ids,
                "world_rule_similarities": world_rule_similarities,
                "character_id": character_id,
                "character_context_chunks": character_context_chunks,
                "model_used": model_used,
                "prompt_token_count": prompt_token_count,
                "generation_token_count": generation_token_count,
                "generation_timestamp": datetime.utcnow().isoformat()
            }

            result = self.supabase.table("sub_chapter_generation_metadata")\
                .insert(metadata)\
                .execute()

            if result.data:
                logger.info(f"Stored generation metadata for sub-chapter {sub_chapter_id}")
            else:
                logger.warning(f"Failed to store generation metadata for {sub_chapter_id}")

        except Exception as e:
            # Don't fail generation if metadata storage fails
            logger.error(f"Error storing generation metadata: {e}")
