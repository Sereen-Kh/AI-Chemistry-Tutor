"""Unit coverage for the Gemini-only ingestion foundation."""

from __future__ import annotations

from pathlib import Path
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import Mock, patch

from app.services.ingestion_pipeline import _extract_page
from app.services.ocr.base import PageExtractionResult


class FakeVisionProvider:
    name = "gemini_vision"
    is_configured = True

    def __init__(self, result: PageExtractionResult):
        self.result = result
        self.calls: list[tuple[str, int, str]] = []

    async def extract_page(self, image_path: str, page_number: int, source_type: str) -> PageExtractionResult:
        self.calls.append((image_path, page_number, source_type))
        return self.result


class MissingVisionProvider:
    name = "gemini_vision"
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
        self.assertGreater(payload["char_count"], 0)

    async def test_needs_vision_page_calls_gemini_and_preserves_structured_content(self):
        result = PageExtractionResult(
            page_number=3,
            sections=[{"heading": None, "content": "نص ممسوح من الصفحة", "content_type": "text"}],
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

        self.assertEqual(payload["status"], "completed_with_vision")
        self.assertEqual(method, "gemini_vision")
        self.assertEqual(provider.calls, [("page_003.png", 3, "textbook")])
        self.assertEqual(len(payload["questions"]), 1)
        self.assertEqual(len(payload["diagrams"]), 1)
        self.assertEqual(len(payload["tables"]), 1)
        self.assertEqual(len(payload["equations"]), 1)

    async def test_mixed_vision_page_merges_and_deduplicates_text(self):
        result = PageExtractionResult(
            page_number=2,
            sections=[
                {"heading": None, "content": "فقرة من طبقة النص", "content_type": "text"},
                {"heading": None, "content": "وصف بصري إضافي", "content_type": "diagram"},
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
        self.assertIn("وصف بصري إضافي", contents)
        self.assertEqual(payload["status"], "completed_with_vision")

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


class QuestionExtractionRulesTests(TestCase):
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
