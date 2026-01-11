# Backend Testing Suite - Consciousness Trilogy App

## Overview

Backend testing suite for the FastAPI application with focus on:
- Unit tests for business logic
- Integration tests with real services (Supabase, Redis, ChromaDB)
- RLS (Row-Level Security) testing
- API endpoint testing

## Quick Start

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=api --cov-report=html

# Run specific test category
pytest tests/unit -v
pytest tests/integration -v -m integration
pytest tests/integration -v -m rls

# Run specific test file
pytest tests/unit/test_trilogy_manager.py -v
```

## Test Structure

```
api/tests/
├── README.md                          # This file
├── conftest.py                        # Shared fixtures and configuration
├── test_data_seeds.py                 # Test data seeding utilities
│
├── unit/                              # Unit tests (fast, no external dependencies)
│   ├── test_auth_service.py          # TODO: Auth service tests
│   ├── test_trilogy_manager.py       # TODO: Trilogy management tests
│   ├── test_character_service.py     # TODO: Character service tests
│   ├── test_world_rules_service.py   # TODO: World rules tests
│   └── test_rag_service.py           # TODO: RAG generation tests
│
├── integration/                       # Integration tests (with real services)
│   ├── test_api_endpoints.py         # TODO: API endpoint tests
│   ├── test_rls_policies.py          # TODO: CRITICAL - RLS security tests
│   ├── test_chromadb.py              # TODO: Vector database tests
│   └── test_redis_cache.py           # TODO: Cache tests
│
└── fixtures/                          # Test data fixtures
    └── sample_data.py                 # Sample test data
```

## Test Data Seeding

### Seeding Utilities (`test_data_seeds.py`)

Provides functions to seed the database with realistic test data for E2E tests.

**Usage:**
```python
from tests.test_data_seeds import seed_test_user, seed_trilogy, seed_characters

# Seed complete test environment
user_id = seed_test_user("test@example.com", "password123")
trilogy_id = seed_trilogy(user_id, "The Consciousness Trilogy")
character_ids = seed_characters(trilogy_id)
```

### Available Seeding Functions

1. **`seed_test_user(email, password, name)`**
   - Creates a test user in Supabase Auth
   - Returns: user_id

2. **`seed_trilogy(user_id, title, author, description)`**
   - Creates a trilogy with 3 books
   - Returns: trilogy_id

3. **`seed_characters(trilogy_id, count=3)`**
   - Creates characters for a trilogy
   - Returns: List of character_ids

4. **`seed_world_rules(trilogy_id, count=5)`**
   - Creates world rules for a trilogy
   - Returns: List of world_rule_ids

5. **`seed_chapters(book_id, character_ids, count=10)`**
   - Creates chapters for a book
   - Returns: List of chapter_ids

6. **`seed_complete_trilogy(email, password)`**
   - Seeds a complete trilogy with all related data
   - Returns: Dictionary with all IDs

7. **`cleanup_test_user(user_id)`**
   - Deletes a test user and all related data
   - Use in teardown

## Configuration

### pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
markers =
    unit: Unit tests (fast, no external dependencies)
    integration: Integration tests (requires services)
    e2e: End-to-end tests (full system)
    slow: Tests that take >5 seconds
    rls: Row Level Security tests (critical)
addopts =
    --cov=api
    --cov-report=html
    --cov-report=term-missing
    --strict-markers
    -v
```

### requirements-dev.txt

```txt
# Testing Framework
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-xdist==3.5.0
pytest-mock==3.12.0

# HTTP Testing
httpx==0.25.2

# Test Data
factory-boy==3.3.0
faker==20.1.0

# Code Quality
black==23.12.1
flake8==6.1.0
mypy==1.7.1
```

## Test Categories

### Unit Tests (tests/unit/)

Fast tests that don't require external services. Mock all dependencies.

**Example:**
```python
import pytest
from api.services.trilogy_manager import TrilogyManager
from unittest.mock import Mock, patch

class TestTrilogyManager:
    @pytest.mark.unit
    def test_create_trilogy_validates_required_fields(self):
        with pytest.raises(ValueError):
            manager = TrilogyManager(user_id="test-user")
            manager.create_project(title="", author="")  # Should fail validation
```

### Integration Tests (tests/integration/)

Tests that interact with real services. Use test database instances.

**Example:**
```python
import pytest
from httpx import AsyncClient
from api.main import app

@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_trilogy_endpoint(test_db, auth_token):
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/trilogy/create",
            json={"title": "Test", "author": "Author"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 201
        assert response.json()["trilogy"]["title"] == "Test"
```

