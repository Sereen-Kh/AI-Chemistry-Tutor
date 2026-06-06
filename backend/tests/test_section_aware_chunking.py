"""Tests for section-aware cached-page chunk construction."""

from __future__ import annotations

from unittest import TestCase

from app.services.chunking import build_page_chunk_records, split_text


class SectionAwareChunkingTests(TestCase):
    def test_default_text_split_uses_larger_retrieval_chunks(self):
        text = " ".join("حمض" for _ in range(400))
        chunks = split_text(text)

        self.assertGreaterEqual(len(chunks), 2)
        self.assertLessEqual(len(chunks[0]), 900)

    def test_table_equation_diagram_and_question_stay_atomic(self):
        payload = {
            "page_number": 11,
            "page_type": "MIXED_VISION",
            "status": "completed_with_vision",
            "sections": [
                {
                    "heading": "الحموض",
                    "content": "الحموض: موادّ تُعطي عند انحلالها في الماء أيونات الهدروجين.",
                    "content_type": "text",
                }
            ],
            "tables": [{"title": "أمثلة", "markdown": "| الحمض | الصيغة |\n| --- | --- |\n| حمض كلور الماء | HCl |"}],
            "equations": [{"equation": "HCl → H+ + Cl-", "description": "تأين حمض كلور الماء"}],
            "diagrams": [{"title": "كاشف", "description": "ورقة عباد الشمس تصبح حمراء.", "labels": ["حمض"]}],
            "questions": [
                {
                    "question_text": "ما تعريف الحمض؟",
                    "question_type": "short_answer",
                    "options": None,
                    "correct_answer": None,
                    "answer_source": "unknown",
                }
            ],
        }

        records = build_page_chunk_records(payload)
        content_types = [record.content_type for record in records]

        self.assertIn("definition", content_types)
        self.assertIn("table", content_types)
        self.assertIn("equation", content_types)
        self.assertIn("diagram", content_types)
        self.assertIn("exercise", content_types)
        self.assertTrue(any("ما تعريف الحمض؟" in record.content for record in records))
        self.assertTrue(any("| الحمض | الصيغة |" in record.content for record in records))

    def test_falls_back_to_merged_content_when_structured_fields_are_empty(self):
        records = build_page_chunk_records(
            {
                "page_number": 2,
                "page_type": "MIXED_VISION",
                "status": "skipped_no_provider",
                "merged_content": "أهداف الدرس: يتعرف المحلول المائي.",
            }
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].content_type, "full_page")
        self.assertEqual(records[0].metadata["page_status"], "skipped_no_provider")
