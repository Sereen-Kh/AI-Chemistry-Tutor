"""Deterministic tests for tutor presentation preferences."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.chat import ChatAskRequest
from app.services.chat_service import _citation_blocks, _media_blocks_for_modes
from app.services.learning_mode_router import resolve_learning_modes
from app.services.preference_mapping import (
    map_legacy_teaching_style,
    preferences_from_user,
)
from app.services.tutor_prompt_builder import build_teaching_instruction


@pytest.mark.parametrize(
    ("legacy", "expected_level", "expected_method"),
    [
        ("Beginner", "simple", "direct"),
        ("Step-By-Step", "standard", "step_by_step"),
        ("Academic", "academic", "direct"),
        ("Real-life style", "standard", "real_life_example"),
    ],
)
def test_legacy_teaching_style_mapping(legacy: str, expected_level: str, expected_method: str) -> None:
    assert map_legacy_teaching_style(legacy) == (expected_level, expected_method)


def test_request_preferences_override_user_defaults() -> None:
    user = SimpleNamespace(
        teaching_style="Academic",
        answer_format="text",
        teaching_level="academic",
        explanation_method="direct",
        learning_modes=["text"],
        student_interests=[],
    )

    preferences = preferences_from_user(
        user,
        teaching_level="simple",
        explanation_method="step_by_step",
        learning_modes=["image"],
        student_interests=["cars"],
    )

    assert preferences.teaching_level == "simple"
    assert preferences.explanation_method == "step_by_step"
    assert preferences.learning_modes == ["text", "image"]
    assert preferences.student_interests == ["cars"]


@pytest.mark.parametrize(
    ("level", "expected_text"),
    [
        ("simple", "مفردات سهلة"),
        ("standard", "مستوى الصف التاسع"),
        ("academic", "صياغة علمية رسمية"),
    ],
)
def test_prompt_builder_teaching_levels(level: str, expected_text: str) -> None:
    instruction = build_teaching_instruction(level, "direct", [])
    assert expected_text in instruction
    assert "لا تغيّر الحقائق العلمية" in instruction
    assert "لم أجد دليلاً كافياً" in instruction


def test_prompt_builder_step_by_step_and_exam_mode_rules() -> None:
    step_instruction = build_teaching_instruction("standard", "step_by_step", [])
    exam_instruction = build_teaching_instruction("academic", "exam_mode", ["football"])

    assert "خطوات مرقمة" in step_instruction
    assert "القانون ثم التعويض ثم النتيجة" in step_instruction
    assert "نمط امتحاني" in exam_instruction
    assert "تجنب التشبيهات" in exam_instruction


def test_prompt_builder_real_life_interests_do_not_replace_science() -> None:
    instruction = build_teaching_instruction("standard", "real_life_example", ["cars", "laboratory"])

    assert "أجب علمياً أولاً" in instruction
    assert "لا تجعل التشبيه بديلاً عن الإجابة العلمية" in instruction
    assert "السيارات" in instruction
    assert "المختبر" in instruction


def test_learning_mode_router_text_always_included() -> None:
    assert resolve_learning_modes(["image"], ["audio"], "اشرح الحموض", 0.9) == ["text", "image"]


def test_learning_mode_router_low_confidence_returns_text_only() -> None:
    assert resolve_learning_modes(["image", "audio"], ["quiz"], "ارسم صورة للتفاعل", 0.2) == ["text"]


@pytest.mark.parametrize(
    ("question", "expected_mode"),
    [
        ("ارسم صورة توضّح التفاعل", "image"),
        ("أريد أن أسمع الشرح بصوت", "audio"),
        ("اعطني فيديو قصير", "video"),
        ("اعطني ريل سريع", "reel"),
        ("اختبرني في الحموض", "quiz"),
        ("اعمل بطاقات مراجعة", "flashcards"),
    ],
)
def test_learning_mode_router_keyword_additions(question: str, expected_mode: str) -> None:
    modes = resolve_learning_modes(None, ["text"], question, 0.9)
    assert "text" in modes
    assert expected_mode in modes


def test_chat_request_accepts_message_alias_and_new_preferences() -> None:
    request = ChatAskRequest(
        message="ما هو الماء؟",
        teaching_level="simple",
        explanation_method="step_by_step",
        learning_modes=["image"],
        student_interests=["cars"],
    )

    assert request.question == "ما هو الماء؟"
    assert request.message == "ما هو الماء؟"
    assert request.teaching_level == "simple"
    assert request.explanation_method == "step_by_step"
    assert request.learning_modes == ["image"]
    assert request.student_interests == ["cars"]


def test_chat_request_rejects_invalid_preference_values() -> None:
    with pytest.raises(ValidationError):
        ChatAskRequest(message="ما هو الماء؟", teaching_level="beginner")
    with pytest.raises(ValidationError):
        ChatAskRequest(message="ما هو الماء؟", learning_modes=["pdf"])


def test_rag_safety_learning_modes_do_not_change_citations() -> None:
    chunk = SimpleNamespace(
        id=17,
        source_id=3,
        source="textbook",
        page_number=11,
        content_type="definition",
        source_type="textbook",
        unit_id="unit_04",
        lesson_id="unit_04_lesson_01",
        quality_status="ready",
        reviewed_metadata_version="2026-06-reviewed-v1",
        curriculum_metadata={
            "source_type": "textbook",
            "unit_id": "unit_04",
            "lesson_id": "unit_04_lesson_01",
            "printed_page_start": 11,
            "printed_page_end": 11,
            "quality_status": "ready",
            "reviewed_metadata_version": "2026-06-reviewed-v1",
        },
        similarity_score=0.87,
    )
    citations = _citation_blocks([chunk])
    diagnostics: dict = {}
    media_blocks = _media_blocks_for_modes(
        learning_modes=["text", "audio", "quiz", "flashcards"],
        blocks=[],
        chunks=[chunk],
        diagnostics=diagnostics,
    )

    assert citations[0]["chunk_id"] == 17
    assert citations[0]["printed_page_start"] == 11
    assert citations[0]["unit_id"] == "unit_04"
    assert citations[0]["lesson_id"] == "unit_04_lesson_01"
    assert citations[0]["quality_status"] == "ready"
    assert citations[0]["reviewed_metadata_version"] == "2026-06-reviewed-v1"
    assert all(block.get("type") != "citation" for block in media_blocks)
    assert diagnostics["audio_requested_but_tts_unavailable"] is True
