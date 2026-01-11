# Testing Strategy for Consciousness Trilogy App
**Recommended Testing Stack & Implementation Guide**

---

## Executive Summary

**Recommended Core Stack:**
- **pytest** - Main testing framework (industry standard for Python)
- **pytest-asyncio** - Async test support for FastAPI
- **httpx** - HTTP client for API testing
- **testcontainers-python** - Real service integration (Supabase, Redis, ChromaDB)
- **pytest-cov** - Code coverage reporting
- **factory_boy** - Test data generation
- **playwright** - E2E testing (critical flows only)

**Why This Stack?**
- ✅ Handles async FastAPI code seamlessly
- ✅ Tests against real services (Supabase, Redis, ChromaDB) - critical for RLS validation
- ✅ Efficient for solo developer (minimal boilerplate)
- ✅ Professional-grade (demonstrates enterprise testing practices)
- ✅ CI/CD friendly (GitHub Actions, Docker)

---

## Testing Pyramid for Your Project

```
         /\
        /  \  E2E Tests (Playwright)
       /____\ ~5% - Critical user flows only
      /      \
     / INTEG  \ Integration Tests (testcontainers)
    /  TESTS  \ ~25% - API + DB + Services
   /__________\
  /            \
 /  UNIT TESTS \ Unit Tests (pytest)
/_______________\ ~70% - Business logic, services
```

---

## 1. Core Testing Tools

### 1.1 pytest (Main Framework)

**Installation:**
```bash
pip install pytest pytest-asyncio pytest-cov pytest-xdist
```

**Why pytest?**
- De facto standard for Python testing
- Excellent async support (critical for FastAPI)
- Rich plugin ecosystem
- Clean, readable test syntax
- Parallel test execution (pytest-xdist)

**Basic Configuration:**
```ini
# pytest.ini
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
    --cov=shared
    --cov-report=html
    --cov-report=term-missing
    --strict-markers
    -v
```

### 1.2 FastAPI Testing with httpx

**Installation:**
```bash
pip install httpx
```

**Why httpx over requests?**
- Native async support (FastAPI is async)
- Better for testing async endpoints
- Same API as requests (familiar)

**Example Test:**
```python
# tests/test_auth.py
import pytest
from httpx import AsyncClient
from api.main import app

@pytest.mark.asyncio
async def test_user_registration():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "SecurePass123!",
            "name": "Test User"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "test@example.com"
        assert "access_token" in data
```

### 1.3 testcontainers-python (Real Service Testing)

**Installation:**
```bash
pip install testcontainers[postgresql] testcontainers[redis]
```

