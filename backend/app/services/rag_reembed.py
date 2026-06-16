"""Production-safe batch re-embedding service for existing RAG chunks."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.textbook import RagChunk
from app.services.embeddings import (
    EMBEDDING_DIM,
    current_embedding_model_name,
    embed_document,
    embed_documents_batch,
    embedding_provider_status,
)

VALID_EMBEDDING_STATUSES = {"pending", "processing", "completed", "failed", "skipped"}


@dataclass
class ReembedResult:
    """Progress/result payload for a RAG re-embedding job."""

    status: str
    source_id: int | None = None
    source_type: str | None = None
    dry_run: bool = False
    force: bool = True
    resume_failed: bool = False
    embedding_model: str = ""
    embedding_dimension: int = EMBEDDING_DIM
    total_chunks: int = 0
    total_candidates: int = 0
    processed: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    progress: int = 0
    last_chunk_id: int | None = None
    errors: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["embedding_provider"] = embedding_provider_status()
        return payload


ReembedProgress = ReembedResult


def _metadata_with_embedding_model(raw: dict | list | None, model_name: str) -> dict[str, Any]:
    metadata = raw if isinstance(raw, dict) else {}
    return {
        **metadata,
        "embedding_model": model_name,
        "embedding_dimension": EMBEDDING_DIM,
        "embedding_status": "completed",
        "embedding_updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _source_filtered_stmt(*, source_id: int | None, source_type: str | None):
    stmt = select(RagChunk)
    if source_id is not None:
        stmt = stmt.where(RagChunk.source_id == source_id)
    if source_type:
        stmt = stmt.where(RagChunk.source_type == source_type)
    return stmt


def _candidate_stmt(
    *,
    source_id: int | None,
    source_type: str | None,
    force: bool,
    resume_failed: bool,
):
    stmt = _source_filtered_stmt(source_id=source_id, source_type=source_type)
    if resume_failed:
        return stmt.where(RagChunk.embedding_status.in_(("pending", "failed")))
    if force:
        return stmt
    model_name = current_embedding_model_name()
    return stmt.where(
        or_(
            RagChunk.embedding.is_(None),
            RagChunk.embedding_model.is_(None),
            RagChunk.embedding_model != model_name,
            RagChunk.embedding_status != "completed",
        )
    )


async def _count(db: AsyncSession, stmt) -> int:
    return int(await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)


def _validate_batch_size(batch_size: int) -> None:
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")
    if batch_size > 500:
        raise ValueError("batch_size must be <= 500")


def _progress_percent(progress: ReembedResult) -> int:
    if progress.total_candidates <= 0:
        return 100
    return min(100, int((progress.processed / progress.total_candidates) * 100))


def _record_failure(progress: ReembedResult, chunk: RagChunk, error: str) -> None:
    progress.failed += 1
    progress.processed += 1
    progress.last_chunk_id = chunk.id
    progress.errors = progress.errors or []
    progress.errors.append({"chunk_id": chunk.id, "error": error})
    chunk.embedding_status = "failed"
    chunk.embedding_error = error[:4000]


def _record_skip(progress: ReembedResult, chunk: RagChunk, reason: str) -> None:
    progress.skipped += 1
    progress.processed += 1
    progress.last_chunk_id = chunk.id
    chunk.embedding_status = "skipped"
    chunk.embedding_error = reason[:4000]


def _mark_completed(chunk: RagChunk, embedding: list[float], model_name: str, now: datetime) -> None:
    if len(embedding) != EMBEDDING_DIM:
        raise RuntimeError(f"Embedding for chunk {chunk.id} has dimension {len(embedding)}; expected {EMBEDDING_DIM}.")
    chunk.embedding = embedding
    chunk.embedding_model = model_name
    chunk.embedding_status = "completed"
    chunk.embedding_updated_at = now
    chunk.embedding_error = None
    chunk.metadata_json = _metadata_with_embedding_model(chunk.metadata_json, model_name)


async def reembed_rag_chunks(
    db: AsyncSession,
    *,
    source_id: int | None = None,
    source_type: str | None = None,
    batch_size: int = 50,
    dry_run: bool = False,
    force: bool = False,
    resume_failed: bool = False,
    resume_after_chunk_id: int | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> ReembedResult:
    """Regenerate embeddings for stored ``rag_chunks`` rows.

    The service is idempotent. It can target a source, dry-run counts, skip
    chunks already embedded with the active model, and resume failed/pending rows.
    """
    _validate_batch_size(batch_size)

    model_name = current_embedding_model_name()
    source_stmt = _source_filtered_stmt(source_id=source_id, source_type=source_type)
    candidate_stmt = _candidate_stmt(
        source_id=source_id,
        source_type=source_type,
        force=force,
        resume_failed=resume_failed,
    )
    total_chunks = await _count(db, source_stmt)
    total_candidates = await _count(db, candidate_stmt)
    progress = ReembedResult(
        status="dry_run" if dry_run else "processing",
        source_id=source_id,
        source_type=source_type,
        dry_run=dry_run,
        force=force,
        resume_failed=resume_failed,
        embedding_model=model_name,
        total_chunks=total_chunks,
        total_candidates=total_candidates,
        skipped=max(0, total_chunks - total_candidates),
        errors=[],
    )

    if dry_run:
        progress.status = "completed"
        progress.progress = 100
        return progress

    failure_limit = max(20, batch_size * 2)
    last_id = resume_after_chunk_id or 0

    while True:
        stmt = (
            _candidate_stmt(
                source_id=source_id,
                source_type=source_type,
                force=force,
                resume_failed=resume_failed,
            )
            .where(RagChunk.id > last_id)
            .order_by(RagChunk.id.asc())
            .limit(batch_size)
        )
        result = await db.execute(stmt)
        chunks = list(result.scalars().all())
        if not chunks:
            break

        non_empty_chunks: list[RagChunk] = []
        for chunk in chunks:
            if not chunk.content.strip():
                _record_skip(progress, chunk, "chunk content is empty")
                last_id = chunk.id
            else:
                chunk.embedding_status = "processing"
                chunk.embedding_error = None
                non_empty_chunks.append(chunk)
        await db.commit()

        if not non_empty_chunks:
            progress.progress = _progress_percent(progress)
            if progress_callback:
                progress_callback(progress.to_dict())
            continue

        now = datetime.now(timezone.utc)
        try:
            embeddings = await embed_documents_batch([chunk.content for chunk in non_empty_chunks], batch_size=batch_size)
            for chunk, embedding in zip(non_empty_chunks, embeddings, strict=True):
                _mark_completed(chunk, embedding, model_name, now)
                progress.updated += 1
                progress.processed += 1
                progress.last_chunk_id = chunk.id
                last_id = chunk.id
        except Exception as batch_exc:
            progress.errors = progress.errors or []
            progress.errors.append(
                {
                    "chunk_id_start": non_empty_chunks[0].id,
                    "chunk_id_end": non_empty_chunks[-1].id,
                    "error": str(batch_exc),
                }
            )
            for chunk in non_empty_chunks:
                try:
                    embedding = await embed_document(chunk.content)
                    _mark_completed(chunk, embedding, model_name, datetime.now(timezone.utc))
                    progress.updated += 1
                    progress.processed += 1
                    progress.last_chunk_id = chunk.id
                except Exception as exc:
                    _record_failure(progress, chunk, str(exc))
                    if progress.failed > failure_limit:
                        progress.status = "failed"
                        progress.progress = _progress_percent(progress)
                        await db.commit()
                        raise RuntimeError(
                            f"RAG re-embedding stopped after {progress.failed} failures. Last error: {exc}"
                        ) from exc
                finally:
                    last_id = chunk.id

        await db.commit()
        progress.progress = _progress_percent(progress)
        if progress_callback:
            progress_callback(progress.to_dict())

    progress.status = "completed" if progress.failed == 0 else "completed_with_errors"
    progress.progress = 100
    return progress


async def reembed_all_chunks(
    db: AsyncSession,
    *,
    source_id: int | None = None,
    source_type: str | None = None,
    batch_size: int = 50,
    dry_run: bool = False,
    force: bool = True,
    resume_failed: bool = False,
    resume_after_chunk_id: int | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> ReembedResult:
    """Backward-compatible wrapper for earlier hardening tests/tasks."""
    return await reembed_rag_chunks(
        db,
        source_id=source_id,
        source_type=source_type,
        batch_size=batch_size,
        dry_run=dry_run,
        force=force,
        resume_failed=resume_failed,
        resume_after_chunk_id=resume_after_chunk_id,
        progress_callback=progress_callback,
    )
