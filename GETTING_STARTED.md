# FictionForge

An AI-assisted novel writing application designed to help authors write complex, multi-character science fiction trilogies using character-specific RAG (Retrieval Augmented Generation) and world-building rule enforcement.
Test

## Project Overview

The FictionForge is a specialized writing assistant that combines traditional novel management tools with advanced AI capabilities to maintain consistency across:
- **3 books** in a trilogy
- **Multiple character perspectives** with distinct voices
- **Complex world-building rules** (physics, technology, consciousness mechanics)
- **300+ sub-chapters** generated with AI assistance

### Key Innovation: Character-Specific RAG

Unlike generic AI writing tools, this app maintains **separate vector embeddings for each character**, ensuring that:
- Each character's voice and perspective remains consistent across the trilogy
- Generated content reflects character-specific knowledge, experiences, and personality
- World rules are automatically applied based on the current book and scene context

---

## Architecture at a Glance

```
┌─────────────────────────────────────────────────────────┐
│  React Frontend (Vite + TypeScript)                     │
│  Real-time WebSocket progress tracking                  │
└──────────────────┬──────────────────────────────────────┘
                   │ REST API + WebSocket
┌──────────────────▼──────────────────────────────────────┐
│  FastAPI Backend (Python 3.11+)                         │
│  • Character RAG Generator                              │
│  • World Rule RAG Provider                              │
│  • Async Job Processing (pg-boss)                       │
└──┬────┬─────┬──────┬───────┬────────────────────────────┘
   │    │     │      │       │
   │    │     │      │       └──► AWS Lambda + Bedrock
   │    │     │      │            (Mistral 7B Instruct)
   │    │     │      │
   │    │     │      └──► Redis Cache
   │    │     │           (15-min TTL for context)
   │    │     │
   │    │     └──► ChromaDB (External SSD)
   │    │          • Character-specific collections
   │    │          • World rule embeddings
   │    │
   │    └──► sentence-transformers
   │         (Local embeddings: all-MiniLM-L6-v2)
   │
   └──► Supabase (PostgreSQL)
        • User authentication (JWT + RLS)
        • Structured data persistence
        • Row-Level Security for multi-tenancy
```

---

## Technology Stack

### Frontend
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite (fast HMR, optimized builds)
- **State Management**: Zustand + React Query
- **UI Components**: Radix UI + Tailwind CSS
- **Real-time**: Native WebSocket API
- **Type Safety**: OpenAPI → TypeScript code generation

### Backend
- **Framework**: FastAPI (async Python)
- **Runtime**: Python 3.11+ with uvicorn
- **Job Queue**: pg-boss (async processing)
- **API Documentation**: Auto-generated OpenAPI/Swagger

### Data Layer
- **Relational DB**: Supabase (PostgreSQL with RLS)
- **Vector DB**: ChromaDB (self-hosted, persisted to external SSD)
- **Cache**: Redis (15-minute TTL for hot data)
- **Authentication**: Supabase Auth (JWT tokens)

### AI/ML
- **LLM**: AWS Bedrock (Mistral 7B Instruct via Lambda + API Gateway)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2, 384 dimensions)
- **RAG**: Custom implementation with dual context (character + world rules)

### Development
- **Version Control**: Git + GitHub
- **Containerization**: Docker + Docker Compose
- **Testing**: pytest (backend), Playwright (E2E)
- **Code Quality**: Black, Ruff, ESLint, Prettier

---

## Project Structure

