"""Read-only production preflight for the reviewed RAG pipeline."""

from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.textbook import RagChunk
from app.services.embeddings import EMBEDDING_DIM, embedding_provider_status
from app.services.reviewed_curriculum_metadata import (
    ReviewedCurriculumMetadataError,
    evaluate_chunk_eligibility,
    load_reviewed_curriculum_metadata,
)
from app.services.reviewed_ingestion_assets import (
    canonical_source_statuses,
    embedding_readiness,
    rag_source_statuses,
)


DATABASE_UNREACHABLE = "DATABASE_UNREACHABLE"
DATABASE_NOT_POSTGRESQL = "DATABASE_NOT_POSTGRESQL"
PGVECTOR_EXTENSION_MISSING = "PGVECTOR_EXTENSION_MISSING"
PGVECTOR_INDEX_MISSING = "PGVECTOR_INDEX_MISSING"
REVIEWED_METADATA_MISSING = "REVIEWED_METADATA_MISSING"
REVIEWED_METADATA_NOT_READY = "REVIEWED_METADATA_NOT_READY"
TEXTBOOK_SOURCE_MISSING = "TEXTBOOK_SOURCE_MISSING"
SOLUTION_BOOK_SOURCE_MISSING = "SOLUTION_BOOK_SOURCE_MISSING"
REVIEWED_TEXTBOOK_CHUNKS_MISSING = "REVIEWED_TEXTBOOK_CHUNKS_MISSING"
REVIEWED_SOLUTION_CHUNKS_MISSING = "REVIEWED_SOLUTION_CHUNKS_MISSING"
GEMINI_EMBEDDING_NOT_CONFIGURED = "GEMINI_EMBEDDING_NOT_CONFIGURED"
NO_DATABASE_CHUNKS = "NO_DATABASE_CHUNKS"
ELIGIBLE_EMBEDDINGS_INCOMPLETE = "ELIGIBLE_EMBEDDINGS_INCOMPLETE"
WRONG_EMBEDDING_DIMENSION = "WRONG_EMBEDDING_DIMENSION"
PGVECTOR_DIMENSION_MISMATCH = "PGVECTOR_DIMENSION_MISMATCH"
EMBEDDING_MODEL_MISMATCH = "EMBEDDING_MODEL_MISMATCH"
COMPLETED_VECTOR_MISSING = "COMPLETED_VECTOR_MISSING"
EMBEDDING_INDEX_EMPTY = "EMBEDDING_INDEX_EMPTY"


def _database_baseline(db: Session) -> dict[str, Any]:
    """Inspect database capabilities without changing schema or rows."""

    bind = db.get_bind()
    dialect = str(bind.dialect.name or "other")
    result: dict[str, Any] = {
        "dialect": dialect,
        "reachable": False,
        "pgvector_available": False,
        "pgvector_version": None,
        "embedding_dimension": EMBEDDING_DIM,
        "vector_column_type": None,
        "vector_dimension_valid": False,
        "vector_index_present": False,
        "vector_index_name": None,
        "vector_index_type": None,
        "distance_operator": None,
    }
    try:
        db.execute(text("SELECT 1")).scalar_one()
        result["reachable"] = True
    except Exception as exc:
        result["error"] = type(exc).__name__
        return result

    if dialect != "postgresql":
        return result

    try:
        version = db.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        ).scalar_one_or_none()
        result["pgvector_available"] = bool(version)
        result["pgvector_version"] = str(version) if version else None
    except Exception as exc:
        result["pgvector_error"] = type(exc).__name__

    try:
        index_row = db.execute(
            text(
                """
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = current_schema()
                  AND tablename = 'rag_chunks'
                  AND indexdef ILIKE '%embedding%'
                ORDER BY CASE WHEN indexname = 'rag_chunks_embedding_idx' THEN 0 ELSE 1 END, indexname
                LIMIT 1
                """
            )
        ).mappings().first()
        if index_row:
            definition = str(index_row.get("indexdef") or "").lower()
            result["vector_index_present"] = True
            result["vector_index_name"] = str(index_row.get("indexname") or "") or None
            result["vector_index_type"] = "ivfflat" if "ivfflat" in definition else "other"
            result["distance_operator"] = "vector_cosine_ops" if "vector_cosine_ops" in definition else None
    except Exception as exc:
        result["vector_index_error"] = type(exc).__name__

    try:
        column_type = db.execute(
            text(
                """
                SELECT format_type(a.atttypid, a.atttypmod)
                FROM pg_attribute a
                JOIN pg_class c ON a.attrelid = c.oid
                JOIN pg_namespace n ON c.relnamespace = n.oid
                WHERE c.relname = 'rag_chunks'
                  AND n.nspname = current_schema()
                  AND a.attname = 'embedding'
                  AND a.attnum > 0
                  AND NOT a.attisdropped
                LIMIT 1
                """
            )
        ).scalar_one_or_none()
        result["vector_column_type"] = str(column_type) if column_type else None
        result["vector_dimension_valid"] = str(column_type or "").lower() == "vector(768)"
    except Exception as exc:
        result["vector_dimension_error"] = type(exc).__name__

    return result


