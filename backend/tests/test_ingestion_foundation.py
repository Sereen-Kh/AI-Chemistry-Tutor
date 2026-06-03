"""Unit coverage for the Gemini-only ingestion foundation."""

from __future__ import annotations

from pathlib import Path
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import Mock, patch

from app.core.config import settings
from app.services.ingestion_pipeline import _extract_page, _final_ingestion_status, _neighboring_pages
from app.services.ocr.base import PageExtractionResult, UploadedDocument
from app.services.ocr.gemini_provider import GeminiVisionProvider


class FakeVisionProvider:
    name = "gemini_document"
    is_configured = True

    def __init__(self, result: PageExtractionResult):
        self.result = result
        self.calls: list[tuple[str, int, str]] = []

    async def extract_page(self, image_path: str, page_number: int, source_type: str) -> PageExtractionResult:
        self.calls.append((image_path, page_number, source_type))
        return self.result


class FakePdfVisionProvider(FakeVisionProvider):
    def __init__(self, pdf_result: PageExtractionResult, image_result: PageExtractionResult | None = None):
        super().__init__(image_result or pdf_result)
        self.pdf_result = pdf_result
        self.pdf_calls: list[tuple[str, int, str, list[int]]] = []

    async def extract_page_from_pdf(
        self,
        uploaded_pdf: UploadedDocument,
        page_number: int,
        source_type: str,
        neighboring_pages: list[int] | None = None,
    ) -> PageExtractionResult:
        self.pdf_calls.append((uploaded_pdf.uri, page_number, source_type, neighboring_pages or []))
        return self.pdf_result


class MissingVisionProvider:
    name = "gemini_document"
    is_configured = False

    async def extract_page(self, image_path: str, page_number: int, source_type: str) -> PageExtractionResult:
        raise AssertionError("Missing Gemini provider must not be called")


def text_payload(content: str = "المحاليل المائية") -> dict:
    return {
        "sections": [{"heading": None, "content": content, "content_type": "text"}],
        "questions": [],
        "diagrams": [],
        "tables": [],
        "equations": [],
        "warnings": [],
    }


