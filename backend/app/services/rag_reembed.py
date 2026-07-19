"""Production-safe batch re-embedding service for existing RAG chunks."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import random
import re
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.textbook import RagChunk
from app.services.embeddings import (
    EMBEDDING_DIM,
    GeminiEmbeddingAuthenticationError,
    GeminiEmbeddingQuotaError,
    current_embedding_model_name,
    embed_document,
    embed_documents_batch,
    embedding_provider_status,
)
from app.services.gemini_client import is_gemini_auth_error, is_gemini_quota_error
from app.services.reviewed_curriculum_metadata import (
    ensure_reviewed_metadata_ready,
    evaluate_chunk_eligibility,
    metadata_with_reviewed_version,
)

VALID_EMBEDDING_STATUSES = {"pending", "processing", "completed", "failed", "skipped"}
EMBEDDING_RETRY_ATTEMPTS = 3
EMBEDDING_RETRY_BASE_DELAY_SECONDS = 2.0
EMBEDDING_RETRY_MAX_DELAY_SECONDS = 60.0
EMBEDDING_RETRY_JITTER_SECONDS = 0.5
QUOTA_ERROR_CODE = "GEMINI_EMBEDDING_QUOTA_EXCEEDED"
AUTH_ERROR_CODE = "GEMINI_EMBEDDING_AUTH_FAILED"
PROVIDER_ERROR_CODE = "GEMINI_EMBEDDING_PROVIDER_FAILED"


class EmbeddingQuotaExceededError(RuntimeError):
    """Pause a resumable embedding job after a Gemini quota response."""

    def __init__(self, *, retry_after_seconds: float | None = None) -> None:
        super().__init__(QUOTA_ERROR_CODE)
        self.retry_after_seconds = retry_after_seconds


class EmbeddingAuthenticationError(RuntimeError):
    """Stop embedding when the configured Gemini credential is rejected."""

    def __init__(self) -> None:
        super().__init__(AUTH_ERROR_CODE)


@dataclass
class ReembedResult:
    """Progress/result payload for a RAG re-embedding job."""

    status: str
    source_id: int | None = None
    source_type: str | None = None
    dry_run: bool = False
    force: bool = False
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
    reviewed_metadata_version: str | None = None
    metadata_ready: bool = False
    skipped_missing_metadata_count: int = 0
    skipped_blocked_count: int = 0
    skipped_stale_count: int = 0
    batches_completed: int = 0
    retry_count: int = 0
    last_retry_delay_seconds: float | None = None
    quota_events: int = 0
    retry_after_seconds: float | None = None
    stopped_reason: str | None = None
    batch_delay_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["embedding_provider"] = embedding_provider_status()
        return payload


ReembedProgress = ReembedResult


def _retry_after_seconds(exc: BaseException) -> float | None:
    """Extract a provider retry delay without retaining raw provider details."""

    for attribute in ("retry_after_seconds", "retry_after", "retry_delay"):
        value = getattr(exc, attribute, None)
        if hasattr(value, "total_seconds"):
            value = value.total_seconds()
        try:
            if value is not None:
                return max(0.0, float(value))
        except (TypeError, ValueError):
            pass

    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers:
        try:
            raw_header = headers.get("Retry-After") or headers.get("retry-after")
            if raw_header is not None:
                return max(0.0, float(raw_header))
        except (AttributeError, TypeError, ValueError):
            pass

    text = str(exc)
    patterns = (
        r"retry(?:Delay|[-_ ]after| in)?[^0-9]{0,20}([0-9]+(?:\.[0-9]+)?)\s*s",
        r"'retryDelay'\s*:\s*'([0-9]+(?:\.[0-9]+)?)s'",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return max(0.0, float(match.group(1)))
    cause = exc.__cause__ or exc.__context__
    if cause is not None and cause is not exc:
        return _retry_after_seconds(cause)
    return None


def redact_embedding_error(exc: BaseException | str) -> str:
    """Return a stable provider error without credentials or verbose payloads."""

    if isinstance(exc, GeminiEmbeddingQuotaError) or is_gemini_quota_error(exc):
        return QUOTA_ERROR_CODE
    if isinstance(exc, GeminiEmbeddingAuthenticationError) or is_gemini_auth_error(exc):
        return AUTH_ERROR_CODE
    text = str(exc)
    api_key = settings.effective_gemini_api_key
    if api_key:
        text = text.replace(api_key, "***redacted***")
    text = re.sub(r"(?i)(api[_ -]?key[=: ]+)[^\s,;&]+", r"\1***redacted***", text)
    text = " ".join(text.split())
    return f"{PROVIDER_ERROR_CODE}:{type(exc).__name__}:{text[:300]}"


def _retry_delay_seconds(attempt: int) -> float:
    exponential = min(
        EMBEDDING_RETRY_MAX_DELAY_SECONDS,
        EMBEDDING_RETRY_BASE_DELAY_SECONDS * (2**attempt),
    )
    return exponential + random.uniform(0.0, EMBEDDING_RETRY_JITTER_SECONDS)


def _metadata_with_embedding_model(
    raw: dict | list | None,
    model_name: str,
    reviewed_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = metadata_with_reviewed_version(raw, reviewed_metadata or ensure_reviewed_metadata_ready())
    return {
        **metadata,
        "embedding_model": model_name,
        "embedding_dimension": EMBEDDING_DIM,
        "embedding_status": "completed",
        "embedding_updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _reviewed_metadata_for_legacy_chunk(
    chunk: RagChunk,
    reviewed_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Return metadata used for per-row embedding readiness checks.

    New reviewed chunks already carry lesson/unit/page/quality metadata. Older
    ``rag_chunks`` rows may only have DB columns such as ``source_type`` and
    ``page_number``. Re-embedding those rows should not fail the whole job after
    the global reviewed metadata gate has passed; instead, mark unmapped rows as
    ``needs_review`` so retrieval can warn and student-facing generation can
    still exclude them.
    """

    metadata = metadata_with_reviewed_version(chunk.metadata_json, reviewed_metadata)
    source_type = metadata.get("source_type") or chunk.source_type
    page_number = chunk.page_number
    has_real_unit_id = metadata.get("unit_id") not in (None, "", []) or chunk.unit_id is not None
    has_real_lesson_id = metadata.get("lesson_id") not in (None, "", []) or chunk.lesson_id is not None
    missing_real_curriculum_link = not (has_real_unit_id and has_real_lesson_id)

    metadata.setdefault("source_type", source_type)
    metadata.setdefault("printed_page_start", page_number)
    metadata.setdefault("printed_page_end", page_number)
    metadata.setdefault("quality_status", "needs_review")
    if missing_real_curriculum_link:
        metadata["quality_status"] = "needs_review"
        metadata["review_status"] = "legacy_unmapped"

    if metadata.get("unit_id") in (None, "", []):
        metadata["unit_id"] = chunk.unit_id if chunk.unit_id is not None else f"unmapped:{source_type}:{chunk.source_id}"
    if metadata.get("lesson_id") in (None, "", []):
        metadata["lesson_id"] = (
            chunk.lesson_id if chunk.lesson_id is not None else f"unmapped:{source_type}:{chunk.source_id}:{chunk.chunk_index}"
        )
    if metadata.get("content_scope") in (None, "", []):
        metadata["content_scope"] = "lesson" if chunk.lesson_id is not None else "legacy_unmapped"

    return metadata


