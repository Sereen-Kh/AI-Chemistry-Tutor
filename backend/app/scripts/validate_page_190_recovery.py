"""Validate the targeted recovery of printed textbook page 190.

Run from ``src/backend``:

    python -m app.scripts.validate_page_190_recovery
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parents[1]

REVIEWED_PAGE_PATH = REPO_ROOT / "data/processed/textbook/pages/page_190_reviewed.json"
PAGE_STRUCTURE_PATH = REPO_ROOT / "data/processed/textbook/page_structure.jsonl"
LESSON_REPORT_PATH = REPO_ROOT / "reports/lesson_division/lesson_division_report.json"
REPORT_DIR = REPO_ROOT / "reports/page_190_recovery"
VALIDATION_JSON_PATH = REPORT_DIR / "page_190_validation_report.json"
VALIDATION_MD_PATH = REPORT_DIR / "page_190_validation_report.md"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_page_structure_row() -> dict[str, Any] | None:
    if not PAGE_STRUCTURE_PATH.exists():
        return None
    for line in PAGE_STRUCTURE_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("printed_page_number") == 190:
            return row
    return None


def _remaining_issue_pages() -> dict[str, list[int]]:
    if not LESSON_REPORT_PATH.exists():
        return {"needs_ocr_pages": [], "needs_vision_pages": []}
    payload = _load_json(LESSON_REPORT_PATH)
    textbook = payload.get("textbook") or {}
    return {
        "needs_ocr_pages": list(textbook.get("needs_ocr_pages") or []),
        "needs_vision_pages": list(textbook.get("needs_vision_pages") or []),
    }


def validate() -> dict[str, Any]:
    remaining_issues: list[str] = []
    reviewed_exists = REVIEWED_PAGE_PATH.exists()
    reviewed = _load_json(REVIEWED_PAGE_PATH) if reviewed_exists else {}
    structure_row = _load_page_structure_row()
    issue_pages = _remaining_issue_pages()

    checks = {
        "reviewed_page_exists": reviewed_exists,
        "printed_page_number_is_190": reviewed.get("printed_page_number") == 190,
        "unit_title_detected": bool(reviewed.get("unit_title")),
        "lesson_title_detected": bool(reviewed.get("lesson_title")),
        "text_not_empty": bool(str(reviewed.get("text") or "").strip()),
        "needs_ocr_false": reviewed.get("quality", {}).get("needs_ocr") is False,
        "needs_vision_false": reviewed.get("quality", {}).get("needs_vision") is False,
        "blocked_false": reviewed.get("quality", {}).get("blocked") is False,
        "page_structure_updated": bool(
            structure_row
            and structure_row.get("review_status") == "reviewed"
            and structure_row.get("needs_ocr") is False
            and structure_row.get("needs_vision") is False
            and structure_row.get("blocked") is False
        ),
        "page_190_removed_from_ocr_issue_list": 190 not in issue_pages["needs_ocr_pages"],
        "page_190_removed_from_vision_issue_list": 190 not in issue_pages["needs_vision_pages"],
    }

    for name, passed in checks.items():
        if not passed:
            remaining_issues.append(name)

    quality = reviewed.get("quality") or {}
    report = {
        "page": 190,
        "reviewed_page_exists": reviewed_exists,
        "text_length": quality.get("text_length") or len(str(reviewed.get("text") or "")),
        "unit_title": reviewed.get("unit_title"),
        "lesson_title": reviewed.get("lesson_title"),
        "needs_ocr": quality.get("needs_ocr"),
        "needs_vision": quality.get("needs_vision"),
        "blocked": quality.get("blocked"),
        "page_structure_updated": checks["page_structure_updated"],
        "page_190_removed_from_ocr_issue_list": checks["page_190_removed_from_ocr_issue_list"],
        "page_190_removed_from_vision_issue_list": checks["page_190_removed_from_vision_issue_list"],
        "validation_status": "passed" if not remaining_issues else "failed",
        "remaining_issues": remaining_issues,
        "checks": checks,
        "files_checked": {
            "reviewed_page": str(REVIEWED_PAGE_PATH.relative_to(REPO_ROOT)),
            "page_structure": str(PAGE_STRUCTURE_PATH.relative_to(REPO_ROOT)),
            "lesson_division_report": str(LESSON_REPORT_PATH.relative_to(REPO_ROOT)),
        },
    }
    return report


def write_reports(report: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    VALIDATION_JSON_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    checks_md = "\n".join(
        f"- {name}: {'passed' if passed else 'failed'}"
        for name, passed in report["checks"].items()
    )
    md = f"""# Page 190 Validation Report

Validation status: `{report["validation_status"]}`

| Field | Value |
| --- | --- |
| Page | {report["page"]} |
| Text length | {report["text_length"]} |
| Unit title | {report.get("unit_title") or ""} |
| Lesson title | {report.get("lesson_title") or ""} |
| needs_ocr | {report.get("needs_ocr")} |
| needs_vision | {report.get("needs_vision")} |
| blocked | {report.get("blocked")} |
| Page structure updated | {report.get("page_structure_updated")} |

## Checks

{checks_md}

## Remaining Issues

{json.dumps(report["remaining_issues"], ensure_ascii=False)}
"""
    VALIDATION_MD_PATH.write_text(md, encoding="utf-8")


def main() -> None:
    report = validate()
    write_reports(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["validation_status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