def _provider_baseline() -> dict[str, Any]:
    provider = embedding_provider_status()
    provider_name = str(provider.get("provider") or settings.embedding_provider).lower()
    configured = (
        provider_name in {"gemini", "auto"}
        and bool(settings.effective_gemini_api_key)
        and settings.gemini_embedding_model == "gemini-embedding-001"
        and EMBEDDING_DIM == 768
    )
    return {
        "provider": provider_name,
        "model": settings.gemini_embedding_model,
        "configured": configured,
    }


def _reviewed_metadata_baseline() -> tuple[dict[str, Any], dict[str, Any] | None]:
    try:
        payload = load_reviewed_curriculum_metadata(require_ready=False)
    except (ReviewedCurriculumMetadataError, ValueError, OSError):
        return {
            "exists": False,
            "status": "missing",
            "version": None,
            "ready_for_embedding": False,
            "blocking_issues": [REVIEWED_METADATA_MISSING],
        }, None
    ready = payload.get("ready_for_embedding") is True
    issues = list(payload.get("blocking_issues") or [])
    if not ready and REVIEWED_METADATA_NOT_READY not in issues:
        issues.append(REVIEWED_METADATA_NOT_READY)
    return {
        "exists": True,
        "status": str(payload.get("status") or "unknown"),
        "version": payload.get("version"),
        "ready_for_embedding": ready,
        "blocking_issues": issues,
    }, payload


def _source_baseline(db: Session) -> dict[str, bool]:
    canonical = {item["source_type"]: item for item in canonical_source_statuses(db)}
    reviewed = {item["source_type"]: item for item in rag_source_statuses(db)}
    textbook = reviewed.get("textbook") or {}
    solution = reviewed.get("solution_book") or {}
    return {
        "textbook_found": bool((canonical.get("textbook") or {}).get("exists")),
        "solution_book_found": bool((canonical.get("solution_book") or {}).get("exists")),
        "reviewed_textbook_chunks_found": textbook.get("chunk_status") not in {None, "missing"},
        "reviewed_solution_chunks_found": solution.get("chunk_status") not in {None, "missing"},
    }


