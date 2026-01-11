"""
Unit tests for CharacterRAGGenerator (Epic 5A).

Tests cover:
- Character context retrieval from ChromaDB
- Enhanced prompt building with character voice
- Content generation using RAG
- Version management
- ChromaDB updates after generation
- Error handling
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from api.services.character_rag_generator import CharacterRAGGenerator, RAGGenerationError


class TestCharacterRAGGenerator:
    """Tests for CharacterRAGGenerator"""

    @pytest.fixture
    def generator(self):
        """Create CharacterRAGGenerator instance."""
        return CharacterRAGGenerator()

    @pytest.fixture
    def mock_chromadb(self):
        """Mock ChromaDB client."""
        mock_client = MagicMock()
        mock_collection = MagicMock()

        # Mock semantic search results
        mock_collection.query.return_value = {
            "documents": [[
                "Character profile: Dr. Sarah Chen",
                "Traits: analytical, determined",
                "Arc: Evolves from skeptic to believer"
            ]],
            "metadatas": [[
                {"type": "profile"},
                {"type": "traits"},
                {"type": "arc"}
            ]],
            "distances": [[0.3, 0.4, 0.5]]
        }

        mock_client.get_collection.return_value = mock_collection
        return mock_client

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM client."""
        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(return_value="Generated narrative content about the character's journey through consciousness...")
        return mock_client

    @pytest.fixture
    def mock_embedding_service(self):
        """Mock embedding service."""
        mock_service = AsyncMock()
        mock_service.add_generated_content = AsyncMock(return_value={
            "success": True,
            "sub_chapter_id": "subchap-789"
        })
        return mock_service

    @pytest.fixture
    def mock_supabase(self):
        """Mock Supabase client."""
        mock_client = MagicMock()

        # Mock character query
        character_mock = MagicMock()
        character_mock.select.return_value.eq.return_value.execute.return_value.data = [{
            "id": "char-456",
            "name": "Dr. Sarah Chen",
            "description": "A brilliant neuroscientist",
            "traits": {
                "personality": ["analytical", "determined"],
                "speech_patterns": ["uses technical language"]
            },
            "character_arc": "Evolves from skeptic to believer",
            "consciousness_themes": ["identity", "free will"]
        }]

        # Mock recent chapters query
        recent_chapters_mock = MagicMock()
        recent_chapters_mock.select.return_value.eq.return_value.not_.is_.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {
                "id": "subchap-100",
                "title": "Previous Chapter",
                "content": "This is previous content written in the character's voice. " * 100,
                "word_count": 500,
                "created_at": "2024-01-01T00:00:00"
            }
        ]

        # Mock version query
        version_query_mock = MagicMock()
        version_query_mock.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []

        # Mock version insert
        version_insert_mock = MagicMock()
        version_insert_mock.insert.return_value.execute.return_value.data = [{
            "id": "version-123",
            "sub_chapter_id": "subchap-789",
            "version_number": 1,
            "content": "Generated content",
            "word_count": 200
        }]

        # Mock sub_chapter update
        subchapter_update_mock = MagicMock()
        subchapter_update_mock.update.return_value.eq.return_value.execute.return_value.data = [{}]

        call_count = [0]
        def table_side_effect(table_name):
            if table_name == "characters":
                return character_mock
            elif table_name == "sub_chapters":
                return recent_chapters_mock
            elif table_name == "sub_chapter_versions":
                call_count[0] += 1
                # First call for version query, second for insert
                return version_query_mock if call_count[0] == 1 else version_insert_mock
            return MagicMock()

        mock_client.table.side_effect = table_side_effect
        return mock_client

    @pytest.mark.asyncio
    async def test_generate_content_success(
        self,
        generator,
        mock_chromadb,
        mock_llm,
        mock_embedding_service,
        mock_supabase
    ):
        """Test successful RAG content generation."""
        # Arrange
        sub_chapter_id = "subchap-789"
        character_id = "char-456"
        writing_prompt = "Write about Sarah's discovery"
        plot_points = "Sarah enters the lab and finds the quantum device"
        target_word_count = 2000
        trilogy_id = "trilogy-123"

        with patch.object(generator, 'chromadb', mock_chromadb), \
             patch.object(generator, 'llm', mock_llm), \
             patch.object(generator, 'embedding_service', mock_embedding_service), \
             patch.object(generator, 'supabase', mock_supabase):

            # Act
            result = await generator.generate_content(
                sub_chapter_id=sub_chapter_id,
                character_id=character_id,
                writing_prompt=writing_prompt,
                plot_points=plot_points,
                target_word_count=target_word_count,
                trilogy_id=trilogy_id
            )

            # Assert
            assert result is not None
            assert "version_id" in result
            assert "version_number" in result
            assert "word_count" in result
            assert "content" in result
            assert result["word_count"] > 0

            # Verify LLM was called
            mock_llm.generate.assert_called_once()

            # Verify embedding service was updated
            mock_embedding_service.add_generated_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_character_context(
        self,
        generator,
        mock_chromadb,
        mock_supabase
    ):
        """Test fetching character context from ChromaDB and database."""
        # Arrange
        character_id = "char-456"
        trilogy_id = "trilogy-123"
        writing_prompt = "Test prompt"
        plot_points = "Test plot points"

        with patch.object(generator, 'chromadb', mock_chromadb), \
             patch.object(generator, 'supabase', mock_supabase):

            with patch.object(generator.embedding_service, 'get_collection_name') as mock_collection_name:
                mock_collection_name.return_value = f"{trilogy_id}_character_{character_id}"

                # Act
                context = await generator._fetch_character_context(
                    character_id=character_id,
                    trilogy_id=trilogy_id,
                    writing_prompt=writing_prompt,
                    plot_points=plot_points
                )

                # Assert
                assert context is not None
                assert "character" in context
                assert "relevant_context" in context
                assert "recent_chapters" in context
                assert "is_first_generation" in context

                assert context["character"]["name"] == "Dr. Sarah Chen"
                assert context["is_first_generation"] is False  # Has recent chapters

    @pytest.mark.asyncio
    async def test_build_enhanced_prompt_with_previous_chapters(self, generator):
        """Test building enhanced prompt with previous chapter examples."""
        # Arrange
        character_context = {
            "character": {
                "name": "Dr. Sarah Chen",
                "description": "A brilliant neuroscientist",
                "traits": {
                    "personality": ["analytical", "determined"]
                },
                "character_arc": "Evolves from skeptic to believer",
                "consciousness_themes": ["identity", "free will"]
            },
            "relevant_context": {"documents": [[]]},
            "recent_chapters": [
                {
                    "title": "Chapter 1",
                    "content": "Previous chapter content in character's voice. " * 100
                }
            ],
            "is_first_generation": False
        }

        writing_prompt = "Write about discovery"
        plot_points = "Sarah finds the device"
        target_word_count = 2000

        # Act
        prompt = generator._build_enhanced_prompt(
            character_context=character_context,
            writing_prompt=writing_prompt,
            plot_points=plot_points,
            target_word_count=target_word_count
        )

        # Assert
        assert "Dr. Sarah Chen" in prompt
        assert "analytical" in prompt
        assert "PREVIOUS WRITING SAMPLES" in prompt
        assert writing_prompt in prompt
        assert plot_points in prompt
        assert str(target_word_count) in prompt
        assert "Continue the established narrative voice" in prompt

    @pytest.mark.asyncio
    async def test_build_enhanced_prompt_first_generation(self, generator):
        """Test building enhanced prompt for first generation (no previous chapters)."""
        # Arrange
        character_context = {
            "character": {
                "name": "Dr. Sarah Chen",
                "description": "A brilliant neuroscientist",
                "traits": None,
                "character_arc": None,
                "consciousness_themes": []
            },
            "relevant_context": {"documents": [[]]},
            "recent_chapters": [],
            "is_first_generation": True
        }

        writing_prompt = "Write about discovery"
        plot_points = "Sarah finds the device"
        target_word_count = 2000

        # Act
        prompt = generator._build_enhanced_prompt(
            character_context=character_context,
            writing_prompt=writing_prompt,
            plot_points=plot_points,
            target_word_count=target_word_count
        )

        # Assert
        assert "Dr. Sarah Chen" in prompt
        assert "PREVIOUS WRITING SAMPLES" not in prompt  # No previous chapters
        assert "first chapter for this character" in prompt
        assert "establish their voice" in prompt

    @pytest.mark.asyncio
    async def test_save_as_version(
        self,
        generator,
        mock_supabase
    ):
        """Test saving generated content as a version."""
        # Arrange
        sub_chapter_id = "subchap-789"
        content = "Generated content for the sub-chapter"
        word_count = 150

        with patch.object(generator, 'supabase', mock_supabase):

            # Act
            version = await generator._save_as_version(
                sub_chapter_id=sub_chapter_id,
                content=content,
                word_count=word_count
            )

            # Assert
            assert version is not None
            assert version["version_number"] == 1

    @pytest.mark.asyncio
    async def test_generate_content_llm_error(
        self,
        generator,
        mock_chromadb,
        mock_llm,
        mock_embedding_service,
        mock_supabase
    ):
        """Test error handling when LLM generation fails."""
        # Arrange
        from api.services.llm_client import LLMError
        mock_llm.generate = AsyncMock(side_effect=LLMError("LLM generation failed"))

        with patch.object(generator, 'chromadb', mock_chromadb), \
             patch.object(generator, 'llm', mock_llm), \
             patch.object(generator, 'embedding_service', mock_embedding_service), \
             patch.object(generator, 'supabase', mock_supabase):

            # Act & Assert
            with pytest.raises(RAGGenerationError, match="LLM generation failed"):
                await generator.generate_content(
                    sub_chapter_id="subchap-789",
                    character_id="char-456",
                    writing_prompt="Test",
                    plot_points="Test",
                    target_word_count=2000,
                    trilogy_id="trilogy-123"
                )

    @pytest.mark.asyncio
    async def test_generate_content_character_not_found(
        self,
        generator,
        mock_chromadb,
        mock_supabase
    ):
        """Test error when character is not found."""
        # Arrange
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        with patch.object(generator, 'chromadb', mock_chromadb), \
             patch.object(generator, 'supabase', mock_supabase):

            # Act & Assert
            with pytest.raises(RAGGenerationError, match="Character.*not found"):
                await generator.generate_content(
                    sub_chapter_id="subchap-789",
                    character_id="non-existent",
                    writing_prompt="Test",
                    plot_points="Test",
                    target_word_count=2000,
                    trilogy_id="trilogy-123"
                )

    @pytest.mark.asyncio
    async def test_word_count_calculation(
        self,
        generator,
        mock_chromadb,
        mock_llm,
        mock_embedding_service,
        mock_supabase
    ):
        """Test that word count is correctly calculated."""
        # Arrange
        generated_text = "This is a test sentence. " * 10  # 50 words
        mock_llm.generate = AsyncMock(return_value=generated_text)

        with patch.object(generator, 'chromadb', mock_chromadb), \
             patch.object(generator, 'llm', mock_llm), \
             patch.object(generator, 'embedding_service', mock_embedding_service), \
             patch.object(generator, 'supabase', mock_supabase):

            # Act
            result = await generator.generate_content(
                sub_chapter_id="subchap-789",
                character_id="char-456",
                writing_prompt="Test",
                plot_points="Test",
                target_word_count=2000,
                trilogy_id="trilogy-123"
            )

            # Assert
            assert result["word_count"] == 50

    @pytest.mark.asyncio
    async def test_target_word_count_affects_max_tokens(
        self,
        generator,
        mock_chromadb,
        mock_llm,
        mock_embedding_service,
        mock_supabase
    ):
        """Test that target_word_count affects LLM max_tokens parameter."""
        # Arrange
        target_word_count = 3000

        with patch.object(generator, 'chromadb', mock_chromadb), \
             patch.object(generator, 'llm', mock_llm), \
             patch.object(generator, 'embedding_service', mock_embedding_service), \
             patch.object(generator, 'supabase', mock_supabase):

            # Act
            await generator.generate_content(
                sub_chapter_id="subchap-789",
                character_id="char-456",
                writing_prompt="Test",
                plot_points="Test",
                target_word_count=target_word_count,
                trilogy_id="trilogy-123"
            )

            # Assert
            # Verify LLM was called with max_tokens = target_word_count * 1.5
            call_args = mock_llm.generate.call_args
            expected_max_tokens = int(target_word_count * 1.5)
            assert call_args[1]['max_tokens'] == expected_max_tokens

    @pytest.mark.asyncio
    async def test_chromadb_update_after_generation(
        self,
        generator,
        mock_chromadb,
        mock_llm,
        mock_embedding_service,
        mock_supabase
    ):
        """Test that ChromaDB is updated with generated content."""
        # Arrange
        with patch.object(generator, 'chromadb', mock_chromadb), \
             patch.object(generator, 'llm', mock_llm), \
             patch.object(generator, 'embedding_service', mock_embedding_service), \
             patch.object(generator, 'supabase', mock_supabase):

            # Act
            result = await generator.generate_content(
                sub_chapter_id="subchap-789",
                character_id="char-456",
                writing_prompt="Test",
                plot_points="Test",
                target_word_count=2000,
                trilogy_id="trilogy-123"
            )

            # Assert
            # Verify embedding service was called to add generated content
            mock_embedding_service.add_generated_content.assert_called_once()
            call_args = mock_embedding_service.add_generated_content.call_args

            assert call_args[1]['character_id'] == "char-456"
            assert call_args[1]['trilogy_id'] == "trilogy-123"
            assert call_args[1]['sub_chapter_id'] == "subchap-789"
            assert call_args[1]['content'] is not None
            assert call_args[1]['version_number'] == 1

    @pytest.mark.asyncio
    async def test_multiple_recent_chapters_in_context(
        self,
        generator,
        mock_supabase
    ):
        """Test that multiple recent chapters are included in context."""
        # Arrange
        mock_supabase.table.return_value.select.return_value.eq.return_value.not_.is_.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"id": "1", "title": "Chapter 1", "content": "Content 1 " * 100, "word_count": 500, "created_at": "2024-01-01"},
            {"id": "2", "title": "Chapter 2", "content": "Content 2 " * 100, "word_count": 500, "created_at": "2024-01-02"},
            {"id": "3", "title": "Chapter 3", "content": "Content 3 " * 100, "word_count": 500, "created_at": "2024-01-03"},
        ]

        with patch.object(generator, 'supabase', mock_supabase):
            with patch.object(generator.embedding_service, 'get_collection_name') as mock_collection_name:
                mock_collection_name.return_value = "test_collection"

                # Mock ChromaDB
                mock_chromadb = MagicMock()
                mock_collection = MagicMock()
                mock_collection.query.return_value = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
                mock_chromadb.get_collection.return_value = mock_collection

                with patch.object(generator, 'chromadb', mock_chromadb):

                    # Act
                    context = await generator._fetch_character_context(
                        character_id="char-456",
                        trilogy_id="trilogy-123",
                        writing_prompt="Test",
                        plot_points="Test"
                    )

                    # Assert
                    assert len(context["recent_chapters"]) == 3