def _embedding_readiness_for_chunk(
    chunk: RagChunk,
    reviewed_metadata: dict[str, Any],
) -> tuple[bool, str | None, list[str], dict[str, Any]]:
    metadata = _reviewed_metadata_for_legacy_chunk(chunk, reviewed_metadata)
    if metadata.get("stale") is True:
        return False, "stale_reviewed_chunk", [], metadata
    candidate = {
        "content": chunk.content,
        "source_type": chunk.source_type,
        "page_number": chunk.page_number,
        "metadata_json": metadata,
    }
    decision = evaluate_chunk_eligibility(candidate, reviewed_metadata, legacy=True)
    reason = None
    if not decision.embedding_allowed:
        reason = next(
            (
                code
                for code in decision.reason_codes
                if code in {
                    "blocked_quality_status",
                    "invalid_source_type",
                    "empty_content",
                    "missing_required_metadata",
                }
            ),
            "missing_reviewed_metadata",
        )
    return decision.embedding_allowed, reason, decision.missing_fields, decision.normalized_metadata


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
        return stmt.where(RagChunk.embedding_status.in_(("pending", "failed", "processing")))
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


def _validate_batch_delay(batch_delay_seconds: float) -> None:
    if batch_delay_seconds < 0:
        raise ValueError("batch_delay_seconds must be >= 0")
    if batch_delay_seconds > 300:
        raise ValueError("batch_delay_seconds must be <= 300")


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


