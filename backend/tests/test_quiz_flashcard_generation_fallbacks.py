from app.models.chemistry import Lesson
from app.models.textbook import ExtractedQuestion
from app.services.flashcard_service import _build_card_payload, _is_generic_back
from app.services.quiz_service import _canonical_question_types, _template_question_payloads, _valid_question


def _lesson() -> Lesson:
    return Lesson(
        id=5,
        chapter_id=1,
        title_ar="المحاليل المائية",
        content_ar="المحاليل المائية تتكون من مذيب ومذاب ويمكن قياس تركيزها بطرق مختلفة.",
        order=1,
        difficulty=2,
        duration_min=30,
        page_start=108,
        page_end=115,
    )


def test_template_quiz_fallback_questions_are_valid():
    lesson = _lesson()
    question_types = _canonical_question_types(["mcq", "true_false", "fill_blank"])
    payloads = _template_question_payloads(
        lesson=lesson,
        topic=None,
        difficulty=3,
        question_types=question_types,
        count=3,
    )

    assert len(payloads) == 3
    questions = [
        ExtractedQuestion(
            id=index + 1,
            source_id=1,
            lesson_id=lesson.id,
            question_text=payload["question_text"],
            question_type=payload["question_type"],
            options=payload["options"],
            correct_answer=payload["correct_answer"],
            explanation=payload["explanation"],
            difficulty=payload["difficulty"],
        )
        for index, payload in enumerate(payloads)
    ]

    assert all(_valid_question(question, question_types) for question in questions)


def test_quiz_validation_rejects_mcq_without_correct_option():
    question = ExtractedQuestion(
        id=1,
        source_id=1,
        lesson_id=5,
        question_text="ما الإجابة الصحيحة؟",
        question_type="multiple_choice",
        options=["أ", "ب", "ج", "د"],
        correct_answer="هـ",
        explanation="يجب أن تكون الإجابة الصحيحة ضمن الخيارات.",
        difficulty=3,
    )

    assert not _valid_question(question, {"multiple_choice"})


def test_flashcard_fallback_has_hint_and_non_generic_answer():
    payload = _build_card_payload(
        lesson=_lesson(),
        topic=None,
        chunk=None,
        card_type="term_definition",
        difficulty="medium",
        created_by="generated",
    )

    assert payload["hint_ar"]
    assert payload["back_ar"]
    assert payload["explanation_ar"]
    assert not _is_generic_back(payload["back_ar"])
