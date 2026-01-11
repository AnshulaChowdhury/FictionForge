"""
Unit tests for CharacterEmbeddingService (Epic 5A).

Tests cover:
- Character profile embedding creation
- Collection naming and management
- Character context updates with generated content
- ChromaDB integration
- Error handling
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from api.services.character_embedding_service import CharacterEmbeddingService


class TestCharacterEmbeddingService:
    """Tests for CharacterEmbeddingService"""

    @pytest.fixture
    def service(self):
        """Create CharacterEmbeddingService instance."""
        return CharacterEmbeddingService()

    @pytest.fixture
    def mock_chromadb(self):
        """Mock ChromaDB client."""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.add = MagicMock()
        mock_collection.query = MagicMock()
        mock_collection.count = MagicMock(return_value=5)
        mock_client.get_or_create_collection = MagicMock(return_value=mock_collection)
        mock_client.get_collection = MagicMock(return_value=mock_collection)
        return mock_client

    @pytest.fixture
    def mock_embedding_service(self):
        """Mock EmbeddingService."""
        mock_service = MagicMock()
        mock_service.embed_batch = MagicMock(return_value=[
            [0.1] * 384,  # Mock 384-dim embedding
            [0.2] * 384,
            [0.3] * 384,
            [0.4] * 384,
        ])
        return mock_service

    @pytest.fixture
    def sample_character_traits(self):
        """Sample character traits."""
        return {
            "personality": ["analytical", "determined"],
            "speech_patterns": ["uses technical jargon"],
            "physical_description": "Tall with dark hair",
            "background": "Former scientist",
            "motivations": ["understand consciousness"]
        }

    def test_get_collection_name(self, service):
        """Test collection name generation."""
        trilogy_id = "trilogy-123"
        character_id = "char-456"

        collection_name = service.get_collection_name(trilogy_id, character_id)

        assert collection_name == "trilogy-123_character_char-456"

    @pytest.mark.asyncio
    async def test_embed_character_success(
        self,
        service,
        mock_chromadb,
        mock_embedding_service,
        sample_character_traits
    ):
        """Test successful character embedding."""
        # Arrange
        trilogy_id = "trilogy-123"
        character_id = "char-456"
        name = "Dr. Sarah Chen"
        description = "A brilliant neuroscientist"
        character_arc = "Evolves from skeptic to believer"
        consciousness_themes = ["identity", "free will"]

        with patch.object(service, 'chromadb', mock_chromadb), \
             patch.object(service, 'embedding_service', mock_embedding_service):

            # Act
            result = await service.embed_character(
                character_id=character_id,
                trilogy_id=trilogy_id,
                name=name,
                description=description,
                traits=sample_character_traits,
                character_arc=character_arc,
                consciousness_themes=consciousness_themes
            )

            # Assert
            assert result["success"] is True
            assert result["character_id"] == character_id
            assert result["trilogy_id"] == trilogy_id
            assert "documents_added" in result

            # Verify collection was created
            mock_chromadb.get_or_create_collection.assert_called_once()

            # Verify embeddings were generated
            mock_embedding_service.embed_batch.assert_called_once()

            # Verify documents were added to collection
            mock_collection = mock_chromadb.get_or_create_collection.return_value
            mock_collection.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_character_minimal_data(
        self,
        service,
        mock_chromadb,
        mock_embedding_service
    ):
        """Test character embedding with minimal data (only required fields)."""
        # Arrange
        trilogy_id = "trilogy-123"
        character_id = "char-456"
        name = "John Doe"

        with patch.object(service, 'chromadb', mock_chromadb), \
             patch.object(service, 'embedding_service', mock_embedding_service):

            # Act
            result = await service.embed_character(
                character_id=character_id,
                trilogy_id=trilogy_id,
                name=name
            )

            # Assert
            assert result["success"] is True

            # Should still add basic profile document
            mock_collection = mock_chromadb.get_or_create_collection.return_value
            mock_collection.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_generated_content(
        self,
        service,
        mock_chromadb,
        mock_embedding_service
    ):
        """Test adding generated content to character embeddings."""
        # Arrange
        character_id = "char-456"
        trilogy_id = "trilogy-123"
        sub_chapter_id = "subchap-789"
        content = "The character walked through the door, contemplating their choices."
        version_number = 1

        with patch.object(service, 'chromadb', mock_chromadb), \
             patch.object(service, 'embedding_service', mock_embedding_service):

            # Act
            result = await service.add_generated_content(
                character_id=character_id,
                trilogy_id=trilogy_id,
                sub_chapter_id=sub_chapter_id,
                content=content,
                version_number=version_number
            )

            # Assert
            assert result["success"] is True
            assert result["sub_chapter_id"] == sub_chapter_id

            # Verify collection was retrieved
            collection_name = f"{trilogy_id}_character_{character_id}"
            mock_chromadb.get_collection.assert_called_with(collection_name)

            # Verify content was embedded
            mock_embedding_service.embed_batch.assert_called_once()

            # Verify document was added
            mock_collection = mock_chromadb.get_collection.return_value
            mock_collection.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_character_embedding(
        self,
        service,
        mock_chromadb,
        mock_embedding_service,
        sample_character_traits
    ):
        """Test updating character embeddings."""
        # Arrange
        character_id = "char-456"
        trilogy_id = "trilogy-123"

        with patch.object(service, 'chromadb', mock_chromadb), \
             patch.object(service, 'embedding_service', mock_embedding_service):

            # Setup - delete existing collection
            mock_chromadb.delete_collection = MagicMock(return_value=True)

            # Act
            result = await service.update_character_embedding(
                character_id=character_id,
                trilogy_id=trilogy_id,
                name="Updated Name",
                description="Updated description",
                traits=sample_character_traits
            )

            # Assert
            assert result["success"] is True

            # Verify old collection was deleted
            collection_name = f"{trilogy_id}_character_{character_id}"
            mock_chromadb.delete_collection.assert_called_with(collection_name)

            # Verify new embeddings were created
            mock_chromadb.get_or_create_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_character_error_handling(
        self,
        service,
        mock_chromadb
    ):
        """Test error handling when embedding fails."""
        # Arrange
        mock_chromadb.get_or_create_collection.side_effect = Exception("ChromaDB error")

        with patch.object(service, 'chromadb', mock_chromadb):

            # Act & Assert
            with pytest.raises(Exception, match="ChromaDB error"):
                await service.embed_character(
                    character_id="char-456",
                    trilogy_id="trilogy-123",
                    name="Test Character"
                )

    def test_prepare_character_documents(self, service, sample_character_traits):
        """Test document preparation for character embedding."""
        # Arrange
        name = "Dr. Sarah Chen"
        description = "A brilliant scientist"
        character_arc = "Evolves throughout the story"
        consciousness_themes = ["identity", "free will"]

        # Act
        documents, ids, metadatas = service._prepare_character_documents(
            character_id="char-456",
            name=name,
            description=description,
            traits=sample_character_traits,
            character_arc=character_arc,
            consciousness_themes=consciousness_themes
        )

        # Assert
        assert len(documents) == 4  # profile, traits, arc, themes
        assert len(ids) == 4
        assert len(metadatas) == 4

        # Check document types
        types = [meta["type"] for meta in metadatas]
        assert "profile" in types
        assert "traits" in types
        assert "arc" in types
        assert "themes" in types

        # Check profile document contains character info
        profile_idx = types.index("profile")
        assert name in documents[profile_idx]
        assert description in documents[profile_idx]

    def test_prepare_character_documents_minimal(self, service):
        """Test document preparation with minimal data."""
        # Act
        documents, ids, metadatas = service._prepare_character_documents(
            character_id="char-456",
            name="John Doe"
        )

        # Assert
        # Should still create profile document
        assert len(documents) >= 1
        assert any(meta["type"] == "profile" for meta in metadatas)

    @pytest.mark.asyncio
    async def test_chunk_content(self, service):
        """Test content chunking for large texts."""
        # Arrange
        long_content = "This is a sentence. " * 200  # ~400 words

        # Act
        chunks = service._chunk_content(long_content, chunk_size=300)

        # Assert
        assert len(chunks) > 1  # Should be split into multiple chunks
        for chunk in chunks:
            word_count = len(chunk.split())
            assert word_count <= 350  # Some buffer for chunk_size

    @pytest.mark.asyncio
    async def test_add_generated_content_with_chunking(
        self,
        service,
        mock_chromadb,
        mock_embedding_service
    ):
        """Test adding large generated content that needs chunking."""
        # Arrange
        long_content = "This is a long narrative passage. " * 500  # Very long content

        with patch.object(service, 'chromadb', mock_chromadb), \
             patch.object(service, 'embedding_service', mock_embedding_service):

            # Act
            result = await service.add_generated_content(
                character_id="char-456",
                trilogy_id="trilogy-123",
                sub_chapter_id="subchap-789",
                content=long_content,
                version_number=1
            )

            # Assert
            assert result["success"] is True

            # Verify multiple documents were added (due to chunking)
            mock_collection = mock_chromadb.get_collection.return_value
            call_args = mock_collection.add.call_args

            # Should have multiple chunks
            assert len(call_args[1]["documents"]) > 1


class TestCharacterEmbeddingServiceIntegration:
    """Integration tests with actual ChromaDB (if available)"""

    @pytest.mark.asyncio
    async def test_full_workflow_with_mocks(self, mock_trilogy_id, mock_character_id):
        """Test complete workflow from character creation to content generation."""
        # This would be an integration test with actual ChromaDB
        # For now, we'll mark it as a placeholder
        pytest.skip("Integration test - requires actual ChromaDB setup")
