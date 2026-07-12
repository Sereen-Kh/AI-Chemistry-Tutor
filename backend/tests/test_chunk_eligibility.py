from __future__ import annotations

from app.services.reviewed_curriculum_metadata import (
    chunk_is_embedding_ready,
    evaluate_chunk_eligibility,
)


def _contract() -> dict:
    return {
        "version": "test-reviewed-v1",
        "ready_for_embedding": True,
        "embedding_contract": {
            "required_chunk_metadata": [
                "lesson_id",
                "unit_id",
                "source_type",
                "printed_page_start",
                "printed_page_end",
                "quality_status",
                "reviewed_metadata_version",
            ],
            "allowed_source_types": ["textbook", "solution_book"],
            "blocked_quality_statuses": ["blocked"],
            "lesson_id_optional_for_content_scopes": ["unit_level", "glossary", "project"],
        },
    }


def _chunk(**overrides) -> dict:
    row = {
        "content": "تعريف كيميائي كامل من الكتاب.",
        "unit_id": "unit_04",
        "lesson_id": "unit_04_lesson_01",
        "source_type": "textbook",
        "printed_page_start": 108,
        "printed_page_end": 108,
        "quality_status": "ready",
        "reviewed_metadata_version": "test-reviewed-v1",
    }
    row.update(overrides)
    return row


def test_ready_chunk_is_eligible_for_embedding_search_and_generation() -> None:
    decision = evaluate_chunk_eligibility(_chunk(), _contract())

    assert decision.normalized_quality_status == "ready"
    assert decision.embedding_allowed is True
    assert decision.rag_search_allowed is True
    assert decision.student_generation_allowed is True
    assert decision.warning_required is False
    assert decision.reason_codes == ["eligible_ready"]


def test_needs_review_chunk_is_searchable_but_not_student_generation() -> None:
    decision = evaluate_chunk_eligibility(_chunk(quality_status="needs_review"), _contract())

    assert decision.normalized_quality_status == "needs_review"
    assert decision.embedding_allowed is True
    assert decision.rag_search_allowed is True
    assert decision.student_generation_allowed is False
    assert decision.warning_required is True
    assert "eligible_needs_review" in decision.reason_codes


def test_blocked_chunk_is_excluded_everywhere() -> None:
    decision = evaluate_chunk_eligibility(_chunk(quality_status="blocked"), _contract())

    assert decision.normalized_quality_status == "blocked"
    assert decision.embedding_allowed is False
    assert decision.rag_search_allowed is False
    assert decision.student_generation_allowed is False
    assert "blocked_quality_status" in decision.reason_codes


def test_legacy_missing_lesson_and_unit_is_downgraded_but_searchable() -> None:
    decision = evaluate_chunk_eligibility(
        _chunk(unit_id=None, lesson_id=None, quality_status="ready"),
        _contract(),
        legacy=True,
    )

    assert decision.normalized_quality_status == "needs_review"
    assert decision.embedding_allowed is True
    assert decision.rag_search_allowed is True
    assert decision.student_generation_allowed is False
    assert decision.warning_required is True
    assert set(decision.missing_fields) >= {"unit_id", "lesson_id"}
    assert "legacy_missing_curriculum_metadata" in decision.reason_codes
    assert decision.normalized_metadata["legacy_unmapped"] is True
    assert decision.normalized_metadata["review_status"] == "legacy_unmapped"


def test_synthetic_legacy_ids_never_make_chunk_ready() -> None:
    decision = evaluate_chunk_eligibility(
        _chunk(
            unit_id="unmapped:textbook:1",
            lesson_id="unmapped:textbook:1:2",
            quality_status="ready",
        ),
        _contract(),
        legacy=True,
    )

    assert decision.normalized_quality_status == "needs_review"
    assert decision.student_generation_allowed is False
    assert decision.normalized_metadata["legacy_unmapped"] is True


def test_fresh_reviewed_chunk_missing_required_metadata_is_rejected() -> None:
    decision = evaluate_chunk_eligibility(_chunk(lesson_id=None), _contract(), legacy=False)

    assert decision.embedding_allowed is False
    assert decision.rag_search_allowed is False
    assert "lesson_id" in decision.missing_fields
    assert "missing_required_metadata" in decision.reason_codes
    assert chunk_is_embedding_ready(_chunk(lesson_id=None), _contract()) == (
        False,
        "missing_reviewed_metadata",
        ["lesson_id"],
    )


def test_unit_level_content_can_omit_lesson_with_real_unit() -> None:
    decision = evaluate_chunk_eligibility(
        _chunk(lesson_id=None, content_scope="unit_level"),
        _contract(),
    )

    assert decision.embedding_allowed is True
    assert decision.student_generation_allowed is True
    assert "lesson_id" not in decision.missing_fields


def test_invalid_source_type_and_empty_content_are_rejected() -> None:
    invalid_source = evaluate_chunk_eligibility(_chunk(source_type="notes"), _contract())
    empty_content = evaluate_chunk_eligibility(_chunk(content="  "), _contract())

    assert invalid_source.embedding_allowed is False
    assert "invalid_source_type" in invalid_source.reason_codes
    assert empty_content.embedding_allowed is False
    assert "empty_content" in empty_content.reason_codes