```
NovelApp/
├── api/                          # FastAPI Backend
│   ├── routes/                   # API endpoints
│   │   ├── auth.py              # Authentication
│   │   ├── trilogy.py           # Trilogy/book/chapter CRUD
│   │   ├── characters.py        # Character management
│   │   ├── world_rules.py       # World building rules
│   │   └── generation.py        # Content generation
│   ├── services/                 # Business logic
│   │   ├── character_rag_generator.py
│   │   ├── world_rule_rag_provider.py
│   │   ├── bedrock_client.py    # AWS Lambda client
│   │   ├── embedding_service.py # Local embeddings
│   │   └── job_processor.py     # Async job orchestration
│   ├── models/                   # Pydantic data models
│   ├── websockets/               # WebSocket connection manager
│   ├── middleware/               # Auth, CORS, logging
│   └── tests/                    # Unit & integration tests
│
├── frontend/                     # React Frontend
│   ├── src/
│   │   ├── api/                 # API client + React Query hooks
│   │   ├── components/          # React components
│   │   ├── pages/               # Route pages
│   │   ├── hooks/               # Custom hooks (WebSocket, auth)
│   │   ├── stores/              # Zustand state stores
│   │   └── lib/                 # Utilities, validation
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── requirements_docs/            # Epic documentation & specs
│   ├── User Stories/            # Epic-by-epic requirements
│   ├── Database/                # ERD and schema docs
│   └── QA/                      # Testing strategy
│
├── docker-compose.yml           # Local development services
├── .env.example                 # Environment variable template
└── README.md                    # This file
```

---

## Feature Roadmap (Epics)

### Epic 0: User Management & Authentication
- User registration and login
- JWT-based authentication
- Row-Level Security (RLS) for data isolation
- **Status**: Foundation for all other epics

### Epic 1: Project Foundation & Setup
- Create trilogy projects (title, author, description)
- Automatically create 3 books with metadata
- Transaction-wrapped operations for data consistency
- **Deliverable**: Basic project structure in database

### Epic 2: Character Management
- Create/edit character profiles
- Define character arcs across trilogy
- Consciousness themes and personality traits
- **Integration**: Character data feeds Epic 5 RAG system

### Epic 3: World Building & Rules Engine
- Define world rules (physics, technology, magic systems)
- Categorize rules (e.g., "Quantum Consciousness", "AI Ethics")
- Associate rules with specific books (Book 1 only, Books 2-3, etc.)
- Track rule violations and accuracy metrics
- **Deliverable**: Consistency checking system

### Epic 4: Chapter Planning & Management
- Define chapters with plot summaries
- Associate chapters with character POV
- Track chapter word count targets
- Organize chapter flow and structure

### Epic 5A: Character-Specific RAG (Content Generation)
- Embed character profiles into ChromaDB
- Retrieve character-specific context for generation
- Generate sub-chapter content with character voice consistency
- **Innovation**: Each character gets their own vector store

### Epic 5B: World Rule RAG (Content Generation)
- Embed world rules into ChromaDB
- Retrieve relevant rules during generation
- Apply rules automatically to generation prompts
- Track which rules were used per generation
- **Integration**: Combines with Epic 5A for comprehensive context

### Epic 6: Sub-Chapter Management System
- Break chapters into sub-chapters (scenes)
- Define plot points for each sub-chapter
- Real-time generation progress tracking (WebSocket)
- Regenerate sub-chapters with different parameters

### Epic 7: Version Control & Content Management
- Save multiple versions of each sub-chapter
- Compare versions side-by-side with diff view
- Restore previous versions
- Track change descriptions and metadata

### Epic 9: Architecture & Infrastructure
- React + FastAPI architecture
- AWS Lambda + Bedrock integration
- WebSocket real-time communication
- Type-safe API contracts (OpenAPI → TypeScript)

### Epic 10: Job Queue & Progress Monitoring
- Async job processing with pg-boss
- Real-time progress updates via WebSocket
- Generation queue management
- Error handling and retry logic

---

## Key Features

### 1. Character Voice Consistency
Each character has a dedicated ChromaDB collection containing:
- Character profile and personality traits
- Consciousness themes and philosophical views
- Previously generated content from that character's POV

When generating new content, the system retrieves similar passages to maintain voice consistency.

