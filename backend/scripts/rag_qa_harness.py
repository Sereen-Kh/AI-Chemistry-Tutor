"""Deterministic QA harness for Grade 9 RAG API tests.

The helpers in this module intentionally avoid PostgreSQL, Redis, and Gemini.
They install FastAPI dependency overrides and fake service functions that return
stable source chunks derived from the JSON QA fixture.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

from app.rag.arabic_normalizer import normalize_arabic
from app.services.rag import RetrievedChunk

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATASET_PATH = BACKEND_DIR / "tests" / "fixtures" / "rag_grade9_qa_cases.json"
REPORT_PATH = BACKEND_DIR / "reports" / "rag_qa_report.json"
REVIEWED_METADATA_VERSION = "2026-06-reviewed-v1"

_CATEGORY_CURRICULUM = {
    "solutions": ("unit_04", "unit_04_lesson_01", 110),
    "acids": ("unit_04", "unit_04_lesson_02", 117),
    "bases": ("unit_04", "unit_04_lesson_03", 124),
    "salts": ("unit_04", "unit_04_lesson_03", 128),
    "reactions": ("unit_04", "unit_04_lesson_04", 134),
    "redox": ("unit_04", "unit_04_lesson_04", 141),
    "formulas": ("unit_04", "unit_04_lesson_05", 148),
    "organic": ("unit_05", "unit_05_lesson_01", 165),
    "radioactivity": ("unit_06", "unit_06_lesson_01", 192),
    "exercises": ("unit_05", "unit_05_lesson_03", 183),
}

REQUIRED_CASE_FIELDS = {
    "id",
    "category",
    "question",
    "expected_answer_keywords",
    "forbidden_keywords",
    "expected_source_topics",
    "min_confidence",
    "expected_behavior",
    "endpoint_targets",
}


def normalize_for_assertion(text: str | None) -> str:
    normalized = normalize_arabic(text or "").lower()
    replacements = {
        "الهيدروجين": "الهدروجين",
        "هيدروجين": "هدروجين",
        "احماض": "حموض",
        "الاحماض": "الحموض",
        "قويه": "قوي",
        "قوية": "قوي",
        "التركيز": "التركز",
        "تركيز": "تركز",
        "غير كافي": "غير كاف",
    }
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    return " ".join(normalized.split()).strip()


def contains_term(text: str, term: str) -> bool:
    return normalize_for_assertion(term) in normalize_for_assertion(text)


def missing_terms(text: str, terms: list[str]) -> list[str]:
    return [term for term in terms if not contains_term(text, term)]


def present_terms(text: str, terms: list[str]) -> list[str]:
    return [term for term in terms if contains_term(text, term)]


def load_cases(path: Path = DATASET_PATH) -> list[dict[str, Any]]:
    cases = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(cases, list):
        raise ValueError(f"RAG QA fixture must be a JSON list: {path}")
    if len(cases) < 50:
        raise ValueError(f"RAG QA fixture must contain at least 50 cases, found {len(cases)}")

    seen_ids: set[str] = set()
    for index, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            raise ValueError(f"Case #{index} must be an object")
        missing = REQUIRED_CASE_FIELDS - set(case)
        if missing:
            raise ValueError(f"Case {case.get('id', index)} is missing fields: {sorted(missing)}")
        if case["id"] in seen_ids:
            raise ValueError(f"Duplicate case id: {case['id']}")
        seen_ids.add(case["id"])
        if case["expected_behavior"] not in {"answerable", "out_of_scope"}:
            raise ValueError(f"Unsupported expected_behavior for {case['id']}: {case['expected_behavior']}")
        if not isinstance(case["endpoint_targets"], list) or not case["endpoint_targets"]:
            raise ValueError(f"Case {case['id']} must target at least one endpoint")
    return cases


def _stable_int(value: str, *, modulo: int = 1_000_000) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % modulo


def case_page_number(case: dict[str, Any]) -> int:
    explicit_pages = case.get("expected_printed_pages")
    if isinstance(explicit_pages, list) and explicit_pages:
        return int(explicit_pages[0])
    return _CATEGORY_CURRICULUM.get(case["category"], ("unit_04", "unit_04_lesson_01", 108))[2]


def case_chunk_id(case: dict[str, Any]) -> int:
    source_case_id = str(case.get("source_case_id") or case["id"])
    return 10_000 + _stable_int(source_case_id, modulo=900_000)


def is_answerable(case: dict[str, Any]) -> bool:
    return case["expected_behavior"] == "answerable"


def source_text_for_case(case: dict[str, Any]) -> str:
    if not is_answerable(case):
        return ""
    parts = [
        f"سؤال: {case['question']}",
        "موضوعات المصدر: " + "، ".join(case["expected_source_topics"]),
        "إجابة الكتاب: " + "، ".join(case["expected_answer_keywords"]),
    ]
    return "\n".join(part for part in parts if part.strip())


def answer_text_for_case(case: dict[str, Any]) -> str:
    if not is_answerable(case):
        return "لم أجد معلومات كافية في مقاطع الكتاب المتاحة، لذلك لا أستطيع تقديم إجابة منسوبة إلى الكتاب."
    page = case_page_number(case)
    return "إجابة من الكتاب: " + "، ".join(case["expected_answer_keywords"]) + f". (صفحة {page})"


def chunk_for_case(case: dict[str, Any]) -> RetrievedChunk:
    score = max(float(case["min_confidence"]), 0.82)
    fallback_unit_id, fallback_lesson_id, fallback_page = _CATEGORY_CURRICULUM.get(
        case["category"], ("unit_04", "unit_04_lesson_01", 108)
    )
    unit_id = case.get("expected_unit_id") or fallback_unit_id
    lesson_id = case.get("expected_lesson_id") or fallback_lesson_id
    printed_page = case_page_number(case) if case.get("expected_printed_pages") else fallback_page
    quality_status = str(
        case.get("expected_quality_status")
        or ("needs_review" if case["category"] == "exercises" else "ready")
    )
    source_type = str(
        case.get("expected_source_type")
        or ("solution_book" if case["category"] == "exercises" else "textbook")
    )
    curriculum_metadata = {
        "source_type": source_type,
        "unit_id": unit_id,
        "lesson_id": lesson_id,
        "printed_page_start": printed_page,
        "printed_page_end": printed_page,
        "quality_status": quality_status,
        "reviewed_metadata_version": REVIEWED_METADATA_VERSION,
        "stale": False,
    }
    return RetrievedChunk(
        id=case_chunk_id(case),
        source_id=9000 + _stable_int(case["category"], modulo=900),
        content=source_text_for_case(case),
        source="EduMind Grade 9 Chemistry QA Fixture",
        source_type=source_type,
        content_type="definition" if case["category"] in {"acids", "bases", "salts"} else "text",
        page_number=printed_page,
        unit_id=unit_id,
        chapter_id=None,
        lesson_id=lesson_id,
        topic_id=None,
        metadata_json={
            "qa_case_id": case["id"],
            "topics": case["expected_source_topics"],
            **curriculum_metadata,
        },
        quality_status=quality_status,
        quality_warning="This source is marked needs_review." if quality_status == "needs_review" else None,
        reviewed_metadata_version=REVIEWED_METADATA_VERSION,
        curriculum_metadata=curriculum_metadata,
        similarity_score=round(score, 4),
    )


def chunk_dict_for_case(case: dict[str, Any]) -> dict[str, Any]:
    chunk = chunk_for_case(case)
    return {
        "chunk_id": chunk.id,
        "source_id": chunk.source_id,
        "source_type": chunk.source_type,
        "page_number": chunk.page_number,
        "printed_page_start": chunk.curriculum_metadata["printed_page_start"],
        "printed_page_end": chunk.curriculum_metadata["printed_page_end"],
        "unit_id": chunk.unit_id,
        "lesson_id": chunk.lesson_id,
        "content_type": chunk.content_type,
        "similarity_score": chunk.similarity_score,
        "quality_status": chunk.quality_status,
        "quality_warning": chunk.quality_warning,
        "reviewed_metadata_version": chunk.reviewed_metadata_version,
        "preview": chunk.content[:180],
    }


def chunk_previews(chunks: list[dict[str, Any]] | list[RetrievedChunk] | None) -> list[dict[str, Any]]:
    previews = []
    for item in chunks or []:
        if isinstance(item, dict):
            previews.append(
                {
                    "chunk_id": item.get("id") or item.get("chunk_id"),
                    "source_id": item.get("source_id"),
                    "source_type": item.get("source_type"),
                    "page_number": item.get("page_number"),
                    "unit_id": item.get("unit_id"),
                    "lesson_id": item.get("lesson_id"),
                    "quality_status": item.get("quality_status"),
                    "quality_warning": item.get("quality_warning"),
                    "reviewed_metadata_version": item.get("reviewed_metadata_version"),
                    "similarity_score": item.get("similarity_score"),
                    "content": str(item.get("content") or item.get("preview") or "")[:180],
                }
            )
        else:
            previews.append(
                {
                    "chunk_id": item.id,
                    "source_id": item.source_id,
                    "source_type": item.source_type,
                    "page_number": item.page_number,
                    "unit_id": item.unit_id,
                    "lesson_id": item.lesson_id,
                    "quality_status": item.quality_status,
                    "quality_warning": item.quality_warning,
                    "reviewed_metadata_version": item.reviewed_metadata_version,
                    "similarity_score": item.similarity_score,
                    "content": item.content[:180],
                }
            )
    return previews


def find_case_by_question(cases: list[dict[str, Any]], question: str) -> dict[str, Any] | None:
    normalized_query = normalize_for_assertion(question)
    for case in cases:
        if normalize_for_assertion(case["question"]) == normalized_query:
            return case
    for case in cases:
        normalized_case = normalize_for_assertion(case["question"])
        if normalized_case and (normalized_case in normalized_query or normalized_query in normalized_case):
            return case
    return None


async def _fake_db_dependency():
    yield SimpleNamespace(bind=None)


def install_deterministic_api_overrides(app, cases: list[dict[str, Any]], monkeypatch=None) -> Callable[[], None]:
    """Patch API route dependencies/services for deterministic QA execution."""
    from app.api import homework as homework_routes
    from app.api.chat import routes as chat_routes
    from app.api.rag import routes as rag_routes
    from app.core.dependencies import get_current_user_id
    from app.database import get_async_db

    async def fake_retrieve_context(
        db,
        query: str,
        user_id: int | None = None,
        unit_id: int | None = None,
        chapter_id: int | None = None,
        lesson_id: int | None = None,
        topic_id: int | None = None,
        source_types: list[str] | None = None,
        content_types: list[str] | None = None,
        top_k: int = 6,
        min_similarity: float = 0.0,
        intent: str = "general",
        diagnostics_callback=None,
    ) -> list[RetrievedChunk]:
        case = find_case_by_question(cases, query)
        if not case or not is_answerable(case):
            if diagnostics_callback:
                diagnostics_callback(
                    {
                        "normalized_query": normalize_for_assertion(query),
                        "final_confidence": 0.0,
                        "hallucination_guard": True,
                        "final_top_k": [],
                    }
                )
            return []
        chunk = chunk_for_case(case)
        chunks = [chunk] if chunk.similarity_score >= min_similarity else []
        if diagnostics_callback:
            diagnostics_callback(
                {
                    "normalized_query": normalize_for_assertion(query),
                    "final_confidence": chunk.similarity_score if chunks else 0.0,
                    "matched_terms": case["expected_answer_keywords"],
                    "final_top_k": chunk_previews(chunks),
                }
            )
        return chunks[:top_k]

    async def fake_ask_question(
        db,
        user_id: int,
        question: str,
        lesson_id: int | None = None,
        topic_id: int | None = None,
        source_types: list[str] | None = None,
        preferred_answer_type: str = "text",
        answer_scope: str = "auto",
        **kwargs,
    ) -> dict[str, Any]:
        case = find_case_by_question(cases, question)
        if not case or not is_answerable(case):
            answer = answer_text_for_case(case or {"expected_behavior": "out_of_scope"})
            return {
                "answer": answer,
                "answer_type": "not_found",
                "route": "not_found",
                "grounding": "book",
                "answer_scope": answer_scope,
                "blocks": [{"type": "text", "content": answer}],
                "sources": [],
                "source_blocks": [],
                "page_numbers": [],
                "confidence": 0.08,
                "diagnostics": {"hallucination_guard": True, "normalized_query": normalize_for_assertion(question)},
                "suggested_next_action": "اسأل عن مفهوم موجود في كتاب الكيمياء.",
            }

        chunk = chunk_for_case(case)
        answer = answer_text_for_case(case)
        return {
            "answer": answer,
            "answer_type": preferred_answer_type if preferred_answer_type != "auto" else "text",
            "route": "textbook_rag",
            "grounding": "book",
            "answer_scope": answer_scope,
            "blocks": [{"type": "text", "content": answer}],
            "sources": [chunk],
            "source_blocks": [
                {
                    "book_id": "qa_fixture",
                    "page": chunk.page_number,
                    "chunk_id": chunk.id,
                    "source_id": chunk.source_id,
                    "chunk_type": chunk.content_type,
                    "source_type": chunk.source_type,
                    "unit_id": chunk.unit_id,
                    "lesson_id": chunk.lesson_id,
                    "quality_status": chunk.quality_status,
                    "quality_warning": chunk.quality_warning,
                    "reviewed_metadata_version": chunk.reviewed_metadata_version,
                    "curriculum_metadata": chunk.curriculum_metadata,
                    "score": chunk.similarity_score,
                }
            ],
            "page_numbers": [chunk.page_number],
            "confidence": chunk.similarity_score,
            "diagnostics": {
                "normalized_query": normalize_for_assertion(question),
                "matched_terms": case["expected_answer_keywords"],
                "qa_case_id": case["id"],
            },
            "suggested_next_action": "راجع المصدر ثم جرّب سؤالاً تدريبياً.",
        }

    async def fake_solve_text(db, user_id: int, problem_text: str, topic_id: int | None = None):
        case = find_case_by_question(cases, problem_text)
        now = datetime.now(timezone.utc)
        if not case or not is_answerable(case):
            return SimpleNamespace(
                id=1,
                user_id=user_id,
                topic_id=topic_id,
                image_url=None,
                problem_text=problem_text,
                extracted_text=None,
                solution=answer_text_for_case(case or {"expected_behavior": "out_of_scope"}),
                source_chunks=[],
                confidence_score=0.08,
                created_at=now,
                updated_at=now,
            )
        chunk_payload = chunk_dict_for_case(case)
        return SimpleNamespace(
            id=case_chunk_id(case),
            user_id=user_id,
            topic_id=topic_id,
            image_url=None,
            problem_text=problem_text,
            extracted_text=None,
            solution=answer_text_for_case(case),
            source_chunks=[chunk_payload],
            confidence_score=chunk_payload["similarity_score"],
            created_at=now,
            updated_at=now,
        )

    def _setattr(target, name: str, value):
        if monkeypatch is not None:
            monkeypatch.setattr(target, name, value)
        else:
            setattr(target, name, value)

    originals = {
        "rag_retrieve_context": rag_routes.retrieve_context,
        "chat_ask_question": chat_routes.chat_service.ask_question,
        "homework_solve_text": homework_routes.homework_service.solve_text,
        "dependency_overrides": dict(app.dependency_overrides),
    }

    _setattr(rag_routes, "retrieve_context", fake_retrieve_context)
    _setattr(chat_routes.chat_service, "ask_question", fake_ask_question)
    _setattr(homework_routes.homework_service, "solve_text", fake_solve_text)
    app.dependency_overrides[get_current_user_id] = lambda: 101
    app.dependency_overrides[get_async_db] = _fake_db_dependency

    def cleanup() -> None:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(originals["dependency_overrides"])
        if monkeypatch is None:
            rag_routes.retrieve_context = originals["rag_retrieve_context"]
            chat_routes.chat_service.ask_question = originals["chat_ask_question"]
            homework_routes.homework_service.solve_text = originals["homework_solve_text"]

    return cleanup


def route_exists(app, path: str, method: str) -> bool:
    wanted = method.upper()
    for route in app.routes:
        if getattr(route, "path", None) == path and wanted in (getattr(route, "methods", None) or set()):
            return True
    return False
