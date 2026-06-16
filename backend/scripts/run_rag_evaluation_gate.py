#!/usr/bin/env python3
"""CI/staging RAG evaluation gate with explicit empty-index handling."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from hardening_reports import BACKEND_DIR, PROJECT_ROOT, bool_env, status_line, write_reports

sys.path.insert(0, str(BACKEND_DIR))

from app.database import AsyncSessionLocal  # noqa: E402
from app.models.textbook import RagChunk  # noqa: E402
from app.services.rag_evaluation import evaluate_rag_dataset  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run RAG evaluation as a quality gate.")
    parser.add_argument("--dataset", default="data/eval/rag_gold_questions.json")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-similarity", type=float, default=float(os.getenv("RAG_EVAL_MIN_TOP_SCORE", "0.50")))
    return parser.parse_args()


def _report_paths() -> tuple[Path, Path]:
    report_dir = PROJECT_ROOT / "reports" / "rag"
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir / "rag_evaluation_report.json", report_dir / "rag_evaluation_report.md"


def _write_empty_index_report(mode: str, allow: bool) -> int:
    result = "skipped" if allow else "failed"
    payload: dict[str, Any] = {
        "result": result,
        "mode": mode,
        "reason": "rag_chunks table has zero indexed chunks",
        "allow_empty_index_in_ci": allow,
        "thresholds": {
            "RAG_EVAL_MIN_HIT_RATE": os.getenv("RAG_EVAL_MIN_HIT_RATE", "0.80"),
            "RAG_EVAL_MIN_TOP_SCORE": os.getenv("RAG_EVAL_MIN_TOP_SCORE", "0.50"),
            "RAG_EVAL_REQUIRED_SOURCE_METADATA": os.getenv("RAG_EVAL_REQUIRED_SOURCE_METADATA", "true"),
        },
    }
    json_path, md_path = _report_paths()
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                "# RAG Evaluation Gate",
                "",
                f"Result: `{result}`",
                "",
                "## Reason",
                "",
                "- The `rag_chunks` table has zero indexed chunks.",
                f"- `RAG_EVAL_ALLOW_EMPTY_INDEX_IN_CI`: `{allow}`",
                "",
                "This is allowed only for explicit CI/mock runs. Staging and production must fail on an empty index.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return 0 if allow else 1


async def run() -> int:
    args = parse_args()
    allow_empty_ci = bool_env("RAG_EVAL_ALLOW_EMPTY_INDEX_IN_CI")
    async with AsyncSessionLocal() as db:
        try:
            chunk_count = int(await db.scalar(select(func.count(RagChunk.id))) or 0)
        except SQLAlchemyError:
            chunk_count = 0
        if chunk_count == 0:
            return _write_empty_index_report("empty_index", allow_empty_ci)

        temp_dir = PROJECT_ROOT / "reports" / "rag" / "_raw"
        result = await evaluate_rag_dataset(
            db,
            dataset_path=args.dataset,
            report_dir=temp_dir,
            top_k=args.top_k,
            min_similarity=args.min_similarity,
        )
    json_path, md_path = _report_paths()
    shutil.copyfile(result.report_json_path, json_path)
    shutil.copyfile(result.report_markdown_path, md_path)

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    metrics = payload.get("metrics", {})
    failures = list(payload.get("threshold_failures") or [])
    min_hit_rate = float(os.getenv("RAG_EVAL_MIN_HIT_RATE", "0.80"))
    min_top_score = float(os.getenv("RAG_EVAL_MIN_TOP_SCORE", "0.50"))
    required_metadata = bool_env("RAG_EVAL_REQUIRED_SOURCE_METADATA", True)

    if metrics.get("top5_expected_page_hit_rate", 0) < min_hit_rate:
        failures.append("top5 expected page hit rate below RAG_EVAL_MIN_HIT_RATE")
    for case in payload.get("cases", []):
        if case.get("retrieved") and float(case["retrieved"][0].get("score") or 0) < min_top_score:
            failures.append(f"{case.get('id')} top score below RAG_EVAL_MIN_TOP_SCORE")
        if required_metadata:
            for item in case.get("retrieved", []):
                if item.get("page_number") is None or not item.get("source_type"):
                    failures.append(f"{case.get('id')} result missing source/page metadata")
                    break

    payload["result"] = "passed" if not failures else "failed"
    payload["threshold_failures"] = sorted(set(failures))
    payload["ci_gate"] = {
        "chunk_count": chunk_count,
        "min_hit_rate": min_hit_rate,
        "min_top_score": min_top_score,
        "required_source_metadata": required_metadata,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_reports(
        report_subdir="rag",
        report_name="rag_evaluation_report_summary",
        title="RAG Evaluation Gate Summary",
        payload=payload,
        sections=[
            (
                "Metrics",
                [status_line(key, value) for key, value in metrics.items()],
            ),
            ("Threshold Failures", [f"- {item}" for item in payload["threshold_failures"]] or ["- None"]),
        ],
    )
    # Keep the requested Markdown file name stable.
    generated_md = PROJECT_ROOT / "reports" / "rag" / "rag_evaluation_report_summary.md"
    if generated_md.exists():
        shutil.copyfile(generated_md, md_path)
    for failure in payload["threshold_failures"]:
        print(f"ERROR: {failure}")
    return 0 if not payload["threshold_failures"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
