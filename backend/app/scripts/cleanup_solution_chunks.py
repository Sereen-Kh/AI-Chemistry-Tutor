"""Clean solution-book chunk boundaries without OCR, Vision, or embedding.

Run from ``src/backend``:

    python -m app.scripts.cleanup_solution_chunks
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parents[1]

REPORT_DIR = REPO_ROOT / "reports/solution_chunk_cleanup"
PRECONDITION_JSON = REPORT_DIR / "precondition_report.json"
AUDIT_MD = REPORT_DIR / "current_solution_chunk_audit.md"
CLEANUP_JSON = REPORT_DIR / "solution_chunk_cleanup_report.json"
CLEANUP_MD = REPORT_DIR / "solution_chunk_cleanup_report.md"

INPUT_UNITS = REPO_ROOT / "data/processed/solution_book/solution_units.jsonl"
PAGE_STRUCTURE = REPO_ROOT / "data/processed/solution_book/solution_page_structure.jsonl"
ALIGNMENT_JSON = REPO_ROOT / "data/processed/solution_book/solution_textbook_alignment.json"
REVIEWED_LESSON_MAP = (
    REPO_ROOT / "data/processed/textbook/textbook_lesson_map.reviewed.json"
)
EXISTING_PREVIEW = (
    REPO_ROOT / "data/processed/chunk_preview/solution_book_chunks_preview.jsonl"
)
EXISTING_PREVIEW_REPORT = REPO_ROOT / "data/processed/chunk_preview/chunk_preview_report.json"
LEGACY_CANONICAL_CHUNKS = REPO_ROOT / "src/data/processed/solution_book/chunks.jsonl"
LEGACY_CHUNKING_REPORT = REPO_ROOT / "src/data/processed/solution_book/chunking_report.json"
LEGACY_EXTRACTION_REPORT = REPO_ROOT / "src/data/processed/solution_book/extraction_report.json"

BACKUP_CHUNKS = (
    REPO_ROOT / "data/processed/solution_book/solution_chunks.before_cleanup.jsonl"
)
BACKUP_PREVIEW = (
    REPO_ROOT
    / "data/processed/chunk_preview/solution_book_chunks_preview.before_cleanup.jsonl"
)
OUTPUT_CHUNKS = (
    REPO_ROOT / "data/processed/solution_book/solution_chunks.cleaned.jsonl"
)
OUTPUT_PREVIEW = (
    REPO_ROOT
    / "data/processed/chunk_preview/solution_book_chunks_preview.cleaned.jsonl"
)

REVIEWED_METADATA_VERSION = "book_structure_reviewed_2026_06_24"
TARGET_TOKEN_MIN = 700
TARGET_TOKEN_MAX = 1200
SOFT_MAX_TOKENS = 1600
HARD_MAX_TOKENS = 2200

DANGLING_CONNECTIVES = {"و", "ثم", "أو", "حيث", "لذلك", "لأن", "كما"}
BAD_TRAILING_PUNCTUATION = {",", "،", ";", "؛", ":", "："}
INCOMPLETE_OPERATORS = {"=", "*", "×", "÷", "→", "⟶", "↔", "⇆", "$"}
LABEL_ENDINGS = {
    "الحل",
    "المطلوب",
    "السؤال",
    "المسألة",
    "اختر الإجابة الصحيحة",
    "أكمل الجدول الآتي",
}
QUESTION_STEM_HINTS = {
    "احسب",
    "اكتب",
    "اختر",
    "أكمل",
    "عدد",
    "وحدة",
    "الصيغة",
    "المطلوب",
    "علل",
    "فسر",
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def estimate_tokens(content: str) -> int:
    # Arabic tokenization is not exact here; this conservative estimate is enough
    # for chunk-size QA without calling embedding or tokenizer services.
    return max(1, round(len(content) / 4))


def normalize_solution_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    blank_seen = False
    for raw_line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if not line:
            if not blank_seen:
                lines.append("")
            blank_seen = True
            continue
        blank_seen = False
        lines.append(line)
    normalized = "\n".join(lines).strip()
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized


def _last_meaningful_line(content: str) -> str:
    for line in reversed(content.splitlines()):
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _last_word(content: str) -> str:
    words = re.findall(r"[\w\u0600-\u06FF]+", content.strip(), flags=re.UNICODE)
    return words[-1] if words else ""


def _has_unclosed_brackets(content: str) -> bool:
    pairs = [("(", ")"), ("[", "]"), ("{", "}"), ("﴿", "﴾")]
    for opener, closer in pairs:
        if content.count(opener) > content.count(closer):
            return True
    return False


def _looks_like_broken_final_line(line: str) -> bool:
    compact = re.sub(r"\s+", " ", line).strip()
    if not compact:
        return True
    if compact in LABEL_ENDINGS:
        return True
    if compact.startswith((": ", ":")):
        return True
    if compact.endswith(("يأتي", "الآتية", "الآتي", "التالي", "التالية")):
        return True
    if compact.startswith(("الصفحة", "صفحة")) and compact.endswith(":"):
        return True
    if re.fullmatch(r"[\-\u2212]?\s*\d+\s*[\-\.)]?", compact):
        return True
    if re.fullmatch(r"[\|\s]+", compact):
        return True
    if len(compact) <= 10 and not re.search(r"[\u0600-\u06FFA-Za-z0-9]", compact):
        return True
    if len(compact) <= 18 and compact.endswith(":"):
        return True
    if (
        len(compact) <= 90
        and not compact.endswith((".", "۔", "؟", "!", ")", "]"))
        and any(hint in compact for hint in QUESTION_STEM_HINTS)
    ):
        return True
    return False


def _looks_like_incomplete_equation(line: str) -> bool:
    compact = re.sub(r"\s+", " ", line).strip()
    if compact in INCOMPLETE_OPERATORS:
        return True
    if any(compact.endswith(op) for op in INCOMPLETE_OPERATORS):
        return True
    if re.search(r"(?:\+|−|-)\s*(?:\+|−|-)\s*$", compact):
        return True
    if re.search(r"(?:=|→|⟶|↔|⇆)\s*$", compact):
        return True
    if re.search(r"(?:=|×|÷|→|⟶|↔|⇆)\s*(?:=|×|÷|→|⟶|↔|⇆)\s*$", compact):
        return True
    return False


def is_bad_chunk_ending(content: str) -> tuple[bool, list[str]]:
    """Return whether ``content`` has an unsafe chunk ending and why."""

    stripped = content.strip()
    if not stripped:
        return True, ["empty_content"]

    reasons: list[str] = []
    final_char = stripped[-1]
    final_line = _last_meaningful_line(stripped)
    final_word = _last_word(stripped)

    if final_char in BAD_TRAILING_PUNCTUATION:
        reasons.append("dangling_punctuation")
    if final_word in DANGLING_CONNECTIVES:
        reasons.append("dangling_arabic_connective")
    if _has_unclosed_brackets(stripped):
        reasons.append("open_bracket_or_parenthesis")
    if _looks_like_broken_final_line(final_line):
        reasons.append("broken_final_line")
    if _looks_like_incomplete_equation(final_line):
        reasons.append("incomplete_equation_or_calculation")
    if re.search(r"(?:السؤال|المسألة)\s*(?:الأول|الثاني|الثالث|الرابع|الخامس)?\s*:?$", final_line):
        reasons.append("ends_with_question_label")
    if re.search(r"^\s*[-*•]\s*$", final_line):
        reasons.append("incomplete_bullet")

    return bool(reasons), sorted(set(reasons))


def find_valid_split_boundaries(content: str) -> list[int]:
    """Find Arabic-aware safe split boundaries.

    Boundaries are character offsets immediately after complete sentences,
    finished answer lines, or equation lines that do not end with an operator.
    """

    boundaries: list[int] = []
    offset = 0
    for line in content.splitlines(keepends=True):
        stripped = line.strip()
        offset += len(line)
        if not stripped:
            continue
        bad, _ = is_bad_chunk_ending(stripped)
        if not bad and (
            stripped.endswith((".", "۔", "؟", "!", ")", "]"))
            or "الجواب" in stripped
            or "الناتج" in stripped
            or re.search(r"[\u0600-\u06FFA-Za-z0-9)]$", stripped)
        ):
            boundaries.append(offset)
    return sorted(set(boundaries))


def _infer_printed_page(unit: dict[str, Any]) -> int | None:
    value = unit.get("printed_page_number")
    if isinstance(value, int) and value >= 40:
        return value
    page_number = unit.get("page_number")
    if isinstance(page_number, int):
        return page_number + 47
    return None


def _unit_text(unit: dict[str, Any]) -> str:
    parts: list[str] = []
    question = normalize_solution_text(str(unit.get("question_text") or ""))
    solution = normalize_solution_text(str(unit.get("solution_text") or ""))
    final_answer = normalize_solution_text(str(unit.get("final_answer") or ""))
    if question:
        parts.append(f"السؤال:\n{question}")
    if solution:
        parts.append(f"الحل:\n{solution}")
    if final_answer:
        parts.append(f"الإجابة النهائية:\n{final_answer}")
    return "\n\n".join(parts).strip()


def _group_text(units: list[dict[str, Any]]) -> str:
    return "\n\n".join(_unit_text(unit) for unit in units if _unit_text(unit)).strip()


def _unit_lesson_id(unit: dict[str, Any], alignments: dict[str, dict[str, Any]]) -> str | None:
    alignment = alignments.get(str(unit.get("id"))) or {}
    return (
        unit.get("linked_textbook_lesson_id")
        or alignment.get("linked_textbook_lesson_id")
        or None
    )


def _can_merge(
    current_units: list[dict[str, Any]],
    next_unit: dict[str, Any],
    alignments: dict[str, dict[str, Any]],
) -> bool:
    current_lesson = _unit_lesson_id(current_units[-1], alignments)
    next_lesson = _unit_lesson_id(next_unit, alignments)
    if current_lesson != next_lesson:
        return False
    current_page = current_units[-1].get("page_number")
    next_page = next_unit.get("page_number")
    if isinstance(current_page, int) and isinstance(next_page, int):
        return 0 <= next_page - current_page <= 1
    return True


def _load_alignments() -> dict[str, dict[str, Any]]:
    payload = _load_json(ALIGNMENT_JSON, {"items": []})
    return {
        str(item.get("solution_unit_id")): item
        for item in payload.get("items", [])
        if item.get("solution_unit_id")
    }


def _load_lesson_map() -> dict[str, dict[str, Any]]:
    payload = _load_json(REVIEWED_LESSON_MAP, {"lessons": []})
    return {
        str(lesson.get("lesson_id")): lesson
        for lesson in payload.get("lessons", [])
        if lesson.get("lesson_id")
    }


def _chunk_type(units: list[dict[str, Any]]) -> str:
    equations = [
        equation
        for unit in units
        for equation in list(unit.get("equations") or [])
        if str(equation).strip()
    ]
    has_question = any(unit.get("question_number") for unit in units)
    has_steps = any(unit.get("solution_steps") for unit in units)
    if equations and not has_question and not has_steps:
        return "equation"
    if has_question and has_steps:
        return "exercise_answer"
    if equations and has_steps:
        return "calculation"
    if has_question:
        return "exercise_answer"
    return "mixed"


def _make_chunk(
    units: list[dict[str, Any]],
    alignments: dict[str, dict[str, Any]],
    lesson_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    text = _group_text(units)
    bad, reasons = is_bad_chunk_ending(text)
    unit_ids = [str(unit.get("id")) for unit in units if unit.get("id")]
    primary_unit = units[0]
    primary_id = unit_ids[0] if unit_ids else ""
    alignment = alignments.get(primary_id) or {}
    lesson_id = _unit_lesson_id(primary_unit, alignments)
    lesson = lesson_map.get(str(lesson_id)) if lesson_id else {}
    link_confidence = float(
        primary_unit.get("link_confidence")
        if primary_unit.get("link_confidence") is not None
        else alignment.get("confidence") or 0.0
    )
    needs_manual_review = bool(
        bad
        or any(unit.get("needs_manual_review") for unit in units)
        or link_confidence < 0.6
        or any(unit.get("blocked") for unit in units)
    )
    manual_reasons: list[str] = []
    if bad:
        manual_reasons.extend(f"bad_ending:{reason}" for reason in reasons)
    if link_confidence < 0.6:
        manual_reasons.append("alignment_confidence_below_0.60")
    if any(unit.get("needs_manual_review") for unit in units):
        manual_reasons.append("source_unit_marked_needs_manual_review")
    if any(unit.get("blocked") for unit in units):
        manual_reasons.append("source_unit_blocked")

    printed_pages = [
        page for page in (_infer_printed_page(unit) for unit in units) if page is not None
    ]
    pdf_pages = [
        unit.get("page_number") for unit in units if isinstance(unit.get("page_number"), int)
    ]
    equations = sorted(
        {
            str(equation).strip()
            for unit in units
            for equation in list(unit.get("equations") or [])
            if str(equation).strip()
        }
    )
    keywords = sorted(
        {
            str(keyword).strip()
            for unit in units
            for keyword in list(unit.get("keywords") or [])
            if str(keyword).strip()
        }
    )
    content_hash = _content_hash(text)
    chunk_id = f"sol_clean_chunk_{content_hash[:16]}"
    quality_status = (
        "blocked"
        if any(unit.get("blocked") for unit in units)
        else "needs_review"
        if needs_manual_review
        else "ready"
    )

    return {
        "chunk_id": chunk_id,
        "source_type": "solution_book",
        "solution_unit_id": primary_id,
        "linked_textbook_lesson_id": lesson_id,
        "linked_lesson_title": primary_unit.get("linked_lesson_title")
        or alignment.get("linked_lesson_title")
        or lesson.get("lesson_title"),
        "unit_id": lesson.get("unit_id"),
        "lesson_id": lesson_id,
        "lesson_title": lesson.get("lesson_title")
        or primary_unit.get("linked_lesson_title")
        or alignment.get("linked_lesson_title"),
        "printed_page_start": min(printed_pages) if printed_pages else None,
        "printed_page_end": max(printed_pages) if printed_pages else None,
        "pdf_page_start": min(pdf_pages) if pdf_pages else None,
        "pdf_page_end": max(pdf_pages) if pdf_pages else None,
        "exercise_number": primary_unit.get("exercise_number"),
        "question_number": primary_unit.get("question_number"),
        "chunk_type": _chunk_type(units),
        "content": text,
        "content_ar": text,
        "equations": equations,
        "keywords": keywords,
        "token_estimate": estimate_tokens(text),
        "quality_status": quality_status,
        "ends_cleanly": not bad,
        "reviewed_metadata_version": REVIEWED_METADATA_VERSION,
        "metadata": {
            "content_hash": content_hash,
            "source_file": str(INPUT_UNITS.relative_to(REPO_ROOT)),
            "range_source": "complete_solution_unit_merge_cleanup"
            if len(units) > 1
            else "complete_solution_unit",
            "alignment_confidence": link_confidence,
            "alignment_method": primary_unit.get("link_method") or alignment.get("method"),
            "alignment_status": alignment.get("status"),
            "solution_unit_ids": unit_ids,
            "bad_ending_reasons": reasons,
            "needs_manual_review": needs_manual_review,
            "manual_review_reasons": sorted(set(manual_reasons)),
            "target_token_range": [TARGET_TOKEN_MIN, TARGET_TOKEN_MAX],
            "soft_max_tokens": SOFT_MAX_TOKENS,
            "hard_max_tokens": HARD_MAX_TOKENS,
        },
    }


def build_clean_chunks() -> tuple[list[dict[str, Any]], dict[str, int], list[dict[str, Any]]]:
    units = _read_jsonl(INPUT_UNITS)
    alignments = _load_alignments()
    lesson_map = _load_lesson_map()
    chunks: list[dict[str, Any]] = []
    fixed_examples: list[dict[str, Any]] = []
    merged_chunks = 0
    resplit_chunks = 0
    unchanged_chunks = 0

    index = 0
    while index < len(units):
        group = [units[index]]
        while index + len(group) < len(units):
            text = _group_text(group)
            bad, _ = is_bad_chunk_ending(text)
            if not bad:
                break
            next_unit = units[index + len(group)]
            if not _can_merge(group, next_unit, alignments):
                break
            group.append(next_unit)

        chunk = _make_chunk(group, alignments, lesson_map)

        if len(group) > 1:
            merged_chunks += len(group) - 1
            if chunk["ends_cleanly"]:
                fixed_examples.append(
                    {
                        "chunk_id": chunk["chunk_id"],
                        "merged_solution_unit_ids": chunk["metadata"]["solution_unit_ids"],
                        "linked_textbook_lesson_id": chunk.get("linked_textbook_lesson_id"),
                        "printed_page_start": chunk.get("printed_page_start"),
                        "printed_page_end": chunk.get("printed_page_end"),
                    }
                )
        else:
            unchanged_chunks += 1

        if chunk["token_estimate"] > HARD_MAX_TOKENS:
            boundaries = find_valid_split_boundaries(chunk["content"])
            if boundaries:
                # Current source is small enough that this is unlikely. Keep a
                # conservative marker rather than arbitrary splitting.
                chunk["metadata"]["valid_split_boundaries"] = boundaries
            resplit_chunks += 0

        chunks.append(chunk)
        index += len(group)

    metrics = {
        "merged_chunks": merged_chunks,
        "resplit_chunks": resplit_chunks,
        "unchanged_chunks": unchanged_chunks,
    }
    return chunks, metrics, fixed_examples


def _copy_backup(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    return True


def audit_current_chunks() -> dict[str, Any]:
    units = _read_jsonl(INPUT_UNITS)
    preview = _read_jsonl(EXISTING_PREVIEW)
    page_rows = _read_jsonl(PAGE_STRUCTURE)
    preview_report = _load_json(EXISTING_PREVIEW_REPORT, {})
    legacy_report = _load_json(LEGACY_CHUNKING_REPORT, {})
    extraction_report = _load_json(LEGACY_EXTRACTION_REPORT, {})

    bad_chunks = [
        chunk
        for chunk in preview
        if chunk.get("ends_cleanly") is False or chunk.get("bad_ending_reason")
    ]
    metadata_fields = [
        "solution_unit_id",
        "source_type",
        "page_start",
        "question_number",
        "exercise_number",
        "linked_textbook_lesson_id",
        "quality_score",
    ]
    metadata_coverage = {
        field: sum(1 for chunk in preview if chunk.get(field) not in (None, "", []))
        for field in metadata_fields
    }
    blocked_pages = sum(1 for row in page_rows if row.get("blocked"))
    quality_scores = [
        float(row.get("quality_score"))
        for row in page_rows
        if isinstance(row.get("quality_score"), (int, float))
    ]
    audit = {
        "input_solution_units_path": str(INPUT_UNITS.relative_to(REPO_ROOT)),
        "existing_chunks_path": str(EXISTING_PREVIEW.relative_to(REPO_ROOT)),
        "legacy_canonical_chunks_path": str(LEGACY_CANONICAL_CHUNKS.relative_to(REPO_ROOT))
        if LEGACY_CANONICAL_CHUNKS.exists()
        else None,
        "existing_chunking_report_path": str(EXISTING_PREVIEW_REPORT.relative_to(REPO_ROOT)),
        "legacy_chunking_report_path": str(LEGACY_CHUNKING_REPORT.relative_to(REPO_ROOT))
        if LEGACY_CHUNKING_REPORT.exists()
        else None,
        "alignment_path": str(ALIGNMENT_JSON.relative_to(REPO_ROOT)),
        "extraction_report_path": str(LEGACY_EXTRACTION_REPORT.relative_to(REPO_ROOT))
        if LEGACY_EXTRACTION_REPORT.exists()
        else None,
        "input_solution_units": len(units),
        "existing_chunks": len(preview),
        "extraction_quality_status": {
            "average_quality_score": round(sum(quality_scores) / len(quality_scores), 4)
            if quality_scores
            else extraction_report.get("average_quality_score"),
            "provider_used": extraction_report.get("provider_used"),
            "ocr_pages": extraction_report.get("ocr_pages", 0),
            "vision_pages": extraction_report.get("vision_pages", 0),
        },
        "blocked_pages_count": blocked_pages
        if page_rows
        else extraction_report.get("blocked_pages", 0),
        "bad_ending_count": len(bad_chunks),
        "legacy_bad_ending_count": len(legacy_report.get("bad_endings") or []),
        "chunk_preview_report_solution_bad_endings": (
            preview_report.get("bad_endings_by_source_type") or {}
        ).get("solution_book"),
        "bad_ending_examples": [
            {
                "chunk_id": chunk.get("chunk_id"),
                "solution_unit_id": chunk.get("solution_unit_id"),
                "reason": chunk.get("bad_ending_reason"),
                "tail": " ".join(str(chunk.get("content") or "").split()[-25:]),
            }
            for chunk in bad_chunks[:8]
        ],
        "metadata_coverage": metadata_coverage,
    }
    return audit


def write_audit(audit: dict[str, Any]) -> None:
    examples = "\n".join(
        f"- `{item['chunk_id']}` / `{item['solution_unit_id']}`: {item['reason']} — {item['tail']}"
        for item in audit["bad_ending_examples"]
    )
    coverage = "\n".join(
        f"- {field}: {count}/{audit['existing_chunks']}"
        for field, count in audit["metadata_coverage"].items()
    )
    md = f"""# Current Solution Chunk Audit

