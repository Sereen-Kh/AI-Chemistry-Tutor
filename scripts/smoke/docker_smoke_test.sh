#!/usr/bin/env bash
set -u -o pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORT_DIR="$ROOT_DIR/reports/smoke"
LOG_DIR="$REPORT_DIR/logs/docker_smoke_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$LOG_DIR"

COMPOSE=(docker compose)
SERVICES=(postgres redis backend celery-worker celery-beat frontend-web)
ERRORS=()

record_error() {
  ERRORS+=("$1")
  echo "ERROR: $1"
}

run_logged() {
  local name="$1"
  shift
  echo "==> $name"
  "$@" >"$LOG_DIR/${name}.log" 2>&1
}

redact_file() {
  local file="$1"
  python3 - "$file" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8", errors="replace")
patterns = [
    r"(?i)(GEMINI_API_KEY|GOOGLE_API_KEY|SECRET_KEY|POSTGRES_PASSWORD|DATABASE_URL|ASYNC_DATABASE_URL|CELERY_BROKER_URL|CELERY_RESULT_BACKEND|REDIS_URL):\s+.*",
]
for pattern in patterns:
    text = re.sub(pattern, lambda m: f"{m.group(1)}: ***redacted***", text)
path.write_text(text, encoding="utf-8")
PY
}

wait_http() {
  local name="$1"
  local url="$2"
  local attempts="${3:-45}"
  local sleep_seconds="${4:-2}"
  for _ in $(seq 1 "$attempts"); do
    if curl -fsS "$url" >"$LOG_DIR/${name}.body" 2>"$LOG_DIR/${name}.err"; then
      return 0
    fi
    sleep "$sleep_seconds"
  done
  return 1
}

compose_logs() {
  "${COMPOSE[@]}" logs --no-color "${SERVICES[@]}" >"$LOG_DIR/compose_services.log" 2>&1 || true
}

