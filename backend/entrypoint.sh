#!/bin/bash
# =============================================================================
# EduMind Backend — Docker Entrypoint
# Runs migrations and optional seeding before starting the main process.
#
# Usage:
#   ./entrypoint.sh                     → run migrations + start uvicorn
#   ./entrypoint.sh celery              → run migrations + start celery worker
#   ./entrypoint.sh migrate             → run migrations only
#   ./entrypoint.sh seed                → run seed scripts only
# =============================================================================

set -e

echo "╔══════════════════════════════════════════════════════╗"
echo "║  EduMind Backend — Starting...                      ║"
echo "╚══════════════════════════════════════════════════════╝"

# ---------------------------------------------------------------------------
# Wait for PostgreSQL to be ready (belt-and-suspenders on top of healthcheck)
# ---------------------------------------------------------------------------
wait_for_postgres() {
    echo "⏳ Waiting for PostgreSQL..."
    local max_attempts=30
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if python -c "
from sqlalchemy import create_engine, text
from app.core.config import settings
engine = create_engine(settings.database_url)
with engine.connect() as conn:
    conn.execute(text('SELECT 1'))
" 2>/dev/null; then
            echo "✅ PostgreSQL is ready"
            return 0
        fi
        attempt=$((attempt + 1))
        echo "   attempt $attempt/$max_attempts..."
        sleep 2
    done
    echo "❌ PostgreSQL not available after $max_attempts attempts"
    exit 1
}

# ---------------------------------------------------------------------------
# Run Alembic migrations
# ---------------------------------------------------------------------------
run_migrations() {
    echo "🔄 Running Alembic migrations..."
    alembic upgrade head
    echo "✅ Migrations complete"
}

# ---------------------------------------------------------------------------
# Seed interest categories (idempotent — checks before inserting)
# ---------------------------------------------------------------------------
run_seed() {
    echo "🌱 Seeding interest categories..."
    python scripts/seed_interests.py || echo "⚠️  Seeding skipped (may already exist)"
    echo "✅ Seeding complete"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

# Skip DB wait for SQLite
if echo "$DATABASE_URL" | grep -q "postgresql"; then
    wait_for_postgres
fi

case "${1:-api}" in
    api)
        run_migrations
        echo "🚀 Starting FastAPI server..."
        exec uvicorn app.main:app \
            --host 0.0.0.0 \
            --port 8000 \
            --workers "${UVICORN_WORKERS:-4}" \
            --log-level "${LOG_LEVEL:-info}"
        ;;
    celery)
        # Migrations are handled by the API container — worker just starts
        echo "🔧 Starting Celery worker..."
        exec celery -A app.workers.celery_app:celery_app worker \
            --loglevel="${LOG_LEVEL:-info}" \
            --concurrency="${CELERY_CONCURRENCY:-2}" \
            --max-tasks-per-child=50 \
            --queues=default,ingestion
        ;;
    migrate)
        run_migrations
        ;;
    seed)
        run_seed
        ;;
    migrate-and-seed)
        run_migrations
        run_seed
        ;;
    *)
        exec "$@"
        ;;
esac
