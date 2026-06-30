"""Local audio storage for uploaded and generated chat audio."""

from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from app.core.config import PROJECT_DIR


_SAFE_SUFFIX_RE = re.compile(r"[^a-zA-Z0-9]+")


class LocalAudioStorage:
    """Minimal local storage under data/uploads/audio for the audio MVP."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or PROJECT_DIR / "data" / "uploads" / "audio"
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
        stem = _SAFE_SUFFIX_RE.sub("_", Path(filename or "student_audio").stem).strip("_") or "student_audio"
        path = self.input_dir / f"input_{uuid4().hex}_{stem}.{ext}"
        path.write_bytes(data)
        return path, self.to_media_url(path)

    def save_output_bytes(self, data: bytes, *, message_id: int | str, extension: str = "mp3") -> tuple[Path, str]:
        ext = extension.lower().lstrip(".") or "mp3"
        path = self.output_dir / f"answer_{message_id}.{ext}"
        path.write_bytes(data)
        return path, self.to_media_url(path)

    def to_media_url(self, path: Path) -> str:
        try:
            relative = path.resolve().relative_to((PROJECT_DIR / "data" / "uploads").resolve())
            return f"/media/uploads/{relative.as_posix()}"
        except ValueError:
            return path.resolve().as_uri()
