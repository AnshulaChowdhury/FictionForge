"""
Unit tests for ChromaDB Client (Epic 9)
Tests the vector database client for character and world rule embeddings
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from services.chromadb_client import ChromaDBClient, chromadb_client


@pytest.fixture
def temp_chromadb_dir():
    """Create a temporary directory for ChromaDB testing"""
    temp_dir = tempfile.mkdtemp(prefix="test_chromadb_")
    yield temp_dir
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def test_chromadb_client(temp_chromadb_dir, monkeypatch):
    """Create a test ChromaDB client with temporary storage"""
    monkeypatch.setenv('CHROMADB_PERSIST_DIR', temp_chromadb_dir)
    client = ChromaDBClient()
    yield client
    # Cleanup any test collections
    try:
        collections = client.list_collections()
        for collection_name in collections:
            client.delete_collection(collection_name)
    except:
        pass


class TestChromaDBClientInitialization:
    """Test suite for ChromaDB client initialization"""

    def test_client_initialization(self, test_chromadb_client):
        """Test that ChromaDB client initializes successfully"""
        assert test_chromadb_client is not None
        assert test_chromadb_client.client is not None

    def test_global_instance_exists(self):
        """Test that global chromadb_client instance is available"""
        assert chromadb_client is not None
        assert isinstance(chromadb_client, ChromaDBClient)

    def test_persist_directory_creation(self, temp_chromadb_dir, monkeypatch):
        """Test that persist directory is created if it doesn't exist"""
        new_dir = os.path.join(temp_chromadb_dir, "new_subdir")
        monkeypatch.setenv('CHROMADB_PERSIST_DIR', new_dir)

        client = ChromaDBClient()

        assert os.path.exists(new_dir)

    def test_default_persist_directory(self, monkeypatch):
        """Test default persist directory when env var not set"""
        monkeypatch.delenv('CHROMADB_PERSIST_DIR', raising=False)
        client = ChromaDBClient()

        # Should use default directory
        assert client.client is not None


class TestChromaDBCollectionOperations:
    """Test suite for collection CRUD operations"""

    def test_create_new_collection(self, test_chromadb_client):
        """Test creating a new collection"""
        collection_name = "test_collection_001"
        metadata = {"test": "epic9", "purpose": "unit_test"}

        collection = test_chromadb_client.get_or_create_collection(
            collection_name,
            metadata=metadata
        )

        assert collection is not None
        assert collection.name == collection_name

    def test_get_existing_collection(self, test_chromadb_client):
        """Test retrieving an existing collection"""
        collection_name = "test_collection_002"

        # Create collection
        collection1 = test_chromadb_client.get_or_create_collection(collection_name)

        # Get same collection
        collection2 = test_chromadb_client.get_or_create_collection(collection_name)

        assert collection1.name == collection2.name

    def test_get_collection_directly(self, test_chromadb_client):
        """Test get_collection method"""
        collection_name = "test_collection_003"

        # Create collection first
        test_chromadb_client.get_or_create_collection(collection_name)

        # Get collection
        collection = test_chromadb_client.get_collection(collection_name)

        assert collection is not None
        assert collection.name == collection_name

    def test_get_nonexistent_collection_raises_error(self, test_chromadb_client):
        """Test that getting non-existent collection raises error"""
        with pytest.raises(ValueError):
            test_chromadb_client.get_collection("nonexistent_collection")

    def test_delete_collection(self, test_chromadb_client):
        """Test deleting a collection"""
        collection_name = "test_collection_004"

        # Create collection
        test_chromadb_client.get_or_create_collection(collection_name)

        # Delete collection
        result = test_chromadb_client.delete_collection(collection_name)

        assert result is True

        # Verify collection is deleted
        with pytest.raises(ValueError):
            test_chromadb_client.get_collection(collection_name)

    def test_delete_nonexistent_collection(self, test_chromadb_client):
        """Test deleting non-existent collection returns False"""
        result = test_chromadb_client.delete_collection("nonexistent_collection")
        assert result is False

    def test_list_collections(self, test_chromadb_client):
        """Test listing all collections"""
        # Create multiple collections
        collection_names = ["test_col_1", "test_col_2", "test_col_3"]

        for name in collection_names:
            test_chromadb_client.get_or_create_collection(name)

        # List collections
        collections = test_chromadb_client.list_collections()

        # Should contain all created collections
        for name in collection_names:
            assert name in collections

    def test_list_collections_empty(self, test_chromadb_client):
        """Test listing collections when none exist"""
        collections = test_chromadb_client.list_collections()
        assert isinstance(collections, list)


