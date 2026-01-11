"""
Integration tests for Epic 5A - Character-Specific RAG Content Generation.

Tests the complete workflow:
1. Character creation triggers embedding job
2. Character embeddings are created in ChromaDB
3. Sub-chapter generation uses RAG to retrieve character context
4. LLM generates content with character voice consistency
5. Generated content is saved as version
6. Character embeddings are updated with new content

These tests use mocked external services (Supabase, AWS Bedrock)
but test the integration of Epic 5A services together.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import UUID
from api.services.character_manager import CharacterManager
from api.services.character_embedding_service import CharacterEmbeddingService
from api.services.character_rag_generator import CharacterRAGGenerator
from api.models.character import CharacterCreate, CharacterTraits


class TestEpic5AIntegration:
    """Integration tests for Epic 5A workflow"""

    @pytest.fixture
    def mock_task_queue(self):
        """Mock the TaskQueue for background jobs."""
        with patch('api.services.character_manager.TaskQueue') as mock_queue:
            mock_queue.enqueue_character_embedding = AsyncMock(return_value="job-123")
            yield mock_queue

    @pytest.fixture
    def mock_chromadb_client(self):
        """Mock ChromaDB client for the workflow."""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.add = MagicMock()
        mock_collection.query = MagicMock(return_value={
            "documents": [["Character profile data", "Traits data"]],
            "metadatas": [[{"type": "profile"}, {"type": "traits"}]],
            "distances": [[0.2, 0.3]]
        })
        mock_collection.count = MagicMock(return_value=2)

        mock_client.get_or_create_collection = MagicMock(return_value=mock_collection)
        mock_client.get_collection = MagicMock(return_value=mock_collection)
        mock_client.delete_collection = MagicMock(return_value=True)

        return mock_client

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client for content generation."""
        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(return_value=(
            "Dr. Sarah Chen examined the quantum consciousness device with analytical precision. "
            "Her years at MIT had prepared her for this moment, though nothing could have truly "
            "readied her for what she was about to discover. The implications were staggering..."
        ) * 10)  # Generate ~200 words
        return mock_client

    @pytest.fixture
    def mock_embedding_service(self):
        """Mock embedding service."""
        mock_service = MagicMock()
        mock_service.embed_batch = MagicMock(return_value=[[0.1] * 384, [0.2] * 384])
        return mock_service

    @pytest.mark.asyncio
    async def test_complete_workflow_character_to_generation(
        self,
        mock_user_id,
        mock_trilogy_id,
        mock_task_queue,
        mock_chromadb_client,
        mock_llm_client,
        mock_embedding_service
    ):
        """
        Test complete workflow from character creation to content generation.

        Steps:
        1. Create character
        2. Verify embedding job is queued
        3. Simulate embedding job execution
        4. Generate content using RAG
        5. Verify content includes character voice
        """
        # === Step 1: Create Character ===

        character_request = CharacterCreate(
            trilogy_id=mock_trilogy_id,
            name="Dr. Sarah Chen",
            description="A brilliant neuroscientist questioning consciousness",
            traits=CharacterTraits(
                personality=["analytical", "determined", "empathetic"],
                speech_patterns=["uses scientific terminology", "speaks precisely"],
                physical_description="Tall with dark hair and piercing eyes",
                background="Former MIT neuroscientist",
                motivations=["understand consciousness", "prevent AI suffering"]
            ),
            character_arc="Evolves from skeptical materialist to accepting transcendence",
            consciousness_themes=["identity", "free will", "emergence"]
        )

        # Mock Supabase for character creation
        mock_supabase = MagicMock()

        # Mock trilogy verification
        trilogy_mock = MagicMock()
        trilogy_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": mock_trilogy_id, "user_id": mock_user_id}
        ]

        # Mock character insert
        character_id = "char-new-123"
        characters_mock = MagicMock()
        characters_mock.insert.return_value.execute.return_value.data = [{
            "id": character_id,
            "trilogy_id": mock_trilogy_id,
            "name": "Dr. Sarah Chen",
            "description": "A brilliant neuroscientist questioning consciousness",
            "traits": character_request.traits.model_dump(),
            "character_arc": "Evolves from skeptical materialist to accepting transcendence",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }]

        def table_side_effect(table_name):
            if table_name == "trilogy_projects":
                return trilogy_mock
            elif table_name == "characters":
                return characters_mock
            return MagicMock()

        mock_supabase.table.side_effect = table_side_effect

        with patch("api.services.character_manager.supabase", mock_supabase):
            manager = CharacterManager(user_id=mock_user_id)
            character = await manager.create_character(character_request)

            # Assert character was created
            assert character.id == character_id
            assert character.name == "Dr. Sarah Chen"

            # Verify embedding job was queued
            mock_task_queue.enqueue_character_embedding.assert_called_once()
            call_args = mock_task_queue.enqueue_character_embedding.call_args
            assert call_args[1]['character_id'] == character_id
            assert call_args[1]['trilogy_id'] == mock_trilogy_id

        # === Step 2: Simulate Embedding Job Execution ===

        embedding_service = CharacterEmbeddingService()

        with patch.object(embedding_service, 'chromadb', mock_chromadb_client), \
             patch.object(embedding_service, 'embedding_service', mock_embedding_service):

            embedding_result = await embedding_service.embed_character(
                character_id=character_id,
                trilogy_id=mock_trilogy_id,
                name=character_request.name,
                description=character_request.description,
                traits=character_request.traits.model_dump(),
                character_arc=character_request.character_arc,
                consciousness_themes=character_request.consciousness_themes
            )

            # Verify embedding was created
            assert embedding_result["success"] is True
            assert embedding_result["character_id"] == character_id

            # Verify ChromaDB collection was created
            mock_chromadb_client.get_or_create_collection.assert_called_once()

        # === Step 3: Generate Content Using RAG ===

        rag_generator = CharacterRAGGenerator()

        # Mock Supabase for RAG generator
        mock_rag_supabase = MagicMock()

        # Mock character query
        character_query_mock = MagicMock()
        character_query_mock.select.return_value.eq.return_value.execute.return_value.data = [{
            "id": character_id,
            "name": "Dr. Sarah Chen",
            "description": "A brilliant neuroscientist questioning consciousness",
            "traits": character_request.traits.model_dump(),
            "character_arc": "Evolves from skeptical materialist to accepting transcendence",
            "consciousness_themes": ["identity", "free will", "emergence"]
        }]

        # Mock recent chapters (none yet - first generation)
        recent_chapters_mock = MagicMock()
        recent_chapters_mock.select.return_value.eq.return_value.not_.is_.return_value.order.return_value.limit.return_value.execute.return_value.data = []

        # Mock version operations
        version_query_mock = MagicMock()
        version_query_mock.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []

        version_insert_mock = MagicMock()
        version_insert_mock.insert.return_value.execute.return_value.data = [{
            "id": "version-1",
            "sub_chapter_id": "subchap-789",
            "version_number": 1,
            "content": mock_llm_client.generate.return_value,
            "word_count": 200
        }]

        subchapter_update_mock = MagicMock()
        subchapter_update_mock.update.return_value.eq.return_value.execute.return_value.data = [{}]

        call_count = [0]
        def rag_table_side_effect(table_name):
            if table_name == "characters":
                return character_query_mock
            elif table_name == "sub_chapters":
                return recent_chapters_mock
            elif table_name == "sub_chapter_versions":
                call_count[0] += 1
                return version_query_mock if call_count[0] == 1 else version_insert_mock
            return subchapter_update_mock

        mock_rag_supabase.table.side_effect = rag_table_side_effect

        # Mock ChromaDB update after generation
        mock_embedding_update = AsyncMock(return_value={
            "success": True,
            "sub_chapter_id": "subchap-789"
        })

        with patch.object(rag_generator, 'chromadb', mock_chromadb_client), \
             patch.object(rag_generator, 'llm', mock_llm_client), \
             patch.object(rag_generator, 'supabase', mock_rag_supabase), \
             patch.object(rag_generator.embedding_service, 'add_generated_content', mock_embedding_update):

            result = await rag_generator.generate_content(
                sub_chapter_id="subchap-789",
                character_id=character_id,
                writing_prompt="Write about Sarah's first encounter with the quantum device",
                plot_points="Sarah enters the lab, discovers the device, questions its implications",
                target_word_count=2000,
                trilogy_id=mock_trilogy_id
            )

            # === Step 4: Verify Generated Content ===

            assert result is not None
            assert "version_id" in result
            assert "content" in result
            assert "word_count" in result

            # Verify content was generated by LLM
            mock_llm_client.generate.assert_called_once()

            # Verify LLM prompt included character context
            llm_call_args = mock_llm_client.generate.call_args
            prompt = llm_call_args[1]['prompt']

            # Prompt should include character profile
            assert "Dr. Sarah Chen" in prompt
            assert "neuroscientist" in prompt
            assert "analytical" in prompt

            # Prompt should include writing instructions
            assert "quantum device" in prompt
            assert "2000" in prompt  # target word count

            # Prompt should indicate first generation
            assert "first chapter" in prompt or "establish their voice" in prompt

            # === Step 5: Verify Embedding Update ===

            # Verify ChromaDB was updated with generated content
            mock_embedding_update.assert_called_once()
            update_call_args = mock_embedding_update.call_args
            assert update_call_args[1]['character_id'] == character_id
            assert update_call_args[1]['trilogy_id'] == mock_trilogy_id
            assert update_call_args[1]['content'] is not None

    @pytest.mark.asyncio
    async def test_subsequent_generation_includes_previous_voice(
        self,
        mock_chromadb_client,
        mock_llm_client,
        mock_embedding_service
    ):
        """
        Test that subsequent generations include previous chapter samples for voice consistency.
        """
        rag_generator = CharacterRAGGenerator()

        # Mock Supabase with previous chapters
        mock_supabase = MagicMock()

        character_mock = MagicMock()
        character_mock.select.return_value.eq.return_value.execute.return_value.data = [{
            "id": "char-456",
            "name": "Dr. Sarah Chen",
            "description": "A neuroscientist",
            "traits": {"personality": ["analytical"]},
            "character_arc": "Growth",
            "consciousness_themes": ["identity"]
        }]

        # Mock with existing chapters
        recent_chapters_mock = MagicMock()
        recent_chapters_mock.select.return_value.eq.return_value.not_.is_.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {
                "id": "prev-1",
                "title": "Previous Chapter",
                "content": "Dr. Chen examined the data with scientific precision. Her analytical mind " * 100,
                "word_count": 500,
                "created_at": "2024-01-01T00:00:00"
            }
        ]

        version_query_mock = MagicMock()
        version_query_mock.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"version_number": 1}
        ]

        version_insert_mock = MagicMock()
        version_insert_mock.insert.return_value.execute.return_value.data = [{
            "id": "version-2",
            "version_number": 2,
            "content": "Generated",
            "word_count": 200
        }]

        call_count = [0]
        def table_side_effect(table_name):
            if table_name == "characters":
                return character_mock
            elif table_name == "sub_chapters":
                return recent_chapters_mock
            elif table_name == "sub_chapter_versions":
                call_count[0] += 1
                return version_query_mock if call_count[0] == 1 else version_insert_mock
            return MagicMock()

        mock_supabase.table.side_effect = table_side_effect

        mock_embedding_update = AsyncMock(return_value={"success": True})

        with patch.object(rag_generator, 'chromadb', mock_chromadb_client), \
             patch.object(rag_generator, 'llm', mock_llm_client), \
             patch.object(rag_generator, 'supabase', mock_supabase), \
             patch.object(rag_generator.embedding_service, 'add_generated_content', mock_embedding_update):

            await rag_generator.generate_content(
                sub_chapter_id="subchap-new",
                character_id="char-456",
                writing_prompt="Continue the story",
                plot_points="Next scene",
                target_word_count=2000,
                trilogy_id="trilogy-123"
            )

            # Verify LLM prompt included previous chapter sample
            llm_call_args = mock_llm_client.generate.call_args
            prompt = llm_call_args[1]['prompt']

            assert "PREVIOUS WRITING SAMPLES" in prompt
            assert "Dr. Chen examined the data" in prompt
            assert "maintain the same voice" in prompt

    @pytest.mark.asyncio
    async def test_error_propagation_in_workflow(self, mock_user_id, mock_trilogy_id):
        """Test that errors at any stage are properly propagated."""
        # Test character creation failure
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        with patch("api.services.character_manager.supabase", mock_supabase):
            manager = CharacterManager(user_id=mock_user_id)

            from api.services.character_manager import CharacterCreationError

            with pytest.raises(CharacterCreationError):
                await manager.create_character(
                    CharacterCreate(
                        trilogy_id=mock_trilogy_id,
                        name="Test"
                    )
                )


class TestEpic5ACharacterEmbeddingWorkflow:
    """Test character embedding specific workflows"""

    @pytest.mark.asyncio
    async def test_embedding_update_workflow(
        self,
        mock_chromadb_client,
        mock_embedding_service
    ):
        """Test updating character embeddings when character is edited."""
        embedding_service = CharacterEmbeddingService()

        with patch.object(embedding_service, 'chromadb', mock_chromadb_client), \
             patch.object(embedding_service, 'embedding_service', mock_embedding_service):

            # Initial embedding
            result1 = await embedding_service.embed_character(
                character_id="char-456",
                trilogy_id="trilogy-123",
                name="Original Name",
                description="Original description"
            )

            assert result1["success"] is True

            # Update embedding
            result2 = await embedding_service.update_character_embedding(
                character_id="char-456",
                trilogy_id="trilogy-123",
                name="Updated Name",
                description="Updated description"
            )

            assert result2["success"] is True

            # Verify old collection was deleted
            mock_chromadb_client.delete_collection.assert_called_once()

            # Verify new collection was created
            assert mock_chromadb_client.get_or_create_collection.call_count == 2
