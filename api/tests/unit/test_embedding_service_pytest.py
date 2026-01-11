"""
Unit tests for Embedding Service (Epic 9)
Tests the sentence-transformers integration for RAG embeddings
"""

import pytest
import numpy as np
from services.embedding_service import embedding_service, EmbeddingService


class TestEmbeddingService:
    """Test suite for EmbeddingService class"""

    def test_singleton_pattern(self):
        """Test that EmbeddingService implements singleton pattern"""
        service1 = EmbeddingService()
        service2 = EmbeddingService()
        assert service1 is service2, "Multiple instances created - singleton pattern violated"

    def test_global_instance_exists(self):
        """Test that global embedding_service instance is available"""
        assert embedding_service is not None
        assert isinstance(embedding_service, EmbeddingService)

    def test_model_loaded(self):
        """Test that the embedding model is loaded successfully"""
        assert embedding_service._model is not None

    def test_get_embedding_dimension(self):
        """Test that embedding dimension is 384 for all-MiniLM-L6-v2"""
        dimension = embedding_service.get_embedding_dimension()
        assert dimension == 384, f"Expected dimension 384, got {dimension}"

    def test_embed_single_text(self):
        """Test embedding generation for a single text"""
        text = "This is a test sentence for embedding generation."
        embedding = embedding_service.embed_text(text)

        # Check type
        assert isinstance(embedding, np.ndarray)

        # Check dimension
        assert len(embedding) == 384

        # Check values are floats
        assert embedding.dtype == np.float32 or embedding.dtype == np.float64

        # Check values are normalized (roughly between -1 and 1)
        assert np.all(embedding >= -2) and np.all(embedding <= 2)

    def test_embed_multiple_texts(self):
        """Test embedding generation for multiple texts"""
        texts = [
            "First test sentence",
            "Second test sentence",
            "Third test sentence"
        ]

        embeddings = embedding_service.embed_text(texts)

        # Check type
        assert isinstance(embeddings, np.ndarray)

        # Check shape (3 texts, 384 dimensions)
        assert embeddings.shape == (3, 384)

    def test_embed_batch(self):
        """Test batch embedding generation"""
        texts = [
            "Mars colonization requires radiation shielding.",
            "The character struggles with AI consciousness.",
            "Terraforming takes centuries of careful planning."
        ]

        embeddings = embedding_service.embed_batch(texts)

        # Check type
        assert isinstance(embeddings, np.ndarray)

        # Check shape
        assert embeddings.shape == (len(texts), 384)

        # Check each embedding is unique
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                similarity = np.dot(embeddings[i], embeddings[j])
                # Embeddings should be different (similarity < 0.99)
                assert similarity < 0.99

    def test_embed_batch_with_custom_batch_size(self):
        """Test batch embedding with custom batch size"""
        texts = ["Text " + str(i) for i in range(10)]
        embeddings = embedding_service.embed_batch(texts, batch_size=5)

        assert embeddings.shape == (10, 384)

    def test_embed_empty_string(self):
        """Test embedding generation for empty string"""
        embedding = embedding_service.embed_text("")

        # Should still return valid embedding
        assert isinstance(embedding, np.ndarray)
        assert len(embedding) == 384

    def test_embed_special_characters(self):
        """Test embedding generation with special characters"""
        text = "Test with special chars: @#$%^&*()_+-=[]{}|;:',.<>?/~`"
        embedding = embedding_service.embed_text(text)

        assert isinstance(embedding, np.ndarray)
        assert len(embedding) == 384

    def test_embed_unicode_characters(self):
        """Test embedding generation with unicode characters"""
        text = "Unicode test: 你好世界 مرحبا العالم Здравствуй мир"
        embedding = embedding_service.embed_text(text)

        assert isinstance(embedding, np.ndarray)
        assert len(embedding) == 384

    def test_compute_similarity_identical_texts(self):
        """Test similarity computation for identical texts"""
        text = "The cat sat on the mat"
        emb1 = embedding_service.embed_text(text)
        emb2 = embedding_service.embed_text(text)

        similarity = embedding_service.compute_similarity(emb1, emb2)

        # Should be very close to 1.0 (identical)
        assert similarity > 0.99, f"Expected similarity > 0.99, got {similarity}"

    def test_compute_similarity_similar_texts(self):
        """Test similarity computation for semantically similar texts"""
        text1 = "The cat sat on the mat"
        text2 = "A feline rested on the rug"

        emb1 = embedding_service.embed_text(text1)
        emb2 = embedding_service.embed_text(text2)

        similarity = embedding_service.compute_similarity(emb1, emb2)

        # Should have high similarity (semantically similar)
        assert similarity > 0.5, f"Expected similarity > 0.5, got {similarity}"

    def test_compute_similarity_different_texts(self):
        """Test similarity computation for unrelated texts"""
        text1 = "The cat sat on the mat"
        text2 = "Quantum computing uses qubits"

        emb1 = embedding_service.embed_text(text1)
        emb2 = embedding_service.embed_text(text2)

        similarity = embedding_service.compute_similarity(emb1, emb2)

        # Should have low similarity (unrelated)
        assert similarity < 0.5, f"Expected similarity < 0.5, got {similarity}"

    def test_compute_similarity_ordering(self):
        """Test that similar texts have higher similarity than different texts"""
        text1 = "The cat sat on the mat"
        text2 = "A feline rested on the rug"  # Similar
        text3 = "Quantum computing uses qubits"  # Different

        emb1 = embedding_service.embed_text(text1)
        emb2 = embedding_service.embed_text(text2)
        emb3 = embedding_service.embed_text(text3)

        sim_similar = embedding_service.compute_similarity(emb1, emb2)
        sim_different = embedding_service.compute_similarity(emb1, emb3)

        assert sim_similar > sim_different, "Similar texts should have higher similarity"

    def test_compute_similarity_zero_vectors(self):
        """Test similarity computation with zero vectors"""
        zero_vector = np.zeros(384)
        normal_embedding = embedding_service.embed_text("test text")

        similarity = embedding_service.compute_similarity(zero_vector, normal_embedding)

        # Should return 0.0 for zero vectors
        assert similarity == 0.0

    def test_embedding_determinism(self):
        """Test that same text produces same embedding (deterministic)"""
        text = "Determinism test sentence"

        emb1 = embedding_service.embed_text(text)
        emb2 = embedding_service.embed_text(text)

        # Should be identical
        assert np.allclose(emb1, emb2), "Embeddings should be deterministic"

    def test_batch_vs_single_consistency(self):
        """Test that batch embedding produces same results as single embedding"""
        texts = ["First text", "Second text", "Third text"]

        # Generate embeddings individually
        individual_embeddings = [embedding_service.embed_text(text) for text in texts]

        # Generate embeddings in batch
        batch_embeddings = embedding_service.embed_batch(texts)

        # Compare
        for i, text in enumerate(texts):
            assert np.allclose(individual_embeddings[i], batch_embeddings[i]), \
                f"Batch embedding differs from individual for text {i}"

    def test_long_text_embedding(self):
        """Test embedding generation for long text"""
        # Generate long text (sentence transformers typically handle up to 512 tokens)
        long_text = " ".join(["This is a test sentence."] * 100)

        embedding = embedding_service.embed_text(long_text)

        assert isinstance(embedding, np.ndarray)
        assert len(embedding) == 384

    def test_embedding_normalization(self):
        """Test that embeddings are roughly normalized"""
        text = "Test text for normalization check"
        embedding = embedding_service.embed_text(text)

        # Calculate L2 norm
        norm = np.linalg.norm(embedding)

        # Sentence transformers typically normalize embeddings
        # Norm should be close to 1.0 (within reasonable range)
        assert 0.8 < norm < 1.2, f"Expected normalized embedding, got norm {norm}"