### RLS Tests (tests/integration/test_rls_policies.py)

**CRITICAL** - Security tests that verify Row-Level Security policies.

**Example:**
```python
import pytest
from tests.test_data_seeds import seed_test_user, seed_trilogy

@pytest.mark.rls
@pytest.mark.asyncio
async def test_user_cannot_access_other_users_trilogies(supabase_client):
    # Create two users
    user_a_id = seed_test_user("user_a@test.com", "password")
    user_b_id = seed_test_user("user_b@test.com", "password")

    # User A creates trilogy
    trilogy_a_id = seed_trilogy(user_a_id, "User A's Trilogy")

    # User B tries to access User A's trilogy
    # This should return empty due to RLS
    response = supabase_client.auth.sign_in(email="user_b@test.com", password="password")
    result = supabase_client.table("trilogy_projects").select("*").eq("id", trilogy_a_id).execute()

    assert len(result.data) == 0, "User B should not see User A's trilogy"
```

## Fixtures (conftest.py)

### Database Fixtures

```python
@pytest.fixture(scope="function")
def test_db():
    """Provides a clean test database for each test"""
    # Setup: Create test database
    db_url = create_test_database()
    run_migrations(db_url)

    yield db_url

    # Teardown: Drop test database
    drop_test_database(db_url)

@pytest.fixture
def supabase_client(test_db):
    """Supabase client connected to test database"""
    return create_client(test_db, "test-key")
```

### Authentication Fixtures

```python
@pytest.fixture
async def test_user(supabase_client):
    """Creates a test user and returns credentials"""
    from tests.test_data_seeds import seed_test_user
    user_id = seed_test_user("test@example.com", "TestPass123!")
    yield {"user_id": user_id, "email": "test@example.com", "password": "TestPass123!"}
    cleanup_test_user(user_id)

@pytest.fixture
async def auth_token(test_user, supabase_client):
    """Returns auth token for test user"""
    response = supabase_client.auth.sign_in(
        email=test_user["email"],
        password=test_user["password"]
    )
    return response.session.access_token
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run by Category
```bash
# Fast unit tests only
pytest tests/unit -v

# Integration tests
pytest tests/integration -v -m integration

# RLS tests only (CRITICAL)
pytest -m rls -v

# Slow tests
pytest -m slow -v --timeout=60
```

### Run with Coverage
```bash
# Generate HTML coverage report
pytest --cov=api --cov-report=html

# Open coverage report
open htmlcov/index.html
```

### Run in Parallel
```bash
# Run tests in parallel (faster)
pytest -n auto
```

## Coverage Goals

Based on testing strategy:

| Component | Target Coverage | Priority |
|-----------|----------------|----------|
| Auth Service | 95%+ | CRITICAL |
| RLS Policies | 100% | CRITICAL |
| Trilogy Manager | 90%+ | HIGH |
| Character Service | 90%+ | HIGH |
| World Rules | 90%+ | HIGH |
| RAG Service | 85%+ | MEDIUM |
| API Routes | 90%+ | HIGH |

## Writing New Tests

### Template for Unit Test

```python
import pytest
from api.services.your_service import YourService

class TestYourService:
    @pytest.mark.unit
    def test_function_does_something(self):
        service = YourService()
        result = service.do_something("input")
        assert result == "expected"

    @pytest.mark.unit
    def test_function_raises_error_on_invalid_input(self):
        service = YourService()
        with pytest.raises(ValueError):
            service.do_something(None)
```

### Template for Integration Test

```python
import pytest
from httpx import AsyncClient
from api.main import app

@pytest.mark.integration
@pytest.mark.asyncio
async def test_endpoint(test_db, auth_token):
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/endpoint",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert "expected_key" in response.json()
```

## Next Steps

1. **Create conftest.py** - Set up shared fixtures
2. **Create test_data_seeds.py** - Implement seeding utilities
3. **Write Unit Tests** - Start with auth and trilogy services
4. **Write RLS Tests** - CRITICAL for security
5. **Write Integration Tests** - Test API endpoints
6. **Set up CI/CD** - Automate test runs

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [httpx](https://www.python-httpx.org/)
- [Testing FastAPI](https://fastapi.tiangolo.com/tutorial/testing/)

---

**Last Updated:** January 21, 2025
**Status:** Foundation created, tests TODO
