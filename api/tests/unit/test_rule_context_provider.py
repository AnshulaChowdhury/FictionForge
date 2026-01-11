"""
Unit tests for RuleContextProvider service (Epic 3).

Tests semantic search and embedding operations for world rules.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from api.services.rule_context_provider import RuleContextProvider


@pytest.fixture
def mock_chromadb():
    """Mock ChromaDB client."""
    return MagicMock()


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service."""
    service = MagicMock()
    service.embed_text.return_value = [0.1] * 384  # Mock 384-dim embedding
    return service


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    return MagicMock()


@pytest.fixture
def rule_provider(mock_chromadb, mock_embedding_service, mock_supabase):
    """RuleContextProvider with mocked dependencies."""
    with patch('api.services.rule_context_provider.chromadb_client', mock_chromadb), \
         patch('api.services.rule_context_provider.embedding_service', mock_embedding_service), \
         patch('api.services.rule_context_provider.get_supabase_client', return_value=mock_supabase):
        return RuleContextProvider()


@pytest.fixture
def sample_rule():
    """Sample world rule."""
    return {
        'id': 'rule-123',
        'title': 'Speed of Light',
        'description': 'Light travels at constant speed',
        'category': 'physics',
        'accuracy_rate': 0.95,
        'times_flagged': 10
    }


# ============================================================================
# Contextual Search Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_contextual_rules_success(rule_provider, mock_chromadb, mock_supabase, sample_rule):
    """Test successful contextual rule retrieval."""
    # Mock collection
    collection = MagicMock()
    collection.count.return_value = 10
    collection.query.return_value = {
        'ids': [['rule-123', 'rule-456']],
        'distances': [[0.3, 0.5]],
        'metadatas': [[{}, {}]]
    }
    mock_chromadb.get_collection.return_value = collection

    # Mock book rules
    book_rules_result = MagicMock()
    book_rules_result.data = [
        {'world_rule_id': 'rule-123'},
        {'world_rule_id': 'rule-456'}
    ]
    mock_supabase.table('world_rule_books').select.return_value.eq.return_value.execute.return_value = book_rules_result

    # Mock rule details
    rules_result = MagicMock()
    rules_result.data = [sample_rule]
    mock_supabase.table('world_rules').select.return_value.in_.return_value.execute.return_value = rules_result

    # Execute
    result = await rule_provider.get_contextual_rules(
        prompt="Write a scene about faster-than-light travel",
        book_id="book-1",
        trilogy_id="trilogy-123"
    )

    # Assertions
    assert len(result) > 0
    assert result[0].id == 'rule-123'
    assert result[0].similarity > 0.0


@pytest.mark.asyncio
async def test_get_contextual_rules_empty_collection(rule_provider, mock_chromadb):
    """Test contextual search with empty collection."""
    # Mock empty collection
    collection = MagicMock()
    collection.count.return_value = 0
    mock_chromadb.get_collection.return_value = collection

    # Execute
    result = await rule_provider.get_contextual_rules(
        prompt="test prompt",
        book_id="book-1",
        trilogy_id="trilogy-123"
    )

    # Assertions
    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_contextual_rules_collection_not_found(rule_provider, mock_chromadb):
    """Test contextual search when collection doesn't exist."""
    # Mock collection not found
    mock_chromadb.get_collection.side_effect = Exception("Collection not found")

    # Execute (should gracefully degrade)
    result = await rule_provider.get_contextual_rules(
        prompt="test prompt",
        book_id="book-1",
        trilogy_id="trilogy-123"
    )

    # Assertions
    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_contextual_rules_filters_by_threshold(rule_provider, mock_chromadb, mock_supabase):
    """Test that rules below similarity threshold are filtered out."""
    # Mock collection with low similarity results
    collection = MagicMock()
    collection.count.return_value = 10
    collection.query.return_value = {
        'ids': [['rule-123', 'rule-456']],
        'distances': [[1.2, 1.5]],  # High distances = low similarity
        'metadatas': [[{}, {}]]
    }
    mock_chromadb.get_collection.return_value = collection

    # Mock book rules
    book_rules_result = MagicMock()
    book_rules_result.data = [
        {'world_rule_id': 'rule-123'},
        {'world_rule_id': 'rule-456'}
    ]
    mock_supabase.table('world_rule_books').select.return_value.eq.return_value.execute.return_value = book_rules_result

    # Execute with high threshold
    result = await rule_provider.get_contextual_rules(
        prompt="test prompt",
        book_id="book-1",
        trilogy_id="trilogy-123",
        similarity_threshold=0.8
    )

    # Assertions - low similarity results should be filtered out
    assert len(result) == 0


