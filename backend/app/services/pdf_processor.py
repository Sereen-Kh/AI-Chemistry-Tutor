"""PDF classification, text extraction, and OCR helpers."""

from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path

from app.core.config import settings

CHEMISTRY_OCR_PROMPT = """
You are a chemistry textbook OCR specialist. Extract ALL content from this page exactly as it appears.

Rules:
1. Extract all Arabic text verbatim and preserve Arabic script exactly.
2. Convert chemical equations to readable chemistry notation.
3. Convert mathematical expressions to LaTeX when needed.
4. Describe diagrams and illustrations as [DIAGRAM: description].
5. Extract tables as markdown.
6. Preserve section headings and page structure.
7. Mark boxes or highlighted sections as [BOX: content].

Output plain text only. Do not summarize.
"""


def _require_pdf(path: str | Path) -> Path:
    pdf_path = Path(path).expanduser()
    if not pdf_path.is_absolute():
        pdf_path = Path.cwd() / pdf_path
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    return pdf_path


def classify_pages(pdf_path: str) -> dict:
    """Classify pages by whether they have enough extractable text."""
    import pdfplumber

    path = _require_pdf(pdf_path)
    text_pages: list[int] = []
    image_pages: list[int] = []
    with pdfplumber.open(path) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            text = (page.extract_text() or "").strip()
            compact_len = len("".join(text.split()))
            if compact_len > 50:
                text_pages.append(index)
            else:
                image_pages.append(index)
    return {"text_pages": text_pages, "image_pages": image_pages, "total_pages": len(text_pages) + len(image_pages)}


def _table_to_markdown(table: list[list[str | None]]) -> str:
    rows = [["" if cell is None else str(cell).strip() for cell in row] for row in table if row]
    if not rows:
        return ""
    header = rows[0]
    body = rows[1:] or [["" for _ in header]]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in body)
    return "\n".join(lines)


def extract_text_page(pdf_path: str, page_num: int) -> str:
    """Extract selectable text and tables from a one-based PDF page number."""
    import pdfplumber

    path = _require_pdf(pdf_path)
    with pdfplumber.open(path) as pdf:
        page = pdf.pages[page_num - 1]
        text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
        tables = page.extract_tables() or []
    table_text = "\n\n".join(_table_to_markdown(table) for table in tables if table)
    return "\n\n".join(part for part in [text.strip(), table_text.strip()] if part)


def render_page_image(pdf_path: str, page_num: int, dpi: int = 300):
    """Render a one-based PDF page to a PIL image."""
    import fitz
    from PIL import Image

    path = _require_pdf(pdf_path)
    doc = fitz.open(path)
    try:
        page = doc[page_num - 1]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    finally:
        doc.close()


async def ocr_page_with_gemini(pdf_path: str, page_num: int) -> str:
    """OCR an image-heavy PDF page with Gemini 2.5 Flash."""
    if not settings.effective_gemini_api_key:
        return ""

    def _call() -> str:
        import google.generativeai as genai
        from PIL import Image

        genai.configure(api_key=settings.effective_gemini_api_key)
        model = genai.GenerativeModel(settings.model_name)
        image = render_page_image(pdf_path, page_num)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        response = model.generate_content([CHEMISTRY_OCR_PROMPT, Image.open(buffer)])
        return response.text or ""

    return await asyncio.to_thread(_call)