**Why testcontainers over mocks?**
- ✅ Test against REAL Supabase/PostgreSQL (catches RLS bugs)
- ✅ Test against REAL Redis (cache behavior)
- ✅ Test against REAL ChromaDB (vector operations)
- ✅ No mocking brittleness - tests reflect production
- ✅ Critical for RLS validation (can't mock database policies)

**Example Setup:**
```python
# tests/conftest.py
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer
from supabase import create_client, Client

@pytest.fixture(scope="session")
def postgres_container():
    """Spin up PostgreSQL container for testing"""
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres

@pytest.fixture(scope="session")
def redis_container():
    """Spin up Redis container for testing"""
    with RedisContainer("redis:7-alpine") as redis:
        yield redis

@pytest.fixture(scope="function")
def test_db(postgres_container):
    """
    Create fresh database for each test with schema + RLS policies
    This ensures clean state and proper RLS testing
    """
    # Get connection string
    db_url = postgres_container.get_connection_url()
    
    # Run migrations (create tables, RLS policies)
    run_migrations(db_url)
    
    yield db_url
    
    # Cleanup happens automatically (container resets)

@pytest.fixture
def supabase_client(test_db) -> Client:
    """Create Supabase client connected to test database"""
    # Note: In real implementation, you'd configure Supabase 
    # to point at test_db or use supabase-py directly
    client = create_client(
        supabase_url=test_db,
        supabase_key="test-key"
    )
    return client
```

### 1.4 factory_boy (Test Data Generation)

**Installation:**
```bash
pip install factory_boy faker
```

**Why factory_boy?**
- Generates realistic test data
- Reduces boilerplate
- Easy to create complex object graphs
- Handles relationships automatically

**Example Factories:**
```python
# tests/factories.py
import factory
from factory import fuzzy
from datetime import datetime
import uuid

class UserFactory(factory.Factory):
    class Meta:
        model = dict
    
    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    email = factory.Faker('email')
    name = factory.Faker('name')
    created_at = factory.LazyFunction(datetime.now)

class TrilogyProjectFactory(factory.Factory):
    class Meta:
        model = dict
    
    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    user_id = factory.LazyAttribute(lambda o: str(uuid.uuid4()))
    title = factory.Faker('sentence', nb_words=4)
    description = factory.Faker('paragraph')
    author = factory.Faker('name')
    narrative_overview = factory.Faker('text', max_nb_chars=500)
    created_at = factory.LazyFunction(datetime.now)

class CharacterFactory(factory.Factory):
    class Meta:
        model = dict
    
    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    trilogy_id = factory.LazyAttribute(lambda o: str(uuid.uuid4()))
    name = factory.Faker('name')
    description = factory.Faker('paragraph')
    consciousness_themes = fuzzy.FuzzyChoice([
        ['quantum_consciousness', 'emergence'],
        ['ai_sentience', 'digital_souls'],
        ['hive_mind', 'collective_intelligence']
    ])

# Usage in tests:
def test_create_character():
    character_data = CharacterFactory.build()
    assert 'id' in character_data
    assert len(character_data['consciousness_themes']) > 0
```

---

## 2. RLS Testing Strategy (CRITICAL)

**Why RLS Testing is Essential:**
- User data isolation is your app's core security feature
- RLS bugs = data leaks between users
- Can't be tested with mocks - must use real PostgreSQL

### 2.1 RLS Test Fixtures

```python
# tests/test_rls.py
import pytest
from supabase import create_client

@pytest.fixture
def user_a_client(test_db):
    """Client authenticated as User A"""
    client = create_client(test_db, "anon-key")
    # Authenticate as User A
    response = client.auth.sign_up({
        "email": "user_a@test.com",
        "password": "password123"
    })
    return client

@pytest.fixture
def user_b_client(test_db):
    """Client authenticated as User B"""
    client = create_client(test_db, "anon-key")
    # Authenticate as User B
    response = client.auth.sign_up({
        "email": "user_b@test.com",
        "password": "password123"
    })
    return client

@pytest.mark.rls
class TestRowLevelSecurity:
    """Critical RLS test suite - must pass 100%"""
    
    def test_user_cannot_see_other_users_projects(
        self, user_a_client, user_b_client
    ):
        """Users A and B should only see their own projects"""
        # User A creates a project
        user_a_project = user_a_client.table("trilogy_projects").insert({
            "title": "User A's Trilogy",
            "author": "User A"
        }).execute()
        
        # User B creates a project
        user_b_project = user_b_client.table("trilogy_projects").insert({
            "title": "User B's Trilogy",
            "author": "User B"
        }).execute()
        
        # User A queries all projects
        user_a_projects = user_a_client.table("trilogy_projects").select("*").execute()
        
        # User A should only see their own project
        assert len(user_a_projects.data) == 1
        assert user_a_projects.data[0]["title"] == "User A's Trilogy"
        
        # User B should only see their own project
        user_b_projects = user_b_client.table("trilogy_projects").select("*").execute()
        assert len(user_b_projects.data) == 1
        assert user_b_projects.data[0]["title"] == "User B's Trilogy"
    
    def test_user_cannot_update_other_users_projects(
        self, user_a_client, user_b_client
    ):
        """User B cannot update User A's project"""
        # User A creates project
        project = user_a_client.table("trilogy_projects").insert({
            "title": "Original Title"
        }).execute()
        project_id = project.data[0]["id"]
        
        # User B attempts to update User A's project
        # This should fail silently (RLS blocks it)
        user_b_client.table("trilogy_projects").update({
            "title": "Hacked Title"
        }).eq("id", project_id).execute()
        
        # Verify project unchanged
        check = user_a_client.table("trilogy_projects").select("*").eq("id", project_id).execute()
        assert check.data[0]["title"] == "Original Title"
    
    def test_cascade_rls_to_child_tables(
        self, user_a_client, user_b_client
    ):
        """RLS should cascade from trilogy_projects to books, chapters, etc."""
        # User A creates trilogy → book → chapter
        trilogy = user_a_client.table("trilogy_projects").insert({
            "title": "Trilogy"
        }).execute()
        trilogy_id = trilogy.data[0]["id"]
        
        book = user_a_client.table("books").insert({
            "trilogy_id": trilogy_id,
            "book_number": 1,
            "title": "Book 1"
        }).execute()
        book_id = book.data[0]["id"]
        
        # User B should not see User A's books
        user_b_books = user_b_client.table("books").select("*").execute()
        assert len(user_b_books.data) == 0
        
        # User B should not see User A's books even with direct ID query
        user_b_book_query = user_b_client.table("books").select("*").eq("id", book_id).execute()
        assert len(user_b_book_query.data) == 0
```

### 2.2 RLS Performance Testing

```python
@pytest.mark.rls
@pytest.mark.slow
def test_rls_performance_with_many_users(test_db):
    """Ensure RLS doesn't slow down queries with many users"""
    import time
    
    # Create 100 users with 10 projects each
    for i in range(100):
        user = create_test_user(f"user_{i}@test.com")
        for j in range(10):
            create_project(user, f"Project {j}")
    
    # Time query for single user
    start = time.time()
    user_projects = query_user_projects(user_id="user_50")
    elapsed = time.time() - start
    
    # Should be fast even with 1000 total projects
    assert elapsed < 0.1  # 100ms max
    assert len(user_projects) == 10  # Only their 10 projects
```

---

## 3. Integration Testing

### 3.1 API Integration Tests

```python
# tests/integration/test_auth_flow.py
import pytest
from httpx import AsyncClient

@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_registration_login_flow(test_db):
    """Test full user journey: register → verify → login → access protected resource"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Step 1: Register
        reg_response = await client.post("/auth/register", json={
            "email": "integration@test.com",
            "password": "SecurePass123!",
            "name": "Integration Test"
        })
        assert reg_response.status_code == 200
        
        # Step 2: Verify email (simulate clicking verification link)
        # In real test, you'd intercept the email or use test endpoint
        verify_token = extract_verification_token(reg_response)
        verify_response = await client.get(f"/auth/verify?token={verify_token}")
        assert verify_response.status_code == 200
        
        # Step 3: Login
        login_response = await client.post("/auth/login", json={
            "email": "integration@test.com",
            "password": "SecurePass123!"
        })
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        
        # Step 4: Access protected resource
        headers = {"Authorization": f"Bearer {access_token}"}
        profile_response = await client.get("/auth/profile", headers=headers)
        assert profile_response.status_code == 200
        assert profile_response.json()["email"] == "integration@test.com"
```

### 3.2 ChromaDB Integration Tests

```python
# tests/integration/test_chromadb.py
import pytest
from chromadb import Client
from api.services.character_service import CharacterService

@pytest.mark.integration
def test_character_rag_retrieval(chromadb_container, test_db):
    """Test character-specific RAG with real ChromaDB"""
    # Setup
    character_service = CharacterService(
        chromadb_host=chromadb_container.get_container_host_ip(),
        chromadb_port=chromadb_container.get_exposed_port(8000)
    )
    
    # Create character
    character_id = "test-char-123"
    trilogy_id = "test-trilogy-456"
    
    # Add character content to ChromaDB
    character_service.add_character_content(
        trilogy_id=trilogy_id,
        character_id=character_id,
        content="Kira gazed at the Martian sunset, contemplating consciousness."
    )
    
    # Query for similar content
    results = character_service.query_character_context(
        trilogy_id=trilogy_id,
        character_id=character_id,
        query="What does Kira think about consciousness?",
        n_results=5
    )
    
    # Verify results
    assert len(results) > 0
    assert "consciousness" in results[0]["text"].lower()
```

---

## 4. E2E Testing (Selective)

**Philosophy:** E2E tests are expensive to write and maintain. Only test critical user journeys.

### 4.1 Playwright for E2E

**Installation:**
```bash
pip install playwright
playwright install chromium
```

**When to Use E2E:**
- ✅ Critical auth flows (registration → login → create project)
- ✅ Payment flows (if added later)
- ❌ NOT for every feature (too slow, brittle)

**Example E2E Test:**
```python
# tests/e2e/test_user_journey.py
import pytest
from playwright.async_api import async_playwright

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_new_user_creates_first_project():
    """E2E: New user registers and creates their first trilogy project"""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Navigate to app
        await page.goto("http://localhost:8501")
        
        # Click register tab
        await page.click("text=Register")
        
        # Fill registration form
        await page.fill("input[aria-label='Name']", "E2E Test User")
        await page.fill("input[aria-label='Email']", "e2e@test.com")
        await page.fill("input[aria-label='Password']", "SecurePass123!")
        await page.fill("input[aria-label='Confirm Password']", "SecurePass123!")
        
        # Submit
        await page.click("button:has-text('Register')")
        
        # Verify success message
        await page.wait_for_selector("text=Registration successful")
        
        # Skip email verification for test
        # (In real test, use test email service or backdoor)
        
        # Login
        await page.fill("input[aria-label='Email']", "e2e@test.com")
        await page.fill("input[aria-label='Password']", "SecurePass123!")
        await page.click("button:has-text('Login')")
        
        # Create project
        await page.wait_for_selector("text=Create New Trilogy")
        await page.click("button:has-text('Create New Trilogy')")
        await page.fill("input[aria-label='Title']", "My First Trilogy")
        await page.fill("textarea[aria-label='Description']", "A story about consciousness")
        await page.click("button:has-text('Create')")
        
        # Verify project created
        await page.wait_for_selector("text=My First Trilogy")
        
        await browser.close()
```

**Recommendation:** Start WITHOUT Playwright, add only if needed after core features work.

---

## 5. Test Organization

```
consciousness-trilogy-app/
├── tests/
│   ├── conftest.py              # Shared fixtures
│   ├── factories.py             # Test data factories
│   │
│   ├── unit/                    # 70% of tests
│   │   ├── test_auth_service.py
│   │   ├── test_character_service.py
│   │   ├── test_world_rules.py
│   │   └── test_rag_service.py
│   │
│   ├── integration/             # 25% of tests
│   │   ├── test_auth_flow.py
│   │   ├── test_rls_policies.py
│   │   ├── test_chromadb.py
│   │   ├── test_redis_cache.py
│   │   └── test_api_endpoints.py
│   │
│   ├── e2e/                     # 5% of tests (optional)
│   │   └── test_user_journey.py
│   │
│   └── performance/             # Optional
│       └── test_rag_performance.py
│
├── pytest.ini
├── .coveragerc
└── requirements-dev.txt
```

---

## 6. CI/CD Integration

### 6.1 GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python 3.11
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run migrations
      run: |
        python scripts/run_migrations.py
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
    
    - name: Run unit tests
      run: pytest tests/unit -v --cov
    
    - name: Run integration tests
      run: pytest tests/integration -v -m integration
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
        REDIS_URL: redis://localhost:6379
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        files: ./coverage.xml
```

---

## 7. Development Workflow

### 7.1 Running Tests Locally

```bash
# Run all tests
pytest

# Run only unit tests (fast)
pytest tests/unit -v

# Run integration tests (slower, needs Docker)
pytest tests/integration -v -m integration

# Run specific test file
pytest tests/unit/test_auth_service.py -v

# Run tests matching pattern
pytest -k "test_rls" -v

# Run with coverage report
pytest --cov=api --cov-report=html

# Run in parallel (faster)
pytest -n auto

# Run only RLS tests (critical)
pytest -m rls -v
```

### 7.2 Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-fast
        name: Run Fast Tests
        entry: pytest tests/unit -v
        language: system
        pass_filenames: false
        always_run: true
```

---

## 8. Required Packages

```txt
# requirements-dev.txt
# Testing Framework
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-xdist==3.5.0
pytest-mock==3.12.0

# HTTP Testing
httpx==0.25.2

# Service Testing
testcontainers==3.7.1
testcontainers[postgresql]==3.7.1
testcontainers[redis]==3.7.1

# Test Data
factory-boy==3.3.0
faker==20.1.0

# E2E Testing (optional)
playwright==1.40.0

# Code Quality
black==23.12.1
flake8==6.1.0
mypy==1.7.1
```

---

## 9. Testing Metrics & Goals

### 9.1 Coverage Goals

| Component | Target Coverage | Priority |
|-----------|----------------|----------|
| Auth Service | 95%+ | CRITICAL |
| RLS Policies | 100% | CRITICAL |
| Character Service | 90%+ | HIGH |
| World Rules | 90%+ | HIGH |
| RAG Service | 85%+ | MEDIUM |
| API Routes | 90%+ | HIGH |
| Utilities | 80%+ | MEDIUM |

### 9.2 Test Execution Time Targets

- **Unit tests:** < 10 seconds total
- **Integration tests:** < 2 minutes total
- **E2E tests:** < 5 minutes total (if used)
- **Full suite:** < 3 minutes total

### 9.3 Quality Gates

**Must pass before merge:**
- ✅ All tests pass
- ✅ >90% code coverage on new code
- ✅ All RLS tests pass (100%)
- ✅ No security vulnerabilities (Bandit)
- ✅ Code formatted (Black)
- ✅ Type hints valid (mypy)

---

## 10. Implementation Roadmap

### Phase 1: Foundation (Week 1)
1. ✅ Install pytest, pytest-asyncio, httpx
2. ✅ Create conftest.py with basic fixtures
3. ✅ Set up pytest.ini configuration
4. ✅ Write first unit test (auth_service.register_user)
5. ✅ Set up coverage reporting

### Phase 2: RLS Testing (Week 1-2)
6. ✅ Install testcontainers
7. ✅ Create PostgreSQL test fixture
8. ✅ Write RLS test suite (CRITICAL)
9. ✅ Verify all RLS policies with tests
10. ✅ Add RLS performance tests

### Phase 3: Integration Testing (Week 2-3)
11. ✅ Add Redis container fixture
12. ✅ Add ChromaDB container fixture
13. ✅ Write API integration tests
14. ✅ Write RAG integration tests
15. ✅ Add factory_boy for test data

### Phase 4: CI/CD (Week 3)
16. ✅ Set up GitHub Actions workflow
17. ✅ Configure coverage reporting (Codecov)
18. ✅ Add pre-commit hooks
19. ✅ Document testing process

### Phase 5: E2E (Optional, Week 4+)
20. ⚠️ Evaluate need for E2E tests
21. ⚠️ If needed, install Playwright
22. ⚠️ Write critical flow tests only

---

## 11. Alternative Testing Approaches

### If You Want Simpler Setup:

**Option B: Minimal Stack** (for rapid prototyping)
- pytest + httpx only
- Mock external services (Supabase, ChromaDB, Redis)
- Faster to start but less confidence in integration

**Pros:**
- ✅ Faster initial setup
- ✅ Tests run super fast
- ✅ No Docker required

**Cons:**
- ❌ Can't validate RLS properly (critical security risk)
- ❌ Mocks may not match real behavior
- ❌ Integration bugs found in production

**Recommendation:** Don't use Option B. RLS testing is too critical.

---

## 12. Example: Complete Test File

```python
# tests/integration/test_trilogy_workflow.py
"""
Integration test: Complete workflow from user registration to content generation
"""
import pytest
from httpx import AsyncClient
from tests.factories import UserFactory, TrilogyProjectFactory

@pytest.mark.integration
@pytest.mark.asyncio
class TestTrilogyWorkflow:
    """Test complete user workflow with real services"""
    
    async def test_user_creates_trilogy_with_characters_and_generates_content(
        self, test_db, chromadb_container, redis_container
    ):
        """
        Complete workflow:
        1. User registers
        2. User logs in
        3. User creates trilogy project
        4. User adds characters
        5. User creates chapter
        6. System generates sub-chapter content using RAG
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Step 1: Register
            user_data = UserFactory.build()
            reg_response = await client.post("/auth/register", json={
                "email": user_data["email"],
                "password": "TestPass123!",
                "name": user_data["name"]
            })
            assert reg_response.status_code == 200
            access_token = reg_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Step 2: Create trilogy
            trilogy_data = TrilogyProjectFactory.build()
            trilogy_response = await client.post(
                "/api/trilogies",
                json=trilogy_data,
                headers=headers
            )
            assert trilogy_response.status_code == 201
            trilogy_id = trilogy_response.json()["id"]
            
            # Step 3: Create character
            character_response = await client.post(
                f"/api/trilogies/{trilogy_id}/characters",
                json={
                    "name": "Kira Chen",
                    "description": "Mars colonist and quantum physicist",
                    "consciousness_themes": ["quantum_consciousness", "emergence"]
                },
                headers=headers
            )
            assert character_response.status_code == 201
            character_id = character_response.json()["id"]
            
            # Step 4: Create book
            book_response = await client.post(
                f"/api/trilogies/{trilogy_id}/books",
                json={
                    "book_number": 1,
                    "title": "Awakening",
                    "description": "The beginning of consciousness"
                },
                headers=headers
            )
            assert book_response.status_code == 201
            book_id = book_response.json()["id"]
            
            # Step 5: Create chapter
            chapter_response = await client.post(
                f"/api/books/{book_id}/chapters",
                json={
                    "chapter_number": 1,
                    "title": "First Contact",
                    "character_id": character_id,
                    "chapter_plot": "Kira discovers anomalous quantum readings"
                },
                headers=headers
            )
            assert chapter_response.status_code == 201
            chapter_id = chapter_response.json()["id"]
            
            # Step 6: Generate sub-chapter content (RAG)
            gen_response = await client.post(
                f"/api/chapters/{chapter_id}/sub-chapters/generate",
                json={
                    "title": "The Anomaly",
                    "plot_points": "Kira analyzes quantum data, discovers consciousness pattern",
                    "target_word_count": 2000
                },
                headers=headers
            )
            assert gen_response.status_code == 202  # Async job started
            job_id = gen_response.json()["job_id"]
            
            # Step 7: Poll for completion
            import asyncio
            for _ in range(30):  # Wait up to 30 seconds
                job_response = await client.get(
                    f"/api/jobs/{job_id}",
                    headers=headers
                )
                if job_response.json()["status"] == "completed":
                    break
                await asyncio.sleep(1)
            
            assert job_response.json()["status"] == "completed"
            sub_chapter_id = job_response.json()["result"]["sub_chapter_id"]
            
            # Step 8: Verify content created with character voice
            content_response = await client.get(
                f"/api/sub-chapters/{sub_chapter_id}",
                headers=headers
            )
            content = content_response.json()["content"]
            
            # Verify RAG worked (content mentions character name and themes)
            assert "Kira" in content or "quantum" in content
            assert len(content.split()) >= 1500  # Close to target word count
```

---

## Final Recommendation

**Start with this stack:**
```bash
pip install pytest pytest-asyncio pytest-cov httpx testcontainers factory-boy faker
```

**Test in this order:**
1. **Week 1:** Unit tests for Epic 0 (auth service, data models)
2. **Week 2:** RLS integration tests (CRITICAL - use testcontainers)
3. **Week 3:** API integration tests (full auth flows)
4. **Week 4+:** Service integration tests (ChromaDB, Redis, RAG)

**Skip for MVP:**
- E2E tests (add later if needed)
- Load/performance tests (add later)
- UI component tests (Streamlit not test-friendly)

**This gives you:**
- ✅ Professional testing setup
- ✅ Confidence in RLS security
- ✅ Fast feedback loop
- ✅ CI/CD ready
- ✅ Portfolio-worthy code quality

---

**Document Version:** 1.0  
**Last Updated:** October 26, 2025  
**Author:** Claude (Sonnet 4.5)