def _chunk_baseline(
    db: Session,
    reviewed_metadata: dict[str, Any] | None,
    reviewed_chunks_total: int,
) -> dict[str, int]:
    rows = list(db.scalars(select(RagChunk).order_by(RagChunk.id.asc())).all())
    quality_counts: Counter[str] = Counter()
    embedding_counts: Counter[str] = Counter()
    missing_metadata = 0
    wrong_dimension = 0
    completed_vectors_missing = 0
    noncompleted_with_embeddings = 0
    embedding_model_mismatch = 0
    stale_chunks = 0

    for chunk in rows:
        decision = (
            evaluate_chunk_eligibility(
                chunk,
                reviewed_metadata,
                legacy=chunk.extraction_method != "reviewed_jsonl",
            )
            if reviewed_metadata is not None
            else None
        )
        quality = decision.normalized_quality_status if decision else "needs_review"
        quality_counts[quality] += 1
        metadata = chunk.metadata_json if isinstance(chunk.metadata_json, dict) else {}
        if metadata.get("stale") is True:
            stale_chunks += 1
        status = str(chunk.embedding_status or "pending")
        if status not in {"pending", "processing", "completed", "failed", "skipped"}:
            status = "pending"
        # Ineligible chunks stay visible in quality/missing counts but are
        # deliberately outside embedding/evaluation readiness calculations.
        if decision and decision.embedding_allowed and status != "skipped" and metadata.get("stale") is not True:
            embedding_counts[status] += 1
        if decision is None:
            missing_metadata += 1
        elif decision.missing_fields:
            missing_metadata += 1
        if decision and decision.embedding_allowed and metadata.get("stale") is not True and status == "completed":
            vector = chunk.embedding
            if vector is None:
                completed_vectors_missing += 1
            try:
                vector_dimension = len(vector) if vector is not None else 0
            except TypeError:
                vector_dimension = 0
            if vector is not None and vector_dimension != EMBEDDING_DIM:
                wrong_dimension += 1
        if decision and decision.embedding_allowed and metadata.get("stale") is not True and status != "completed" and chunk.embedding is not None:
            noncompleted_with_embeddings += 1
        if chunk.embedding is not None and chunk.embedding_model not in (None, settings.gemini_embedding_model):
            embedding_model_mismatch += 1

    return {
        "reviewed_chunks_total": int(reviewed_chunks_total),
        "database_chunks_total": len(rows),
        "ready_chunks": quality_counts["ready"],
        "needs_review_chunks": quality_counts["needs_review"],
        "blocked_chunks": quality_counts["blocked"],
        "missing_metadata_chunks": missing_metadata,
        "pending_embeddings": embedding_counts["pending"],
        "processing_embeddings": embedding_counts["processing"],
        "completed_embeddings": embedding_counts["completed"],
        "failed_embeddings": embedding_counts["failed"],
        "wrong_dimension_embeddings": wrong_dimension,
        "completed_vectors_missing": completed_vectors_missing,
        "noncompleted_with_embeddings": noncompleted_with_embeddings,
        "embedding_model_mismatch": embedding_model_mismatch,
        "stale_chunks": stale_chunks,
    }


