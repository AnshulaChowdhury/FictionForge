# Dockerfile for Consciousness Trilogy App - FastAPI Backend
# Multi-stage build for optimized production image

# ============================================================================
# Stage 1: Builder - Install dependencies and download models
# ============================================================================
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies needed for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies to a local directory
RUN pip install --no-cache-dir --user -r requirements.txt

# Pre-download the sentence-transformers model to cache it
# This reduces startup time and ensures the model is available
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# ============================================================================
# Stage 2: Runtime - Minimal production image
# ============================================================================
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime system dependencies (minimal)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local
COPY --from=builder /root/.cache /root/.cache

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code to /app/api to maintain module structure
COPY . /app/api

# Create necessary directories
RUN mkdir -p /app/chromadb_data /app/models/embeddings

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    EMBEDDING_MODEL=all-MiniLM-L6-v2 \
    EMBEDDING_CACHE_DIR=/root/.cache/torch/sentence_transformers

# Expose the port FastAPI runs on
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application with uvicorn
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
