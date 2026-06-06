"""Evaluate RAG retrieval against a JSON benchmark file.

Run from the backend directory:
    EMBEDDING_PROVIDER=local_hash .venv/bin/python -m scripts.evaluate_rag_retrieval
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import re
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database import AsyncSessionLocal  # noqa: E402
from app.services.chunking import normalize_arabic, normalize_formula  # noqa: E402
from app.services.rag import retrieve_context  # noqa: E402

DEFAULT_EVAL_FILE = PROJECT_DIR / "data" / "textbooks" / "syria_grade_9_chemistry" / "benchmarks" / "rag_eval_queries.json"
_ARABIC_DIACRITICS_RE = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")


def _norm(text: str) -> str:
    lowered = _ARABIC_DIACRITICS_RE.sub("", normalize_arabic(str(text).lower()))
    lowered = normalize_formula(lowered)
    lowered = lowered.replace("اال", "ال")
    lowered = lowered.replace("السيتون", "الاسيتون")
    lowered = lowered.replace("طالء", "طلاء")
    lowered = lowered.replace("الظافر", "الاظافر")
    return re.sub(r"\s+", " ", lowered).strip()


def _resolve_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate
    project_candidate = PROJECT_DIR / candidate
    if project_candidate.exists():
        return project_candidate
    return candidate.resolve()


def _keyword_hits(must_contain: list[str], retrieved_text: str) -> list[str]:
    normalized_text = _norm(retrieved_text)
    hits = []
    for keyword in must_contain:
        if _norm(keyword) in normalized_text:
            hits.append(keyword)
    return hits


async def evaluate(input_path: Path, output_path: Path | None, top_k: int) -> dict:
    cases = json.loads(input_path.read_text(encoding="utf-8"))
    results = []
    recall_hits = 0
    keyword_full_hits = 0
    mrr_total = 0.0

    async with AsyncSessionLocal() as db:
        for case in cases:
            diagnostics: dict = {}
            chunks = await retrieve_context(
                db,
                query=case["question"],
                source_types=["textbook"],
                top_k=top_k,
                min_similarity=0.0,
                intent=case.get("intent", "general"),
                diagnostics_callback=diagnostics.update,
            )
            retrieved_pages = [chunk.page_number for chunk in chunks if chunk.page_number is not None]
            expected_pages = set(case.get("expected_pages") or [])
            first_rank = next(
                (index + 1 for index, page in enumerate(retrieved_pages) if page in expected_pages),
                None,
            )
            page_hit = first_rank is not None
            if page_hit:
                recall_hits += 1
                mrr_total += 1.0 / float(first_rank)

            retrieved_text = "\n\n".join(chunk.content for chunk in chunks)
            hits = _keyword_hits(case.get("must_contain") or [], retrieved_text)
            keyword_hit = len(hits) == len(case.get("must_contain") or [])
            if keyword_hit:
                keyword_full_hits += 1

            results.append(
                {
                    "id": case.get("id"),
                    "question": case["question"],
                    "intent": case.get("intent", "general"),
                    "expected_pages": sorted(expected_pages),
                    "retrieved_pages": retrieved_pages,
                    "page_hit": page_hit,
                    "first_expected_rank": first_rank,
                    "must_contain": case.get("must_contain") or [],
                    "must_contain_hits": hits,
                    "must_contain_full_hit": keyword_hit,
                    "top_chunks": [
                        {
                            "chunk_id": chunk.id,
                            "page_number": chunk.page_number,
                            "content_type": chunk.content_type,
                            "similarity_score": chunk.similarity_score,
                            "snippet": chunk.content[:220].replace("\n", " "),
                        }
                        for chunk in chunks
                    ],
                    "diagnostics": diagnostics,
                }
            )

    total = len(cases)
    summary = {
        "total_cases": total,
        "top_k": top_k,
        "page_recall_at_k": round(recall_hits / total, 4) if total else 0.0,
        "keyword_full_hit_rate": round(keyword_full_hits / total, 4) if total else 0.0,
        "mrr": round(mrr_total / total, 4) if total else 0.0,
        "page_hits": recall_hits,
        "keyword_full_hits": keyword_full_hits,
    }
    payload = {"summary": summary, "results": results}
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


async def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate RAG retrieval quality.")
    parser.add_argument("--input", default=str(DEFAULT_EVAL_FILE))
    parser.add_argument("--output", default=None)
    parser.add_argument("--top-k", type=int, default=6)
    args = parser.parse_args()

    input_path = _resolve_path(args.input)
    output_path = _resolve_path(args.output) if args.output else None
    payload = await evaluate(input_path, output_path, args.top_k)
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    if output_path:
        print(f"Wrote detailed results to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
