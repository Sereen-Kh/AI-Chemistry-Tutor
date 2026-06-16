#!/usr/bin/env python3
"""Verify Redis, Celery worker, Beat schedule, and safe task execution."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from redis import Redis

from hardening_reports import BACKEND_DIR, redact_url, status_line, write_reports

sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.workers.celery_app import celery_app  # noqa: E402


REQUIRED_TASKS = {
    "app.workers.notification_tasks.check_pending_reminders",
    "reembed_rag_chunks",
    "app.workers.health_tasks.ping",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify Celery runtime.")
    parser.add_argument("--timeout", type=int, default=10)
    return parser.parse_args()


def run() -> int:
    args = parse_args()
    errors: list[str] = []
    report: dict[str, Any] = {
        "broker_url": redact_url(settings.celery_broker_url),
        "redis_url": redact_url(settings.redis_url),
        "redis_reachable": False,
        "workers_online": [],
        "registered_tasks": [],
        "required_tasks_present": [],
        "required_tasks_missing": [],
        "beat_schedule_entries": list(celery_app.conf.beat_schedule.keys()),
        "reminder_schedule_present": "check-pending-reminders-every-minute" in celery_app.conf.beat_schedule,
        "test_task_id": None,
        "test_task_result": None,
        "errors": errors,
    }
    try:
        redis_client = Redis.from_url(settings.redis_url, socket_connect_timeout=3, socket_timeout=3)
        report["redis_reachable"] = bool(redis_client.ping())
    except Exception as exc:
        errors.append(f"Redis broker/cache is not reachable: {type(exc).__name__}: {exc}")

    try:
        inspector = celery_app.control.inspect(timeout=args.timeout)
        ping = inspector.ping() or {}
        report["workers_online"] = sorted(ping.keys())
        if not report["workers_online"]:
            errors.append("No Celery workers responded to inspect.ping().")
        registered = inspector.registered() or {}
        task_names = sorted({task for tasks in registered.values() for task in tasks})
        report["registered_tasks"] = task_names
        missing = sorted(REQUIRED_TASKS - set(task_names))
        present = sorted(REQUIRED_TASKS & set(task_names))
        report["required_tasks_present"] = present
        report["required_tasks_missing"] = missing
        if missing:
            errors.append(f"Required Celery tasks are not registered by online workers: {missing}")
    except Exception as exc:
        errors.append(f"Celery inspect failed: {type(exc).__name__}: {exc}")

    if not report["reminder_schedule_present"]:
        errors.append("Celery Beat schedule is missing check-pending-reminders-every-minute.")

    if report["workers_online"]:
        try:
            async_result = celery_app.send_task("app.workers.health_tasks.ping", kwargs={"message": "p0-smoke"})
            report["test_task_id"] = async_result.id
            report["test_task_result"] = async_result.get(timeout=args.timeout)
            if not isinstance(report["test_task_result"], dict) or not report["test_task_result"].get("ok"):
                errors.append(f"Health task returned unexpected result: {report['test_task_result']}")
        except Exception as exc:
            errors.append(f"Celery health task dispatch/consume failed: {type(exc).__name__}: {exc}")

    report["errors"] = errors
    report["result"] = "passed" if not errors else "failed"
    write_reports(
        report_subdir="smoke",
        report_name="celery_runtime_report",
        title="Celery Runtime Verification",
        payload=report,
        sections=[
            (
                "Runtime",
                [
                    status_line("Broker URL", report["broker_url"]),
                    status_line("Redis reachable", report["redis_reachable"]),
                    status_line("Workers online", report["workers_online"]),
                    status_line("Reminder Beat schedule present", report["reminder_schedule_present"]),
                ],
            ),
            (
                "Tasks",
                [
                    status_line("Required tasks present", report["required_tasks_present"]),
                    status_line("Required tasks missing", report["required_tasks_missing"]),
                    status_line("Health task id", report["test_task_id"]),
                    status_line("Health task result", report["test_task_result"]),
                ],
            ),
            ("Errors", [f"- {item}" for item in errors] if errors else ["- None"]),
        ],
    )
    for item in errors:
        print(f"ERROR: {item}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(run())