# ============================================================================
# Embedding Tests
# ============================================================================

@pytest.mark.asyncio
async def test_embed_rule_success(rule_provider, mock_chromadb):
    """Test successful rule embedding."""
    # Mock collection
    collection = MagicMock()
    mock_chromadb.get_or_create_collection.return_value = collection

    # Execute
    result = await rule_provider.embed_rule(
        rule_id="rule-123",
        rule_title="Test Rule",
        rule_description="Test description",
        rule_category="physics",
        trilogy_id="trilogy-123"
    )

    # Assertions
    assert result is True
    collection.add.assert_called_once()


@pytest.mark.asyncio
async def test_embed_rule_failure(rule_provider, mock_chromadb):
    """Test rule embedding failure."""
    # Mock collection that raises error
    collection = MagicMock()
    collection.add.side_effect = Exception("Embedding failed")
    mock_chromadb.get_or_create_collection.return_value = collection

    # Execute
    result = await rule_provider.embed_rule(
        rule_id="rule-123",
        rule_title="Test Rule",
        rule_description="Test description",
        rule_category="physics",
        trilogy_id="trilogy-123"
    )

    # Assertions
    assert result is False


@pytest.mark.asyncio
async def test_delete_rule_embedding_success(rule_provider, mock_chromadb):
    """Test successful rule embedding deletion."""
    # Mock collection
    collection = MagicMock()
    mock_chromadb.get_collection.return_value = collection

    # Execute
    result = await rule_provider.delete_rule_embedding(
        rule_id="rule-123",
        trilogy_id="trilogy-123"
    )

    # Assertions
    assert result is True
    collection.delete.assert_called_once_with(ids=["rule-123"])


@pytest.mark.asyncio
async def test_update_rule_embedding_success(rule_provider, mock_chromadb):
    """Test successful rule embedding update."""
    # Mock collection
    collection = MagicMock()
    mock_chromadb.get_collection.return_value = collection
    mock_chromadb.get_or_create_collection.return_value = collection

    # Execute
    result = await rule_provider.update_rule_embedding(
        rule_id="rule-123",
        rule_title="Updated Rule",
        rule_description="Updated description",
        rule_category="physics",
        trilogy_id="trilogy-123"
    )

    # Assertions
    assert result is True
    collection.delete.assert_called_once()  # Delete old
    collection.add.assert_called_once()  # Add new


# ============================================================================
# Batch Operations Tests
# ============================================================================

@pytest.mark.asyncio
async def test_embed_all_rules_for_trilogy(rule_provider, mock_chromadb, mock_supabase):
    """Test batch embedding all rules for a trilogy."""
    # Mock rules
    rules_result = MagicMock()
    rules_result.data = [
        {
            'id': 'rule-1',
            'title': 'Rule 1',
            'description': 'Description 1',
            'category': 'physics'
        },
        {
            'id': 'rule-2',
            'title': 'Rule 2',
            'description': 'Description 2',
            'category': 'consciousness'
        }
    ]
    mock_supabase.table('world_rules').select.return_value.eq.return_value.execute.return_value = rules_result

    # Mock collection
    collection = MagicMock()
    mock_chromadb.get_or_create_collection.return_value = collection

    # Execute
    result = await rule_provider.embed_all_rules_for_trilogy("trilogy-123")

    # Assertions
    assert result['total'] == 2
    assert result['successful'] == 2
    assert result['failed'] == 0


# ============================================================================
# Relevance Explanation Tests
# ============================================================================

def test_explain_relevance_with_keyword_match(rule_provider):
    """Test relevance explanation with keyword matches."""
    explanation = rule_provider._explain_relevance(
        rule_title="Speed of Light",
        rule_category="physics",
        prompt="Write a scene about light travel",
        similarity=0.85
    )

    assert "light" in explanation.lower()


def test_explain_relevance_high_similarity(rule_provider):
    """Test relevance explanation based on high similarity."""
    explanation = rule_provider._explain_relevance(
        rule_title="Rule Title",
        rule_category="category",
        prompt="completely different text",
        similarity=0.95
    )

    assert "high" in explanation.lower() or "very" in explanation.lower()


def test_explain_relevance_moderate_similarity(rule_provider):
    """Test relevance explanation based on moderate similarity."""
    explanation = rule_provider._explain_relevance(
        rule_title="Rule Title",
        rule_category="category",
        prompt="different text",
        similarity=0.75
    )

    assert "semantic" in explanation.lower()
