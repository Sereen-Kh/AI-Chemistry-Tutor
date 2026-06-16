#!/usr/bin/env bash
set -u -o pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORT_DIR="$ROOT_DIR/reports/smoke"
LOG_DIR="$REPORT_DIR/logs/clean_db_migration_$(date -u +%Y%m%dT%H%M%SZ)"
CONTAINER_NAME="${CLEAN_DB_CONTAINER_NAME:-edumind-clean-migration-postgres}"
PORT="${CLEAN_DB_PORT:-55433}"
DB_URL="postgresql://edumind:edumind@127.0.0.1:${PORT}/edumind_migration_test"
if [ -x "$ROOT_DIR/backend/.venv/bin/python" ]; then
  PYTHON_BIN="$ROOT_DIR/backend/.venv/bin/python"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi
mkdir -p "$LOG_DIR"

cd "$ROOT_DIR" || exit 1

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker CLI is required for the disposable clean migration test."
  exit 1
fi

docker rm -f "$CONTAINER_NAME" >"$LOG_DIR/docker_rm_existing.log" 2>&1 || true

docker run -d --rm \
  --name "$CONTAINER_NAME" \
  -e POSTGRES_DB=edumind_migration_test \
  -e POSTGRES_USER=edumind \
  -e POSTGRES_PASSWORD=edumind \
  -p "${PORT}:5432" \
  pgvector/pgvector:pg16 >"$LOG_DIR/docker_run.log" 2>&1
started=$?

cleanup() {
  if [ "${KEEP_CLEAN_DB_CONTAINER:-0}" != "1" ]; then
    docker rm -f "$CONTAINER_NAME" >"$LOG_DIR/docker_cleanup.log" 2>&1 || true
  fi
}
trap cleanup EXIT

if [ "$started" -ne 0 ]; then
  echo "Failed to start disposable pgvector PostgreSQL container. See $LOG_DIR/docker_run.log"
  exit 1
fi

ready=0
for _ in $(seq 1 45); do
  if docker exec "$CONTAINER_NAME" pg_isready -U edumind -d edumind_migration_test >"$LOG_DIR/pg_isready.log" 2>&1; then
    ready=1
    break
  fi
  sleep 2
done

if [ "$ready" -ne 1 ]; then
  echo "Disposable PostgreSQL did not become ready. See $LOG_DIR/pg_isready.log"
  exit 1
fi

(
  cd "$ROOT_DIR/backend" || exit 1
  CLEAN_DATABASE_URL="$DB_URL" DATABASE_URL="$DB_URL" ASYNC_DATABASE_URL="postgresql+asyncpg://edumind:edumind@127.0.0.1:${PORT}/edumind_migration_test" \
    "$PYTHON_BIN" scripts/verify_clean_migration.py
) >"$LOG_DIR/verify_clean_migration.log" 2>&1
status=$?

if [ "$status" -ne 0 ]; then
  echo "Clean migration verification failed. See $LOG_DIR/verify_clean_migration.log"
  exit "$status"
fi

(
  cd "$ROOT_DIR/backend" || exit 1
  DATABASE_URL="$DB_URL" ASYNC_DATABASE_URL="postgresql+asyncpg://edumind:edumind@127.0.0.1:${PORT}/edumind_migration_test" \
    "$PYTHON_BIN" scripts/verify_pgvector.py --database-url "$DB_URL"
) >"$LOG_DIR/verify_pgvector.log" 2>&1
status=$?

if [ "$status" -ne 0 ]; then
  echo "pgvector verification failed. See $LOG_DIR/verify_pgvector.log"
  exit "$status"
fi

echo "Clean migration verification passed. Reports written to $REPORT_DIR"
