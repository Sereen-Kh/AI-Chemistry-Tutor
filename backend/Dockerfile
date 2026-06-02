# =============================================================================
# EduMind Backend — Production Dockerfile
# Multi-stage build: deps layer (cached) → app layer (fast rebuild)
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Base image with system dependencies
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS base

# Prevent Python from buffering stdout/stderr (important for Docker logging)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System packages required by the backend:
#   - poppler-utils    → pdf2image (PDF page rendering)
#   - libpq-dev        → asyncpg / psycopg2 (PostgreSQL drivers)
#   - build-essential  → compile C extensions (bcrypt, etc.)
#   - libffi-dev       → cffi (python-jose cryptography)
#   - curl             → health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    libpq-dev \
    build-essential \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Stage 2: Install Python dependencies (cached unless requirements.txt changes)
# ---------------------------------------------------------------------------
FROM base AS deps

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 3: Final runtime image
# ---------------------------------------------------------------------------
FROM deps AS runtime

WORKDIR /app

# Copy application code
COPY . .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Create non-root user for security
RUN groupadd -r edumind && useradd -r -g edumind -d /app -s /sbin/nologin edumind \
    && mkdir -p /app/data/textbooks \
    && chown -R edumind:edumind /app

USER edumind

EXPOSE 8000

# Health check — hit the /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use entrypoint for startup orchestration (migrations, seeding, etc.)
ENTRYPOINT ["./entrypoint.sh"]

# Default mode: API server. Override with "celery" for worker.
CMD ["api"]