class IngestionPageExtractionTests(IsolatedAsyncioTestCase):
    async def test_selectable_text_page_does_not_call_gemini(self):
        provider = MissingVisionProvider()
        with patch("app.services.ingestion_pipeline._structured_text_page", return_value=text_payload()):
            payload, method = await _extract_page(
                "book.pdf",
                1,
                "SELECTABLE_TEXT",
                "chemistry",
                "textbook",
                provider,
                "production",
                True,
            )

        self.assertEqual(payload["status"], "completed_text_only")
        self.assertEqual(payload["page_number"], 1)
        self.assertEqual(payload["extraction_methods"], ["pymupdf", "pdfplumber"])
        self.assertEqual(method, "pymupdf+pdfplumber")
        self.assertIn("raw_markdown", payload)
        self.assertIn("quality_report", payload)
        self.assertGreater(payload["char_count"], 0)

    async def test_needs_vision_page_calls_gemini_and_preserves_structured_content(self):
        result = PageExtractionResult(
            page_number=3,
            sections=[
                {
                    "heading": None,
                    "content": "نص ممسوح من الصفحة يحتوي على شرح كاف للتأكد من جودة الاستخراج من نموذج جيميني.",
                    "content_type": "text",
                }
            ],
            questions=[{"question_text": "ما تعريف المحلول؟", "answer_source": "unknown"}],
            diagrams=[{"title": "مخطط", "description": "وصف المخطط", "labels": []}],
            tables=[{"title": "جدول", "markdown": "| أ | ب |\n| --- | --- |"}],
            equations=[{"equation": "H₂O", "description": "الماء"}],
        )
        provider = FakeVisionProvider(result)
        with (
            patch("app.services.ingestion_pipeline._structured_text_page", return_value={"sections": []}),
            patch("app.services.ingestion_pipeline.render_page_to_image", return_value=Path("page_003.png")),
        ):
            payload, method = await _extract_page(
                "book.pdf",
                3,
                "NEEDS_VISION",
                "chemistry",
                "textbook",
                provider,
                "production",
                True,
            )

        self.assertEqual(payload["status"], "completed_with_image_fallback")
        self.assertEqual(method, "gemini_image_300dpi")
        self.assertEqual(provider.calls, [("page_003.png", 3, "textbook")])
        self.assertEqual(len(payload["questions"]), 1)
        self.assertEqual(len(payload["diagrams"]), 1)
        self.assertEqual(len(payload["tables"]), 1)
        self.assertEqual(len(payload["equations"]), 1)
        self.assertIn("gemini_image_fallback_content", payload)
        self.assertIn("raw_markdown", payload)

    async def test_mixed_vision_page_merges_and_deduplicates_text(self):
        result = PageExtractionResult(
            page_number=2,
            sections=[
                {"heading": None, "content": "فقرة من طبقة النص", "content_type": "text"},
                {
                    "heading": None,
                    "content": "وصف بصري إضافي طويل يشرح الرسم الكيميائي والعلاقات بين أجزائه بشكل مناسب.",
                    "content_type": "diagram",
                },
            ],
        )
        provider = FakeVisionProvider(result)
        with (
            patch("app.services.ingestion_pipeline._structured_text_page", return_value=text_payload("فقرة من طبقة النص")),
            patch("app.services.ingestion_pipeline.render_page_to_image", return_value=Path("page_002.png")),
        ):
            payload, _method = await _extract_page(
                "book.pdf",
                2,
                "MIXED_VISION",
                "chemistry",
                "textbook",
                provider,
                "production",
                True,
            )

        contents = [section["content"] for section in payload["sections"]]
        self.assertEqual(contents.count("فقرة من طبقة النص"), 1)
        self.assertIn("وصف بصري إضافي طويل يشرح الرسم الكيميائي والعلاقات بين أجزائه بشكل مناسب.", contents)
        self.assertEqual(payload["status"], "completed_with_image_fallback")

    async def test_vision_page_uses_uploaded_pdf_before_rendered_image(self):
        result = PageExtractionResult(
            page_number=3,
            sections=[
                {
                    "heading": None,
                    "content": "نص من ملف PDF المرفوع يحتوي على محتوى كيميائي كاف لتجاوز فحص الجودة.",
                    "content_type": "text",
                }
            ],
        )
        provider = FakePdfVisionProvider(result)
        uploaded_pdf = UploadedDocument(name="files/book", uri="https://gemini.test/files/book", mime_type="application/pdf")
        with (
            patch("app.services.ingestion_pipeline._structured_text_page", return_value={"sections": []}),
            patch("app.services.ingestion_pipeline.render_page_to_image") as render_page,
        ):
            payload, method = await _extract_page(
                "book.pdf",
                3,
                "NEEDS_VISION",
                "chemistry",
                "textbook",
                provider,
                "production",
                True,
                uploaded_pdf,
            )

        self.assertEqual(payload["status"], "completed_with_pdf_extraction")
        self.assertEqual(method, "gemini_pdf_file")
        self.assertEqual(payload["vision_source"], "gemini_files_api_pdf")
        self.assertEqual(provider.pdf_calls, [("https://gemini.test/files/book", 3, "textbook", [])])
        self.assertEqual(provider.calls, [])
        self.assertTrue(payload["gemini_pdf_content"])
        self.assertEqual(payload["gemini_image_fallback_content"], {})
        render_page.assert_not_called()

    async def test_vision_page_falls_back_to_300_dpi_image_when_pdf_has_no_content(self):
        pdf_result = PageExtractionResult(page_number=3)
        image_result = PageExtractionResult(
            page_number=3,
            sections=[
                {
                    "heading": None,
                    "content": "نص من الصورة المولدة بدقة عالية ويحتوي على تفاصيل كيميائية كافية.",
                    "content_type": "text",
                }
            ],
        )
        provider = FakePdfVisionProvider(pdf_result=pdf_result, image_result=image_result)
        uploaded_pdf = UploadedDocument(name="files/book", uri="https://gemini.test/files/book", mime_type="application/pdf")
        with (
            patch("app.services.ingestion_pipeline._structured_text_page", return_value={"sections": []}),
            patch("app.services.ingestion_pipeline.render_page_to_image", return_value=Path("page_003.png")) as render_page,
        ):
            payload, method = await _extract_page(
                "book.pdf",
                3,
                "NEEDS_VISION",
                "chemistry",
                "textbook",
                provider,
                "production",
                True,
                uploaded_pdf,
            )

        self.assertEqual(payload["status"], "completed_with_image_fallback")
        self.assertEqual(method, "gemini_pdf_file+gemini_image_300dpi")
        self.assertEqual(payload["vision_source"], "gemini_rendered_image_300dpi")
        self.assertTrue(payload["gemini_pdf_content"])
        self.assertTrue(payload["gemini_image_fallback_content"])
        self.assertEqual(provider.calls, [("page_003.png", 3, "textbook")])
        render_page.assert_called_once()
        self.assertEqual(render_page.call_args.args[:2], ("book.pdf", 3))
        self.assertEqual(render_page.call_args.kwargs, {"dpi": 300})

    async def test_direct_pdf_extraction_receives_neighboring_page_context(self):
        result = PageExtractionResult(
            page_number=4,
            sections=[
                {
                    "heading": None,
                    "content": "نص عربي كيميائي كاف من الصفحة الهدف مع سياق الصفحات المجاورة.",
                    "content_type": "text",
                }
            ],
        )
        provider = FakePdfVisionProvider(result)
        uploaded_pdf = UploadedDocument(name="files/book", uri="https://gemini.test/files/book", mime_type="application/pdf")
        with patch("app.services.ingestion_pipeline._structured_text_page", return_value={"sections": []}):
            payload, _method = await _extract_page(
                "book.pdf",
                4,
                "NEEDS_VISION",
                "chemistry",
                "textbook",
                provider,
                "production",
                True,
                uploaded_pdf,
                [3, 5],
            )

        self.assertEqual(provider.pdf_calls, [("https://gemini.test/files/book", 4, "textbook", [3, 5])])
        self.assertEqual(payload["neighboring_pages"], [3, 5])

    async def test_missing_gemini_dry_run_records_skipped_page(self):
        with patch("app.services.ingestion_pipeline._structured_text_page", return_value=text_payload()):
            payload, _method = await _extract_page(
                "book.pdf",
                2,
                "MIXED_VISION",
                "chemistry",
                "textbook",
                MissingVisionProvider(),
                "dry_run",
                True,
            )

        self.assertEqual(payload["status"], "skipped_dry_run")
        self.assertTrue(payload["warnings"])
        self.assertFalse(payload["errors"])
        self.assertGreater(payload["char_count"], 0)

    async def test_missing_gemini_production_fails_page(self):
        with patch("app.services.ingestion_pipeline._structured_text_page", return_value={"sections": []}):
            payload, _method = await _extract_page(
                "book.pdf",
                3,
                "NEEDS_VISION",
                "chemistry",
                "textbook",
                MissingVisionProvider(),
                "production",
                True,
            )

        self.assertEqual(payload["status"], "failed")
        self.assertTrue(payload["errors"])
        self.assertEqual(payload["char_count"], 0)

    async def test_gemini_document_provider_retries_fallback_model_on_low_char_count(self):
        provider = GeminiVisionProvider()
        primary_result = PageExtractionResult(
            page_number=1,
            detected_language="ar",
            sections=[{"heading": None, "content": "قصير", "content_type": "text"}],
        )
        fallback_result = PageExtractionResult(
            page_number=1,
            detected_language="ar",
            sections=[
                {
                    "heading": None,
                    "content": "محتوى كيميائي عربي طويل بما يكفي لتجاوز حد عدد الأحرف وفحص الجودة.",
                    "content_type": "text",
                }
            ],
        )

        with (
            patch.object(settings, "gemini_document_model", "model-primary"),
            patch.object(settings, "gemini_document_fallback_model", "model-fallback"),
            patch.object(provider, "_generate_result", side_effect=[primary_result, fallback_result]) as generate,
        ):
            result = await provider._extract_with_model_routing(
                page_number=1,
                provider="gemini_document_pdf",
                build_contents=lambda: ["pdf_part", "prompt_part"],
            )

        self.assertEqual(generate.call_args_list[0].args[1], "model-primary")
        self.assertEqual(generate.call_args_list[1].args[1], "model-fallback")
        self.assertEqual(result.model_name, "model-fallback")
        self.assertEqual(result.provider, "gemini_document_pdf")
        self.assertTrue(result.schema_valid)
        self.assertGreaterEqual(result.char_count or 0, 40)
        self.assertTrue(result.warnings)

    async def test_gemini_document_provider_retries_fallback_model_on_request_failure(self):
        provider = GeminiVisionProvider()
        fallback_result = PageExtractionResult(
            page_number=1,
            detected_language="ar",
            sections=[
                {
                    "heading": None,
                    "content": "استخراج ناجح من نموذج fallback بعد فشل طلب النموذج الأساسي للصفحة.",
                    "content_type": "text",
                }
            ],
        )

        with (
            patch.object(settings, "gemini_document_model", "model-primary"),
            patch.object(settings, "gemini_document_fallback_model", "model-fallback"),
            patch.object(
                provider,
                "_generate_result",
                side_effect=[RuntimeError("model unavailable"), fallback_result],
            ) as generate,
        ):
            result = await provider._extract_with_model_routing(
                page_number=1,
                provider="gemini_document_pdf",
                build_contents=lambda: ["pdf_part", "prompt_part"],
            )

        self.assertEqual(generate.call_args_list[0].args[1], "model-primary")
        self.assertEqual(generate.call_args_list[1].args[1], "model-fallback")
        self.assertEqual(result.model_name, "model-fallback")


