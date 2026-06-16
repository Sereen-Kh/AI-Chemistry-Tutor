#!/usr/bin/env python3
"""Run the EduMind RAG gold-question evaluation suite."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.database import AsyncSessionLocal  # noqa: E402
from app.services.rag_evaluation import evaluate_rag_dataset  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate EduMind RAG retrieval quality.")
    parser.add_argument("--dataset", default="data/eval/rag_gold_questions.json")
    parser.add_argument("--report-dir", default="data/eval/reports")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-similarity", type=float, default=0.45)
    parser.add_argument("--fail-on-threshold", action="store_true")
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    async with AsyncSessionLocal() as db:
        result = await evaluate_rag_dataset(
            db,
            dataset_path=args.dataset,
            report_dir=args.report_dir,
            top_k=args.top_k,
            min_similarity=args.min_similarity,
        )
    print(f"RAG eval report JSON: {result.report_json_path}")
    print(f"RAG eval report Markdown: {result.report_markdown_path}")
    print(f"Passed: {result.passed}")
    if result.threshold_failures:
        print("Threshold failures:")
        for failure in result.threshold_failures:
            print(f"- {failure}")
    if args.fail_on_threshold and not result.passed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