class TestEmbeddingServicePerformance:
    """Performance and memory tests for EmbeddingService"""

    def test_batch_size_performance(self):
        """Test that batch processing is used correctly"""
        # This test just ensures batch_size parameter is accepted
        texts = ["Text " + str(i) for i in range(100)]

        # Should not raise error
        embeddings = embedding_service.embed_batch(texts, batch_size=32)
        assert embeddings.shape == (100, 384)

    def test_show_progress_parameter(self):
        """Test that show_progress parameter is accepted"""
        texts = ["Text " + str(i) for i in range(10)]

        # Should not raise error
        embeddings = embedding_service.embed_batch(texts, show_progress=False)
        assert embeddings.shape == (10, 384)


class TestEmbeddingServiceEdgeCases:
    """Edge case tests for EmbeddingService"""

    def test_single_word_embedding(self):
        """Test embedding for single word"""
        embedding = embedding_service.embed_text("word")
        assert len(embedding) == 384

    def test_numeric_string_embedding(self):
        """Test embedding for numeric string"""
        embedding = embedding_service.embed_text("123456789")
        assert len(embedding) == 384

    def test_punctuation_only_embedding(self):
        """Test embedding for punctuation only"""
        embedding = embedding_service.embed_text("!!!")
        assert len(embedding) == 384

    def test_whitespace_embedding(self):
        """Test embedding for whitespace"""
        embedding = embedding_service.embed_text("   ")
        assert len(embedding) == 384

    def test_mixed_case_consistency(self):
        """Test that different cases affect embeddings"""
        text1 = "THE CAT SAT ON THE MAT"
        text2 = "the cat sat on the mat"
        text3 = "The Cat Sat On The Mat"

        emb1 = embedding_service.embed_text(text1)
        emb2 = embedding_service.embed_text(text2)
        emb3 = embedding_service.embed_text(text3)

        # Different cases should produce similar but not identical embeddings
        sim_12 = embedding_service.compute_similarity(emb1, emb2)
        sim_23 = embedding_service.compute_similarity(emb2, emb3)

        # Should be very similar (> 0.95) but potentially not identical
        assert sim_12 > 0.95
        assert sim_23 > 0.95