class TestChromaDBDocumentOperations:
    """Test suite for document add/query operations"""

    def test_add_documents_to_collection(self, test_chromadb_client):
        """Test adding documents to a collection"""
        collection_name = "test_collection_docs"
        collection = test_chromadb_client.get_or_create_collection(collection_name)

        # Add documents
        documents = ["Document 1 content", "Document 2 content", "Document 3 content"]
        ids = ["doc1", "doc2", "doc3"]
        metadatas = [{"type": "test"} for _ in documents]

        # Create fake embeddings (384 dimensions)
        import numpy as np
        embeddings = np.random.rand(len(documents), 384).tolist()

        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

        # Verify documents were added
        count = test_chromadb_client.get_collection_count(collection_name)
        assert count == 3

    def test_query_collection(self, test_chromadb_client):
        """Test querying a collection"""
        collection_name = "test_collection_query"
        collection = test_chromadb_client.get_or_create_collection(collection_name)

        # Add documents
        import numpy as np
        documents = ["The cat sat on the mat", "Dogs are loyal animals", "Python is a programming language"]
        ids = ["doc1", "doc2", "doc3"]
        embeddings = np.random.rand(len(documents), 384).tolist()

        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings
        )

        # Query with similar embedding
        query_embedding = np.random.rand(384).tolist()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=2
        )

        assert len(results['ids'][0]) == 2
        assert len(results['documents'][0]) == 2

    def test_get_collection_count(self, test_chromadb_client):
        """Test getting document count in collection"""
        collection_name = "test_collection_count"
        collection = test_chromadb_client.get_or_create_collection(collection_name)

        # Initially should be 0
        count = test_chromadb_client.get_collection_count(collection_name)
        assert count == 0

        # Add some documents
        import numpy as np
        documents = ["Doc 1", "Doc 2", "Doc 3", "Doc 4", "Doc 5"]
        ids = [f"doc{i}" for i in range(1, 6)]
        embeddings = np.random.rand(len(documents), 384).tolist()

        collection.add(ids=ids, documents=documents, embeddings=embeddings)

        # Should now be 5
        count = test_chromadb_client.get_collection_count(collection_name)
        assert count == 5

    def test_get_collection_count_nonexistent(self, test_chromadb_client):
        """Test getting count for non-existent collection returns 0"""
        count = test_chromadb_client.get_collection_count("nonexistent")
        assert count == 0


class TestChromaDBCollectionInfo:
    """Test suite for collection information methods"""

    def test_get_collection_info(self, test_chromadb_client):
        """Test getting collection information"""
        collection_name = "test_collection_info"
        metadata = {"test": "true", "purpose": "info_test"}

        # Create collection with metadata
        test_chromadb_client.get_or_create_collection(collection_name, metadata=metadata)

        # Get collection info
        info = test_chromadb_client.get_collection_info(collection_name)

        assert info['name'] == collection_name
        assert info['count'] == 0
        assert 'metadata' in info

    def test_get_collection_info_with_documents(self, test_chromadb_client):
        """Test collection info includes correct document count"""
        collection_name = "test_collection_info_docs"
        collection = test_chromadb_client.get_or_create_collection(collection_name)

        # Add documents
        import numpy as np
        documents = ["Doc 1", "Doc 2"]
        ids = ["doc1", "doc2"]
        embeddings = np.random.rand(len(documents), 384).tolist()

        collection.add(ids=ids, documents=documents, embeddings=embeddings)

        # Get info
        info = test_chromadb_client.get_collection_info(collection_name)

        assert info['count'] == 2

    def test_get_collection_info_nonexistent(self, test_chromadb_client):
        """Test getting info for non-existent collection"""
        info = test_chromadb_client.get_collection_info("nonexistent")

        assert 'error' in info


