"""Shared helpers for production-hardening verification scripts."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
REPORTS_DIR = PROJECT_ROOT / "reports"


def now_iso() -> str:
    """Return a UTC timestamp suitable for reports."""
    return datetime.now(timezone.utc).isoformat()


def bool_env(name: str, default: bool = False) -> bool:
    """Read a boolean environment variable."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def redact_url(url: str | None) -> str | None:
    """Redact credentials from a URL without hiding host/db context."""
    if not url:
        return url
    try:
        parsed = urlsplit(url)
    except Exception:
        return "<invalid-url>"
    if "@" not in parsed.netloc:
        return url
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"***:***@{host}{port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def write_reports(
    *,
    report_subdir: str,
    report_name: str,
    title: str,
    payload: dict[str, Any],
    sections: list[tuple[str, list[str]]] | None = None,
) -> tuple[Path, Path]:
    """Write matching JSON and Markdown reports."""
    report_dir = REPORTS_DIR / report_subdir
    report_dir.mkdir(parents=True, exist_ok=True)
    payload = {"generated_at": now_iso(), **payload}
    json_path = report_dir / f"{report_name}.json"
    md_path = report_dir / f"{report_name}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [f"# {title}", ""]
    result = payload.get("result")
    if result is not None:
        lines.append(f"Result: `{result}`")
        lines.append("")
    if sections:
        for heading, body_lines in sections:
            lines.extend([f"## {heading}", ""])
            lines.extend(body_lines or ["- None"])
            lines.append("")
    else:
        lines.extend(["## Report", ""])
        for key, value in payload.items():
            if key == "generated_at":
                continue
            lines.append(f"- `{key}`: `{value}`")
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return json_path, md_path


def status_line(label: str, value: Any) -> str:
    """Format a Markdown status line."""
    return f"- **{label}:** `{value}`"
