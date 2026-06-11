"""Resolve requested learning/output modes for a grounded tutor response."""

from __future__ import annotations

from app.models.enums import LearningMode
from app.services.preference_mapping import normalize_learning_modes
from app.services.ocr.normalization import normalize_text

_IMAGE_TERMS = ("صورة", "رسم", "شكل", "diagram", "image")
_AUDIO_TERMS = ("صوت", "اسمع", "audio", "voice")
_VIDEO_TERMS = ("فيديو", "video")
_REEL_TERMS = ("ريل", "reel")
_QUIZ_TERMS = ("اختبرني", "اختبار", "تدرب", "تدريب", "practice", "quiz", "test")
_FLASHCARD_TERMS = ("بطاقات", "فلاش", "مراجعة", "راجع", "revision", "flashcard", "flashcards")


def _contains_any(question: str, terms: tuple[str, ...]) -> bool:
    normalized = normalize_text(question).lower()
    return any(term in normalized or term in question.lower() for term in terms)


def resolve_learning_modes(
    requested_modes: list[str] | None,
    user_default_modes: list[str],
    question: str,
    confidence: float,
) -> list[str]:
    """Resolve learning modes from request/profile/question while preserving safety.

    Text is always included. When confidence is too low, only text is returned
    because media generation should not amplify weak retrieval.
    """
    if confidence < 0.45:
        return [LearningMode.TEXT.value]

    modes = normalize_learning_modes(requested_modes if requested_modes is not None else user_default_modes)

    if _contains_any(question, _IMAGE_TERMS):
        modes = normalize_learning_modes([*modes, LearningMode.IMAGE.value])
    if _contains_any(question, _AUDIO_TERMS):
        modes = normalize_learning_modes([*modes, LearningMode.AUDIO.value])
    if _contains_any(question, _VIDEO_TERMS):
        modes = normalize_learning_modes([*modes, LearningMode.VIDEO.value])
    if _contains_any(question, _REEL_TERMS):
        modes = normalize_learning_modes([*modes, LearningMode.REEL.value])
    if _contains_any(question, _QUIZ_TERMS):
        modes = normalize_learning_modes([*modes, LearningMode.QUIZ.value])
    if _contains_any(question, _FLASHCARD_TERMS):
        modes = normalize_learning_modes([*modes, LearningMode.FLASHCARDS.value])

    return modes
