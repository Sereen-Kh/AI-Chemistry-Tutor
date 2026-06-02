"""Gemini document provider for chemistry textbook page understanding."""

from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
import time
from pathlib import Path

from pydantic import ValidationError

from app.core.config import settings
from app.services.gemini_client import document_generation_config, get_gemini_client
from app.services.ocr.base import PageExtractionResult, UploadedDocument, VisionExtractionProvider
from app.services.ocr.quality import evaluate_extraction_quality

logger = logging.getLogger(__name__)

GEMINI_DOCUMENT_PROMPT = """
You are extracting content from an Arabic Grade 9 Chemistry textbook PDF.

Target page: {page_number}

Extract ONLY the target page.
If neighboring page numbers are provided, use them only to understand context, headings, continuation, or references.
Do not include neighboring page content in the target page result.

Return valid JSON matching the provided schema.

Rules:
- Preserve Arabic text exactly.
- Do not transliterate Arabic.
- Do not summarize.
- Extract all visible educational content from the target page.
- Include a complete raw_markdown field containing the full extracted content of the target page.
- Extract headings, body text, side boxes, examples, exercises, tables, diagrams, labels, equations, and answer keys if visible.
- Preserve chemical notation such as H₂O, CO₂, H₂SO₄, NaCl.
- Preserve reaction notation such as 2H₂ + O₂ → 2H₂O.
- Extract tables as markdown.
- Describe diagrams clearly enough for retrieval-augmented generation.
- Extract all visible questions.
- Keep each question with its options.
- If an official answer is visible, include it.
- If the answer is not visible, set correct_answer=null and answer_source="unknown".
- Do not invent answers.
- If text is unclear, add a warning.
- Return JSON only.
"""


def gemini_page_prompt(
    page_number: int,
    source_type: str,
    source_kind: str,
    neighboring_pages: list[int] | None = None,
) -> str:
    """Build the structured extraction prompt for one page."""
    if source_kind == "pdf":
        page_instruction = (
            f"The attached PDF is the full source document. Extract ONLY page {page_number}. "
            "Ignore every other page."
        )
    else:
        page_instruction = f"The attached image is page {page_number}."
    return (
        f"{GEMINI_DOCUMENT_PROMPT.format(page_number=page_number)}\n\n"
        f"source_type={source_type}\n"
        f"page_number={page_number}\n"
        f"neighboring_pages={neighboring_pages or []}\n"
        f"{page_instruction}"
    )


def _has_structured_content(result: PageExtractionResult) -> bool:
    return bool(result.sections or result.questions or result.diagrams or result.tables or result.equations)


def _result_text(result: PageExtractionResult) -> str:
    parts: list[str] = [result.raw_markdown]
    parts.extend(section.content for section in result.sections if section.content)
    parts.extend(question.question_text for question in result.questions if question.question_text)
    parts.extend(diagram.description for diagram in result.diagrams if diagram.description)
    parts.extend(table.markdown for table in result.tables if table.markdown)
    parts.extend(equation.equation for equation in result.equations if equation.equation)
    return "\n\n".join(parts)


def _quality_issue(result: PageExtractionResult) -> str | None:
    report = evaluate_extraction_quality(result)
    return report.issues[0] if report.should_fallback and report.issues else None


def _finalize_result(result: PageExtractionResult, *, model_name: str, provider: str) -> PageExtractionResult:
    result.provider = provider
    result.model_name = model_name
    result.char_count = result.char_count if result.char_count is not None else len(_result_text(result))
    if result.completeness_score is None:
        result.completeness_score = 1.0 if _has_structured_content(result) else 0.0
    result.quality_report = evaluate_extraction_quality(result)
    return result


class GeminiExtractionQualityError(RuntimeError):
    """Raised when direct Gemini document extraction cannot meet quality thresholds."""


def _file_state_name(file_obj: object) -> str:
    state = getattr(file_obj, "state", None)
    if state is None:
        return ""
    name = getattr(state, "name", None)
    return str(name or state).upper()