### 2. World Rule Enforcement
World rules are semantically indexed and automatically retrieved based on:
- Similarity to the current writing prompt
- Book applicability (rules can apply to specific books)
- Historical accuracy (rules with low adherence rates are weighted down)

### 3. Real-Time Generation Tracking
WebSocket-based progress updates show:
- Current generation stage (context retrieval, rule lookup, LLM generation)
- Percentage completion
- Estimated time remaining
- Error messages with retry options

### 4. Dual Context RAG
Every generation combines TWO RAG contexts:
1. **Character Context**: Voice, personality, previous content
2. **World Rules Context**: Applicable physics/technology constraints

This ensures both character consistency AND world-building consistency.

### 5. Learning Loop
The system tracks:
- Which rules are violated most often
- Which rules prevent violations when included in prompts
- Which rules are frequently dismissed as "intentional breaks"

This feedback improves future rule selection and accuracy.

---

## Database Schema Highlights

### Core Tables
- `trilogy_projects` - Top-level trilogy metadata
- `books` - 3 books per trilogy (auto-created)
- `chapters` - Chapter definitions with plot summaries
- `sub_chapters` - Scene-level content units
- `sub_chapter_versions` - Version history for each sub-chapter

### Character System
- `characters` - Character profiles and arcs
- `character_vector_stores` - Metadata tracking ChromaDB collections
- `character_consciousness_themes` - Many-to-many character themes

### World Building
- `world_rules` - Physics, technology, magic system rules
- `world_rule_books` - Junction table (which rules apply to which books)
- `world_rule_embeddings` - Embedding status tracking
- `world_rule_violations` - Violation tracking for learning loop

### Generation System
- `generation_jobs` - Async job queue tracking
- `sub_chapter_generation_metadata` - Records which rules/context were used

**Row-Level Security (RLS)**: All user-facing tables enforce RLS to ensure users can only access their own trilogies.

---

## Development Setup

### Prerequisites
- **Hardware**: 8GB+ RAM, external SSD recommended for ChromaDB
- **Software**:
  - Python 3.11+
  - Node.js 20+ (LTS)
  - Docker Desktop
  - Git

### Environment Variables

Create `.env` files in both `api/` and `frontend/` directories:

**Backend (`api/.env`):**
```bash
# API
API_HOST=0.0.0.0
API_PORT=8000
FRONTEND_URL=http://localhost:5173

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-key
SUPABASE_ANON_KEY=your-anon-key

# ChromaDB
CHROMADB_PERSIST_DIR=/Volumes/ExternalSSD/chromadb
CHROMADB_HOST=localhost
CHROMADB_PORT=8000

# Redis
REDIS_URL=redis://localhost:6379

# AWS Bedrock
AWS_API_GATEWAY_URL=https://your-api.execute-api.ca-central-1.amazonaws.com/prod/generate
AWS_REGION=ca-central-1

# Embeddings
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

**Frontend (`frontend/.env`):**
```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

### Installation

```bash
# 1. Clone repository
git clone <repo-url>
cd NovelApp

# 2. Backend setup
cd api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Frontend setup
cd ../frontend
npm install

# 4. Start services (Redis, ChromaDB)
docker-compose up -d

# 5. Initialize database
cd ../api
python scripts/init_db.py
```

### Running the App

**Quick Start (Recommended):**
```bash
# Start backend server
./start

# Run tests
./test              # All tests
./test unit         # Unit tests only
./test integration  # Integration tests only
./test coverage     # With coverage report
```