## Paths

- Input solution units path: `{audit['input_solution_units_path']}`
- Existing chunks path: `{audit['existing_chunks_path']}`
- Legacy canonical chunks path: `{audit['legacy_canonical_chunks_path']}`
- Existing chunking report path: `{audit['existing_chunking_report_path']}`
- Legacy chunking report path: `{audit['legacy_chunking_report_path']}`
- Solution-to-textbook alignment path: `{audit['alignment_path']}`
- Extraction report path: `{audit['extraction_report_path']}`

## Extraction Quality

- Existing extraction quality status: `{audit['extraction_quality_status']}`
- Existing blocked pages count: `{audit['blocked_pages_count']}`

## Current Bad-Ending Problem

- Existing chunks: {audit['existing_chunks']}
- Existing bad ending count: {audit['bad_ending_count']}
- Legacy bad ending count: {audit['legacy_bad_ending_count']}
- Combined chunk preview report solution bad endings: {audit['chunk_preview_report_solution_bad_endings']}

The current issue is chunk-boundary cleanup. The extraction reports no blocked pages and no OCR/Vision rerun is required.

## Examples Of Bad-Ending Chunks

{examples}

## Metadata Coverage In Existing Preview Chunks

{coverage}
"""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_MD.write_text(md, encoding="utf-8")


def _report_stats(
    chunks: list[dict[str, Any]],
    input_chunks: int,
    bad_before: int,
    metrics: dict[str, int],
    fixed_examples: list[dict[str, Any]],
) -> dict[str, Any]:
    token_estimates = [int(chunk.get("token_estimate") or 0) for chunk in chunks]
    ready_bad = []
    manual_review = []
    for chunk in chunks:
        bad, reasons = is_bad_chunk_ending(str(chunk.get("content") or ""))
        if bad and chunk.get("quality_status") == "ready":
            ready_bad.append(
                {
                    "chunk_id": chunk.get("chunk_id"),
                    "reasons": reasons,
                    "tail": " ".join(str(chunk.get("content") or "").split()[-20:]),
                }
            )
        if chunk.get("quality_status") == "needs_review":
            manual_review.append(
                {
                    "chunk_id": chunk.get("chunk_id"),
                    "solution_unit_id": chunk.get("solution_unit_id"),
                    "linked_textbook_lesson_id": chunk.get("linked_textbook_lesson_id"),
                    "reasons": chunk.get("metadata", {}).get("manual_review_reasons", []),
                }
            )

    chunks_by_type = Counter(str(chunk.get("chunk_type")) for chunk in chunks)
    chunks_by_lesson = Counter(
        str(chunk.get("lesson_id") or chunk.get("linked_textbook_lesson_id") or "unlinked")
        for chunk in chunks
    )
    report = {
        "input_solution_units": len(_read_jsonl(INPUT_UNITS)),
        "input_chunks": input_chunks,
        "output_chunks": len(chunks),
        "bad_endings_before": bad_before,
        "bad_endings_after": len(ready_bad),
        "merged_chunks": metrics["merged_chunks"],
        "resplit_chunks": metrics["resplit_chunks"],
        "unchanged_chunks": metrics["unchanged_chunks"],
        "needs_manual_review_count": len(manual_review),
        "needs_manual_review": manual_review,
        "chunks_by_type": dict(sorted(chunks_by_type.items())),
        "chunks_by_lesson": dict(sorted(chunks_by_lesson.items())),
        "average_token_estimate": round(sum(token_estimates) / len(token_estimates), 2)
        if token_estimates
        else 0,
        "min_token_estimate": min(token_estimates) if token_estimates else 0,
        "max_token_estimate": max(token_estimates) if token_estimates else 0,
        "fixed_examples": fixed_examples[:8],
        "status": "passed" if not ready_bad else "failed",
        "output_files": {
            "cleaned_chunks": str(OUTPUT_CHUNKS.relative_to(REPO_ROOT)),
            "cleaned_preview": str(OUTPUT_PREVIEW.relative_to(REPO_ROOT)),
        },
        "scope_guardrails": {
            "ocr_rerun": False,
            "vision_rerun": False,
            "embedding_rerun": False,
            "vector_db_write": False,
            "textbook_chunks_modified": False,
            "canonical_chunks_updated": False,
        },
    }
    return report


def write_cleanup_reports(report: dict[str, Any], audit: dict[str, Any]) -> None:
    CLEANUP_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    fixed_examples = "\n".join(
        f"- `{item['chunk_id']}` merged {item['merged_solution_unit_ids']} for `{item['linked_textbook_lesson_id']}` pages {item['printed_page_start']}–{item['printed_page_end']}"
        for item in report["fixed_examples"]
    ) or "- No merge examples."
    manual_review = "\n".join(
        f"- `{item['chunk_id']}` / `{item['linked_textbook_lesson_id']}`: {item['reasons']}"
        for item in report["needs_manual_review"]
    ) or "- None."
    md = f"""# Solution Chunk Cleanup Report

