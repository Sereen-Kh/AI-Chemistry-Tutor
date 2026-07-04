"""Local audio storage for uploaded and generated chat audio."""

from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from app.core.config import PROJECT_DIR, settings


_SAFE_SUFFIX_RE = re.compile(r"[^a-zA-Z0-9]+")


class LocalAudioStorage:
    """Minimal local storage under data/uploads/audio for the audio MVP."""

    def __init__(self, root: Path | None = None, public_base_url: str | None = None) -> None:
        configured_root = Path(settings.audio_storage_dir)
        if not configured_root.is_absolute():
            configured_root = PROJECT_DIR / configured_root
        self.root = (root or configured_root).resolve()
        self.public_base_url = (public_base_url or settings.audio_public_base_url or "/media/uploads").rstrip("/")
        self.input_dir = self.root / "input"
        self.output_dir = self.root / "output"
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def safe_extension(filename: str | None, content_type: str | None = None) -> str:
        suffix = Path(filename or "").suffix.lower().lstrip(".")
        if suffix in {"webm", "mp3", "wav", "m4a"}:
            return suffix
        content_type = (content_type or "").lower()
        if "webm" in content_type:
            return "webm"
        if "mpeg" in content_type or "mp3" in content_type:
            return "mp3"
        if "wav" in content_type:
            return "wav"
        if "mp4" in content_type or "m4a" in content_type:
            return "m4a"
        return "webm"

    def save_input_bytes(self, data: bytes, *, filename: str | None, content_type: str | None) -> tuple[Path, str]:
        ext = self.safe_extension(filename, content_type)
        path = self.input_dir / f"input_{uuid4().hex}.{ext}"
        path.write_bytes(data)
        return path, self.to_media_url(path)

    def save_output_bytes(self, data: bytes, *, message_id: int | str, extension: str = "mp3") -> tuple[Path, str]:
        ext = _SAFE_SUFFIX_RE.sub("", extension.lower().lstrip(".")) or "mp3"
        path = self.output_dir / f"answer_{message_id}_{uuid4().hex}.{ext}"
        path.write_bytes(data)
        return path, self.to_media_url(path)

    def to_media_url(self, path: Path) -> str:
        resolved = path.resolve()
        uploads_root = (PROJECT_DIR / "data" / "uploads").resolve()
        try:
            relative = resolved.relative_to(uploads_root)
            return f"/media/uploads/{relative.as_posix()}"
        except ValueError:
            relative = resolved.relative_to(self.root)
            return f"{self.public_base_url}/audio/{relative.as_posix()}"
