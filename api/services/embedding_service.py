"""
Embedding Service for Consciousness Trilogy App
Uses sentence-transformers to generate embeddings for RAG

Model: all-MiniLM-L6-v2
- Size: ~80MB download
- Embedding dimension: 384
- Memory usage: ~500MB when loaded
- Speed: ~1000 sentences/second on CPU
"""

from sentence_transformers import SentenceTransformer
from typing import List, Union
import numpy as np
import os


class EmbeddingService:
    """
    Singleton service for generating embeddings using all-MiniLM-L6-v2

    This service manages the sentence-transformer model lifecycle and provides
    methods for generating embeddings for both single texts and batches.
    """

    _instance = None
    _model = None

    def __new__(cls):
        """Ensure only one instance of EmbeddingService exists (Singleton pattern)"""
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the embedding model (happens only once due to singleton)"""
        if self._model is None:
            self._load_model()

    def _load_model(self):
        """
        Load the embedding model
        Model will be downloaded to ~/.cache/torch/sentence_transformers/ on first run
        """
        print("Loading embedding model: all-MiniLM-L6-v2...")

        # Get cache directory from environment or use default
        cache_dir = os.getenv('EMBEDDING_CACHE_DIR', None)

        # Load model
        self._model = SentenceTransformer(
            'all-MiniLM-L6-v2',
            cache_folder=cache_dir if cache_dir else None
        )

        print(f"Model loaded successfully. Embedding dimension: {self._model.get_sentence_embedding_dimension()}")

    def embed_text(self, text: Union[str, List[str]]) -> Union[np.ndarray, List[np.ndarray]]:
        """
        Generate embeddings for text

        Args:
            text: Single string or list of strings

        Returns:
            numpy array(s) of normalized embeddings (dimension 384)

        Example:
            >>> service = EmbeddingService()
            >>> embedding = service.embed_text("This is a test sentence")
            >>> print(embedding.shape)  # (384,)
        """
        if self._model is None:
            raise RuntimeError("Embedding model not loaded. Call _load_model() first.")

        return self._model.encode(text, convert_to_numpy=True, normalize_embeddings=True)

    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Generate embeddings for a batch of texts efficiently

        Args:
            texts: List of strings to embed
            batch_size: Batch size for processing (default 32)
            show_progress: Show progress bar for large batches (default False)

        Returns:
            numpy array of normalized embeddings, shape (len(texts), 384)

        Example:
            >>> service = EmbeddingService()
            >>> texts = ["First text", "Second text", "Third text"]
            >>> embeddings = service.embed_batch(texts)
            >>> print(embeddings.shape)  # (3, 384)
        """
        if self._model is None:
            raise RuntimeError("Embedding model not loaded. Call _load_model() first.")

        # Show progress bar only for large batches
        show_progress_bar = show_progress or len(texts) > 100

        return self._model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=show_progress_bar
        )

    def get_embedding_dimension(self) -> int:
        """
        Returns the embedding dimension (384 for all-MiniLM-L6-v2)

        Returns:
            int: Embedding dimension
        """
        if self._model is None:
            raise RuntimeError("Embedding model not loaded. Call _load_model() first.")

        return self._model.get_sentence_embedding_dimension()

    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            float: Cosine similarity score between -1 and 1

        Example:
            >>> service = EmbeddingService()
            >>> emb1 = service.embed_text("The cat sat on the mat")
            >>> emb2 = service.embed_text("A feline rested on the rug")
            >>> similarity = service.compute_similarity(emb1, emb2)
            >>> print(similarity)  # High similarity (>0.7)
        """
        # Normalize vectors
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        # Compute cosine similarity
        return float(np.dot(embedding1, embedding2) / (norm1 * norm2))


# Global singleton instance
# Import this instance throughout the application
embedding_service = EmbeddingService()


def get_embedding_service() -> EmbeddingService:
    """
    Get the global EmbeddingService instance.

    Returns:
        EmbeddingService: The singleton embedding service
    """
    return embedding_service
