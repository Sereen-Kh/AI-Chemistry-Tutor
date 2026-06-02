"""Focused tests for Arabic RAG ranking and local source fallback."""

from __future__ import annotations

from unittest import TestCase

from app.services.chat_service import _local_rag_answer
from app.services.rag import RetrievedChunk, _hybrid_score, lexical_relevance_score


def chunk(chunk_id: int, page_number: int, content: str, score: float = 0.8) -> RetrievedChunk:
    return RetrievedChunk(
        id=chunk_id,
        source_id=1,
        content=content,
        source="كتاب الكيمياء",
        source_type="textbook",
        content_type="text",
        page_number=page_number,
        chapter_id=None,
        lesson_id=None,
        topic_id=None,
        metadata_json=None,
        similarity_score=score,
    )


class ArabicRagRankingTests(TestCase):
    def test_acid_query_prefers_matching_textbook_chunk_over_weak_vector_score(self):
        query = "اشرح لي ما هي الحموض من الكتاب؟"
        acid_content = """
        :الحموض
        في صيغتها الأيونية H+ تحتوي الحموض على أيون الهدروجين.
        الحموض: موادّ تُعطي عند انحلالها في الماء أيَّونات الهدروجين.
        """
        unrelated_content = """
        أنواع الروابط المشتركة بين ذرات الكربون:
        رابطة مشتركة أحادية ورابطة مشتركة ثنائية ورابطة مشتركة ثلاثية.
        """

        self.assertGreater(lexical_relevance_score(query, acid_content), 0.7)
        self.assertEqual(lexical_relevance_score(query, unrelated_content), 0.0)
        self.assertGreater(
            _hybrid_score(query, acid_content, vector_score=0.12),
            _hybrid_score(query, unrelated_content, vector_score=0.6),
        )

    def test_local_fallback_extracts_answer_lines_instead_of_dumping_unrelated_chunks(self):
        answer = _local_rag_answer(
            "اشرح لي ما هي الحموض من الكتاب؟",
            [
                chunk(
                    13,
                    11,
                    """
                    :الحموض
                    في صيغتها الأيونية H+ تحتوي الحموض على أيون الهدروجين.
                    عدد الوظائف الحمضيَّة: هو عدد أيونات الهدروجين في الصّيغة الأيونية للحمض.
                    الحموض: موادّ تُعطي عند انحلالها في الماء أيَّونات الهدروجين.
                    """,
                ),
                chunk(
                    16,
                    13,
                    """
                    تتأيَّن الحموض القويَّة تأيّناً كلّيّاً في الماء.
                    تتأيَّن الحموض الضَّعيفة تأيّناً جزئيَّاً في الماء.
                    تلوّن المحاليل الحمضيَّة ورقة عباد الشَّمس باللَّون الأحمر.
                    """,
                ),
                chunk(
                    77,
                    77,
                    "صيغة الإيتن هي C2H4، والصيغة العامة للألكنات هي CnH2n.",
                    score=0.1,
                ),
            ],
            reason="تعذر استخدام Gemini حالياً، لذلك أعرض لك إجابة محلية من مصادر الكتاب.",
        )

        self.assertIn("من الكتاب", answer)
        self.assertIn("الحموض هي مواد", answer)
        self.assertIn("الحموض القوية تتأين كلياً", answer)
        self.assertIn("صفحة 11", answer)
        self.assertIn("13", answer)
        self.assertNotIn("صيغة الإيتن", answer)
