"""
ChromaDB Client for Consciousness Trilogy App
Manages vector database for character-specific and world rule embeddings

Storage: External SSD for larger datasets
Purpose: Enable RAG (Retrieval Augmented Generation) for character voice consistency
"""

import chromadb
from typing import List, Dict, Optional
import os
from pathlib import Path


class ChromaDBClient:
    """
    Client for managing ChromaDB vector stores for Consciousness Trilogy app

    Manages collections for:
    - Character-specific embeddings (one collection per character)
    - World rule embeddings (one collection per trilogy)
    - Generated content context
    """

    def __init__(self):
        """Initialize ChromaDB client with persistent storage"""
        # Get persist directory from environment
        persist_directory = os.getenv(
            'CHROMADB_PERSIST_DIR',
            './chromadb_data'
        )

        # Ensure directory exists
        persist_path = Path(persist_directory)
        persist_path.mkdir(parents=True, exist_ok=True)

        print(f"Initializing ChromaDB with persist directory: {persist_directory}")

        # Initialize ChromaDB client with persistent storage (ChromaDB 1.3.0+ API)
        self.client = chromadb.PersistentClient(
            path=str(persist_path)
        )

        print("ChromaDB client initialized successfully")

    def get_or_create_collection(
        self,
        collection_name: str,
        metadata: Optional[Dict] = None,
        distance_function: str = "cosine"
    ):
        """
        Get existing collection or create new one

        Args:
            collection_name: Name of the collection
            metadata: Optional metadata for the collection
            distance_function: Distance metric to use ("cosine", "l2", or "ip")
                              Default is "cosine" which works best with normalized embeddings

        Returns:
            ChromaDB collection object

        Example:
            >>> client = ChromaDBClient()
            >>> collection = client.get_or_create_collection(
            ...     "trilogy_123_character_456",
            ...     metadata={"trilogy_id": "123", "character_id": "456"}
            ... )
        """
        try:
            collection = self.client.get_collection(name=collection_name)
            print(f"Retrieved existing collection: {collection_name}")
            return collection
        except Exception:
            # Collection doesn't exist, create it
            # Use cosine distance for normalized embeddings (best for semantic similarity)
            # ChromaDB uses metadata["hnsw:space"] to specify distance metric
            collection_metadata = metadata or {}
            collection_metadata["hnsw:space"] = distance_function

            collection = self.client.create_collection(
                name=collection_name,
                metadata=collection_metadata
            )
            print(f"Created new collection: {collection_name} (distance: {distance_function})")
            return collection

    def get_collection(self, collection_name: str):
        """
        Get an existing collection

        Args:
            collection_name: Name of the collection

        Returns:
            ChromaDB collection object

        Raises:
            ValueError: If collection doesn't exist
        """
        try:
            return self.client.get_collection(name=collection_name)
        except Exception as e:
            raise ValueError(f"Collection '{collection_name}' not found: {str(e)}")

    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection

        Args:
            collection_name: Name of the collection to delete

        Returns:
            bool: True if deleted successfully, False otherwise
        """
        try:
            self.client.delete_collection(name=collection_name)
            print(f"Deleted collection: {collection_name}")
            return True
        except Exception as e:
            print(f"Error deleting collection {collection_name}: {e}")
            return False

    def list_collections(self) -> List[str]:
        """
        List all collections

        Returns:
            List of collection names
        """
        collections = self.client.list_collections()
        return [c.name for c in collections]

    def get_collection_count(self, collection_name: str) -> int:
        """
        Get the number of documents in a collection

        Args:
            collection_name: Name of the collection

        Returns:
            int: Number of documents in the collection
        """
        try:
            collection = self.client.get_collection(name=collection_name)
            return collection.count()
        except Exception as e:
            print(f"Error getting count for collection {collection_name}: {e}")
            return 0

    def persist(self):
        """
        Manually persist changes to disk

        Note: ChromaDB 1.3.0+ auto-persists automatically. This method is kept for compatibility.
        """
        # ChromaDB 1.3.0+ uses PersistentClient which auto-persists
        # No explicit persist() call needed
        print("ChromaDB auto-persists with PersistentClient")

    def reset(self):
        """
        Reset the database (delete all collections)

        WARNING: This will delete all data! Use with caution.
        """
        try:
            # Delete all collections manually
            collections = self.client.list_collections()
            for collection in collections:
                self.client.delete_collection(name=collection.name)
            print("ChromaDB reset - all collections deleted")
        except Exception as e:
            print(f"Error resetting ChromaDB: {e}")

    def get_collection_info(self, collection_name: str) -> Dict:
        """
        Get information about a collection

        Args:
            collection_name: Name of the collection

        Returns:
            Dict with collection metadata
        """
        try:
            collection = self.client.get_collection(name=collection_name)
            return {
                "name": collection_name,
                "count": collection.count(),
                "metadata": collection.metadata
            }
        except Exception as e:
            return {
                "error": str(e),
                "name": collection_name
            }

    def health_check(self) -> Dict[str, bool]:
        """
        Check if ChromaDB is healthy

        Returns:
            Dict with health status
        """
        try:
            # Try to list collections to verify connection
            self.client.list_collections()
            return {
                "healthy": True,
                "message": "ChromaDB is operational"
            }
        except Exception as e:
            return {
                "healthy": False,
                "message": f"ChromaDB error: {str(e)}"
            }


# Global singleton instance
# Import this instance throughout the application
chromadb_client = ChromaDBClient()


def get_chromadb_client() -> ChromaDBClient:
    """
    Get the global ChromaDB client instance.

    Returns:
        ChromaDBClient: The singleton ChromaDB client
    """
    return chromadb_client
