"""RAG retrieval evaluation utilities used by CLI and admin APIs."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import PROJECT_DIR
from app.services.rag import RetrievedChunk, retrieve_context

THRESHOLDS = {
    "top5_expected_page_hit_rate": 0.80,
    "no_result_rate": 0.10,
    "wrong_source_rate": 0.15,
    "low_confidence_rate": 0.25,
    "average_retrieval_latency_ms": 1500,
}


@dataclass
class RagEvaluationResult:
    """Serializable RAG evaluation result."""

    passed: bool
    metrics: dict[str, Any]
    cases: list[dict[str, Any]]
    threshold_failures: list[str]
    report_json_path: str
    report_markdown_path: str


def resolve_project_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    return candidate if candidate.is_absolute() else PROJECT_DIR / candidate


def load_eval_cases(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(resolve_project_path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        cases = payload.get("cases", [])
    else:
        cases = payload
    if not isinstance(cases, list):
        raise ValueError("RAG eval dataset must contain a list or {'cases': [...]}.")
    return cases


def _contains_keyword(chunks: list[RetrievedChunk], keyword: str) -> bool:
    text = "\n".join(chunk.content for chunk in chunks).lower()
    return keyword.lower() in text


def _expected_page_rank(chunks: list[RetrievedChunk], expected_pages: list[int]) -> int | None:
    expected = {int(page) for page in expected_pages}
    for rank, chunk in enumerate(chunks, start=1):
        if chunk.page_number in expected:
            return rank
    return None


def _source_type_hit(chunks: list[RetrievedChunk], expected_source_types: list[str]) -> bool:
    expected = set(expected_source_types)
    return any(chunk.source_type in expected for chunk in chunks)


def _top_source_wrong(chunks: list[RetrievedChunk], expected_source_types: list[str]) -> bool:
    if not chunks:
        return False
    return chunks[0].source_type not in set(expected_source_types)


def _markdown_report(result: RagEvaluationResult) -> str:
    metrics = result.metrics
    lines = [
        "# RAG Evaluation Report",
        "",
        f"Passed: `{result.passed}`",
        "",
        "## Metrics",
        "",
    ]
    for key, value in metrics.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Threshold Failures", ""])
    if result.threshold_failures:
        lines.extend(f"- {item}" for item in result.threshold_failures)
    else:
        lines.append("- None")
    lines.extend(["", "## Cases", ""])
    for case in result.cases:
        lines.append(
            f"- `{case['id']}`: top_score=`{case.get('top_score')}`, "
            f"expected_page_rank=`{case.get('expected_page_rank')}`, "
            f"source_hit=`{case.get('source_type_hit')}`, keyword_hit=`{case.get('keyword_hit')}`"
        )
    return "\n".join(lines) + "\n"


def _threshold_failures(metrics: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if metrics["top5_expected_page_hit_rate"] < THRESHOLDS["top5_expected_page_hit_rate"]:
        failures.append("top5_expected_page_hit_rate below threshold")
    if metrics["no_result_rate"] > THRESHOLDS["no_result_rate"]:
        failures.append("no_result_rate above threshold")
    if metrics["wrong_source_rate"] > THRESHOLDS["wrong_source_rate"]:
        failures.append("wrong_source_rate above threshold")
    if metrics["low_confidence_rate"] > THRESHOLDS["low_confidence_rate"]:
        failures.append("low_confidence_rate above threshold")
    if metrics["average_retrieval_latency_ms"] > THRESHOLDS["average_retrieval_latency_ms"]:
        failures.append("average_retrieval_latency_ms above threshold")
    return failures


async def evaluate_rag_dataset(
    db: AsyncSession,
    *,
    dataset_path: str | Path = "data/eval/rag_gold_questions.json",
    report_dir: str | Path = "data/eval/reports",
    top_k: int = 5,
    min_similarity: float = 0.45,
) -> RagEvaluationResult:
    """Run retrieval evaluation and write latest JSON/Markdown reports."""
    cases = load_eval_cases(dataset_path)
    evaluated: list[dict[str, Any]] = []
    latencies: list[int] = []
    no_result = 0
    low_confidence = 0
    wrong_source = 0
    top1_hits = 0
    top3_hits = 0
    top5_hits = 0
    keyword_hits = 0
    reciprocal_ranks: list[float] = []

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
        expected_pages = [int(page) for page in case.get("expected_pages", [])]
        expected_source_types = case.get("expected_source_types", [])
        rank = _expected_page_rank(chunks, expected_pages) if expected_pages else None
        top_score = float(chunks[0].similarity_score) if chunks else 0.0
        keyword_hit = all(_contains_keyword(chunks, keyword) for keyword in case.get("expected_keywords", []))
        source_hit = _source_type_hit(chunks, expected_source_types) if expected_source_types else True

        if not chunks:
            no_result += 1
        if top_score < float(case.get("min_top1_similarity", min_similarity)):
            low_confidence += 1
        if expected_source_types and _top_source_wrong(chunks, expected_source_types):
            wrong_source += 1
        if rank == 1:
            top1_hits += 1
        if rank is not None and rank <= 3:
            top3_hits += 1
        if rank is not None and rank <= 5:
            top5_hits += 1
        if rank:
            reciprocal_ranks.append(1 / rank)
        if keyword_hit:
            keyword_hits += 1

        evaluated.append(
            {
                "id": case["id"],
                "query": case["query"],
                "expected_pages": expected_pages,
                "expected_source_types": expected_source_types,
                "expected_page_rank": rank,
                "top_score": round(top_score, 4),
                "source_type_hit": source_hit,
                "keyword_hit": keyword_hit,
                "latency_ms": latency_ms,
                "retrieved": [
                    {
                        "chunk_id": chunk.id,
                        "source_type": chunk.source_type,
                        "page_number": chunk.page_number,
                        "content_type": chunk.content_type,
                        "score": chunk.similarity_score,
                        "preview": chunk.content[:160],
                    }
                    for chunk in chunks
                ],
            }
        )

    total = max(len(cases), 1)
    metrics = {
        "case_count": len(cases),
        "top1_expected_page_hit_rate": round(top1_hits / total, 4),
        "top3_expected_page_hit_rate": round(top3_hits / total, 4),
        "top5_expected_page_hit_rate": round(top5_hits / total, 4),
        "keyword_hit_rate": round(keyword_hits / total, 4),
        "mrr": round(sum(reciprocal_ranks) / total, 4),
        "no_result_rate": round(no_result / total, 4),
        "low_confidence_rate": round(low_confidence / total, 4),
        "wrong_source_rate": round(wrong_source / total, 4),
        "average_retrieval_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,
        "thresholds": THRESHOLDS,
    }
    failures = _threshold_failures(metrics)
    report_dir_path = resolve_project_path(report_dir)
    report_dir_path.mkdir(parents=True, exist_ok=True)
    json_path = report_dir_path / "rag_eval_latest.json"
    md_path = report_dir_path / "rag_eval_latest.md"
    result = RagEvaluationResult(
        passed=not failures,
        metrics=metrics,
        cases=evaluated,
        threshold_failures=failures,
        report_json_path=str(json_path),
        report_markdown_path=str(md_path),
    )
    json_path.write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_markdown_report(result), encoding="utf-8")
    return result
