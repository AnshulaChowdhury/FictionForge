# Docker Setup for Consciousness Trilogy App

Complete Docker containerization for the Consciousness Trilogy App, including FastAPI backend, ChromaDB, and Redis.

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Services](#services)
- [Environment Variables](#environment-variables)
- [Volume Management](#volume-management)
- [Running Tests](#running-tests)
- [Troubleshooting](#troubleshooting)

---

## Overview

The Docker setup includes three containerized services:

1. **API** - FastAPI backend with sentence-transformers
2. **ChromaDB** - Vector database for embeddings
3. **Redis** - Caching layer for character context and world rules

## Prerequisites

- Docker Desktop (Mac/Windows) or Docker Engine (Linux)
- Docker Compose v2.0+
- 8GB+ RAM available for Docker
- External SSD (optional, for larger ChromaDB datasets)

### Installation

**macOS:**
```bash
brew install --cask docker
```

**Linux:**
```bash
# Install Docker Engine
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

---

## Quick Start

### 1. Configure Environment Variables

The API service reads environment variables from your `.env` file. Ensure you have:

```bash
# api/.env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
AWS_API_GATEWAY_URL=https://your-api-id.execute-api.ca-central-1.amazonaws.com/prod/generate
SECRET_KEY=your-secret-key-here
```

### 2. Start All Services

```bash
# From project root
docker-compose up -d
```

This starts:
- API on `http://localhost:8000`
- ChromaDB on `http://localhost:8001`
- Redis on `localhost:6379`

### 3. Verify Services

```bash
# Check all services are running
docker-compose ps

# Check API health
curl http://localhost:8000/health

# Check API logs
docker-compose logs -f api
```

### 4. Stop Services

```bash
# Stop and remove containers (keeps data volumes)
docker-compose down

# Stop, remove containers AND delete data volumes
docker-compose down -v
```

---

## Services

### API Service (FastAPI Backend)

**Container Name:** `consciousness-trilogy-api`
**Port:** `8000`
**Health Check:** `http://localhost:8000/health`

**Features:**
- FastAPI with automatic OpenAPI docs
- Sentence-transformers (all-MiniLM-L6-v2)
- Hot reload for development
- Persistent embedding model cache

**Logs:**
```bash
docker-compose logs -f api
```

**Exec into container:**
```bash
docker-compose exec api bash
```

### ChromaDB Service (Vector Database)

**Container Name:** `consciousness-trilogy-chromadb`
**Port:** `8001` (mapped from internal `8000`)
**Health Check:** `http://localhost:8001/api/v1/heartbeat`

**Features:**
- Persistent vector storage
- DuckDB+Parquet backend
- Automatic collection management

**Logs:**
```bash
docker-compose logs -f chromadb
```

**Data Location:**
- Container: `/chroma/chroma`
- Volume: `consciousness-trilogy-chromadb-data`

### Redis Service (Cache)

**Container Name:** `consciousness-trilogy-redis`
**Port:** `6379`
**Health Check:** `redis-cli ping`

**Features:**
- 256MB max memory with LRU eviction
- AOF persistence enabled
- Optimized for caching character context and world rules

**Logs:**
```bash
docker-compose logs -f redis
```

**Connect to Redis CLI:**
```bash
docker-compose exec redis redis-cli
```

---

## Environment Variables

### Required Variables

These **must** be set in `api/.env`:

| Variable | Description | Example |
|----------|-------------|---------|
| `SUPABASE_URL` | Supabase project URL | `https://xxx.supabase.co` |
| `SUPABASE_ANON_KEY` | Supabase anon key | `eyJhbGciOiJIUzI1NiI...` |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key | `eyJhbGciOiJIUzI1NiI...` |
| `AWS_API_GATEWAY_URL` | AWS Bedrock API Gateway URL | `https://xxx.amazonaws.com/prod/generate` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `True` | Enable debug mode |
| `API_HOST` | `0.0.0.0` | API bind address |
| `API_PORT` | `8000` | API port |
| `REDIS_TTL_SECONDS` | `900` | Cache TTL (15 minutes) |
| `SECRET_KEY` | (generated) | JWT secret key |

---

## Volume Management

### Named Volumes

Docker Compose creates three named volumes for data persistence:

```bash
# List volumes
docker volume ls | grep consciousness-trilogy

# Inspect a volume
docker volume inspect consciousness-trilogy-chromadb-data

# Backup a volume (example)
docker run --rm -v consciousness-trilogy-chromadb-data:/data -v $(pwd):/backup alpine tar czf /backup/chromadb-backup.tar.gz -C /data .

# Restore a volume (example)
docker run --rm -v consciousness-trilogy-chromadb-data:/data -v $(pwd):/backup alpine tar xzf /backup/chromadb-backup.tar.gz -C /data
```

### Using External SSD (Optional)

To use an external SSD for ChromaDB data:

1. Edit `docker-compose.yml`
2. Uncomment the external mount:

```yaml
volumes:
  - /Volumes/T7/NovelApp/chromadb_data:/app/chromadb_data
```

3. Restart services:

```bash
docker-compose down
docker-compose up -d
```

---

## Running Tests

### Run Tests in Docker

```bash
# Run all tests
docker-compose exec api pytest

# Run with coverage
docker-compose exec api pytest --cov=services --cov-report=html

# Run specific test file
docker-compose exec api pytest tests/unit/test_embedding_service_pytest.py

# Run Epic 9 tests only
docker-compose exec api pytest -v tests/unit/test_embedding_service_pytest.py tests/unit/test_chromadb_client.py tests/integration/test_epic9_rag_integration.py
```

### Run Interactive Test Script

```bash
docker-compose exec api python tests/unit/test_epic9_embedding_service.py
```

---

## Development Workflow

### Hot Reload

The API service is configured with volume mounts for hot reload:

```yaml
volumes:
  - ./api:/app  # Code changes reload automatically
```

**Edit code locally → Changes reflect immediately in container**

### Rebuild After Dependency Changes

If you update `requirements.txt`:

```bash
# Rebuild API container
docker-compose build api

# Restart with new image
docker-compose up -d api
```

### View Real-Time Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail=100 api
```

---

## Troubleshooting

### Issue: API Container Keeps Restarting

**Check logs:**
```bash
docker-compose logs api
```

**Common causes:**
- Missing environment variables → Check `api/.env`
- Port conflict → Change port mapping in `docker-compose.yml`
- Memory limits → Increase Docker Desktop memory allocation

### Issue: ChromaDB Connection Failed

**Verify ChromaDB is running:**
```bash
docker-compose ps chromadb
curl http://localhost:8001/api/v1/heartbeat
```

**Restart ChromaDB:**
```bash
docker-compose restart chromadb
```

### Issue: Embedding Model Download Fails

The embedding model (~80MB) downloads on first run. If it fails:

```bash
# Exec into container
docker-compose exec api bash

# Manually download model
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

### Issue: Out of Memory

Docker Desktop default is 2GB RAM, but this app needs ~4GB:

1. Open Docker Desktop Settings
2. Resources → Memory → Set to 4GB+
3. Apply & Restart

### Issue: Permission Denied on Volumes

**Linux only:**

```bash
# Fix volume permissions
sudo chown -R $USER:$USER /var/lib/docker/volumes/consciousness-trilogy-*

# Or run with correct user in docker-compose.yml
user: "${UID}:${GID}"
```

### Issue: Redis Connection Refused

```bash
# Check Redis is running
docker-compose exec redis redis-cli ping

# Should return: PONG

# If fails, restart Redis
docker-compose restart redis
```

---

## Production Deployment

### Build Production Images

```bash
# Build optimized production image
docker build -f api/Dockerfile --target=production -t consciousness-trilogy-api:latest ./api

# Push to registry (example)
docker tag consciousness-trilogy-api:latest your-registry/consciousness-trilogy-api:v1.0.0
docker push your-registry/consciousness-trilogy-api:v1.0.0
```

### Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  api:
    image: your-registry/consciousness-trilogy-api:v1.0.0
    restart: always
    environment:
      - DEBUG=False
      - ENVIRONMENT=production
    # ... other production settings
```

Run with:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

---

## Useful Commands

```bash
# Start services
docker-compose up -d

# Stop services (keep data)
docker-compose down

# Stop services (delete data)
docker-compose down -v

# Restart a service
docker-compose restart api

# View logs
docker-compose logs -f

# Exec into container
docker-compose exec api bash

# Check service status
docker-compose ps

# View resource usage
docker stats

# Rebuild and restart
docker-compose up -d --build

# Pull latest images
docker-compose pull

# Remove unused images
docker system prune -a
```

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────┐
│  Host Machine (Mac/Linux/Windows)                        │
│                                                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Docker Network: consciousness-trilogy-network     │  │
│  │                                                     │  │
│  │  ┌─────────────────┐     ┌──────────────────┐     │  │
│  │  │  API Container  │────▶│  Redis Container │     │  │
│  │  │  Port: 8000     │     │  Port: 6379      │     │  │
│  │  └────────┬────────┘     └──────────────────┘     │  │
│  │           │                                        │  │
│  │           │                                        │  │
│  │           ▼                                        │  │
│  │  ┌──────────────────┐                             │  │
│  │  │ChromaDB Container│                             │  │
│  │  │  Port: 8001      │                             │  │
│  │  └──────────────────┘                             │  │
│  └────────────────────────────────────────────────────┘  │
│                                                           │
│  Volumes:                                                 │
│  • consciousness-trilogy-redis-data                       │
│  • consciousness-trilogy-chromadb-data                    │
│  • consciousness-trilogy-embedding-cache                  │
└──────────────────────────────────────────────────────────┘
```

---

## Support

For issues or questions:
1. Check logs: `docker-compose logs -f`
2. Check GitHub Issues
3. Verify environment variables in `api/.env`
4. Ensure Docker has sufficient resources (4GB+ RAM)

---

**Last Updated:** November 2025
**Epic:** 9 - Infrastructure & Deployment
**Status:** Production Ready
