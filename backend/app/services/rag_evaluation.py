"""Eligibility-aware Grade 9 RAG retrieval evaluation gate."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import PROJECT_DIR, settings
from app.models.textbook import RagChunk
from app.services.rag import RetrievedChunk, retrieve_context
from app.services.rag_runtime import active_reviewed_metadata_version
from app.services.reviewed_curriculum_metadata import (
    ReviewedCurriculumMetadataError,
    evaluate_chunk_eligibility,
    load_reviewed_curriculum_metadata,
)

EMBEDDING_INDEX_INCOMPLETE = "EMBEDDING_INDEX_INCOMPLETE"
EMBEDDING_INDEX_EMPTY = "EMBEDDING_INDEX_EMPTY"
EMBEDDING_MODEL_MISMATCH = "EMBEDDING_MODEL_MISMATCH"
REVIEWED_METADATA_VERSION_MISMATCH = "REVIEWED_METADATA_VERSION_MISMATCH"
EVALUATION_DATASET_INVALID = "EVALUATION_DATASET_INVALID"

THRESHOLDS = {
    "top5_expected_printed_page_hit_rate": 0.80,
    # Compatibility alias retained in reports consumed by the existing UI.
    "top5_expected_page_hit_rate": 0.80,
    "no_result_rate": 0.10,
    "wrong_source_rate": 0.15,
    "low_confidence_rate": 0.25,
    "average_retrieval_latency_ms": 1500,
    "required_curriculum_metadata_completeness": 1.0,
    "blocked_or_stale_result_rate": 0.0,
    "reviewed_version_mismatch_rate": 0.0,
}

_ALLOWED_SOURCE_TYPES = {"textbook", "solution_book"}
_REQUIRED_CITATION_FIELDS = (
    "chunk_id",
    "source_id",
    "source_type",
    "printed_page_start",
    "printed_page_end",
    "unit_id",
    "lesson_id",
    "quality_status",
    "reviewed_metadata_version",
    "score",
)


class EvaluationDatasetError(ValueError):
    def __init__(self, detail: str) -> None:
        self.code = EVALUATION_DATASET_INVALID
        self.detail = detail
        super().__init__(f"{self.code}: {detail}")


@dataclass
class RagEvaluationResult:
    """Serializable evaluation/blocked-gate report."""

    status: str
    passed: bool
    reviewed_metadata_version: str
    embedding_model: str
    preconditions: dict[str, Any]
    metrics: dict[str, Any]
    threshold_failures: list[str]
    failed_cases: list[dict[str, Any]]
    cases: list[dict[str, Any]]
    report_json_path: str
    report_markdown_path: str


def resolve_project_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    return candidate if candidate.is_absolute() else PROJECT_DIR / candidate


def _int_list(value: Any, field_name: str) -> list[int]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise EvaluationDatasetError(f"{field_name} must be a list")
    try:
        return [int(item) for item in value]
    except (TypeError, ValueError) as exc:
        raise EvaluationDatasetError(f"{field_name} must contain integers") from exc


def _string_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise EvaluationDatasetError(f"{field_name} must be a list")
    values = [str(item).strip() for item in value if str(item).strip()]
    if field_name == "expected_source_types" and any(item not in _ALLOWED_SOURCE_TYPES for item in values):
        raise EvaluationDatasetError(f"{field_name} contains an unsupported source type")
    return values


def load_eval_cases(path: str | Path) -> list[dict[str, Any]]:
    resolved = resolve_project_path(path)
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        raise EvaluationDatasetError(f"Could not read valid JSON from {resolved}") from exc
    cases = payload.get("cases", []) if isinstance(payload, dict) else payload
    if not isinstance(cases, list) or not cases:
        raise EvaluationDatasetError("dataset must contain a non-empty cases list")

    normalized_cases: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_case in enumerate(cases, start=1):
        if not isinstance(raw_case, dict):
            raise EvaluationDatasetError(f"case #{index} must be an object")
        case_id = str(raw_case.get("id") or "").strip()
        query = str(raw_case.get("query") or "").strip()
        if not case_id or not query:
            raise EvaluationDatasetError(f"case #{index} requires id and query")
        if case_id in seen_ids:
            raise EvaluationDatasetError(f"duplicate case id: {case_id}")
        seen_ids.add(case_id)

        printed_pages = _int_list(raw_case.get("expected_printed_pages"), "expected_printed_pages")
        pdf_pages = _int_list(raw_case.get("expected_pdf_pages"), "expected_pdf_pages")
        if "expected_pages" in raw_case:
            legacy_pages = _int_list(raw_case.get("expected_pages"), "expected_pages")
            number_type = str(raw_case.get("page_number_type") or "").strip()
            if number_type not in {"printed", "pdf"}:
                raise EvaluationDatasetError(
                    f"case {case_id}: expected_pages requires page_number_type=printed|pdf"
                )
            if number_type == "printed":
                printed_pages = printed_pages or legacy_pages
            else:
                pdf_pages = pdf_pages or legacy_pages

        normalized = {
            **raw_case,
            "id": case_id,
            "query": query,
            "expected_printed_pages": printed_pages,
            "expected_pdf_pages": pdf_pages,
            "expected_unit_ids": _string_list(raw_case.get("expected_unit_ids"), "expected_unit_ids"),
            "expected_lesson_ids": _string_list(raw_case.get("expected_lesson_ids"), "expected_lesson_ids"),
            "expected_source_types": _string_list(
                raw_case.get("expected_source_types"), "expected_source_types"
            ),
            "expected_keywords": _string_list(raw_case.get("expected_keywords"), "expected_keywords"),
        }
        if not any(
            normalized[field]
            for field in (
                "expected_printed_pages",
                "expected_pdf_pages",
                "expected_unit_ids",
                "expected_lesson_ids",
                "expected_source_types",
                "expected_keywords",
            )
        ):
            raise EvaluationDatasetError(f"case {case_id} has no verifiable expectation")
        normalized_cases.append(normalized)
    return normalized_cases


def _metadata_dict(raw: Any) -> dict[str, Any]:
    return dict(raw) if isinstance(raw, dict) else {}


def _chunk_metadata(chunk: RetrievedChunk) -> dict[str, Any]:
    return {
        **_metadata_dict(chunk.metadata_json),
        **_metadata_dict(chunk.curriculum_metadata),
        "source_type": chunk.source_type,
        "unit_id": chunk.unit_id,
        "lesson_id": chunk.lesson_id,
        "quality_status": chunk.quality_status,
        "reviewed_metadata_version": chunk.reviewed_metadata_version,
    }


def _range_intersects(start: Any, end: Any, expected: list[int]) -> bool:
    if not expected or start is None:
        return False
    try:
        start_int = int(start)
        end_int = int(end if end is not None else start)
    except (TypeError, ValueError):
        return False
    low, high = sorted((start_int, end_int))
    return any(low <= page <= high for page in expected)


def _expected_rank(chunks: list[RetrievedChunk], field_prefix: str, expected: list[int]) -> int | None:
    for rank, chunk in enumerate(chunks, start=1):
        metadata = _chunk_metadata(chunk)
        if _range_intersects(
            metadata.get(f"{field_prefix}_page_start"),
            metadata.get(f"{field_prefix}_page_end"),
            expected,
        ):
            return rank
    return None


def _stable_id_hit(chunks: list[RetrievedChunk], field: str, expected: list[str]) -> bool:
    if not expected:
        return True
    wanted = set(expected)
    return any(str(_chunk_metadata(chunk).get(field) or "") in wanted for chunk in chunks)


def _contains_keyword(chunks: list[RetrievedChunk], keyword: str) -> bool:
    text = "\n".join(chunk.content for chunk in chunks).lower()
    return keyword.lower() in text


def _citation_payload(chunk: RetrievedChunk) -> dict[str, Any]:
    metadata = _chunk_metadata(chunk)
    return {
        "chunk_id": chunk.id,
        "source_id": chunk.source_id,
        "source_type": chunk.source_type,
        "printed_page_start": metadata.get("printed_page_start") or chunk.page_number,
        "printed_page_end": metadata.get("printed_page_end") or chunk.page_number,
        "pdf_page_start": metadata.get("pdf_page_start"),
        "pdf_page_end": metadata.get("pdf_page_end"),
        "unit_id": metadata.get("unit_id"),
        "lesson_id": metadata.get("lesson_id"),
        "quality_status": metadata.get("quality_status"),
        "reviewed_metadata_version": metadata.get("reviewed_metadata_version"),
        "stale": bool(metadata.get("stale") is True),
        "content_type": chunk.content_type,
        "score": round(float(chunk.similarity_score), 6),
        "preview": chunk.content[:180],
    }


def _missing_citation_fields(citation: dict[str, Any]) -> list[str]:
    return [field for field in _REQUIRED_CITATION_FIELDS if citation.get(field) in (None, "", [])]


async def build_evaluation_preconditions(db: AsyncSession) -> dict[str, Any]:
    """Check current-version eligible vector completeness without provider calls."""

    issues: list[str] = []
    active_version = active_reviewed_metadata_version()
    try:
        reviewed = load_reviewed_curriculum_metadata(require_ready=True)
    except ReviewedCurriculumMetadataError as exc:
        reviewed = {}
        issues.append(exc.code)
    reviewed_version = str(reviewed.get("version") or "")
    if not active_version or reviewed_version != active_version:
        issues.append(REVIEWED_METADATA_VERSION_MISMATCH)

    rows = list((await db.execute(select(RagChunk).order_by(RagChunk.id.asc()))).scalars().all())
    counts = {
        "database_chunks": len(rows),
        "eligible_chunks": 0,
        "completed_embeddings": 0,
        "incomplete_embeddings": 0,
        "blocked_chunks_excluded": 0,
        "stale_chunks_excluded": 0,
        "invalid_chunks_excluded": 0,
        "missing_version_chunks_excluded": 0,
        "wrong_version_chunks": 0,
        "model_mismatch_chunks": 0,
        "wrong_dimension_chunks": 0,
    }

    for chunk in rows:
        metadata = _metadata_dict(chunk.metadata_json)
        if metadata.get("stale") is True:
            counts["stale_chunks_excluded"] += 1
            continue
        decision = evaluate_chunk_eligibility(
            chunk,
            reviewed,
            legacy=chunk.extraction_method != "reviewed_jsonl",
        ) if reviewed else None
        if decision and decision.normalized_quality_status == "blocked":
            counts["blocked_chunks_excluded"] += 1
            continue
        if not decision or not decision.embedding_allowed or not decision.rag_search_allowed:
            counts["invalid_chunks_excluded"] += 1
            continue
        raw_version = str(metadata.get("reviewed_metadata_version") or "")
        if not raw_version:
            counts["missing_version_chunks_excluded"] += 1
            continue
        if raw_version != active_version:
            counts["wrong_version_chunks"] += 1
            continue

        counts["eligible_chunks"] += 1
        vector = chunk.embedding
        complete = chunk.embedding_status == "completed" and vector is not None
        if complete:
            counts["completed_embeddings"] += 1
            if chunk.embedding_model != settings.gemini_embedding_model:
                counts["model_mismatch_chunks"] += 1
            try:
                if len(vector) != settings.embedding_dimension:
                    counts["wrong_dimension_chunks"] += 1
            except TypeError:
                counts["wrong_dimension_chunks"] += 1
        else:
            counts["incomplete_embeddings"] += 1

    if counts["eligible_chunks"] == 0:
        issues.append(EMBEDDING_INDEX_EMPTY)
    if counts["incomplete_embeddings"]:
        issues.append(EMBEDDING_INDEX_INCOMPLETE)
    if counts["model_mismatch_chunks"] or counts["wrong_dimension_chunks"]:
        issues.append(EMBEDDING_MODEL_MISMATCH)
    if counts["wrong_version_chunks"] or counts["missing_version_chunks_excluded"]:
        issues.append(REVIEWED_METADATA_VERSION_MISMATCH)

    issues = list(dict.fromkeys(issues))
    return {
        "status": "ready" if not issues else "blocked",
        "ready": not issues,
        "reviewed_metadata_ready": bool(reviewed),
        "active_reviewed_metadata_version": active_version,
        "reviewed_metadata_version": reviewed_version or None,
        "required_embedding_model": settings.gemini_embedding_model,
        "required_embedding_dimension": settings.embedding_dimension,
        "counts": counts,
        "blocking_issues": issues,
    }


def _threshold_failures(metrics: dict[str, Any]) -> list[str]:
    checks = (
        ("top5_expected_printed_page_hit_rate", "below"),
        ("no_result_rate", "above"),
        ("wrong_source_rate", "above"),
        ("low_confidence_rate", "above"),
        ("average_retrieval_latency_ms", "above"),
        ("required_curriculum_metadata_completeness", "below"),
        ("blocked_or_stale_result_rate", "above"),
        ("reviewed_version_mismatch_rate", "above"),
    )
    failures: list[str] = []
    for metric, direction in checks:
        lookup_metric = metric
        if metric == "top5_expected_printed_page_hit_rate" and metric not in metrics:
            lookup_metric = "top5_expected_page_hit_rate"
        if lookup_metric not in metrics:
            continue
        value = float(metrics.get(lookup_metric) or 0.0)
        threshold = float(THRESHOLDS[metric])
        failed = value < threshold if direction == "below" else value > threshold
        if failed:
            failures.append(f"{metric}_{direction}_threshold")
    return failures


def _markdown_report(result: RagEvaluationResult) -> str:
    lines = [
        "# Grade 9 RAG Retrieval Evaluation",
        "",
        f"Status: `{result.status}`",
        f"Reviewed metadata: `{result.reviewed_metadata_version}`",
        f"Embedding model: `{result.embedding_model}`",
        "",
        "## Preconditions",
        "",
    ]
    lines.extend(f"- `{key}`: `{value}`" for key, value in result.preconditions.items() if key != "counts")
    for key, value in (result.preconditions.get("counts") or {}).items():
        lines.append(f"- `counts.{key}`: `{value}`")
    lines.extend(["", "## Metrics", ""])
    lines.extend(f"- `{key}`: `{value}`" for key, value in result.metrics.items())
    lines.extend(["", "## Failures", ""])
    lines.extend(f"- `{item}`" for item in result.threshold_failures)
    if not result.threshold_failures:
        lines.append("- None")
    lines.extend(["", "## Failed Cases", ""])
    for case in result.failed_cases:
        lines.append(f"- `{case.get('id')}`: {', '.join(case.get('failure_reasons') or [])}")
    if not result.failed_cases:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def _write_result(result: RagEvaluationResult) -> RagEvaluationResult:
    json_path = Path(result.report_json_path)
    md_path = Path(result.report_markdown_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_markdown_report(result), encoding="utf-8")
    return result


async def evaluate_rag_dataset(
    db: AsyncSession,
    *,
    dataset_path: str | Path = "data/eval/rag_gold_questions.json",
    report_dir: str | Path = "data/eval/reports",
    top_k: int = 5,
    min_similarity: float = 0.45,
) -> RagEvaluationResult:
    """Run the live retrieval gate only after the eligible index is complete."""

    report_dir_path = resolve_project_path(report_dir)
    json_path = report_dir_path / "rag_eval_latest.json"
    md_path = report_dir_path / "rag_eval_latest.md"
    version = active_reviewed_metadata_version()
    preconditions = await build_evaluation_preconditions(db)
    try:
        cases = load_eval_cases(dataset_path)
    except EvaluationDatasetError as exc:
        preconditions = {
            **preconditions,
            "status": "blocked",
            "ready": False,
            "dataset_error": exc.detail,
            "blocking_issues": list(
                dict.fromkeys([*(preconditions.get("blocking_issues") or []), exc.code])
            ),
        }
        return _write_result(
            RagEvaluationResult(
                status="blocked",
                passed=False,
                reviewed_metadata_version=version,
                embedding_model=settings.gemini_embedding_model,
                preconditions=preconditions,
                metrics={"dataset_case_count": 0, "thresholds": THRESHOLDS},
                threshold_failures=list(preconditions["blocking_issues"]),
                failed_cases=[],
                cases=[],
                report_json_path=str(json_path),
                report_markdown_path=str(md_path),
            )
        )

    if not preconditions["ready"]:
        return _write_result(
            RagEvaluationResult(
                status="blocked",
                passed=False,
                reviewed_metadata_version=version,
                embedding_model=settings.gemini_embedding_model,
                preconditions=preconditions,
                metrics={"dataset_case_count": len(cases), "thresholds": THRESHOLDS},
                threshold_failures=list(preconditions["blocking_issues"]),
                failed_cases=[],
                cases=[],
                report_json_path=str(json_path),
                report_markdown_path=str(md_path),
            )
        )

    evaluated: list[dict[str, Any]] = []
    latencies: list[int] = []
    no_result = low_confidence = wrong_source = 0
    printed_page_cases = printed_page_hits = 0
    keyword_hits = 0
    citation_count = complete_citations = blocked_or_stale = version_mismatch = 0

    for case in cases:
        start = time.monotonic()
        chunks = await retrieve_context(
            db,
            query=case["query"],
            source_types=case.get("source_types"),
            top_k=top_k,
            min_similarity=min_similarity,
            intent=case.get("expected_answer_type") or "general",
            log_retrieval=False,
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        latencies.append(latency_ms)
        citations = [_citation_payload(chunk) for chunk in chunks]
        citation_count += len(citations)
        complete_citations += sum(not _missing_citation_fields(citation) for citation in citations)
        blocked_or_stale += sum(
            citation.get("quality_status") == "blocked" or citation.get("stale") is True
            for citation in citations
        )
        version_mismatch += sum(
            citation.get("reviewed_metadata_version") != version for citation in citations
        )

        expected_printed = case["expected_printed_pages"]
        expected_pdf = case["expected_pdf_pages"]
        printed_rank = _expected_rank(chunks, "printed", expected_printed) if expected_printed else None
        pdf_rank = _expected_rank(chunks, "pdf", expected_pdf) if expected_pdf else None
        top_score = float(chunks[0].similarity_score) if chunks else 0.0
        source_hit = (
            any(chunk.source_type in set(case["expected_source_types"]) for chunk in chunks)
            if case["expected_source_types"]
            else True
        )
        keyword_hit = all(_contains_keyword(chunks, keyword) for keyword in case["expected_keywords"])
        unit_hit = _stable_id_hit(chunks, "unit_id", case["expected_unit_ids"])
        lesson_hit = _stable_id_hit(chunks, "lesson_id", case["expected_lesson_ids"])

        if expected_printed:
            printed_page_cases += 1
            if printed_rank is not None and printed_rank <= 5:
                printed_page_hits += 1
        if not chunks:
            no_result += 1
        if top_score < float(case.get("min_top1_similarity", min_similarity)):
            low_confidence += 1
        if chunks and case["expected_source_types"] and chunks[0].source_type not in set(case["expected_source_types"]):
            wrong_source += 1
        if keyword_hit:
            keyword_hits += 1

        reasons: list[str] = []
        if not chunks:
            reasons.append("no_result")
        if expected_printed and (printed_rank is None or printed_rank > 5):
            reasons.append("expected_printed_page_not_in_top5")
        if expected_pdf and pdf_rank is None:
            reasons.append("expected_pdf_page_not_found")
        if not source_hit:
            reasons.append("expected_source_type_not_found")
        if not unit_hit:
            reasons.append("expected_unit_not_found")
        if not lesson_hit:
            reasons.append("expected_lesson_not_found")
        if not keyword_hit:
            reasons.append("expected_keyword_not_found")
        if any(_missing_citation_fields(citation) for citation in citations):
            reasons.append("citation_metadata_incomplete")
        if any(citation.get("quality_status") == "blocked" or citation.get("stale") for citation in citations):
            reasons.append("blocked_or_stale_result")
        if any(citation.get("reviewed_metadata_version") != version for citation in citations):
            reasons.append("reviewed_metadata_version_mismatch")

        evaluated.append(
            {
                "id": case["id"],
                "query": case["query"],
                "expected_printed_pages": expected_printed,
                "expected_pdf_pages": expected_pdf,
                "expected_unit_ids": case["expected_unit_ids"],
                "expected_lesson_ids": case["expected_lesson_ids"],
                "expected_source_types": case["expected_source_types"],
                "printed_page_rank": printed_rank,
                "pdf_page_rank": pdf_rank,
                "top_score": round(top_score, 4),
                "source_type_hit": source_hit,
                "unit_hit": unit_hit,
                "lesson_hit": lesson_hit,
                "keyword_hit": keyword_hit,
                "latency_ms": latency_ms,
                "passed": not reasons,
                "failure_reasons": reasons,
                "retrieved": citations,
            }
        )

    total = max(len(cases), 1)
    citation_denominator = max(citation_count, 1)
    printed_rate = round(printed_page_hits / max(printed_page_cases, 1), 4)
    metrics = {
        "dataset_case_count": len(cases),
        "printed_page_expectation_case_count": printed_page_cases,
        "top5_expected_printed_page_hit_rate": printed_rate,
        "top5_expected_page_hit_rate": printed_rate,
        "keyword_hit_rate": round(keyword_hits / total, 4),
        "no_result_rate": round(no_result / total, 4),
        "low_confidence_rate": round(low_confidence / total, 4),
        "wrong_source_rate": round(wrong_source / total, 4),
        "average_retrieval_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
        "required_curriculum_metadata_completeness": round(complete_citations / citation_denominator, 4),
        "blocked_or_stale_result_rate": round(blocked_or_stale / citation_denominator, 4),
        "reviewed_version_mismatch_rate": round(version_mismatch / citation_denominator, 4),
        "thresholds": THRESHOLDS,
    }
    failures = _threshold_failures(metrics)
    failed_cases = [case for case in evaluated if not case["passed"]]
    result = RagEvaluationResult(
        status="passed" if not failures else "failed",
        passed=not failures,
        reviewed_metadata_version=version,
        embedding_model=settings.gemini_embedding_model,
        preconditions=preconditions,
        metrics=metrics,
        threshold_failures=failures,
        failed_cases=failed_cases,
        cases=evaluated,
        report_json_path=str(json_path),
        report_markdown_path=str(md_path),
    )
    return _write_result(result)