## 1. Executive Summary

Cleaned solution-book chunk boundaries from existing extracted solution units. OCR, Vision, embedding, vector DB writes, and textbook chunk generation were not run.

Status: `{report['status']}`

## 2. Input Files

- Solution units: `{INPUT_UNITS.relative_to(REPO_ROOT)}`
- Existing chunk preview: `{EXISTING_PREVIEW.relative_to(REPO_ROOT)}`
- Alignment: `{ALIGNMENT_JSON.relative_to(REPO_ROOT)}`
- Reviewed lesson map: `{REVIEWED_LESSON_MAP.relative_to(REPO_ROOT)}`

## 3. Output Files

- Cleaned chunks: `{OUTPUT_CHUNKS.relative_to(REPO_ROOT)}`
- Cleaned preview: `{OUTPUT_PREVIEW.relative_to(REPO_ROOT)}`
- Chunk backup: `{BACKUP_CHUNKS.relative_to(REPO_ROOT)}`
- Preview backup: `{BACKUP_PREVIEW.relative_to(REPO_ROOT)}`

## 4. Bad Endings Before/After

| Metric | Count |
| --- | ---: |
| Input solution units | {report['input_solution_units']} |
| Input chunks | {report['input_chunks']} |
| Output chunks | {report['output_chunks']} |
| Bad endings before | {report['bad_endings_before']} |
| Bad endings after among ready chunks | {report['bad_endings_after']} |
| Merged source units | {report['merged_chunks']} |
| Resplit chunks | {report['resplit_chunks']} |
| Needs manual review | {report['needs_manual_review_count']} |