def _record_metadata_skip(
    progress: ReembedResult,
    chunk: RagChunk,
    reason: str | None,
    missing: list[str],
) -> None:
    skip_reason = reason or "reviewed metadata check failed"
    _record_skip(progress, chunk, skip_reason)
    if reason == "blocked_quality_status":
        progress.skipped_blocked_count += 1
    elif reason == "missing_reviewed_metadata":
        progress.skipped_missing_metadata_count += 1
    elif reason == "stale_reviewed_chunk":
        progress.skipped_stale_count += 1
    progress.errors = progress.errors or []
    progress.errors.append(
        {
            "chunk_id": chunk.id,
            "skip_reason": reason,
            "missing_metadata": missing,
        }
    )


def _mark_completed(
    chunk: RagChunk,
    embedding: list[float],
    model_name: str,
    now: datetime,
    reviewed_metadata: dict[str, Any],
) -> None:
    if len(embedding) != EMBEDDING_DIM:
        raise RuntimeError(f"Embedding for chunk {chunk.id} has dimension {len(embedding)}; expected {EMBEDDING_DIM}.")
    chunk.embedding = embedding
    chunk.embedding_model = model_name
    chunk.embedding_status = "completed"
    chunk.embedding_updated_at = now
    chunk.embedding_error = None
    chunk.metadata_json = _metadata_with_embedding_model(
        _reviewed_metadata_for_legacy_chunk(chunk, reviewed_metadata),
        model_name,
        reviewed_metadata,
    )


async def _embed_batch_with_retry(
    texts: list[str],
    batch_size: int,
    *,
    retry_callback: Callable[[float], None] | None = None,
) -> list[list[float]]:
    last_error: Exception | None = None
    for attempt in range(EMBEDDING_RETRY_ATTEMPTS):
        try:
            return await embed_documents_batch(texts, batch_size=batch_size)
        except Exception as exc:  # provider/transient network failures
            if isinstance(exc, GeminiEmbeddingQuotaError) or is_gemini_quota_error(exc):
                raise EmbeddingQuotaExceededError(
                    retry_after_seconds=_retry_after_seconds(exc)
                ) from exc
            if isinstance(exc, GeminiEmbeddingAuthenticationError) or is_gemini_auth_error(exc):
                raise EmbeddingAuthenticationError() from exc
            last_error = exc
            if attempt + 1 < EMBEDDING_RETRY_ATTEMPTS:
                delay = _retry_delay_seconds(attempt)
                if retry_callback:
                    retry_callback(delay)
                await asyncio.sleep(delay)
    assert last_error is not None
    raise last_error