**Manual Start - Backend:**
```bash
# From project root
source venv/bin/activate
./venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Manual Start - Frontend (Coming Soon):**
```bash
cd frontend
npm run dev
# Visit http://localhost:5173
```

**Services (Future Epics):**
```bash
docker-compose up
# Redis: localhost:6379
# ChromaDB: localhost:8000
```

---

## API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Key Endpoints

**Authentication:**
- `POST /auth/register` - Create new user
- `POST /auth/login` - Login and get JWT token
- `POST /auth/refresh` - Refresh expired token

**Trilogy Management:**
- `POST /api/trilogy` - Create new trilogy (auto-creates 3 books)
- `GET /api/trilogy` - List user's trilogies
- `GET /api/trilogy/{id}` - Get trilogy details

**Character Management:**
- `POST /api/characters` - Create character
- `GET /api/characters/{trilogy_id}` - List characters
- `PUT /api/characters/{id}` - Update character

**Content Generation:**
- `POST /api/generation/generate` - Submit generation job (returns job_id)
- `WS /ws/{job_id}` - WebSocket for real-time progress
- `GET /api/jobs/{job_id}` - Poll job status (alternative to WebSocket)

---

## Testing Strategy

### Unit Tests (70% of test suite)
- Service layer business logic
- RAG retrieval functions
- Embedding generation
- Utility functions

**Run:**
```bash
cd api
pytest tests/unit -v
```

### Integration Tests (25% of test suite)
- API endpoint testing with testcontainers
- ChromaDB integration
- Redis caching behavior
- Row-Level Security validation (CRITICAL)

**Run:**
```bash
cd api
pytest tests/integration -v -m integration
```

### E2E Tests (5% of test suite, optional)
- Critical user flows only (Playwright)
- Registration → Login → Create Trilogy → Generate Content

**Run:**
```bash
cd frontend
npm run test:e2e
```

### Coverage Goals
| Component | Target | Priority |
|-----------|--------|----------|
| Auth Service | 95%+ | CRITICAL |
| RLS Policies | 100% | CRITICAL |
| Character RAG | 90%+ | HIGH |
| World Rules | 90%+ | HIGH |
| API Routes | 90%+ | HIGH |

---

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| API Response (CRUD) | <200ms | p95 latency |
| Character Context (cache hit) | <50ms | Redis lookup |
| Character Context (cache miss) | <500ms | ChromaDB query |
| World Rule Retrieval | <800ms | Including filters |
| Content Generation | <180s | AWS Lambda/Bedrock |
| WebSocket Latency | <100ms | Progress updates |
| Concurrent Generations | ≥3 | Without degradation |

### Memory Usage (8GB MacBook)
- FastAPI: ~300MB
- sentence-transformers: ~600MB
- ChromaDB: ~200MB
- Redis: ~100MB
- **Total Backend**: ~1.2GB (plenty of headroom!)

---

## Deployment

### Backend Options
- **Recommended**: Render, Railway, or Fly.io (Docker-based)
- **Alternative**: AWS ECS/Fargate (if already using AWS)
- **Budget**: ~$7-15/month for hobby tier

### Frontend Options
- **Recommended**: Vercel or Netlify (automatic builds from Git)
- **Free tier available** for personal projects

### Database
- **Supabase**: Already cloud-hosted (free tier: 500MB database, 1GB file storage)

### ChromaDB
- **Option 1**: Deploy alongside backend (Docker volume)
- **Option 2**: Use managed vector DB service (Pinecone, Weaviate)

---

## Cost Estimate

| Service | Monthly Cost |
|---------|-------------|
| Supabase (Free Tier) | $0 |
| AWS Bedrock (Mistral 7B) | <$1 (300 generations) |
| Backend Hosting (Render) | $7 |
| Frontend Hosting (Vercel) | $0 |
| Redis (Upstash free tier) | $0 |
| **Total** | **~$8/month** |

Note: AWS Bedrock cost is negligible (~$0.0014 per 2000-word generation).

---

## Contributing

This is currently a personal project, but contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

**Please ensure:**
- All tests pass (`pytest tests/`)
- Code is formatted (`black .` and `npm run format`)
- Type checks pass (`mypy api/` and `npm run type-check`)

---

## Security

### Authentication
- JWT tokens with 1-hour expiry
- Refresh tokens with 30-day expiry
- Row-Level Security (RLS) enforces data isolation

### API Security
- CORS restricted to frontend origin only
- Rate limiting on generation endpoints (10/hour per user)
- Input validation with Pydantic (backend) and Zod (frontend)

### Secrets Management
- Never commit `.env` files
- Use platform secret managers in production
- Service role keys never exposed to frontend

---

## Known Issues & Limitations

1. **Memory Constraints**: Embedding model requires ~600MB RAM. On 8GB machines, close unnecessary applications during development.
2. **Generation Time**: AWS Lambda cold start can add 5-10 seconds to first generation. Subsequent generations are faster.
3. **ChromaDB Scale**: Self-hosted ChromaDB suitable for <100K embeddings. For larger scale, consider managed vector DB.
4. **WebSocket Support**: Some corporate firewalls block WebSockets. Fallback to polling available via `/api/jobs/{id}` endpoint.

---

## Roadmap

### Phase 1 (Complete)
- [x] Architecture design
- [x] Epic documentation (0-10)
- [x] Database schema design
- [x] Testing strategy

### Phase 2 (Current - Weeks 1-2)
- [ ] Backend foundation (FastAPI + Supabase)
- [ ] Authentication and RLS
- [ ] Basic CRUD endpoints
- [ ] Frontend foundation (React + Vite)

### Phase 3 (Weeks 3-4)
- [ ] ChromaDB integration
- [ ] Embedding service (sentence-transformers)
- [ ] Character RAG implementation
- [ ] World Rule RAG implementation

### Phase 4 (Weeks 5-6)
- [ ] Content generation pipeline
- [ ] WebSocket progress tracking
- [ ] Job queue (pg-boss)
- [ ] AWS Lambda/Bedrock integration

### Phase 5 (Weeks 7-8)
- [ ] Version management
- [ ] Analytics dashboard
- [ ] Export functionality (DOCX, PDF)
- [ ] UI/UX polish

### Phase 6 (Weeks 9-10)
- [ ] Testing suite
- [ ] Security audit
- [ ] Performance optimization
- [ ] Production deployment

---

# Quick Start Guide - FictionForge

## Backend (Epic 1) - READY ✅

### Start the API Server

**Easy Way (Recommended):**
```bash
# Navigate to project root and run the start script
cd /Volumes/T7/NovelApp
./start
```

**Manual Way:**
```bash
# 1. Navigate to project root
cd /Volumes/T7/NovelApp