def build_rag_preflight(db: Session) -> dict[str, Any]:
    """Return the current production RAG baseline without side effects."""

    database = _database_baseline(db)
    provider = _provider_baseline()
    reviewed_metadata, reviewed_payload = _reviewed_metadata_baseline()
    sources = _source_baseline(db)
    readiness = embedding_readiness()
    reviewed_chunks_total = int(readiness.get("textbook_chunks_total") or 0) + int(
        readiness.get("solution_chunks_total") or 0
    )
    chunks = _chunk_baseline(db, reviewed_payload, reviewed_chunks_total)

    blockers: list[str] = []
    warnings: list[str] = []

    if not database["reachable"]:
        blockers.append(DATABASE_UNREACHABLE)
    if database["dialect"] != "postgresql":
        blockers.append(DATABASE_NOT_POSTGRESQL)
    if database["dialect"] == "postgresql" and not database["pgvector_available"]:
        blockers.append(PGVECTOR_EXTENSION_MISSING)
    if database["dialect"] == "postgresql" and not database["vector_index_present"]:
        blockers.append(PGVECTOR_INDEX_MISSING)
    if database["dialect"] == "postgresql" and database.get("vector_column_type") and not database.get("vector_dimension_valid"):
        blockers.append(PGVECTOR_DIMENSION_MISMATCH)
    if not reviewed_metadata["exists"]:
        blockers.append(REVIEWED_METADATA_MISSING)
    elif not reviewed_metadata["ready_for_embedding"]:
        blockers.append(REVIEWED_METADATA_NOT_READY)
    if not sources["textbook_found"]:
        blockers.append(TEXTBOOK_SOURCE_MISSING)
    if not sources["solution_book_found"]:
        blockers.append(SOLUTION_BOOK_SOURCE_MISSING)
    if not sources["reviewed_textbook_chunks_found"]:
        blockers.append(REVIEWED_TEXTBOOK_CHUNKS_MISSING)
    if not sources["reviewed_solution_chunks_found"]:
        blockers.append(REVIEWED_SOLUTION_CHUNKS_MISSING)
    if not provider["configured"]:
        blockers.append(GEMINI_EMBEDDING_NOT_CONFIGURED)
    if chunks["wrong_dimension_embeddings"]:
        blockers.append(WRONG_EMBEDDING_DIMENSION)
    if chunks["embedding_model_mismatch"]:
        blockers.append(EMBEDDING_MODEL_MISMATCH)
    if chunks["completed_vectors_missing"]:
        blockers.append(COMPLETED_VECTOR_MISSING)
    if chunks["database_chunks_total"] == 0:
        warnings.append(NO_DATABASE_CHUNKS)
    elif chunks["completed_embeddings"] == 0:
        warnings.append(EMBEDDING_INDEX_EMPTY)

    foundational_source_ready = all(sources.values()) and reviewed_metadata["ready_for_embedding"]
    can_load_chunks = bool(database["reachable"] and foundational_source_ready)
    production_embedding_ready = bool(
        database["reachable"]
        and database["dialect"] == "postgresql"
        and database["pgvector_available"]
        and database["vector_index_present"]
        and provider["configured"]
        and foundational_source_ready
    )
    eligible_total = (
        chunks["pending_embeddings"]
        + chunks["processing_embeddings"]
        + chunks["completed_embeddings"]
        + chunks["failed_embeddings"]
    )
    pending_or_failed = (
        chunks["pending_embeddings"]
        + chunks["processing_embeddings"]
        + chunks["failed_embeddings"]
    )
    can_embed = bool(production_embedding_ready and eligible_total > 0 and pending_or_failed > 0)
    can_evaluate = bool(
        production_embedding_ready
        and eligible_total > 0
        and chunks["completed_embeddings"] >= eligible_total
        and pending_or_failed == 0
        and chunks["wrong_dimension_embeddings"] == 0
        and chunks["completed_vectors_missing"] == 0
        and chunks["noncompleted_with_embeddings"] == 0
        and chunks["embedding_model_mismatch"] == 0
        and (database.get("vector_dimension_valid", True) is True)
    )
    if eligible_total > 0 and not can_evaluate:
        warnings.append(ELIGIBLE_EMBEDDINGS_INCOMPLETE)

    blockers = list(dict.fromkeys(blockers))
    warnings = list(dict.fromkeys(warnings))
    hard_blockers = {
        DATABASE_UNREACHABLE,
        DATABASE_NOT_POSTGRESQL,
        PGVECTOR_EXTENSION_MISSING,
        PGVECTOR_INDEX_MISSING,
        REVIEWED_METADATA_MISSING,
        REVIEWED_METADATA_NOT_READY,
        TEXTBOOK_SOURCE_MISSING,
        SOLUTION_BOOK_SOURCE_MISSING,
        REVIEWED_TEXTBOOK_CHUNKS_MISSING,
        REVIEWED_SOLUTION_CHUNKS_MISSING,
        GEMINI_EMBEDDING_NOT_CONFIGURED,
        WRONG_EMBEDDING_DIMENSION,
        PGVECTOR_DIMENSION_MISMATCH,
        EMBEDDING_MODEL_MISMATCH,
        COMPLETED_VECTOR_MISSING,
    }
    status = "ready" if can_evaluate else "blocked" if hard_blockers.intersection(blockers) else "degraded"
    return {
        "status": status,
        "database": database,
        "provider": provider,
        "reviewed_metadata": reviewed_metadata,
        "sources": sources,
        "chunks": chunks,
        "can_load_chunks": can_load_chunks,
        "can_embed": can_embed,
        "can_evaluate": can_evaluate,
        "blocking_issues": blockers,
        "warnings": warnings,
    }