async def _embed_document_with_retry(
    text: str,
    *,
    retry_callback: Callable[[float], None] | None = None,
) -> list[float]:
    last_error: Exception | None = None
    for attempt in range(EMBEDDING_RETRY_ATTEMPTS):
        try:
            return await embed_document(text)
        except Exception as exc:
            if isinstance(exc, GeminiEmbeddingQuotaError) or is_gemini_quota_error(exc):
                raise EmbeddingQuotaExceededError(
                    retry_after_seconds=_retry_after_seconds(exc)
                ) from exc
            if isinstance(exc, GeminiEmbeddingAuthenticationError) or is_gemini_auth_error(exc):
                raise EmbeddingAuthenticationError() from exc
            last_error = exc
            if attempt + 1 < EMBEDDING_RETRY_ATTEMPTS:
                delay = _retry_delay_seconds(attempt)
                if retry_callback:
                    retry_callback(delay)
                await asyncio.sleep(delay)
    assert last_error is not None
    raise last_error


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
    batch_delay_seconds: float = 0.0,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> ReembedResult:
    """Regenerate embeddings for stored ``rag_chunks`` rows.

    The service is idempotent. It can target a source, dry-run counts, skip
    chunks already embedded with the active model, and resume failed/pending rows.
    """
    _validate_batch_size(batch_size)
    _validate_batch_delay(batch_delay_seconds)

    reviewed_metadata = ensure_reviewed_metadata_ready()
    model_name = current_embedding_model_name()
    if not dry_run:
        provider = embedding_provider_status()
        if (
            str(provider.get("provider") or "").lower() != "gemini"
            or model_name != "gemini-embedding-001"
            or not settings.effective_gemini_api_key
            or EMBEDDING_DIM != 768
        ):
            raise RuntimeError(
                "PRODUCTION_GEMINI_EMBEDDING_REQUIRED: re-embedding requires "
                "EMBEDDING_PROVIDER=gemini, GEMINI_EMBEDDING_MODEL=gemini-embedding-001, "
                "a configured GEMINI_API_KEY, and vector dimension 768."
            )
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
        reviewed_metadata_version=str(reviewed_metadata.get("version") or ""),
        metadata_ready=True,
        batch_delay_seconds=batch_delay_seconds,
    )

    def record_retry(delay: float) -> None:
        progress.retry_count += 1
        progress.last_retry_delay_seconds = round(delay, 3)

    async def stop_for_provider(
        *,
        chunks: list[RagChunk],
        status: str,
        reason: str,
        retry_after_seconds: float | None = None,
    ) -> ReembedResult:
        for pending_chunk in chunks:
            if pending_chunk.embedding_status != "completed":
                pending_chunk.embedding_status = "pending"
                pending_chunk.embedding_error = reason
        progress.status = status
        progress.stopped_reason = reason
        progress.retry_after_seconds = retry_after_seconds
        progress.errors = progress.errors or []
        progress.errors.append(
            {
                "error": reason,
                "retry_after_seconds": retry_after_seconds,
            }
        )
        await db.commit()
        progress.progress = _progress_percent(progress)
        if progress_callback:
            progress_callback(progress.to_dict())
        return progress

    if dry_run and not hasattr(db, "execute"):
        progress.status = "completed"
        progress.progress = 100
        return progress

    if dry_run:
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
            for chunk in chunks:
                ready, reason, missing, _metadata = _embedding_readiness_for_chunk(chunk, reviewed_metadata)
                if not ready:
                    progress.skipped += 1
                    if reason == "blocked_quality_status":
                        progress.skipped_blocked_count += 1
                    elif reason == "missing_reviewed_metadata":
                        progress.skipped_missing_metadata_count += 1
                    elif reason == "stale_reviewed_chunk":
                        progress.skipped_stale_count += 1
                    progress.errors = progress.errors or []
                    progress.errors.append(
                        {
                            "chunk_id": chunk.id,
                            "skip_reason": reason,
                            "missing_metadata": missing,
                        }
                    )
                last_id = chunk.id
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
            ready, reason, missing, metadata = _embedding_readiness_for_chunk(chunk, reviewed_metadata)
            if not ready:
                _record_metadata_skip(progress, chunk, reason, missing)
                last_id = chunk.id
            elif not chunk.content.strip():
                _record_skip(progress, chunk, "chunk content is empty")
                last_id = chunk.id
            else:
                chunk.metadata_json = metadata
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
        if progress.batches_completed > 0 and batch_delay_seconds > 0:
            await asyncio.sleep(batch_delay_seconds)
        try:
            embeddings = await _embed_batch_with_retry(
                [chunk.content for chunk in non_empty_chunks],
                batch_size=batch_size,
                retry_callback=record_retry,
            )
            if len(embeddings) != len(non_empty_chunks):
                raise RuntimeError(
                    f"Embedding provider returned {len(embeddings)} vectors for "
                    f"{len(non_empty_chunks)} chunks."
                )
            bad_dimensions = sorted(
                {len(embedding) for embedding in embeddings if len(embedding) != EMBEDDING_DIM}
            )
            if bad_dimensions:
                raise RuntimeError(
                    f"Embedding provider returned dimensions {bad_dimensions}; expected {EMBEDDING_DIM}."
                )
            for chunk, embedding in zip(non_empty_chunks, embeddings, strict=True):
                _mark_completed(chunk, embedding, model_name, now, reviewed_metadata)
                progress.updated += 1
                progress.processed += 1
                progress.last_chunk_id = chunk.id
                last_id = chunk.id
            progress.batches_completed += 1
        except EmbeddingQuotaExceededError as quota_exc:
            progress.quota_events += 1
            return await stop_for_provider(
                chunks=non_empty_chunks,
                status="paused_quota",
                reason=QUOTA_ERROR_CODE,
                retry_after_seconds=quota_exc.retry_after_seconds,
            )
        except EmbeddingAuthenticationError:
            return await stop_for_provider(
                chunks=non_empty_chunks,
                status="failed",
                reason=AUTH_ERROR_CODE,
            )
        except Exception as batch_exc:
            progress.errors = progress.errors or []
            progress.errors.append(
                {
                    "chunk_id_start": non_empty_chunks[0].id,
                    "chunk_id_end": non_empty_chunks[-1].id,
                    "error": redact_embedding_error(batch_exc),
                }
            )
            for chunk_index, chunk in enumerate(non_empty_chunks):
                try:
                    embedding = await _embed_document_with_retry(
                        chunk.content,
                        retry_callback=record_retry,
                    )
                    _mark_completed(chunk, embedding, model_name, datetime.now(timezone.utc), reviewed_metadata)
                    progress.updated += 1
                    progress.processed += 1
                    progress.last_chunk_id = chunk.id
                except EmbeddingQuotaExceededError as quota_exc:
                    progress.quota_events += 1
                    return await stop_for_provider(
                        chunks=non_empty_chunks[chunk_index:],
                        status="paused_quota",
                        reason=QUOTA_ERROR_CODE,
                        retry_after_seconds=quota_exc.retry_after_seconds,
                    )
                except EmbeddingAuthenticationError:
                    return await stop_for_provider(
                        chunks=non_empty_chunks[chunk_index:],
                        status="failed",
                        reason=AUTH_ERROR_CODE,
                    )
                except Exception as exc:
                    safe_error = redact_embedding_error(exc)
                    _record_failure(progress, chunk, safe_error)
                    if progress.failed > failure_limit:
                        progress.status = "failed"
                        progress.progress = _progress_percent(progress)
                        await db.commit()
                        raise RuntimeError(
                            f"RAG re-embedding stopped after {progress.failed} failures. "
                            f"Last error: {safe_error}"
                        ) from exc
                finally:
                    last_id = chunk.id
            progress.batches_completed += 1

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
    batch_delay_seconds: float = 0.0,
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
        batch_delay_seconds=batch_delay_seconds,
        progress_callback=progress_callback,
    )
