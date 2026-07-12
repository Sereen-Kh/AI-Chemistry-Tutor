#!/usr/bin/env python3
"""Run RAG-008 after eligibility-aware vector preconditions pass."""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict
import json
from pathlib import Path
import shutil
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database import AsyncSessionLocal  # noqa: E402
from app.services.rag_evaluation import evaluate_rag_dataset  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the eligibility-aware Grade 9 RAG retrieval gate.")
    parser.add_argument("--dataset", default="data/eval/rag_gold_questions.json")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-similarity", type=float, default=0.45)
    return parser.parse_args()


async def run() -> int:
    args = parse_args()
    async with AsyncSessionLocal() as db:
        result = await evaluate_rag_dataset(
            db,
            dataset_path=args.dataset,
            report_dir="data/eval/reports",
            top_k=args.top_k,
            min_similarity=args.min_similarity,
        )

    stable_dir = PROJECT_DIR / "reports" / "rag"
    stable_dir.mkdir(parents=True, exist_ok=True)
    stable_json = stable_dir / "rag_evaluation_report.json"
    stable_md = stable_dir / "rag_evaluation_report.md"
    shutil.copyfile(result.report_json_path, stable_json)
    shutil.copyfile(result.report_markdown_path, stable_md)

    payload = asdict(result)
    print(
        json.dumps(
            {
                "status": result.status,
                "reviewed_metadata_version": result.reviewed_metadata_version,
                "embedding_model": result.embedding_model,
                "preconditions": result.preconditions,
                "metrics": result.metrics,
                "threshold_failures": result.threshold_failures,
                "report_json_path": str(stable_json),
                "report_markdown_path": str(stable_md),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