class TestCharacterRAGGeneratorPromptBuilding:
    """Focused tests on prompt building logic"""

    @pytest.fixture
    def generator(self):
        return CharacterRAGGenerator()

    def test_prompt_includes_all_character_data(self, generator):
        """Test that prompt includes all available character data."""
        # Arrange
        character_context = {
            "character": {
                "name": "Dr. Sarah Chen",
                "description": "A neuroscientist",
                "traits": {
                    "personality": ["analytical"],
                    "speech_patterns": ["technical"],
                    "physical_description": "Tall",
                    "background": "MIT graduate",
                    "motivations": ["discover truth"]
                },
                "character_arc": "Growth from doubt to belief",
                "consciousness_themes": ["identity", "free will"]
            },
            "relevant_context": {"documents": [[]]},
            "recent_chapters": [],
            "is_first_generation": True
        }

        # Act
        prompt = generator._build_enhanced_prompt(
            character_context=character_context,
            writing_prompt="Write a scene",
            plot_points="Character enters room",
            target_word_count=2000
        )

        # Assert
        assert "Dr. Sarah Chen" in prompt
        assert "neuroscientist" in prompt
        assert "analytical" in prompt
        assert "technical" in prompt
        assert "MIT graduate" in prompt
        assert "identity" in prompt
        assert "free will" in prompt
        assert "Growth from doubt to belief" in prompt

    def test_prompt_structure_sections(self, generator):
        """Test that prompt has all required sections."""
        # Arrange
        character_context = {
            "character": {
                "name": "Test Character",
                "description": "Test",
                "traits": {},
                "character_arc": "Test arc",
                "consciousness_themes": []
            },
            "relevant_context": {"documents": [[]]},
            "recent_chapters": [],
            "is_first_generation": True
        }

        # Act
        prompt = generator._build_enhanced_prompt(
            character_context=character_context,
            writing_prompt="Test prompt",
            plot_points="Test plot",
            target_word_count=2000
        )

        # Assert
        assert "CHARACTER PROFILE:" in prompt
        assert "CURRENT SCENE:" in prompt
        assert "WRITING INSTRUCTIONS:" in prompt
        assert "Plot Points:" in prompt
        assert "Writing Prompt:" in prompt