# 2. Activate virtual environment
source venv/bin/activate

# 3. Start the FastAPI server
cd api
python main.py
```

Server will start on **http://localhost:8000**

### Test the API

**Health Check:**
```bash
curl http://localhost:8000/health
```

**View API Documentation:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Run Tests

**Easy Way (Recommended):**
```bash
cd /Volumes/T7/NovelApp

# Run all tests
./test

# Run only unit tests
./test unit

# Run only integration tests
./test integration

# Run with coverage report
./test coverage
```

**Manual Way:**
```bash
cd /Volumes/T7/NovelApp/api

# Run all tests
../venv/bin/pytest tests -v

# Run only unit tests
../venv/bin/pytest tests/unit -v

# Run only integration tests
../venv/bin/pytest tests/integration -v

# Run with coverage report
../venv/bin/pytest tests -v --cov=api --cov-report=html
```

---

## Frontend (Epic 1) - PENDING 🔄

### Next Steps:
1. Create React + Vite project structure
2. Set up authentication with Supabase
3. Build trilogy creation form
4. Connect to backend API

Stay tuned for frontend implementation!

---

## Environment Variables

All configured in `/Volumes/T7/NovelApp/.env`:

| Variable | Description | Status |
|----------|-------------|--------|
| SUPABASE_URL | Supabase project URL | ✅ Configured |
| SUPABASE_ANON_KEY | Frontend public key | ✅ Configured |
| SUPABASE_SERVICE_ROLE_KEY | Backend service key | ✅ Configured |
| API_HOST | API server host | ✅ 0.0.0.0 |
| API_PORT | API server port | ✅ 8000 |
| FRONTEND_URL | Frontend URL (CORS) | ✅ http://localhost:5173 |

---

## Database Schema

Your Supabase database should have the following tables (from ERD):

**Epic 1 Tables**:
- ✅ `trilogy_projects` - Main trilogy metadata
- ✅ `books` - 3 books per trilogy (auto-created)

**Authentication**:
- ✅ `auth.users` - Managed by Supabase Auth
- ✅ `user_profiles` - User profile extension

**Row-Level Security (RLS)** is enforced on all user-facing tables.

---

## Testing Epic 1 End-to-End

### 1. Get JWT Token from Supabase

You'll need to authenticate a user to get a JWT token. You can do this via:

**Option A: Supabase Dashboard**
1. Go to Supabase Dashboard → Authentication → Users
2. Create a test user or use existing user
3. Copy the access token

**Option B: Supabase Auth API**
```bash
curl -X POST 'https://YOUR_PROJECT_REF.supabase.co/auth/v1/signup' \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "securepassword123"
  }'
