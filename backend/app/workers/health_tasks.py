"""Safe Celery health-check tasks."""

from __future__ import annotations

from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.health_tasks.ping")
def ping(message: str = "pong") -> dict[str, str | bool]:
    """Return a small payload without mutating application data."""
    return {"ok": True, "message": message}
