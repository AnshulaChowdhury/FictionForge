"""
Integration tests for World Rules API (Epic 3).

Tests full API request/response cycle with authentication.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch
from api.main import app


@pytest.fixture
async def client():
    """HTTP client for API requests."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_auth():
    """Mock authentication to return a test user."""
    with patch('api.middleware.auth.get_current_user_id', return_value='user-123'):
        yield


@pytest.fixture
def sample_rule_create():
    """Sample rule creation payload."""
    return {
        "trilogy_id": "trilogy-123",
        "title": "Speed of Light Constant",
        "description": "The speed of light remains constant at 299,792,458 m/s",
        "category": "physics",
        "book_ids": ["book-1", "book-2", "book-3"]
    }


# ============================================================================
# Create Rule Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_rule_success(client, mock_auth, sample_rule_create):
    """Test successful rule creation."""
    with patch('api.routes.world_rules.WorldRuleManager') as MockManager, \
         patch('api.routes.world_rules.TaskQueue') as MockQueue:

        # Mock manager
        manager_instance = MockManager.return_value
        manager_instance.create_rule = AsyncMock(return_value=MagicMock(
            id="rule-123",
            trilogy_id="trilogy-123",
            title=sample_rule_create["title"],
            description=sample_rule_create["description"],
            category=sample_rule_create["category"],
            book_ids=sample_rule_create["book_ids"],
            created_at="2025-11-03T12:00:00Z",
            updated_at="2025-11-03T12:00:00Z",
            times_flagged=0,
            times_true_violation=0,
            times_false_positive=0,
            times_intentional_break=0,
            times_checker_error=0,
            accuracy_rate=1.0
        ))

        # Mock task queue
        MockQueue.enqueue_rule_embedding = AsyncMock(return_value="job-123")

        # Execute
        response = await client.post("/api/world_rules", json=sample_rule_create)

        # Assertions
        assert response.status_code == 201
        data = response.json()
        assert data['id'] == "rule-123"
        assert data['title'] == sample_rule_create['title']
        assert len(data['book_ids']) == 3


@pytest.mark.asyncio
async def test_create_rule_validation_error(client, mock_auth):
    """Test rule creation with validation errors."""
    invalid_data = {
        "trilogy_id": "trilogy-123",
        "title": "",  # Empty title - should fail validation
        "description": "Test description",
        "category": "physics",
        "book_ids": []  # Empty book_ids - should fail validation
    }

    response = await client.post("/api/world_rules", json=invalid_data)

    # Should fail validation
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_rule_unauthorized(client, sample_rule_create):
    """Test rule creation without authentication."""
    with patch('api.middleware.auth.get_current_user_id', side_effect=Exception("Unauthorized")):
        response = await client.post("/api/world_rules", json=sample_rule_create)

        # Should return 500 or auth error
        assert response.status_code in [401, 403, 500]


# ============================================================================
# List Rules Tests
# ============================================================================

@pytest.mark.asyncio
async def test_list_rules_success(client, mock_auth):
    """Test listing rules for a trilogy."""
    with patch('api.routes.world_rules.WorldRuleManager') as MockManager:
        # Mock manager
        manager_instance = MockManager.return_value
        manager_instance.list_rules = AsyncMock(return_value=MagicMock(
            rules=[],
            total=0,
            page=1,
            page_size=50,
            total_pages=0
        ))

        # Execute
        response = await client.get("/api/world_rules?trilogy_id=trilogy-123")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert 'rules' in data
        assert 'total' in data


@pytest.mark.asyncio
async def test_list_rules_with_filters(client, mock_auth):
    """Test listing rules with category and book filters."""
    with patch('api.routes.world_rules.WorldRuleManager') as MockManager:
        # Mock manager
        manager_instance = MockManager.return_value
        manager_instance.list_rules = AsyncMock(return_value=MagicMock(
            rules=[],
            total=0,
            page=1,
            page_size=50,
            total_pages=0
        ))

        # Execute
        response = await client.get(
            "/api/world_rules?trilogy_id=trilogy-123&category=physics&book_id=book-1"
        )

        # Assertions
        assert response.status_code == 200


# ============================================================================
# Get Rule Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_rule_success(client, mock_auth):
    """Test getting a single rule."""
    with patch('api.routes.world_rules.WorldRuleManager') as MockManager:
        # Mock manager
        manager_instance = MockManager.return_value
        manager_instance.get_rule_by_id = AsyncMock(return_value=MagicMock(
            id="rule-123",
            trilogy_id="trilogy-123",
            title="Test Rule",
            description="Test description",
            category="physics",
            book_ids=["book-1"],
            created_at="2025-11-03T12:00:00Z",
            updated_at="2025-11-03T12:00:00Z",
            times_flagged=0,
            times_true_violation=0,
            times_false_positive=0,
            times_intentional_break=0,
            times_checker_error=0,
            accuracy_rate=1.0
        ))

        # Execute
        response = await client.get("/api/world_rules/rule-123")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == "rule-123"


@pytest.mark.asyncio
async def test_get_rule_not_found(client, mock_auth):
    """Test getting non-existent rule."""
    with patch('api.routes.world_rules.WorldRuleManager') as MockManager:
        # Mock manager to raise ValueError
        manager_instance = MockManager.return_value
        manager_instance.get_rule_by_id = AsyncMock(side_effect=ValueError("Rule not found"))

        # Execute
        response = await client.get("/api/world_rules/nonexistent")

        # Assertions
        assert response.status_code == 404