```

### 2. Create a Trilogy

```bash
curl -X POST http://localhost:8000/api/trilogy/create \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My First Trilogy",
    "description": "A test trilogy",
    "author": "Test Author",
    "narrative_overview": "An epic journey"
  }'
```

### 3. List Your Trilogies

```bash
curl http://localhost:8000/api/trilogy \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 4. Get Specific Trilogy

```bash
curl http://localhost:8000/api/trilogy/{TRILOGY_ID} \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Development Workflow

### Before Starting Work
```bash
cd /Volumes/T7/NovelApp
source venv/bin/activate
```

### Code Formatting
```bash
cd api

# Format code with Black
../venv/bin/black .

# Lint with Ruff
../venv/bin/ruff check .

# Type check with mypy
../venv/bin/mypy .
```

### Making Changes

1. **Edit code** in `api/` directory
2. **Add tests** in `api/tests/`
3. **Run tests** to ensure nothing breaks
4. **Commit changes** to git

```bash
git add .
git commit -m "Your commit message"
git push origin main
```

---

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>
```

### Database Connection Issues
- Verify Supabase credentials in `.env`
- Check if Supabase project is active
- Ensure RLS policies allow service role access

### Import Errors
```bash
# Reinstall dependencies
cd /Volumes/T7/NovelApp
source venv/bin/activate
pip install -r api/requirements.txt
```

### Tests Failing
```bash
# Clear pytest cache
cd api
rm -rf .pytest_cache __pycache__

# Run tests again
../venv/bin/pytest tests -v
```

---
# Executable Scripts Guide

This project includes convenient bash scripts for common operations.

---

## 📜 Available Scripts

### `./start` - Start the Backend Server

**What it does:**
- Checks if virtual environment exists
- Checks if dependencies are installed (offers to install if missing)
- Checks if port 8000 is available (offers to kill conflicting process)
- Activates the virtual environment
- Starts the FastAPI server on http://localhost:8000

**Usage:**
```bash
cd /Volumes/T7/NovelApp
./start
```

**What you'll see:**
```
============================================================
FictionForge - Starting Backend Server
============================================================

→ Working directory: /Volumes/T7/NovelApp
✓ Virtual environment found
✓ API directory found
✓ Port 8000 is available

============================================================
Starting FastAPI Server
============================================================

→ Activating virtual environment...
→ Changing to API directory...
✓ Starting server...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Server will start on: http://localhost:8000
  API Documentation:    http://localhost:8000/docs
  Health Check:         http://localhost:8000/health

  Press Ctrl+C to stop the server
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**To stop the server:**
Press `Ctrl+C`

---

### `./test` - Run Tests

**What it does:**
- Checks if virtual environment exists
- Activates the virtual environment
- Runs the test suite based on the argument provided

**Usage:**
```bash
cd /Volumes/T7/NovelApp

