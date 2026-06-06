"""Retry Gemini OCR/document extraction for failed cached textbook pages.

This script does not rebuild vectors. It only rewrites failed ``page_NNN.json``
cache files. Run ``scripts.rebuild_rag_from_cache`` afterward.

Run from the backend directory:
    .venv/bin/python -m scripts.retry_failed_page_ocr
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import PROJECT_DIR as APP_PROJECT_DIR  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models.textbook import ContentSource  # noqa: E402
from app.services.ingestion_pipeline import (  # noqa: E402
    _extract_page,
    _neighboring_pages,
    _page_cache_payload,
    _write_page_cache,
)
from app.services.ocr import get_vision_provider  # noqa: E402

DEFAULT_CACHE_DIR = APP_PROJECT_DIR / "data" / "textbooks" / "syria_grade_9_chemistry" / "pages"
DEFAULT_PDF_PATH = APP_PROJECT_DIR / "data" / "textbooks" / "syria_grade_9" / "Chemistry.pdf"
AUTH_MARKERS = ("401", "UNAUTHENTICATED", "ACCESS_TOKEN_TYPE_UNSUPPORTED", "invalid authentication")
QUOTA_MARKERS = ("429", "RESOURCE_EXHAUSTED", "quota", "Quota", "rate limit", "RATE_LIMIT")


def _resolve_project_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate
    cwd_candidate = Path.cwd() / candidate
    if ".." in candidate.parts:
        return cwd_candidate
    if cwd_candidate.exists():
        return cwd_candidate
    project_candidate = PROJECT_DIR / candidate
    if project_candidate.exists():
        return project_candidate
    backend_candidate = BACKEND_DIR / candidate
    if backend_candidate.exists():
        return backend_candidate
    return project_candidate


def _parse_pages(raw: str | None) -> set[int] | None:
    if not raw:
        return None
    pages: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            pages.update(range(int(start), int(end) + 1))
        else:
            pages.add(int(part))
    return pages


def _page_char_count(payload: dict[str, Any]) -> int:
    explicit = int(payload.get("char_count") or 0)
    if explicit > 0:
        return explicit
    fallback = (
        payload.get("merged_content")
        or payload.get("raw_markdown")
        or payload.get("text_layer_content")
        or payload.get("raw_text")
        or ""
    )
    return len(str(fallback).strip())


def _load_target_pages(cache_dir: Path, requested_pages: set[int] | None) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for page_file in sorted(cache_dir.glob("page_*.json")):
        payload = json.loads(page_file.read_text(encoding="utf-8"))
        page_number = int(payload.get("page_number") or page_file.stem.split("_")[-1])
        if requested_pages is not None and page_number not in requested_pages:
            continue
        if payload.get("status") == "failed" or _page_char_count(payload) <= 0:
            targets.append(
                {
                    "page_number": page_number,
                    "page_type": payload.get("page_type") or payload.get("classification") or "NEEDS_VISION",
                    "path": page_file,
                    "source_id": payload.get("source_id"),
                }
            )
    return targets


def _source_id_for_title(title: str) -> int | None:
    db = SessionLocal()
    try:
        source = db.query(ContentSource).filter(ContentSource.title == title).first()
        return source.id if source else None
    finally:
        db.close()


def _is_quota_error(error: str) -> bool:
    return any(marker in error for marker in QUOTA_MARKERS)


def _is_auth_error(error: str) -> bool:
    return any(marker in error for marker in AUTH_MARKERS)


async def retry_failed_pages(
    *,
    pdf_path: Path,
    cache_dir: Path,
    title: str,
    source_type: str,
    pages: set[int] | None,
    stop_on_quota: bool,
) -> dict[str, Any]:
    provider = get_vision_provider("gemini")
    if not provider.is_configured:
        raise RuntimeError("Gemini is not configured. Set GEMINI_API_KEY or GOOGLE_API_KEY before retrying OCR.")
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if not cache_dir.exists():
        raise FileNotFoundError(f"Cache directory not found: {cache_dir}")

    targets = _load_target_pages(cache_dir, pages)
    source_id = _source_id_for_title(title)
    total_pages = max(
        [item["page_number"] for item in targets]
        + [int(path.stem.split("_")[-1]) for path in cache_dir.glob("page_*.json")]
        + [0]
    )

    uploaded_pdf = None
    upload_warning = None
    try:
        uploaded_pdf = await provider.upload_pdf(str(pdf_path))
    except Exception as exc:
        upload_warning = f"Gemini PDF upload failed; using image fallback: {exc}"

    succeeded: list[int] = []
    failed: list[dict[str, Any]] = []
    stopped_for_quota = False
    stopped_for_auth = False
    stopped_reason = None

    for index, target in enumerate(targets, start=1):
        page_number = int(target["page_number"])
        page_type = str(target["page_type"])
        print(f"[{index}/{len(targets)}] retrying page {page_number:03d} ({page_type})", flush=True)
        try:
            payload, method = await _extract_page(
                str(pdf_path),
                page_number,
                page_type,
                title,
                source_type,
                provider,
                "production",
                True,
                uploaded_pdf,
                _neighboring_pages(page_number, total_pages),
            )
            payload["classification"] = page_type
            if source_id is not None:
                payload["source_id"] = source_id
            if upload_warning:
                payload.setdefault("warnings", []).insert(0, upload_warning)
            _write_page_cache(title, page_number, payload)
            if payload.get("status") == "failed" or _page_char_count(payload) <= 0:
                failed.append(
                    {
                        "page_number": page_number,
                        "status": payload.get("status"),
                        "char_count": payload.get("char_count") or 0,
                        "errors": payload.get("errors") or [],
                        "warnings": payload.get("warnings") or [],
                    }
                )
            else:
                succeeded.append(page_number)
            print(
                f"  -> {payload.get('status')} via {payload.get('extraction_method') or method}; "
                f"chars={payload.get('char_count') or 0}",
                flush=True,
            )
        except Exception as exc:
            error = str(exc)
            failed.append({"page_number": page_number, "status": "exception", "errors": [error]})
            failed_payload = _page_cache_payload(
                page_number=page_number,
                page_type=page_type,
                extraction_methods=["exception"],
                status="failed",
                text_layer_content="",
                vision_payload=None,
                sections=[],
                questions=[],
                diagrams=[],
                tables=[],
                equations=[],
                warnings=[],
                errors=[error],
                completeness_score=0.0,
            )
            failed_payload["classification"] = page_type
            if source_id is not None:
                failed_payload["source_id"] = source_id
            _write_page_cache(title, page_number, failed_payload)
            print(f"  -> failed: {error}", flush=True)
            if stop_on_quota and (_is_quota_error(error) or _is_auth_error(error)):
                stopped_for_quota = _is_quota_error(error)
                stopped_for_auth = _is_auth_error(error)
                stopped_reason = "auth" if stopped_for_auth else "quota"
                print(f"Stopping after unrecoverable Gemini {stopped_reason} error.", flush=True)
                break

    return {
        "total_targets": len(targets),
        "succeeded": succeeded,
        "failed": failed,
        "succeeded_count": len(succeeded),
        "failed_count": len(failed),
        "stopped_for_quota": stopped_for_quota,
        "stopped_for_auth": stopped_for_auth,
        "stopped_reason": stopped_reason,
        "upload_warning": upload_warning,
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Retry Gemini OCR for failed cached pages only.")
    parser.add_argument("--pdf-path", default=str(DEFAULT_PDF_PATH))
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    parser.add_argument("--title", default="syria_grade_9_chemistry")
    parser.add_argument("--source-type", default="textbook")
    parser.add_argument("--pages", default=None, help="Optional comma/range list, e.g. 3,14,41-45")
    parser.add_argument("--keep-going-on-quota", action="store_true")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    result = await retry_failed_pages(
        pdf_path=_resolve_project_path(args.pdf_path).resolve(),
        cache_dir=_resolve_project_path(args.cache_dir).resolve(),
        title=args.title,
        source_type=args.source_type,
        pages=_parse_pages(args.pages),
        stop_on_quota=not args.keep_going_on_quota,
    )
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        output_path = _resolve_project_path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    asyncio.run(main())
