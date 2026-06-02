"""Celery application configuration."""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "edumind",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    # --- Serialization ---
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # --- Task tracking ---
    task_track_started=True,
    result_expires=3600,  # results expire after 1 hour

    # --- Reliability ---
    task_acks_late=True,            # acknowledge after task completes (not before)
    worker_prefetch_multiplier=1,   # one task at a time per worker process
    task_reject_on_worker_lost=True,

    # --- Timezone ---
    timezone="UTC",
    enable_utc=True,

    # --- Queues ---
    task_default_queue="default",
    task_routes={
        "ingest_pdf": {"queue": "ingestion"},
    },

    # --- Auto-discovery ---
    include=["app.workers.ingestion_tasks"],
)
