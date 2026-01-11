"""
Pytest configuration and shared fixtures.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime
import tempfile
import shutil
import os


@pytest.fixture
def mock_user_id():
    """Mock user ID for testing."""
    return "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def mock_trilogy_id():
    """Mock trilogy ID for testing."""
    return "660e8400-e29b-41d4-a716-446655440001"


@pytest.fixture
def mock_book_ids():
    """Mock book IDs for testing."""
    return [
        "770e8400-e29b-41d4-a716-446655440010",
        "770e8400-e29b-41d4-a716-446655440011",
        "770e8400-e29b-41d4-a716-446655440012",
    ]


@pytest.fixture
def sample_trilogy_data(mock_user_id, mock_trilogy_id):
    """Sample trilogy data for testing."""
    return {
        "id": mock_trilogy_id,
        "user_id": mock_user_id,
        "title": "The Consciousness Trilogy",
        "description": "A sci-fi trilogy about consciousness.",
        "author": "Jane Doe",
        "narrative_overview": "Humanity's journey through evolving consciousness.",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


@pytest.fixture
def sample_books_data(mock_trilogy_id, mock_book_ids):
    """Sample books data for testing."""
    books = []
    for i, book_id in enumerate(mock_book_ids, start=1):
        books.append({
            "id": book_id,
            "trilogy_id": mock_trilogy_id,
            "book_number": i,
            "title": f"Book {i}",
            "description": None,
            "target_word_count": 80000,
            "current_word_count": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        })
    return books


@pytest.fixture
def mock_supabase_client(sample_trilogy_data, sample_books_data):
    """Mock Supabase client for testing."""
    mock_client = MagicMock()

    # Mock trilogy table
    trilogy_mock = MagicMock()
    trilogy_mock.insert.return_value.execute.return_value.data = [sample_trilogy_data]

    # Mock books table
    books_mock = MagicMock()
    books_mock.insert.return_value.execute.return_value.data = sample_books_data

    # Configure table method to return appropriate mocks
    def table_side_effect(table_name):
        if table_name == "trilogy_projects":
            return trilogy_mock
        elif table_name == "books":
            return books_mock
        return MagicMock()

    mock_client.table.side_effect = table_side_effect

    return mock_client


# =============================================================================
# Epic 9 Fixtures - Embedding Service & ChromaDB
# =============================================================================

@pytest.fixture(scope="session")
def embedding_service_instance():
    """
    Session-scoped embedding service instance.
    Model loads once per test session to improve performance.
    """
    from services.embedding_service import embedding_service
    return embedding_service


@pytest.fixture
def temp_chromadb_dir():
    """Create a temporary directory for ChromaDB testing."""
    temp_dir = tempfile.mkdtemp(prefix="test_chromadb_")
    yield temp_dir
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def test_chromadb_client(temp_chromadb_dir, monkeypatch):
    """Create a test ChromaDB client with temporary storage."""
    from services.chromadb_client import ChromaDBClient

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


@pytest.fixture
def mock_character_id():
    """Mock character ID for testing."""
    return "880e8400-e29b-41d4-a716-446655440020"


@pytest.fixture
def mock_chapter_id():
    """Mock chapter ID for testing."""
    return "990e8400-e29b-41d4-a716-446655440030"


@pytest.fixture
def sample_character_data(mock_trilogy_id, mock_character_id):
    """Sample character data for Epic 2 testing."""
    return {
        "id": mock_character_id,
        "trilogy_id": mock_trilogy_id,
        "name": "Dr. Sarah Chen",
        "description": "A brilliant neuroscientist who questions the nature of consciousness",
        "traits": {
            "personality": ["analytical", "determined", "empathetic"],
            "speech_patterns": ["uses scientific terminology", "speaks precisely"],
            "physical_description": "Tall with short dark hair and piercing blue eyes",
            "background": "Former MIT neuroscientist, lost her partner in an AI accident",
            "motivations": ["understand consciousness", "prevent AI suffering", "find redemption"]
        },
        "character_arc": "Begins as skeptical materialist, evolves to accept consciousness transcendence",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


@pytest.fixture
def sample_world_rules():
    """Sample world rules for Epic 9 testing."""
    return [
        {
            "id": "rule_001",
            "title": "Consciousness Transfer Limitation",
            "description": "Consciousness transfer requires quantum precision. Loss >0.1% causes degradation.",
            "category": "consciousness_mechanics",
            "book_ids": [1, 2, 3],
            "accuracy": 0.95
        },
        {
            "id": "rule_002",
            "title": "Mars Atmospheric Pressure",
            "description": "Mars pressure is 0.6% of Earth's. Habitats maintain 1 atm with redundancy.",
            "category": "environment",
            "book_ids": [1, 2, 3],
            "accuracy": 1.0
        },
        {
            "id": "rule_003",
            "title": "AI Rights Timeline",
            "description": "AI gained personhood in 2087. Before this, no legal standing.",
            "category": "society",
            "book_ids": [2, 3],
            "accuracy": 0.90
        }
    ]


@pytest.fixture
def sample_embeddings(embedding_service_instance):
    """Generate sample embeddings for testing."""
    texts = [
        "Sample text one for testing",
        "Sample text two for testing",
        "Sample text three for testing"
    ]
    return embedding_service_instance.embed_batch(texts)


@pytest.fixture
def sample_chapter_data(mock_book_ids, mock_character_id, mock_chapter_id):
    """Sample chapter data for Epic 4 testing."""
    return {
        "id": mock_chapter_id,
        "book_id": mock_book_ids[0],  # First book
        "character_id": mock_character_id,
        "title": "The Awakening",
        "chapter_number": 1,
        "description": "Sarah discovers the quantum consciousness lab",
        "target_word_count": 3000,
        "current_word_count": 0,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