class QuestionExtractionRulesTests(TestCase):
    def test_neighboring_pages_excludes_out_of_range_pages(self):
        self.assertEqual(_neighboring_pages(1, 96), [2])
        self.assertEqual(_neighboring_pages(40, 96), [39, 41])
        self.assertEqual(_neighboring_pages(96, 96), [95])

    def test_dry_run_with_skipped_vision_pages_is_not_completed(self):
        status = _final_ingestion_status(
            ingestion_mode="dry_run",
            failed_pages=[3],
            skipped_dry_run_pages=[3],
        )

        self.assertEqual(status, "dry_run_incomplete")

    def test_production_with_failed_required_pages_is_failed(self):
        status = _final_ingestion_status(
            ingestion_mode="production",
            failed_pages=[3],
            skipped_dry_run_pages=[],
        )

        self.assertEqual(status, "failed")

    def test_visible_answers_keep_official_answer_source(self):
        from app.services.ingestion_pipeline import _store_questions

        db = Mock()
        source = Mock(id=7)
        page_payload = {
            "questions": [
                {
                    "question_text": "اختر الإجابة الصحيحة",
                    "question_type": "multiple_choice",
                    "correct_answer": "أ",
                    "answer_source": "page",
                },
                {
                    "question_text": "اشرح السبب",
                    "question_type": "short_answer",
                    "correct_answer": None,
                    "answer_source": "unknown",
                },
            ]
        }

        created = _store_questions(db, source, 4, page_payload, None, None, None)

        self.assertEqual(created, 2)
        first_call, second_call = db.add.call_args_list
        self.assertEqual(first_call.args[0].answer_source, "page")
        self.assertFalse(first_call.args[0].needs_review)
        self.assertEqual(second_call.args[0].answer_source, "unknown")
        self.assertTrue(second_call.args[0].needs_review)