class TestChromaDBHealthCheck:
    """Test suite for health check functionality"""

    def test_health_check_healthy(self, test_chromadb_client):
        """Test health check returns healthy status"""
        health = test_chromadb_client.health_check()

        assert health['healthy'] is True
        assert 'message' in health

    def test_health_check_structure(self, test_chromadb_client):
        """Test health check returns correct structure"""
        health = test_chromadb_client.health_check()

        assert isinstance(health, dict)
        assert 'healthy' in health
        assert 'message' in health
        assert isinstance(health['healthy'], bool)


class TestChromaDBPersistence:
    """Test suite for persistence operations"""

    def test_persist_method(self, test_chromadb_client):
        """Test manual persist method"""
        # Should not raise error
        test_chromadb_client.persist()

    def test_data_persists_across_instances(self, temp_chromadb_dir, monkeypatch):
        """Test that data persists when client is recreated"""
        monkeypatch.setenv('CHROMADB_PERSIST_DIR', temp_chromadb_dir)

        # Create first client and add data
        client1 = ChromaDBClient()
        collection_name = "persistent_collection"
        collection = client1.get_or_create_collection(collection_name)

        import numpy as np
        documents = ["Persistent doc"]
        ids = ["doc1"]
        embeddings = np.random.rand(1, 384).tolist()

        collection.add(ids=ids, documents=documents, embeddings=embeddings)
        client1.persist()

        # Create new client with same persist directory
        client2 = ChromaDBClient()
        count = client2.get_collection_count(collection_name)

        assert count == 1, "Data should persist across client instances"


class TestChromaDBReset:
    """Test suite for reset functionality"""

    def test_reset_deletes_all_collections(self, test_chromadb_client):
        """Test reset deletes all collections"""
        # Create multiple collections
        for i in range(3):
            test_chromadb_client.get_or_create_collection(f"test_col_{i}")

        # Verify collections exist
        collections_before = test_chromadb_client.list_collections()
        assert len(collections_before) >= 3

        # Reset
        test_chromadb_client.reset()

        # Verify all collections are deleted
        collections_after = test_chromadb_client.list_collections()
        assert len(collections_after) == 0


class TestChromaDBEdgeCases:
    """Test suite for edge cases"""

    def test_collection_name_with_special_characters(self, test_chromadb_client):
        """Test collection names with special characters"""
        collection_name = "test_collection_123_special"

        collection = test_chromadb_client.get_or_create_collection(collection_name)
        assert collection.name == collection_name

    def test_empty_metadata(self, test_chromadb_client):
        """Test creating collection with empty metadata"""
        collection_name = "test_empty_metadata"

        collection = test_chromadb_client.get_or_create_collection(
            collection_name,
            metadata={}
        )

        assert collection is not None

    def test_none_metadata(self, test_chromadb_client):
        """Test creating collection with None metadata"""
        collection_name = "test_none_metadata"

        collection = test_chromadb_client.get_or_create_collection(
            collection_name,
            metadata=None
        )

        assert collection is not None

    def test_large_metadata(self, test_chromadb_client):
        """Test creating collection with large metadata"""
        collection_name = "test_large_metadata"
        metadata = {f"key_{i}": f"value_{i}" for i in range(100)}

        collection = test_chromadb_client.get_or_create_collection(
            collection_name,
            metadata=metadata
        )

        assert collection is not None
