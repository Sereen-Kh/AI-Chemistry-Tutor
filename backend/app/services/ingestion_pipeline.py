"""End-to-end PDF ingestion pipeline."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.textbook import TextbookChunk
from app.services.embeddings import embed_batch
from app.services.pdf_processor import classify_pages, extract_text_page, ocr_page_with_gemini

ProgressCallback = Callable[[int, str], None]


def split_text(text: str, chunk_size: int = 600, chunk_overlap: int = 80) -> list[str]:
    """Split Arabic textbook text into overlapping chunks."""
    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not normalized:
        return []
    chunks: list[str] = []
    start = 0
    length = len(normalized)
    while start < length:
        hard_end = min(start + chunk_size, length)
        end = hard_end
        if hard_end < length:
            candidates = [normalized.rfind(sep, start, hard_end) for sep in ["\n\n", "\n", ".", "،", " "]]
            best = max(candidates)
            if best > start + chunk_size // 2:
                end = best + 1
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = max(0, end - chunk_overlap)
    return chunks


async def _extract_page(pdf_path: str, page_num: int, image_pages: set[int]) -> tuple[str, str, str]:
    """Extract one page and return content, source type, and method."""
    if page_num in image_pages:
        text = await ocr_page_with_gemini(pdf_path, page_num)
        if text:
            return text, "ocr", "gemini-2.5-flash"
        return extract_text_page(pdf_path, page_num), "image", "pdfplumber-fallback"
    return extract_text_page(pdf_path, page_num), "text", "pdfplumber"


async def run_full_ingestion(
    pdf_path: str,
    chapter_id: int | None = None,
    clear_existing: bool = False,
    progress_callback: ProgressCallback | None = None,
    db: Session | None = None,
) -> dict:
    """Classify, extract, chunk, embed, and store a chemistry textbook PDF."""
    owns_db = db is None
    session = db or SessionLocal()
    errors: list[str] = []
    chunks_created = 0
    pages_processed = 0

    try:
        if progress_callback:
            progress_callback(1, "classifying")
        classification = classify_pages(pdf_path)
        total_pages = classification["total_pages"] or 1
        image_pages = set(classification["image_pages"])

        if clear_existing:
            query = session.query(TextbookChunk)
            if chapter_id is not None:
                query = query.filter(TextbookChunk.chapter_id == chapter_id)
            query.delete(synchronize_session=False)
            session.commit()

        for page_num in range(1, total_pages + 1):
            try:
                text, source_type, method = await _extract_page(pdf_path, page_num, image_pages)
                chunks = split_text(text)
                embeddings = await embed_batch(chunks)
                for content, embedding in zip(chunks, embeddings):
                    session.add(
                        TextbookChunk(
                            chapter_id=chapter_id,
                            page_number=page_num,
                            content=content,
                            source=f"{pdf_path}#page={page_num}",
                            source_type=source_type,
                            extraction_method=method,
                            embedding=embedding,
                        )
                    )
                    chunks_created += 1
                session.commit()
                pages_processed += 1
            except Exception as exc:
                session.rollback()
                errors.append(f"page {page_num}: {exc}")
            if progress_callback:
                progress = 5 + int((pages_processed / total_pages) * 95)
                progress_callback(min(progress, 100), f"processed page {page_num}/{total_pages}")

        return {
            "chunks_created": chunks_created,
            "pages_processed": pages_processed,
            "errors": errors,
            "classification": classification,
        }
    finally:
        if owns_db:
            session.close()