write_report() {
  local result="$1"
  local compose_config="$2"
  local compose_up="$3"
  local backend_health="$4"
  local frontend_health="$5"
  local db_check="$6"
  local redis_check="$7"
  local worker_check="$8"
  local beat_check="$9"
  local report_args=(
    "$REPORT_DIR" "$LOG_DIR" "$result" "$compose_config" "$compose_up"
    "$backend_health" "$frontend_health" "$db_check" "$redis_check"
    "$worker_check" "$beat_check"
  )
  if [ "${#ERRORS[@]}" -gt 0 ]; then
    report_args+=("${ERRORS[@]}")
  fi
  python3 - "${report_args[@]}" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

report_dir = Path(sys.argv[1])
log_dir = Path(sys.argv[2])
keys = [
    "result",
    "compose_config_result",
    "compose_up_result",
    "backend_health_result",
    "frontend_reachability_result",
    "db_check_result",
    "redis_check_result",
    "celery_worker_check_result",
    "celery_beat_check_result",
]
values = sys.argv[3:12]
errors = sys.argv[12:]
payload = dict(zip(keys, values))
payload.update(
    {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "services": ["postgres", "redis", "backend", "celery-worker", "celery-beat", "frontend-web"],
        "failed_logs_path": str(log_dir) if errors else None,
        "errors": errors,
    }
)
report_dir.mkdir(parents=True, exist_ok=True)
(report_dir / "docker_smoke_report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
lines = [
    "# Docker Smoke Test Report",
    "",
    f"Result: `{payload['result']}`",
    "",
    "## Checks",
    "",
]
for key in keys[1:]:
    lines.append(f"- **{key}:** `{payload[key]}`")
lines.extend(["", "## Services", ""])
lines.extend(f"- `{service}`" for service in payload["services"])
lines.extend(["", "## Errors", ""])
lines.extend(f"- {error}" for error in errors or ["None"])
lines.extend(["", "## Logs", "", f"- `{payload['failed_logs_path']}`"])
(report_dir / "docker_smoke_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
}

cd "$ROOT_DIR" || exit 1

COMPOSE_CONFIG="failed"
COMPOSE_UP="not_run"
BACKEND_HEALTH="not_run"
FRONTEND_HEALTH="not_run"
DB_CHECK="not_run"
REDIS_CHECK="not_run"
WORKER_CHECK="not_run"
BEAT_CHECK="not_run"

if ! command -v docker >/dev/null 2>&1; then
  record_error "Docker CLI is not installed or not on PATH."
  write_report "failed" "$COMPOSE_CONFIG" "$COMPOSE_UP" "$BACKEND_HEALTH" "$FRONTEND_HEALTH" "$DB_CHECK" "$REDIS_CHECK" "$WORKER_CHECK" "$BEAT_CHECK"
  exit 1
fi

if ! run_logged compose_config "${COMPOSE[@]}" config; then
  record_error "docker compose config failed. See $LOG_DIR/compose_config.log"
else
  redact_file "$LOG_DIR/compose_config.log"
  COMPOSE_CONFIG="passed"
fi

if [ "$COMPOSE_CONFIG" = "passed" ]; then
  if ! run_logged compose_up "${COMPOSE[@]}" up -d --build "${SERVICES[@]}"; then
    record_error "docker compose up failed. See $LOG_DIR/compose_up.log"
    COMPOSE_UP="failed"
    compose_logs
  else
    COMPOSE_UP="passed"
  fi
fi

if [ "$COMPOSE_UP" = "passed" ]; then
  if wait_http backend_health "http://127.0.0.1:8000/health"; then
    BACKEND_HEALTH="passed"
  else
    BACKEND_HEALTH="failed"
    record_error "Backend health endpoint did not respond at http://127.0.0.1:8000/health."
  fi

  if wait_http frontend_reachability "http://127.0.0.1:5173/"; then
    FRONTEND_HEALTH="passed"
  else
    FRONTEND_HEALTH="failed"
    record_error "Frontend did not respond at http://127.0.0.1:5173/."
  fi

  if run_logged db_check "${COMPOSE[@]}" exec -T postgres pg_isready -U edumind -d edumind; then
    DB_CHECK="passed"
  else
    DB_CHECK="failed"
    record_error "PostgreSQL readiness check failed."
  fi

  if run_logged redis_check "${COMPOSE[@]}" exec -T redis redis-cli ping; then
    REDIS_CHECK="passed"
  else
    REDIS_CHECK="failed"
    record_error "Redis ping failed."
  fi

  if run_logged celery_worker_check "${COMPOSE[@]}" exec -T celery-worker celery -A app.workers.celery_app:celery_app inspect ping --timeout=10; then
    WORKER_CHECK="passed"
  else
    WORKER_CHECK="failed"
    record_error "Celery worker inspect ping failed."
  fi

  if run_logged celery_beat_check docker inspect -f "{{.State.Running}}" edumind-celery-beat; then
    if ! grep -q "true" "$LOG_DIR/celery_beat_check.log"; then
      BEAT_CHECK="failed"
      record_error "Celery Beat container is not running."
    else
      BEAT_CHECK="passed"
    fi
  else
    BEAT_CHECK="failed"
    record_error "Celery Beat container inspect failed."
  fi
fi

if [ "${#ERRORS[@]}" -gt 0 ]; then
  compose_logs
  RESULT="failed"
else
  RESULT="passed"
fi

write_report "$RESULT" "$COMPOSE_CONFIG" "$COMPOSE_UP" "$BACKEND_HEALTH" "$FRONTEND_HEALTH" "$DB_CHECK" "$REDIS_CHECK" "$WORKER_CHECK" "$BEAT_CHECK"

if [ "${SMOKE_STOP_AFTER:-${CI:-0}}" = "1" ] || [ "${SMOKE_STOP_AFTER:-${CI:-0}}" = "true" ]; then
  "${COMPOSE[@]}" down >"$LOG_DIR/compose_down.log" 2>&1 || true
fi

if [ "$RESULT" = "passed" ]; then
  echo "Docker smoke test passed. Reports written to $REPORT_DIR"
  exit 0
fi

echo "Docker smoke test failed. Reports written to $REPORT_DIR; logs in $LOG_DIR"
exit 1