# Run all tests (default)
./test

# Run only unit tests
./test unit

# Run only integration tests
./test integration

# Run tests with coverage report
./test coverage
```

**Examples:**

**All tests:**
```bash
./test
```
Output:
```
============================================================
FictionForge - Running Tests
============================================================

→ Working directory: /Volumes/T7/NovelApp
✓ Virtual environment found
→ Activating virtual environment...

============================================================
Running All Tests
============================================================

tests/unit/test_trilogy_manager.py::TestTrilogyManagerCreate::test_create_project_success PASSED
tests/unit/test_trilogy_manager.py::TestTrilogyManagerCreate::test_create_project_with_minimal_fields PASSED
...
======================== 20 passed in 1.50s ========================

✓ All tests passed!
```

**Unit tests only:**
```bash
./test unit
```

**Integration tests only:**
```bash
./test integration
```

**With coverage report:**
```bash
./test coverage
```
This generates an HTML coverage report at `api/htmlcov/index.html`

---

## 🛠️ Troubleshooting

### Scripts not executable?

Make them executable with:
```bash
chmod +x start test
```

### Virtual environment not found?

Create it first:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r api/requirements.txt
```

### Port 8000 already in use?

The `./start` script will detect this and offer to kill the conflicting process.

Or manually:
```bash
# Find process using port 8000
lsof -ti:8000

# Kill it
lsof -ti:8000 | xargs kill -9
```

### Dependencies not installed?

The `./start` script will detect this and offer to install them automatically.

Or manually:
```bash
source venv/bin/activate
pip install -r api/requirements.txt
```

---

## 🎯 Quick Workflow

### First Time Setup
```bash
cd /Volumes/T7/NovelApp

# Create virtual environment
python3 -m venv venv

# Install dependencies
source venv/bin/activate
pip install -r api/requirements.txt
```

### Daily Development
```bash
cd /Volumes/T7/NovelApp

# Start the server
./start

# In another terminal: Run tests
./test

# Or run specific test types
./test unit
./test integration
./test coverage
```

---

## 📁 Script Locations

```
/Volumes/T7/NovelApp/
├── start          # ← Server startup script
├── test           # ← Test runner script
├── api/           # Backend code
├── venv/          # Virtual environment
└── ...
```

---

## 💡 Tips

1. **Always start from project root**: Scripts are designed to run from `/Volumes/T7/NovelApp/`

2. **Check script output**: Both scripts provide colored output:
   - ✓ Green = Success
   - → Blue = Info/Progress
   - ⚠ Yellow = Warning
   - ✗ Red = Error

3. **Test before committing**: Always run `./test` before committing code

4. **Keep server running**: The `./start` script will keep the server running until you press Ctrl+C

5. **Multiple test runs**: You can run `./test` multiple times while the server is running in another terminal

---

## Support

- **Documentation**: See `ProgressNotes.md` for detailed information
- **API Docs**: http://localhost:8000/docs
- **GitHub Issues**: Create issues for bugs or features

---

**Last Updated**: November 3, 2025
**Epic 1 Backend Status**: ✅ COMPLETE AND TESTED


---

## License

This project is owned by Moonray Ventures - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- **FastAPI** for the excellent async Python framework
- **React** and **Vite** for the modern frontend stack
- **Supabase** for database and authentication infrastructure
- **ChromaDB** for vector storage
- **AWS Bedrock** for managed LLM access
- **sentence-transformers** for local embeddings

---

## Support

For questions, issues, or feature requests:
- Open an issue on GitHub
- Contact: Anshula Chowdhury at ac@moonray.ventures
- Documentation: See `requirements_docs/` for detailed epic specifications

---

**Built with ❤️ for authors writing complex science fiction trilogies**

Last Updated: 2025-11-03
