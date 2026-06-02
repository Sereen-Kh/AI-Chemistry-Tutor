"""Benchmark cached extraction outputs without calling live OCR services."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.ingestion_pipeline import slugify_source  # noqa: E402

_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
_CHEMICAL_RE = re.compile(r"\b(?:H|O|C|Na|Cl|Mg|Zn|Fe|Cu|Al|Ca|SO|CO|NO|OH)[A-Za-z0-9₂₃₄₅₆₇₈₉+\-]*\b|[→↔=]")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _pages_dir(source_slug: str) -> Path:
    return PROJECT_DIR / "data" / "textbooks" / source_slug / "pages"


def _ocrarena_dir(source_slug: str) -> Path:
    return PROJECT_DIR / "data" / "textbooks" / source_slug / "ocrarena"


def _benchmark_dir(source_slug: str) -> Path:
    path = PROJECT_DIR / "data" / "textbooks" / source_slug / "benchmarks"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _text_from_payload(payload: dict) -> str:
    parts = [
        payload.get("raw_markdown"),
        payload.get("merged_content"),
        payload.get("text_layer_content"),
        payload.get("raw_text"),
    ]
    for section in payload.get("sections") or []:
        parts.append(section.get("content"))
    for question in payload.get("questions") or []:
        parts.append(question.get("question_text"))
    for diagram in payload.get("diagrams") or []:
        parts.append(diagram.get("description"))
    for table in payload.get("tables") or []:
        parts.append(table.get("markdown"))
    for equation in payload.get("equations") or []:
        parts.append(equation.get("equation"))
    return "\n\n".join(str(part).strip() for part in parts if str(part or "").strip())


def _arabic_ratio(text: str) -> float:
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for char in letters if _ARABIC_RE.match(char)) / len(letters)


def _score_payload(payload: dict) -> dict:
    text = _text_from_payload(payload)
    char_count = len(text)
    raw_markdown = payload.get("raw_markdown") or ""
    table_count = len(payload.get("tables") or []) + text.count("| ---")
    diagram_count = len(payload.get("diagrams") or [])
    equation_count = len(payload.get("equations") or []) + len(_CHEMICAL_RE.findall(text))
    question_count = len(payload.get("questions") or []) + text.count("السّ ؤال") + text.count("السؤال")
    schema_valid = bool(payload.get("sections") or raw_markdown or payload.get("merged_content") or payload.get("text_layer_content"))

    arabic_score = min(char_count / 900, 1.0) * min(_arabic_ratio(text) / 0.75, 1.0) * 25
    equation_score = min(equation_count / 3, 1.0) * 20
    table_score = min(table_count / 1, 1.0) * 15
    diagram_score = min(diagram_count / 1, 1.0) * 15
    question_score = min(question_count / 3, 1.0) * 15
    answer_score = 5 if any((q.get("correct_answer") and q.get("answer_source") in {"page", "answer_key"}) for q in payload.get("questions") or []) else 0
    schema_score = 5 if schema_valid else 0

    total = arabic_score + equation_score + table_score + diagram_score + question_score + answer_score + schema_score
    return {
        "score": round(min(total, 100), 2),
        "char_count": char_count,
        "raw_markdown_chars": len(raw_markdown),
        "arabic_ratio": round(_arabic_ratio(text), 4),
        "table_count": table_count,
        "diagram_count": diagram_count,
        "equation_signal_count": equation_count,
        "question_signal_count": question_count,
        "visible_answer_count": sum(1 for q in payload.get("questions") or [] if q.get("correct_answer")),
        "schema_valid": schema_valid,
    }


def _method_payloads(page_payload: dict, ocrarena_payload: dict | None) -> dict[str, dict]:
    methods = {"current_cache": page_payload}
    for key in ("gemini_pdf_content", "gemini_fallback_model_content", "gemini_image_fallback_content"):
        value = page_payload.get(key)
        if isinstance(value, dict) and value:
            methods[key] = value
    if ocrarena_payload:
        methods["ocrarena_cached"] = ocrarena_payload
    return methods


def _select_pages(pages: list[dict], limit: int = 7) -> list[int]:
    buckets: dict[str, list[int]] = defaultdict(list)
    for payload in pages:
        page_number = int(payload.get("page_number") or 0)
        text = _text_from_payload(payload)
        page_type = payload.get("page_type") or payload.get("classification") or "unknown"
        buckets[page_type].append(page_number)
        if payload.get("tables") or "| ---" in text:
            buckets["table_heavy"].append(page_number)
        if payload.get("equations") or _CHEMICAL_RE.search(text):
            buckets["equation_heavy"].append(page_number)
        if payload.get("questions") or "السّ ؤال" in text or "السؤال" in text:
            buckets["exercise"].append(page_number)
        if payload.get("diagrams") or page_type in {"NEEDS_VISION", "MIXED_VISION"}:
            buckets["diagram_or_vision"].append(page_number)

    selected: list[int] = []
    for bucket in (
        "SELECTABLE_TEXT",
        "NEEDS_VISION",
        "MIXED_VISION",
        "table_heavy",
        "equation_heavy",
        "exercise",
        "diagram_or_vision",
    ):
        for page_number in buckets.get(bucket, []):
            if page_number and page_number not in selected:
                selected.append(page_number)
                break
    return selected[:limit]


def build_benchmark(source_slug: str, selected_pages: list[int] | None = None) -> dict:
    pages_path = _pages_dir(source_slug)
    if not pages_path.exists():
        raise SystemExit(f"Page cache not found: {pages_path}")
    pages = [_read_json(path) for path in sorted(pages_path.glob("page_*.json"))]
    ocrarena_path = _ocrarena_dir(source_slug)
    ocrarena_available = ocrarena_path.exists() and any(ocrarena_path.glob("page_*.json"))
    selected = selected_pages or _select_pages(pages)
    by_page = {int(payload.get("page_number") or 0): payload for payload in pages}

    page_reports = []
    method_totals: dict[str, list[float]] = defaultdict(list)
    for page_number in selected:
        page_payload = by_page.get(page_number)
        if not page_payload:
            continue
        ocrarena_payload = None
        ocrarena_file = ocrarena_path / f"page_{page_number:03d}.json"
        if ocrarena_file.exists():
            ocrarena_payload = _read_json(ocrarena_file)
        method_scores = {}
        for method, payload in _method_payloads(page_payload, ocrarena_payload).items():
            score = _score_payload(payload)
            method_scores[method] = score
            method_totals[method].append(score["score"])
        page_reports.append(
            {
                "page_number": page_number,
                "page_type": page_payload.get("page_type") or page_payload.get("classification"),
                "status": page_payload.get("status"),
                "methods": method_scores,
                "recommendation": _recommend(method_scores, ocrarena_available),
            }
        )

    return {
        "source_slug": source_slug,
        "pages_dir": str(pages_path),
        "ocrarena_cache_available": ocrarena_available,
        "selected_pages": selected,
        "method_averages": {
            method: round(sum(scores) / len(scores), 2)
            for method, scores in sorted(method_totals.items())
            if scores
        },
        "pages": page_reports,
    }


def _recommend(method_scores: dict[str, dict], ocrarena_available: bool) -> str:
    best_method = max(method_scores.items(), key=lambda item: item[1]["score"])[0] if method_scores else "none"
    if not ocrarena_available:
        return f"No cached OCRArena output; inspect {best_method} and run improved Gemini extraction for fair comparison."
    if best_method == "ocrarena_cached":
        return "Cached OCRArena scores higher; investigate Gemini prompt/model/preprocessing before changing production."
    return f"{best_method} scores highest; keep Gemini production path and use OCRArena only as benchmark reference."


def write_reports(report: dict) -> tuple[Path, Path]:
    out_dir = _benchmark_dir(report["source_slug"])
    json_path = out_dir / "extraction_benchmark.json"
    md_path = out_dir / "extraction_benchmark.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# Extraction Benchmark: {report['source_slug']}",
        "",
        f"- OCRArena cache available: `{report['ocrarena_cache_available']}`",
        f"- Selected pages: `{report['selected_pages']}`",
        f"- Method averages: `{report['method_averages']}`",
        "",
        "| Page | Type | Status | Method Scores | Recommendation |",
        "| --- | --- | --- | --- | --- |",
    ]
    for page in report["pages"]:
        method_scores = ", ".join(f"{name}: {score['score']}" for name, score in page["methods"].items())
        lines.append(
            f"| {page['page_number']} | {page['page_type']} | {page['status']} | {method_scores} | {page['recommendation']} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark cached textbook extraction outputs.")
    parser.add_argument("--source-slug", default=slugify_source("syria_grade_9_chemistry"))
    parser.add_argument("--pages", default="", help="Optional comma-separated page numbers.")
    args = parser.parse_args()

    pages = [int(item) for item in args.pages.split(",") if item.strip()] or None
    report = build_benchmark(args.source_slug, pages)
    json_path, md_path = write_reports(report)
    print(json.dumps({"json": str(json_path), "markdown": str(md_path), **report}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