def _guess_mime_type(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "image/png"


class GeminiVisionProvider(VisionExtractionProvider):
    """Gemini document/page extraction provider."""

    name = "gemini_document"

    @property
    def is_configured(self) -> bool:
        return bool(settings.effective_gemini_api_key)

    def _client(self):
        return get_gemini_client()

    def _generate_result(
        self,
        contents: list[object],
        model_name: str,
        page_number: int,
        provider: str,
    ) -> PageExtractionResult:
        client = self._client()
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=document_generation_config(PageExtractionResult),
        )
        parsed = getattr(response, "parsed", None)
        if parsed is not None:
            if isinstance(parsed, PageExtractionResult):
                result = parsed
            else:
                result = PageExtractionResult.model_validate(parsed)
            result.provider = provider
            result.model_name = model_name
            result.schema_valid = True
            result.raw_text = response.text or result.raw_text
            return result
        return parse_gemini_json(response.text or "", page_number, provider=provider, model_name=model_name)

    def _document_models(self) -> list[str]:
        models = [settings.gemini_document_model]
        fallback = settings.gemini_document_fallback_model
        if fallback and fallback not in models:
            models.append(fallback)
        return models

    async def _extract_with_model_routing(
        self,
        *,
        page_number: int,
        provider: str,
        build_contents,
    ) -> PageExtractionResult:
        """Run primary document model, then fallback model when quality is too low."""
        last_issue = ""
        primary_issue = ""

        for index, model_name in enumerate(self._document_models()):
            try:
                result = await asyncio.to_thread(
                    lambda: self._generate_result(build_contents(), model_name, page_number, provider)
                )
            except Exception as exc:
                last_issue = f"request_failed:{exc}"
                if index == 0:
                    primary_issue = last_issue
                    logger.warning(
                        "Gemini document extraction request failed for page %s with model %s: %s",
                        page_number,
                        model_name,
                        exc,
                    )
                    continue
                raise GeminiExtractionQualityError(
                    f"Gemini document extraction failed for page {page_number} with model {model_name}: {exc}"
                ) from exc

            result = _finalize_result(result, model_name=model_name, provider=provider)
            issue = _quality_issue(result)
            if not issue:
                if primary_issue:
                    result.warnings.insert(
                        0,
                        f"Primary Gemini document model {settings.gemini_document_model} failed quality check: {primary_issue}.",
                    )
                return result

            last_issue = issue
            if index == 0:
                primary_issue = issue
                logger.warning(
                    "Gemini document extraction quality check failed for page %s with model %s: %s",
                    page_number,
                    model_name,
                    issue,
                )

        raise GeminiExtractionQualityError(
            f"Gemini document extraction failed quality checks for page {page_number}: {last_issue}"
        )

    async def upload_pdf(self, pdf_path: str) -> UploadedDocument | None:
        """Upload the PDF once through the Gemini Files API."""
        if not self.is_configured or not settings.pdf_direct_extraction_enabled:
            return None

        source_path = Path(pdf_path).expanduser().resolve()
        if not source_path.exists():
            raise FileNotFoundError(f"PDF not found: {source_path}")

        def _call() -> UploadedDocument:
            from google.genai import types

            client = self._client()
            file_obj = client.files.upload(
                file=str(source_path),
                config=types.UploadFileConfig(
                    mime_type="application/pdf",
                    display_name=source_path.name,
                ),
            )

            # PDF uploads can briefly be PROCESSING. Wait for ACTIVE, but fail fast
            # if Gemini marks the file as failed.
            for _ in range(30):
                state = _file_state_name(file_obj)
                if not state or "ACTIVE" in state:
                    break
                if "FAILED" in state:
                    raise RuntimeError(f"Gemini file upload failed for {source_path.name}: {state}")
                time.sleep(2)
                file_obj = client.files.get(name=file_obj.name)

            state = _file_state_name(file_obj)
            if state and "ACTIVE" not in state:
                raise TimeoutError(f"Gemini file upload did not become ACTIVE for {source_path.name}: {state}")
            if not file_obj.uri:
                raise RuntimeError(f"Gemini file upload did not return a file URI for {source_path.name}.")

            return UploadedDocument(
                provider=self.name,
                name=file_obj.name,
                uri=file_obj.uri,
                mime_type=file_obj.mime_type or "application/pdf",
                display_name=file_obj.display_name,
            )

        return await asyncio.to_thread(_call)

    async def extract_page_from_pdf(
        self,
        uploaded_pdf: UploadedDocument,
        page_number: int,
        source_type: str,
        neighboring_pages: list[int] | None = None,
    ) -> PageExtractionResult:
        """Extract a single page directly from an uploaded PDF file handle."""
        if not self.is_configured:
            return PageExtractionResult(
                page_number=page_number,
                provider=self.name,
                schema_valid=False,
                warnings=["Gemini document extraction is not configured. GEMINI_API_KEY is required for PDF extraction."],
            )
        if not settings.pdf_direct_extraction_enabled:
            return PageExtractionResult(
                page_number=page_number,
                provider=self.name,
                schema_valid=False,
                warnings=["Gemini direct PDF extraction is disabled by PDF_DIRECT_EXTRACTION_ENABLED=false."],
            )

        def _contents() -> list[object]:
            from google.genai import types

            prompt = gemini_page_prompt(
                page_number,
                source_type,
                source_kind="pdf",
                neighboring_pages=neighboring_pages,
            )
            pdf_part = types.Part.from_uri(file_uri=uploaded_pdf.uri, mime_type=uploaded_pdf.mime_type)
            return [pdf_part, types.Part.from_text(text=prompt)]

        return await self._extract_with_model_routing(
            page_number=page_number,
            provider=f"{self.name}_pdf",
            build_contents=_contents,
        )

    async def extract_page(
        self,
        image_path: str,
        page_number: int,
        source_type: str,
    ) -> PageExtractionResult:
        if not self.is_configured:
            return PageExtractionResult(
                page_number=page_number,
                provider=self.name,
                schema_valid=False,
                warnings=["Gemini document extraction is not configured. GEMINI_API_KEY is required for image extraction."],
            )
        if not settings.pdf_image_fallback_enabled:
            return PageExtractionResult(
                page_number=page_number,
                provider=self.name,
                schema_valid=False,
                warnings=["Gemini image fallback is disabled by PDF_IMAGE_FALLBACK_ENABLED=false."],
            )

        def _contents() -> list[object]:
            from google.genai import types

            path = Path(image_path).expanduser().resolve()
            prompt = gemini_page_prompt(page_number, source_type, source_kind="image")
            image_part = types.Part.from_bytes(data=path.read_bytes(), mime_type=_guess_mime_type(path))
            return [image_part, types.Part.from_text(text=prompt)]

        return await self._extract_with_model_routing(
            page_number=page_number,
            provider=f"{self.name}_image",
            build_contents=_contents,
        )


def parse_gemini_json(
    raw: str,
    page_number: int,
    provider: str = "gemini_document",
    model_name: str | None = None,
    strip_code_fences: bool = False,
) -> PageExtractionResult:
    """Parse Gemini JSON with a conservative plain-text fallback."""
    text = (raw or "").strip()
    if strip_code_fences and text.startswith("```"):
        text = text.strip("`").strip()
        if text.startswith("json"):
            text = text[4:].strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            data.setdefault("page_number", page_number)
            data["provider"] = provider
            data["model_name"] = model_name
            data["schema_valid"] = True
            data["raw_text"] = raw
            return PageExtractionResult.model_validate(data)
    except (TypeError, ValueError, json.JSONDecodeError, ValidationError) as exc:
        logger.warning("Gemini JSON parsing failed for page %s: %s", page_number, exc)
    return PageExtractionResult(
        page_number=page_number,
        sections=[{"heading": None, "content": raw, "content_type": "mixed"}] if raw else [],
        warnings=["Gemini document response was not valid structured JSON."],
        provider=provider,
        model_name=model_name,
        schema_valid=False,
        char_count=len(raw or ""),
        completeness_score=0.0,
        raw_markdown=raw or "",
        raw_text=raw,
    )