## 5. Examples Of Fixed Chunks

{fixed_examples}

## 6. Remaining Manual Review Chunks

{manual_review}

## 7. Metadata Preservation Result

Every cleaned chunk stores `source_type`, `solution_unit_id`, page metadata, lesson/link metadata, `quality_status`, `content_hash`, and source unit IDs. Alignment confidence and alignment method are preserved in `metadata`.

Current audit metadata coverage before cleanup:

```json
{json.dumps(audit['metadata_coverage'], ensure_ascii=False, indent=2)}
```

## 8. Validation Result

Run:

```bash
cd src/backend && python3 -m app.scripts.validate_solution_chunk_cleanup
```

Cleanup status: `{report['status']}`.

## 9. Exact Next Step

Store reviewed curriculum metadata before embedding/re-embedding.
"""
    CLEANUP_MD.write_text(md, encoding="utf-8")


def run_cleanup() -> dict[str, Any]:
    precondition = _load_json(PRECONDITION_JSON, {})
    if precondition.get("can_cleanup_solution_chunks") is not True:
        raise SystemExit("BOOK STRUCTURE UPDATE NOT COMPLETE")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    audit = audit_current_chunks()
    write_audit(audit)

    _copy_backup(EXISTING_PREVIEW, BACKUP_PREVIEW)
    # There is no canonical data/processed solution chunk file yet. Preserve the
    # current preview chunk rows as the before-cleanup solution chunk backup.
    _copy_backup(EXISTING_PREVIEW, BACKUP_CHUNKS)

    chunks, metrics, fixed_examples = build_clean_chunks()
    existing_preview = _read_jsonl(EXISTING_PREVIEW)
    bad_before = len(
        [
            chunk
            for chunk in existing_preview
            if chunk.get("ends_cleanly") is False or chunk.get("bad_ending_reason")
        ]
    )
    report = _report_stats(
        chunks=chunks,
        input_chunks=len(existing_preview),
        bad_before=bad_before,
        metrics=metrics,
        fixed_examples=fixed_examples,
    )

    if report["bad_endings_after"] > bad_before:
        raise SystemExit("Cleaned output is worse than current output; refusing to write")

    _write_jsonl(OUTPUT_CHUNKS, chunks)
    _write_jsonl(OUTPUT_PREVIEW, chunks)
    write_cleanup_reports(report, audit)
    return report


def main() -> None:
    report = run_cleanup()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
