"""
Unit tests for WorldRuleManager service (Epic 3).

Tests CRUD operations for world rules and book associations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import uuid
from api.services.world_rule_manager import WorldRuleManager
from api.models.world_rule import WorldRuleCreate, WorldRuleUpdate


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    return MagicMock()


@pytest.fixture
def rule_manager(mock_supabase):
    """WorldRuleManager instance with mocked Supabase."""
    with patch('api.services.world_rule_manager.get_supabase_client', return_value=mock_supabase):
        return WorldRuleManager()


@pytest.fixture
def sample_rule_data():
    """Sample rule creation data."""
    return WorldRuleCreate(
        trilogy_id=str(uuid.uuid4()),
        title="Speed of Light Constant",
        description="The speed of light remains constant at 299,792,458 m/s in vacuum",
        category="physics",
        book_ids=[str(uuid.uuid4()) for _ in range(3)]
    )


@pytest.fixture
def test_ids():
    """Generate consistent test UUIDs."""
    return {
        'trilogy_id': str(uuid.uuid4()),
        'user_id': str(uuid.uuid4()),
        'rule_id': str(uuid.uuid4()),
        'book_ids': [str(uuid.uuid4()) for _ in range(3)]
    }


@pytest.fixture
def sample_trilogy(test_ids):
    """Sample trilogy data."""
    return {
        'id': test_ids['trilogy_id'],
        'user_id': test_ids['user_id'],
        'title': 'Test Trilogy'
    }


@pytest.fixture
def sample_books(test_ids):
    """Sample books data."""
    return [
        {'id': test_ids['book_ids'][0], 'trilogy_id': test_ids['trilogy_id'], 'book_number': 1},
        {'id': test_ids['book_ids'][1], 'trilogy_id': test_ids['trilogy_id'], 'book_number': 2},
        {'id': test_ids['book_ids'][2], 'trilogy_id': test_ids['trilogy_id'], 'book_number': 3}
    ]


@pytest.fixture
def sample_rule(test_ids):
    """Sample world rule from database."""
    return {
        'id': test_ids['rule_id'],
        'trilogy_id': test_ids['trilogy_id'],
        'title': 'Speed of Light Constant',
        'description': 'The speed of light remains constant at 299,792,458 m/s in vacuum',
        'category': 'physics',
        'created_at': '2025-11-03T12:00:00Z',
        'updated_at': '2025-11-03T12:00:00Z',
        'times_flagged': 0,
        'times_true_violation': 0,
        'times_false_positive': 0,
        'times_intentional_break': 0,
        'times_checker_error': 0,
        'accuracy_rate': 1.0
    }


# ============================================================================
# Create Rule Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_rule_success(rule_manager, mock_supabase, sample_rule_data, sample_trilogy, sample_books, sample_rule, test_ids):
    """Test successful rule creation with book associations."""
    # Update sample_rule_data to use test_ids
    sample_rule_data.trilogy_id = test_ids['trilogy_id']
    sample_rule_data.book_ids = test_ids['book_ids']

    # Mock trilogy verification
    trilogy_result = MagicMock()
    trilogy_result.data = [sample_trilogy]
    mock_supabase.table('trilogy_projects').select.return_value.eq.return_value.execute.return_value = trilogy_result

    # Mock books verification
    books_result = MagicMock()
    books_result.data = sample_books
    mock_supabase.table('books').select.return_value.in_.return_value.execute.return_value = books_result

    # Mock rule insertion
    rule_result = MagicMock()
    rule_result.data = [sample_rule]
    mock_supabase.table('world_rules').insert.return_value.execute.return_value = rule_result

    # Mock book associations insertion
    assoc_result = MagicMock()
    assoc_result.data = [{'world_rule_id': test_ids['rule_id'], 'book_id': bid} for bid in sample_rule_data.book_ids]
    mock_supabase.table('world_rule_books').insert.return_value.execute.return_value = assoc_result

    # Mock get_rule_by_id for return value
    rule_with_books_result = MagicMock()
    rule_with_books_result.data = [{**sample_rule, 'trilogy_projects': {'user_id': test_ids['user_id']}}]
    mock_supabase.table('world_rules').select.return_value.eq.return_value.execute.return_value = rule_with_books_result

    books_assoc_result = MagicMock()
    books_assoc_result.data = [{'book_id': bid} for bid in sample_rule_data.book_ids]
    mock_supabase.table('world_rule_books').select.return_value.eq.return_value.execute.return_value = books_assoc_result

    # Execute
    result = await rule_manager.create_rule(sample_rule_data, test_ids['user_id'])

    # Assertions
    assert result.id == test_ids['rule_id']
    assert result.title == sample_rule_data.title
    assert result.category == sample_rule_data.category
    assert len(result.book_ids) == 3


@pytest.mark.asyncio
async def test_create_rule_trilogy_not_found(rule_manager, mock_supabase, sample_rule_data):
    """Test rule creation with non-existent trilogy."""
    # Mock trilogy not found
    trilogy_result = MagicMock()
    trilogy_result.data = []
    mock_supabase.table('trilogy_projects').select.return_value.eq.return_value.execute.return_value = trilogy_result

    # Execute and assert
    with pytest.raises(ValueError, match="Trilogy .* not found"):
        await rule_manager.create_rule(sample_rule_data, 'user-456')


@pytest.mark.asyncio
async def test_create_rule_wrong_user(rule_manager, mock_supabase, sample_rule_data, sample_trilogy):
    """Test rule creation by unauthorized user."""
    # Mock trilogy belongs to different user
    trilogy_result = MagicMock()
    trilogy_result.data = [sample_trilogy]
    mock_supabase.table('trilogy_projects').select.return_value.eq.return_value.execute.return_value = trilogy_result

    # Execute and assert
    with pytest.raises(ValueError, match="Trilogy does not belong to user"):
        await rule_manager.create_rule(sample_rule_data, 'wrong-user')


@pytest.mark.asyncio
async def test_create_rule_invalid_books(rule_manager, mock_supabase, sample_rule_data, sample_trilogy):
    """Test rule creation with invalid book IDs."""
    # Mock trilogy verification
    trilogy_result = MagicMock()
    trilogy_result.data = [sample_trilogy]
    mock_supabase.table('trilogy_projects').select.return_value.eq.return_value.execute.return_value = trilogy_result

    # Mock books - only return 2 out of 3
    books_result = MagicMock()
    books_result.data = [
        {'id': 'book-1', 'trilogy_id': 'trilogy-123'},
        {'id': 'book-2', 'trilogy_id': 'trilogy-123'}
    ]
    mock_supabase.table('books').select.return_value.in_.return_value.execute.return_value = books_result

    # Execute and assert
    with pytest.raises(ValueError, match="Books not found"):
        await rule_manager.create_rule(sample_rule_data, 'user-456')


# ============================================================================
# Get Rule Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_rule_by_id_success(rule_manager, mock_supabase, sample_rule, test_ids):
    """Test retrieving a rule by ID."""
    # Mock rule retrieval
    rule_result = MagicMock()
    rule_result.data = [{**sample_rule, 'trilogy_projects': {'user_id': test_ids['user_id']}}]
    mock_supabase.table('world_rules').select.return_value.eq.return_value.execute.return_value = rule_result

    # Mock book associations
    books_result = MagicMock()
    books_result.data = [
        {'book_id': test_ids['book_ids'][0]},
        {'book_id': test_ids['book_ids'][1]}
    ]
    mock_supabase.table('world_rule_books').select.return_value.eq.return_value.execute.return_value = books_result

    # Execute
    result = await rule_manager.get_rule_by_id(test_ids['rule_id'], test_ids['user_id'])

    # Assertions
    assert result.id == test_ids['rule_id']
    assert result.title == sample_rule['title']
    assert len(result.book_ids) == 2
    assert test_ids['book_ids'][0] in result.book_ids


@pytest.mark.asyncio
async def test_get_rule_by_id_not_found(rule_manager, mock_supabase):
    """Test getting non-existent rule."""
    # Mock rule not found
    rule_result = MagicMock()
    rule_result.data = []
    mock_supabase.table('world_rules').select.return_value.eq.return_value.execute.return_value = rule_result

    # Execute and assert
    with pytest.raises(ValueError, match="Rule .* not found"):
        await rule_manager.get_rule_by_id('nonexistent', 'user-456')


@pytest.mark.asyncio
async def test_get_rule_by_id_wrong_user(rule_manager, mock_supabase, sample_rule, test_ids):
    """Test getting rule by unauthorized user."""
    # Mock rule retrieval with different user
    rule_result = MagicMock()
    other_user_id = str(uuid.uuid4())
    rule_result.data = [{**sample_rule, 'trilogy_projects': {'user_id': other_user_id}}]
    mock_supabase.table('world_rules').select.return_value.eq.return_value.execute.return_value = rule_result

    # Execute and assert
    with pytest.raises(ValueError, match="Access denied"):
        await rule_manager.get_rule_by_id(test_ids['rule_id'], test_ids['user_id'])


# ============================================================================
# List Rules Tests
# ============================================================================

@pytest.mark.asyncio
async def test_list_rules_basic(rule_manager, mock_supabase, sample_trilogy, sample_rule, test_ids):
    """Test listing rules for a trilogy."""
    # Mock trilogy verification
    trilogy_result = MagicMock()
    trilogy_result.data = [sample_trilogy]

    # Setup proper mock chain for trilogy verification
    trilogy_table = MagicMock()
    trilogy_select = MagicMock()
    trilogy_eq = MagicMock()
    trilogy_eq.execute.return_value = trilogy_result
    trilogy_select.eq.return_value = trilogy_eq
    trilogy_table.select.return_value = trilogy_select

    # Mock rules list with proper chain
    rules_result = MagicMock()
    rule2_id = str(uuid.uuid4())
    rules_result.data = [sample_rule, {**sample_rule, 'id': rule2_id, 'title': 'Rule 2'}]
    rules_result.count = 2

    rules_table = MagicMock()
    rules_select = MagicMock()
    rules_eq = MagicMock()
    rules_order = MagicMock()
    rules_range = MagicMock()
    rules_range.execute.return_value = rules_result
    rules_order.range.return_value = rules_range
    rules_eq.order.return_value = rules_order
    rules_select.eq.return_value = rules_eq
    rules_table.select.return_value = rules_select

    # Mock book associations
    books_result = MagicMock()
    books_result.data = [{'book_id': test_ids['book_ids'][0]}]
    books_table = MagicMock()
    books_select = MagicMock()
    books_eq = MagicMock()
    books_eq.execute.return_value = books_result
    books_select.eq.return_value = books_eq
    books_table.select.return_value = books_select

    # Setup table routing
    def table_router(table_name):
        if table_name == 'trilogy_projects':
            return trilogy_table
        elif table_name == 'world_rules':
            return rules_table
        elif table_name == 'world_rule_books':
            return books_table
        return MagicMock()

    mock_supabase.table.side_effect = table_router

    # Execute
    result = await rule_manager.list_rules(test_ids['trilogy_id'], test_ids['user_id'], page=1, page_size=50)

    # Assertions
    assert result.total == 2
    assert len(result.rules) == 2
    assert result.page == 1


@pytest.mark.asyncio
async def test_list_rules_with_category_filter(rule_manager, mock_supabase, sample_trilogy, sample_rule):
    """Test listing rules filtered by category."""
    # Mock trilogy verification
    trilogy_result = MagicMock()
    trilogy_result.data = [sample_trilogy]
    mock_supabase.table('trilogy_projects').select.return_value.eq.return_value.execute.return_value = trilogy_result

    # Mock filtered rules
    rules_result = MagicMock()
    rules_result.data = [sample_rule]
    rules_result.count = 1

    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.order.return_value = query
    query.range.return_value = query
    query.execute.return_value = rules_result

    mock_supabase.table.return_value = query

    # Mock book associations
    books_result = MagicMock()
    books_result.data = [{'book_id': 'book-1'}]
    mock_supabase.table('world_rule_books').select.return_value.eq.return_value.execute.return_value = books_result

    # Execute
    result = await rule_manager.list_rules('trilogy-123', 'user-456', category='physics')

    # Assertions
    assert result.total == 1
    assert result.rules[0].category == 'physics'


# ============================================================================
# Update Rule Tests
# ============================================================================

@pytest.mark.asyncio
async def test_update_rule_title_and_description(rule_manager, mock_supabase, sample_rule):
    """Test updating rule title and description."""
    # Mock existing rule
    rule_result = MagicMock()
    rule_result.data = [{**sample_rule, 'trilogy_projects': {'user_id': 'user-456'}}]
    mock_supabase.table('world_rules').select.return_value.eq.return_value.execute.return_value = rule_result

    books_result = MagicMock()
    books_result.data = [{'book_id': 'book-1'}]
    mock_supabase.table('world_rule_books').select.return_value.eq.return_value.execute.return_value = books_result

    # Mock update
    update_result = MagicMock()
    updated_rule = {**sample_rule, 'title': 'Updated Title'}
    update_result.data = [updated_rule]
    mock_supabase.table('world_rules').update.return_value.eq.return_value.execute.return_value = update_result

    # Execute
    update_data = WorldRuleUpdate(title="Updated Title", description="Updated description")
    result = await rule_manager.update_rule('rule-789', update_data, 'user-456')

    # Assertions
    assert result.id == 'rule-789'


@pytest.mark.asyncio
async def test_update_rule_book_associations(rule_manager, mock_supabase, sample_rule, sample_books):
    """Test updating rule book associations."""
    # Mock existing rule
    rule_result = MagicMock()
    rule_result.data = [{**sample_rule, 'trilogy_projects': {'user_id': 'user-456'}}]
    mock_supabase.table('world_rules').select.return_value.eq.return_value.execute.return_value = rule_result

    books_result = MagicMock()
    books_result.data = [{'book_id': 'book-1'}]
    mock_supabase.table('world_rule_books').select.return_value.eq.return_value.execute.return_value = books_result

    # Mock book validation
    books_validate_result = MagicMock()
    books_validate_result.data = sample_books[:2]  # Only books 1 and 2
    mock_supabase.table('books').select.return_value.in_.return_value.execute.return_value = books_validate_result

    # Mock delete and insert
    delete_result = MagicMock()
    mock_supabase.table('world_rule_books').delete.return_value.eq.return_value.execute.return_value = delete_result

    insert_result = MagicMock()
    mock_supabase.table('world_rule_books').insert.return_value.execute.return_value = insert_result

    # Execute
    update_data = WorldRuleUpdate(book_ids=['book-1', 'book-2'])
    result = await rule_manager.update_rule('rule-789', update_data, 'user-456')

    # Assertions
    assert result.id == 'rule-789'


# ============================================================================
# Delete Rule Tests
# ============================================================================

@pytest.mark.asyncio
async def test_delete_rule_success(rule_manager, mock_supabase, sample_rule):
    """Test successful rule deletion."""
    # Mock existing rule
    rule_result = MagicMock()
    rule_result.data = [{**sample_rule, 'trilogy_projects': {'user_id': 'user-456'}}]
    mock_supabase.table('world_rules').select.return_value.eq.return_value.execute.return_value = rule_result

    books_result = MagicMock()
    books_result.data = []
    mock_supabase.table('world_rule_books').select.return_value.eq.return_value.execute.return_value = books_result

    # Mock deletion
    delete_result = MagicMock()
    delete_result.data = [sample_rule]
    mock_supabase.table('world_rules').delete.return_value.eq.return_value.execute.return_value = delete_result

    # Execute
    result = await rule_manager.delete_rule('rule-789', 'user-456')

    # Assertions
    assert result['status'] == 'success'
    assert 'rule-789' in result['message']


# ============================================================================
# Category Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_categories(rule_manager, mock_supabase, sample_trilogy):
    """Test getting unique categories for a trilogy."""
    # Mock trilogy verification
    trilogy_result = MagicMock()
    trilogy_result.data = [sample_trilogy]
    mock_supabase.table('trilogy_projects').select.return_value.eq.return_value.execute.return_value = trilogy_result

    # Mock categories
    categories_result = MagicMock()
    categories_result.data = [
        {'category': 'physics'},
        {'category': 'consciousness'},
        {'category': 'physics'},  # Duplicate
        {'category': 'technology'}
    ]
    mock_supabase.table('world_rules').select.return_value.eq.return_value.execute.return_value = categories_result

    # Execute
    result = await rule_manager.get_categories('trilogy-123', 'user-456')

    # Assertions
    assert len(result.categories) == 3  # Unique categories
    assert 'physics' in result.categories
    assert 'consciousness' in result.categories
    assert 'technology' in result.categories


# ============================================================================
# Get Rules for Book Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_rules_for_book(rule_manager, mock_supabase, sample_rule):
    """Test getting all rules applicable to a specific book."""
    # Mock book verification
    book_result = MagicMock()
    book_result.data = [{
        'id': 'book-1',
        'trilogy_id': 'trilogy-123',
        'trilogy_projects': {'user_id': 'user-456'}
    }]
    mock_supabase.table('books').select.return_value.eq.return_value.execute.return_value = book_result

    # Mock book rules
    book_rules_result = MagicMock()
    book_rules_result.data = [
        {'world_rule_id': 'rule-789'},
        {'world_rule_id': 'rule-790'}
    ]
    mock_supabase.table('world_rule_books').select.return_value.eq.return_value.execute.return_value = book_rules_result

    # Mock rules
    rules_result = MagicMock()
    rules_result.data = [sample_rule, {**sample_rule, 'id': 'rule-790'}]
    mock_supabase.table('world_rules').select.return_value.in_.return_value.order.return_value.execute.return_value = rules_result

    # Mock book associations for each rule
    assoc_result = MagicMock()
    assoc_result.data = [{'book_id': 'book-1'}]
    mock_supabase.table('world_rule_books').select.return_value.eq.return_value.execute.return_value = assoc_result

    # Execute
    result = await rule_manager.get_rules_for_book('book-1', 'user-456')

    # Assertions
    assert len(result) == 2
    assert result[0].id in ['rule-789', 'rule-790']