# ============================================================================
# Update Rule Tests
# ============================================================================

@pytest.mark.asyncio
async def test_update_rule_success(client, mock_auth):
    """Test successful rule update."""
    with patch('api.routes.world_rules.WorldRuleManager') as MockManager, \
         patch('api.routes.world_rules.TaskQueue') as MockQueue:

        # Mock manager
        manager_instance = MockManager.return_value
        manager_instance.update_rule = AsyncMock(return_value=MagicMock(
            id="rule-123",
            trilogy_id="trilogy-123",
            title="Updated Title",
            description="Updated description",
            category="physics",
            book_ids=["book-1"],
            created_at="2025-11-03T12:00:00Z",
            updated_at="2025-11-03T13:00:00Z",
            times_flagged=0,
            times_true_violation=0,
            times_false_positive=0,
            times_intentional_break=0,
            times_checker_error=0,
            accuracy_rate=1.0
        ))

        # Mock task queue
        MockQueue.enqueue_rule_embedding_update = AsyncMock(return_value="job-456")

        # Execute
        update_data = {"title": "Updated Title"}
        response = await client.put("/api/world_rules/rule-123", json=update_data)

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data['title'] == "Updated Title"


# ============================================================================
# Delete Rule Tests
# ============================================================================

@pytest.mark.asyncio
async def test_delete_rule_success(client, mock_auth):
    """Test successful rule deletion."""
    with patch('api.routes.world_rules.WorldRuleManager') as MockManager, \
         patch('api.routes.world_rules.TaskQueue') as MockQueue:

        # Mock manager
        manager_instance = MockManager.return_value
        manager_instance.get_rule_by_id = AsyncMock(return_value=MagicMock(
            id="rule-123",
            trilogy_id="trilogy-123"
        ))
        manager_instance.delete_rule = AsyncMock(return_value={"status": "success"})

        # Mock task queue
        MockQueue.enqueue_rule_embedding_deletion = AsyncMock(return_value="job-789")

        # Execute
        response = await client.delete("/api/world_rules/rule-123")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'


# ============================================================================
# Contextual Search Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_contextual_rules(client, mock_auth):
    """Test contextual rule search."""
    with patch('api.routes.world_rules.WorldRuleManager') as MockManager, \
         patch('api.routes.world_rules.RuleContextProvider') as MockProvider:

        # Mock manager (for access check)
        manager_instance = MockManager.return_value
        manager_instance.get_rules_for_book = AsyncMock(return_value=[])

        # Mock provider
        provider_instance = MockProvider.return_value
        provider_instance.get_contextual_rules = AsyncMock(return_value=[
            MagicMock(
                id="rule-123",
                title="Relevant Rule",
                description="Description",
                category="physics",
                similarity=0.85,
                relevance_reason="High similarity",
                is_critical=False,
                accuracy_rate=0.95
            )
        ])

        # Execute
        response = await client.get(
            "/api/world_rules/contextual/search?"
            "prompt=test+prompt&book_id=book-1&trilogy_id=trilogy-123"
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert 'rules' in data
        assert len(data['rules']) > 0


# ============================================================================
# Preview Rules Tests
# ============================================================================

@pytest.mark.asyncio
async def test_preview_rules_for_generation(client, mock_auth):
    """Test rule preview for content generation."""
    with patch('api.routes.world_rules.WorldRuleManager') as MockManager, \
         patch('api.routes.world_rules.WorldRuleRAGProvider') as MockProvider:

        # Mock manager
        manager_instance = MockManager.return_value
        manager_instance.get_rules_for_book = AsyncMock(return_value=[])

        # Mock provider
        provider_instance = MockProvider.return_value
        provider_instance.preview_rules = AsyncMock(return_value=MagicMock(
            rules=[],
            formatted_prompt_section="",
            cache_hit=False
        ))

        # Execute
        preview_data = {
            "prompt": "Write a scene",
            "plot_points": "Key plot points",
            "book_id": "book-1",
            "trilogy_id": "trilogy-123"
        }
        response = await client.post("/api/world_rules/preview", json=preview_data)

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert 'rules' in data
        assert 'formatted_prompt_section' in data


# ============================================================================
# Category Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_categories(client, mock_auth):
    """Test getting unique categories."""
    with patch('api.routes.world_rules.WorldRuleManager') as MockManager:
        # Mock manager
        manager_instance = MockManager.return_value
        manager_instance.get_categories = AsyncMock(return_value=MagicMock(
            categories=["physics", "consciousness", "technology"]
        ))

        # Execute
        response = await client.get("/api/world_rules/categories/list?trilogy_id=trilogy-123")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert 'categories' in data
        assert len(data['categories']) == 3


# ============================================================================
# Batch Operations Tests
# ============================================================================

@pytest.mark.asyncio
async def test_batch_embed_trilogy(client, mock_auth):
    """Test batch embedding endpoint."""
    with patch('api.routes.world_rules.WorldRuleManager') as MockManager, \
         patch('api.routes.world_rules.TaskQueue') as MockQueue:

        # Mock manager
        manager_instance = MockManager.return_value
        manager_instance.get_categories = AsyncMock(return_value=MagicMock(categories=[]))

        # Mock task queue
        MockQueue.enqueue_batch_trilogy_embedding = AsyncMock(return_value="batch-job-123")

        # Execute
        response = await client.post("/api/world_rules/batch/embed-trilogy?trilogy_id=trilogy-123")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'enqueued'
        assert 'job_id' in data
