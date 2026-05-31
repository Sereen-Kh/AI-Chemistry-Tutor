"""PDF classification, text extraction, and OCR helpers."""

from __future__ import annotations

from pathlib import Path


def _require_pdf(path: str | Path) -> Path:
    pdf_path = Path(path).expanduser()
    if not pdf_path.is_absolute():
        pdf_path = Path.cwd() / pdf_path
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    return pdf_path


def classify_pages(pdf_path: str) -> dict:
    """Classify pages as SELECTABLE_TEXT, NEEDS_VISION, or MIXED_VISION."""
    import fitz
    import pdfplumber

    path = _require_pdf(pdf_path)
    text_pages: list[int] = []
    image_pages: list[int] = []
    mixed_pages: list[int] = []
    pages: list[dict] = []
    doc = fitz.open(path)
    with pdfplumber.open(path) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            text = (doc[index - 1].get_text("text") or page.extract_text() or "").strip()
            compact_len = len("".join(text.split()))
            visual = detect_visual_content(pdf_path, index)
            image_count = visual["image_count"]
            image_area_ratio = visual["image_area_ratio"]
            if compact_len <= 50:
                page_type = "NEEDS_VISION"
                image_pages.append(index)
            elif visual["has_important_visual_content"]:
                page_type = "MIXED_VISION"
                mixed_pages.append(index)
            else:
                page_type = "SELECTABLE_TEXT"
                text_pages.append(index)
            pages.append(
                {
                    "page_number": index,
                    "page_type": page_type,
                    "text_chars": len(text),
                    "image_count": image_count,
                    "image_area_ratio": round(image_area_ratio, 4),
                    "table_count": visual["table_count"],
                    "has_equation_hints": visual["has_equation_hints"],
                }
            )
    doc.close()
    return {
        "text_pages": text_pages,
        "image_pages": image_pages,
        "mixed_pages": mixed_pages,
        "pages": pages,
        "total_pages": len(pages),
    }


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
    import fitz
    import pdfplumber

    path = _require_pdf(pdf_path)
    doc = fitz.open(path)
    try:
        text = doc[page_num - 1].get_text("text") or ""
    finally:
        doc.close()
    with pdfplumber.open(path) as pdf:
        page = pdf.pages[page_num - 1]
        tables = page.extract_tables() or []
    table_text = "\n\n".join(_table_to_markdown(table) for table in tables if table)
    return "\n\n".join(part for part in [text.strip(), table_text.strip()] if part)


def extract_selectable_text_page(pdf_path: str, page_num: int) -> str:
    """Extract selectable page text for ingestion."""
    return extract_text_page(pdf_path, page_num)


def detect_visual_content(pdf_path: str, page_num: int) -> dict:
    """Detect whether a page likely contains important visual content."""
    import fitz
    import pdfplumber

    path = _require_pdf(pdf_path)
    with pdfplumber.open(path) as pdf:
        page = pdf.pages[page_num - 1]
        width = float(page.width or 1)
        height = float(page.height or 1)
        page_area = width * height
        image_count = len(page.images or [])
        image_area = sum(float(img.get("width", 0)) * float(img.get("height", 0)) for img in page.images or [])
        image_area_ratio = min(image_area / page_area, 1.0) if page_area else 0
        table_count = len(page.extract_tables() or [])
    doc = fitz.open(path)
    try:
        text = doc[page_num - 1].get_text("text") or ""
    finally:
        doc.close()
    equation_markers = ["=", "→", "↔", "H₂", "O₂", "CO₂", "NaCl", "مول", "معادلة"]
    has_equation_hints = any(marker in text for marker in equation_markers)
    return {
        "image_count": image_count,
        "image_area_ratio": round(image_area_ratio, 4),
        "table_count": table_count,
        "has_equation_hints": has_equation_hints,
        "has_important_visual_content": image_area_ratio >= 0.15 or table_count > 0,
    }


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


def render_page_image_file(
    pdf_path: str,
    page_num: int,
    output_dir: str | Path,
    dpi: int = 300,
) -> Path:
    """Render a one-based PDF page to a PNG file and return its path."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    image_path = output_path / f"page_{page_num:03d}.png"
    if image_path.exists():
        return image_path
    image = render_page_image(pdf_path, page_num, dpi=dpi)
    image.save(image_path, format="PNG")
    return image_path


def render_page_to_image(
    pdf_path: str,
    page_num: int,
    output_dir: str | Path,
    dpi: int = 300,
) -> Path:
    """Render a one-based PDF page to a 300 DPI PNG file for Gemini Vision."""
    return render_page_image_file(pdf_path, page_num, output_dir, dpi=dpi)
