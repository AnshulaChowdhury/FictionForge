# Scripts

Utility scripts for development, testing, and debugging.

## Usage

All scripts should be run from the project root directory.

### Application Scripts

| Script | Description | Usage |
|--------|-------------|-------|
| `start` | Start the full stack (Backend + Frontend) | `./scripts/start` |
| `start --down` | Stop all Docker services | `./scripts/start --down` |
| `test` | Run backend tests | `./scripts/test` |

### Test Options

```bash
./scripts/test              # Run all backend tests
./scripts/test unit         # Run only unit tests
./scripts/test integration  # Run only integration tests
./scripts/test coverage     # Run with coverage report
./scripts/test e2e          # Run all frontend e2e tests
./scripts/test e2e --ui     # Run e2e tests with Playwright UI
```

### Debug Scripts

| Script | Description | Usage |
|--------|-------------|-------|
| `check_chromadb_embeddings.py` | Inspect character/world-rule embeddings in ChromaDB | `python scripts/check_chromadb_embeddings.py <trilogy_id>` |
| `check_redis_queue.py` | Monitor Redis cache and Arq job queue status | `python scripts/check_redis_queue.py` |
