"""Contract tests for Gemini document extraction foundation."""

from __future__ import annotations

from pathlib import Path
from unittest import TestCase

from app.services.ocr.base import PageExtractionResult
from app.services.ocr.gemini_provider import GeminiDocumentProvider, GeminiVisionProvider, parse_gemini_json
from app.services.ocr.quality import evaluate_extraction_quality
from scripts.benchmark_extraction import _score_payload


class ExtractionContractTests(TestCase):
    def test_legacy_google_generativeai_is_not_imported(self):
        backend_dir = Path(__file__).resolve().parents[1]
        offenders = []
        search_roots = [backend_dir / "app", backend_dir / "scripts", backend_dir / "requirements.txt"]
        for root in search_roots:
            paths = root.rglob("*.py") if root.is_dir() else [root]
            for path in paths:
                if "__pycache__" in path.parts:
                    continue
                if "google.generativeai" in path.read_text(encoding="utf-8", errors="ignore"):
                    offenders.append(str(path.relative_to(backend_dir)))
        self.assertEqual(offenders, [])

    def test_google_genai_dependency_is_declared(self):
        requirements = Path(__file__).resolve().parents[1] / "requirements.txt"
        text = requirements.read_text(encoding="utf-8")
        active_lines = "\n".join(line for line in text.splitlines() if not line.strip().startswith("#"))

        self.assertIn("google-genai", text)
        self.assertNotIn("google-generativeai", active_lines)

    def test_document_provider_exposes_requested_contract_names(self):
        provider = GeminiDocumentProvider()

        self.assertTrue(hasattr(provider, "prepare_document"))
        self.assertTrue(hasattr(provider, "extract_pdf_page"))
        self.assertTrue(hasattr(provider, "extract_page_image_fallback"))

    def test_page_extraction_result_always_has_raw_markdown(self):
        result = PageExtractionResult(
            page_number=11,
            sections=[
                {
                    "heading": "الحموض",
                    "content": "الحموض: مواد تعطي عند انحلالها في الماء أيونات الهدروجين.",
                    "content_type": "text",
                }
            ],
        )

        self.assertIn("الحموض", result.raw_markdown)
        self.assertGreater(result.char_count or 0, 0)

    def test_quality_report_flags_empty_or_low_quality_output(self):
        result = PageExtractionResult(page_number=3, schema_valid=False)

        report = evaluate_extraction_quality(result, page_type="NEEDS_VISION")

        self.assertTrue(report.should_fallback)
        self.assertIn("invalid_schema", report.issues)
        self.assertIn("empty_output", report.issues)

    def test_normal_json_parser_does_not_strip_fences(self):
        raw = '```json\n{"page_number": 1, "raw_markdown": "نص", "sections": []}\n```'

        result = parse_gemini_json(raw, page_number=1)

        self.assertFalse(result.schema_valid)
        self.assertEqual(result.raw_markdown, raw)

    def test_generate_result_uses_response_parsed_when_available(self):
        provider = GeminiVisionProvider()
        parsed = PageExtractionResult(
            page_number=5,
            raw_markdown="نص عربي كامل من الصفحة.",
            sections=[{"heading": None, "content": "نص عربي كامل من الصفحة.", "content_type": "text"}],
        )

        class FakeResponse:
            text = '{"page_number": 5}'

        FakeResponse.parsed = parsed

        class FakeModels:
            def generate_content(self, **_kwargs):
                return FakeResponse()

        class FakeClient:
            models = FakeModels()

        provider._client = lambda: FakeClient()  # type: ignore[method-assign]

        result = provider._generate_result(["contents"], "gemini-test", 5, "gemini_document_pdf")

        self.assertTrue(result.schema_valid)
        self.assertEqual(result.provider, "gemini_document_pdf")
        self.assertEqual(result.model_name, "gemini-test")
        self.assertEqual(result.raw_markdown, "نص عربي كامل من الصفحة.")

    def test_benchmark_payload_scoring_detects_structured_signals(self):
        score = _score_payload(
            {
                "raw_markdown": "الحموض مواد تعطي H+ عند انحلالها في الماء.",
                "sections": [{"content": "الحموض مواد تعطي H+.", "content_type": "text"}],
                "tables": [{"markdown": "| الحمض | الصيغة |\n| --- | --- |"}],
                "equations": [{"equation": "HCl → H+ + Cl-"}],
                "questions": [{"question_text": "ما تعريف الحمض؟", "correct_answer": None}],
            }
        )

        self.assertGreater(score["score"], 40)
        self.assertTrue(score["schema_valid"])
        self.assertGreaterEqual(score["table_count"], 1)
        self.assertGreaterEqual(score["equation_signal_count"], 1)
