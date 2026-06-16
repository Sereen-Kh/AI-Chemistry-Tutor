"""Guided chemistry problem-solving service.

MVP scope: Grade 9 concentration calculations. Numeric correctness is
deterministic; RAG is used for grounding/source references.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.interactive_solver import (
    InteractiveSession,
    InteractiveStep,
    MisconceptionEvent,
    SkillMastery,
    StudentStepAnswer,
)
from app.models.user import User
from app.schemas.interactive_solver import (
    InteractiveAnswerResponse,
    InteractiveAnswerSubmit,
    InteractiveSessionCreate,
    InteractiveSessionResponse,
    InteractiveSessionSummaryResponse,
    InteractiveSourceReference,
    InteractiveStepResponse,
)
from app.services.semantic_rag import semantic_retrieve_context

_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_SUBSCRIPT_DIGITS = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
_DIACRITICS_RE = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
_NUMBER_RE = re.compile(r"[-+]?\d+(?:[.,]\d+)?")


@dataclass(frozen=True)
class ParsedProblem:
    """Values extracted from a concentration problem."""

    problem_type: str
    solute_formula: str | None = None
    mass_g: float | None = None
    volume_ml: float | None = None
    volume_l: float | None = None
    molar_mass_g_mol: float | None = None
    dilution: dict[str, float] | None = None


@dataclass(frozen=True)
class ValidationResult:
    """Deterministic validation output for one step answer."""

    is_correct: bool
    feedback_ar: str
    parsed_value: float | None = None
    parsed_unit: str | None = None
    misconception_type: str | None = None


def normalize_solver_text(text: str) -> str:
    """Normalize Arabic/English chemistry text for deterministic matching."""
    normalized = (text or "").strip().lower().translate(_ARABIC_DIGITS).translate(_SUBSCRIPT_DIGITS)
    normalized = _DIACRITICS_RE.sub("", normalized)
    normalized = normalized.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي").replace("ة", "ه")
    normalized = normalized.replace("×", "*").replace("÷", "/").replace("−", "-")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def classify_problem_type(problem_text: str) -> str:
    """Classify the supported MVP problem type."""
    normalized = normalize_solver_text(problem_text)
    concentration_terms = (
        "التركيز الغرامي",
        "التركيز المولي",
        "التركز الغرامي",
        "التركز المولي",
        "cg",
        "cm",
        "c=",
        "m/v",
    )
    dilution_terms = ("تمديد", "ممدد", "اضيف ماء", "ماء مقطر", "c1", "v1", "c2", "v2")
    if any(term in normalized for term in concentration_terms) or (
        "محلول" in normalized and any(unit in normalized for unit in ("ml", "g", "غ", "مول", "لتر"))
    ):
        return "concentration_calculation"
    if any(term in normalized for term in dilution_terms):
        return "concentration_calculation"
    raise HTTPException(
        status_code=422,
        detail="يدعم المختبر التفاعلي حالياً مسائل التركيز فقط: التركيز الغرامي، التركيز المولي، أو التمديد.",
    )


def _extract_formula(text: str) -> str | None:
    normalized = normalize_solver_text(text)
    if "hcl" in normalized or "حمض كلور الماء" in normalized:
        return "HCl"
    if "naoh" in normalized:
        return "NaOH"
    match = re.search(r"\b([A-Z][a-z]?[0-9]?(?:[A-Z][a-z]?[0-9]?)+)\b", text.translate(_SUBSCRIPT_DIGITS))
    return match.group(1) if match else None


def _numbers_with_context(text: str) -> list[tuple[float, str]]:
    normalized = normalize_solver_text(text)
    items: list[tuple[float, str]] = []
    for match in _NUMBER_RE.finditer(normalized):
        raw = match.group(0).replace(",", ".")
        try:
            value = float(raw)
        except ValueError:
            continue
        context = normalized[match.end() : match.end() + 20]
        items.append((value, context))
    return items


def _molar_mass(formula: str | None) -> float | None:
    masses = {
        "HCl": 36.5,
        "NaOH": 40.0,
        "H2O": 18.0,
        "H2SO4": 98.0,
    }
    return masses.get(formula or "")


def _parse_problem(problem_text: str) -> ParsedProblem:
    formula = _extract_formula(problem_text)
    mass_g: float | None = None
    volume_ml: float | None = None
    volume_l: float | None = None
    for value, context in _numbers_with_context(problem_text):
        if any(unit in context for unit in ("ml", "مل", "ملل")):
            volume_ml = value
            volume_l = value / 1000.0
        elif re.search(r"\b(l|لتر)\b", context):
            volume_l = value
            volume_ml = value * 1000.0
        elif any(unit in context for unit in ("g", "غ", "غرام")):
            mass_g = value
    return ParsedProblem(
        problem_type=classify_problem_type(problem_text),
        solute_formula=formula,
        mass_g=mass_g,
        volume_ml=volume_ml,
        volume_l=volume_l,
        molar_mass_g_mol=_molar_mass(formula),
    )


async def retrieve_problem_context(
    db: AsyncSession,
    *,
    problem_text: str,
    user_id: int,
    source_types: list[str] | None,
    topic_id: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Retrieve source chunks without making session creation depend on RAG availability."""
    try:
        result = await semantic_retrieve_context(
            db,
            problem_text,
            user_id=user_id,
            source_types=source_types or ["textbook", "solution_book"],
            topic_id=topic_id,
            top_k=5,
            intent="exercise_solving",
        )
    except Exception as exc:  # pragma: no cover - depends on DB/API config
        return [], {"rag_warning": str(exc)}

    sources = [
        {
            "chunk_id": chunk.id,
            "page_number": chunk.page_number,
            "source_type": chunk.source_type,
            "content_type": chunk.content_type,
            "preview": " ".join(chunk.content.split())[:220],
            "similarity_score": chunk.similarity_score,
        }
        for chunk in result.chunks
    ]
    return sources, {"rag_diagnostics": result.diagnostics}


def _concentration_step_records(parsed: ParsedProblem) -> list[dict[str, Any]]:
    mass = parsed.mass_g if parsed.mass_g is not None else 3.65
    volume_ml = parsed.volume_ml if parsed.volume_ml is not None else 100.0
    volume_l = parsed.volume_l if parsed.volume_l is not None else volume_ml / 1000.0
    molar_mass = parsed.molar_mass_g_mol if parsed.molar_mass_g_mol is not None else 36.5
    moles = mass / molar_mass
    gram_concentration = mass / volume_l
    molar_concentration = moles / volume_l
    formula = parsed.solute_formula or "HCl"

    return [
        {
            "step_key": "identify_gram_concentration_formula",
            "title_ar": "اختيار قانون التركيز الغرامي",
            "prompt_ar": "ما القانون المناسب لحساب التركيز الغرامي Cg؟",
            "expected_answer_type": "formula",
            "expected_formula": "Cg=m/V",
            "expected_unit": None,
            "hint_ar": "نحتاج العلاقة بين كتلة المذاب وحجم المحلول.",
            "explanation_ar": "التركيز الغرامي يساوي كتلة المذاب مقسومة على حجم المحلول.",
            "metadata_json": {"formula_aliases": ["cg=m/v", "c=m/v", "التركيز=الكتله/الحجم", "التركيز=الكتلة/الحجم"]},
        },
        {
            "step_key": "convert_volume_ml_to_l",
            "title_ar": "تحويل الحجم إلى اللتر",
            "prompt_ar": f"حوّل حجم المحلول من {volume_ml:g} mL إلى L.",
            "expected_answer_type": "numeric",
            "expected_numeric": volume_l,
            "expected_unit": "L",
            "hint_ar": "كل 1000 mL تساوي 1 L.",
            "explanation_ar": f"{volume_ml:g} mL = {volume_ml:g} / 1000 = {volume_l:g} L.",
            "metadata_json": {"skill_key": "ml_to_l_conversion", "original_ml": volume_ml},
        },
        {
            "step_key": "calculate_gram_concentration",
            "title_ar": "حساب التركيز الغرامي",
            "prompt_ar": "احسب التركيز الغرامي Cg بوحدة g/L.",
            "expected_answer_type": "numeric",
            "expected_numeric": gram_concentration,
            "expected_unit": "g/L",
            "hint_ar": f"عوّض: Cg = {mass:g} / {volume_l:g}.",
            "explanation_ar": f"Cg = m / V = {mass:g} / {volume_l:g} = {gram_concentration:g} g/L.",
            "metadata_json": {"skill_key": "gram_concentration", "mass_g": mass, "volume_l": volume_l},
        },
        {
            "step_key": "calculate_molar_mass",
            "title_ar": "حساب الكتلة المولية",
            "prompt_ar": f"ما الكتلة المولية للمركب {formula}؟",
            "expected_answer_type": "numeric",
            "expected_numeric": molar_mass,
            "expected_unit": "g/mol",
            "hint_ar": "اجمع الكتل الذرية للعناصر في الصيغة.",
            "explanation_ar": f"بالنسبة إلى {formula}: الكتلة المولية = {molar_mass:g} g/mol.",
            "metadata_json": {"skill_key": "molar_mass", "formula": formula},
        },
        {
            "step_key": "calculate_moles",
            "title_ar": "حساب عدد المولات",
            "prompt_ar": "احسب عدد مولات المذاب n.",
            "expected_answer_type": "numeric",
            "expected_numeric": moles,
            "expected_unit": "mol",
            "hint_ar": "استخدم العلاقة: n = m / M.",
            "explanation_ar": f"n = m / M = {mass:g} / {molar_mass:g} = {moles:g} mol.",
            "metadata_json": {"skill_key": "moles_from_mass", "mass_g": mass, "molar_mass": molar_mass},
        },
        {
            "step_key": "calculate_molar_concentration",
            "title_ar": "حساب التركيز المولي",
            "prompt_ar": "احسب التركيز المولي C بوحدة mol/L.",
            "expected_answer_type": "numeric",
            "expected_numeric": molar_concentration,
            "expected_unit": "mol/L",
            "hint_ar": "استخدم العلاقة: C = n / V.",
            "explanation_ar": f"C = n / V = {moles:g} / {volume_l:g} = {molar_concentration:g} mol/L.",
            "metadata_json": {"skill_key": "molar_concentration", "moles": moles, "volume_l": volume_l},
        },
        {
            "step_key": "final_answer",
            "title_ar": "كتابة الجواب النهائي",
            "prompt_ar": "اكتب الجواب النهائي متضمناً التركيز الغرامي والتركيز المولي مع الوحدات.",
            "expected_answer_type": "final",
            "expected_formula": None,
            "expected_numeric": None,
            "expected_unit": None,
            "hint_ar": "اذكر قيمتي Cg و C مع الوحدات.",
            "explanation_ar": f"الجواب النهائي: Cg = {gram_concentration:g} g/L، و C = {molar_concentration:g} mol/L.",
            "metadata_json": {
                "skill_key": "final_answer_units",
                "gram_concentration": gram_concentration,
                "molar_concentration": molar_concentration,
                "accepted_keywords": [f"{gram_concentration:g}", f"{molar_concentration:g}", "g/l", "mol/l"],
            },
        },
    ]


def build_concentration_solution_plan(problem_text: str) -> dict[str, Any]:
    """Build the deterministic concentration calculation plan."""
    parsed = _parse_problem(problem_text)
    steps = _concentration_step_records(parsed)
    final = steps[-1]["explanation_ar"].replace("الجواب النهائي: ", "")
    return {
        "problem_type": parsed.problem_type,
        "parsed": {
            "solute_formula": parsed.solute_formula,
            "mass_g": parsed.mass_g,
            "volume_ml": parsed.volume_ml,
            "volume_l": parsed.volume_l,
            "molar_mass_g_mol": parsed.molar_mass_g_mol,
        },
        "steps": steps,
        "final_answer": final,
    }


def create_interactive_steps(session: InteractiveSession, plan: dict[str, Any]) -> list[InteractiveStep]:
    """Create ORM step objects for a session from a deterministic plan."""
    steps: list[InteractiveStep] = []
    for index, item in enumerate(plan["steps"]):
        steps.append(
            InteractiveStep(
                session=session,
                step_index=index,
                status="current" if index == 0 else "pending",
                tolerance=0.02,
                **item,
            )
        )
    return steps


def _source_refs(raw: list | dict | None) -> list[InteractiveSourceReference]:
    items = raw if isinstance(raw, list) else []
    return [InteractiveSourceReference(**item) for item in items if isinstance(item, dict)]


def _step_response(step: InteractiveStep | None) -> InteractiveStepResponse | None:
    return InteractiveStepResponse.model_validate(step) if step else None


def _current_step(session: InteractiveSession) -> InteractiveStep | None:
    for step in session.steps:
        if step.status == "current":
            return step
    return next((step for step in session.steps if step.status == "pending"), None)


def _weak_topics(session: InteractiveSession) -> list[str]:
    values = session.weak_topics if isinstance(session.weak_topics, list) else []
    return [str(item) for item in values]


def _suggested_actions(session_id: int) -> dict[str, Any]:
    return {
        "mini_quiz": {"action": "generate_quiz", "session_id": session_id, "topic": "concentration_calculation"},
        "flashcards": {"action": "generate_flashcards", "session_id": session_id, "topic": "concentration_calculation"},
    }


def _session_response(session: InteractiveSession) -> InteractiveSessionResponse:
    current = _current_step(session)
    return InteractiveSessionResponse(
        id=session.id,
        user_id=session.user_id,
        topic_id=session.topic_id,
        problem_text=session.problem_text,
        problem_type=session.problem_type,
        status=session.status,
        current_step_index=session.current_step_index,
        source_chunks=_source_refs(session.source_chunks),
        current_step=_step_response(current),
        steps=[InteractiveStepResponse.model_validate(step) for step in session.steps],
        final_answer=session.final_answer,
        weak_topics=_weak_topics(session),
        suggested_actions=_suggested_actions(session.id),
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


async def _get_owned_session(db: AsyncSession, user_id: int, session_id: int) -> InteractiveSession:
    result = await db.execute(
        select(InteractiveSession)
        .options(selectinload(InteractiveSession.steps), selectinload(InteractiveSession.answers))
        .where(InteractiveSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Interactive session not found")
    return session


async def start_interactive_session(
    db: AsyncSession,
    user: User,
    request: InteractiveSessionCreate,
) -> InteractiveSessionResponse:
    """Start a concentration-solving session and create deterministic steps."""
    problem_type = classify_problem_type(request.problem_text)
    source_chunks, context_meta = await retrieve_problem_context(
        db,
        problem_text=request.problem_text,
        user_id=user.id,
        source_types=request.source_types,
        topic_id=request.topic_id,
    )
    plan = build_concentration_solution_plan(request.problem_text)
    session = InteractiveSession(
        user_id=user.id,
        topic_id=request.topic_id,
        problem_text=request.problem_text,
        problem_type=problem_type,
        status="active",
        current_step_index=0,
        source_chunks=source_chunks,
        final_answer=None,
        weak_topics=[],
        metadata_json={"plan": plan, **context_meta},
    )
    db.add(session)
    await db.flush()
    for step in create_interactive_steps(session, plan):
        db.add(step)
    await db.commit()
    return _session_response(await _get_owned_session(db, user.id, session.id))


def _normalize_formula(text: str) -> str:
    normalized = normalize_solver_text(text)
    normalized = normalized.replace(" ", "")
    normalized = normalized.replace("الكتلة", "m").replace("الكتله", "m").replace("الحجم", "v")
    normalized = normalized.replace("التركيزالغرامي", "cg").replace("التركيز", "c")
    normalized = normalized.replace(":", "=")
    return normalized


def _parse_numeric_answer(answer: str) -> tuple[float | None, str | None]:
    normalized = normalize_solver_text(answer)
    match = _NUMBER_RE.search(normalized)
    value = float(match.group(0).replace(",", ".")) if match else None
    unit = _parse_unit(normalized)
    return value, unit


def _parse_unit(normalized: str) -> str | None:
    text = normalized.replace(" ", "")
    if any(unit in text for unit in ("g/mol", "g.mol-1", "غ/مول", "غرام/مول")):
        return "g/mol"
    if any(unit in text for unit in ("mol/l", "mol.l-1", "مول/ل", "مول/لتر")):
        return "mol/L"
    if any(unit in text for unit in ("g/l", "g.l-1", "غ/ل", "غرام/لتر")):
        return "g/L"
    if re.search(r"\bmol\b", normalized) or "مول" in normalized:
        return "mol"
    if re.search(r"\bml\b", normalized) or "مل" in normalized:
        return "mL"
    if re.search(r"\bl\b", normalized) or "لتر" in normalized:
        return "L"
    return None


def _unit_matches(parsed: str | None, expected: str | None) -> bool:
    if expected is None:
        return True
    return parsed == expected


def _within_tolerance(value: float, expected: float, tolerance: float) -> bool:
    absolute = abs(value - expected)
    relative = absolute / max(abs(expected), 1e-9)
    return absolute <= tolerance or relative <= tolerance


def _feedback_for_misconception(step: InteractiveStep, answer: str, value: float | None, unit: str | None) -> tuple[str, str | None]:
    expected = step.expected_numeric
    normalized = normalize_solver_text(answer)
    if step.step_key == "convert_volume_ml_to_l" and unit == "mL":
        return "انتبه: المطلوب هو التحويل إلى اللتر. اقسم قيمة mL على 1000.", "forgot_ml_to_l_conversion"
    if expected is not None and unit is None and step.expected_unit:
        return "القيمة قريبة، لكن يجب كتابة الوحدة حتى يكون الجواب الكيميائي كاملاً.", "missing_unit"
    if step.step_key == "calculate_moles" and value is not None:
        mass = (step.metadata_json or {}).get("mass_g") if isinstance(step.metadata_json, dict) else None
        if mass is not None and math.isclose(value, float(mass), rel_tol=0.02, abs_tol=0.02):
            return "استخدمت الكتلة مباشرة. لحساب عدد المولات يجب استعمال n = m / M.", "used_mass_instead_of_moles"
    if step.step_key == "calculate_molar_mass" and value is not None and not _within_tolerance(value, float(expected or 0), 0.02):
        return "راجع جمع الكتل الذرية في الصيغة؛ الكتلة المولية لـ HCl هي 36.5 g/mol.", "wrong_molar_mass"
    if expected and value and _within_tolerance(value, 1 / expected, 0.02):
        return "يبدو أنك قسمت بالعكس. راجع ترتيب البسط والمقام في القانون.", "divided_in_wrong_direction"
    if "/" in normalized and step.expected_formula and _normalize_formula(step.expected_formula) not in _normalize_formula(answer):
        return "القانون أو التعويض غير مناسب لهذه الخطوة. راجع المطلوب في السؤال.", "wrong_formula"
    return "الإجابة غير صحيحة بعد. جرّب مرة أخرى مستفيداً من التلميح.", "incorrect_answer"


def validate_step_answer(step: InteractiveStep, answer_text: str) -> ValidationResult:
    """Validate formula, numeric, and final-answer steps deterministically."""
    answer = normalize_solver_text(answer_text)
    if step.expected_answer_type == "formula":
        expected = _normalize_formula(step.expected_formula or "")
        aliases = []
        if isinstance(step.metadata_json, dict):
            aliases = [str(item) for item in step.metadata_json.get("formula_aliases", [])]
        accepted = {expected, *[_normalize_formula(item) for item in aliases]}
        if _normalize_formula(answer_text) in accepted:
            return ValidationResult(True, "صحيح. اخترت القانون المناسب لهذه الخطوة.")
        return ValidationResult(False, "القانون غير مناسب. المطلوب علاقة كتلة المذاب بحجم المحلول.", misconception_type="wrong_formula")

    if step.expected_answer_type == "numeric":
        value, unit = _parse_numeric_answer(answer_text)
        if value is None or step.expected_numeric is None:
            return ValidationResult(False, "لم أستطع قراءة قيمة عددية واضحة من جوابك.", misconception_type="missing_numeric_value")
        if not _within_tolerance(value, step.expected_numeric, step.tolerance):
            feedback, misconception = _feedback_for_misconception(step, answer_text, value, unit)
            return ValidationResult(False, feedback, parsed_value=value, parsed_unit=unit, misconception_type=misconception)
        if not _unit_matches(unit, step.expected_unit):
            feedback, misconception = _feedback_for_misconception(step, answer_text, value, unit)
            return ValidationResult(False, feedback, parsed_value=value, parsed_unit=unit, misconception_type=misconception)
        return ValidationResult(True, "صحيح. القيمة والوحدة مناسبتان.", parsed_value=value, parsed_unit=unit)

    if step.expected_answer_type == "final":
        meta = step.metadata_json if isinstance(step.metadata_json, dict) else {}
        keywords = [normalize_solver_text(str(item)) for item in meta.get("accepted_keywords", [])]
        if all(keyword in answer for keyword in keywords if keyword):
            return ValidationResult(True, "ممتاز. الجواب النهائي يتضمن القيم والوحدات المطلوبة.")
        return ValidationResult(
            False,
            "الجواب النهائي يجب أن يذكر التركيز الغرامي والتركيز المولي مع الوحدات.",
            misconception_type="incomplete_final_answer",
        )

    return ValidationResult(False, "نوع الخطوة غير مدعوم.", misconception_type="unsupported_step")


async def _record_misconception(
    db: AsyncSession,
    *,
    session: InteractiveSession,
    step: InteractiveStep,
    result: ValidationResult,
) -> None:
    if not result.misconception_type:
        return
    weak_topics = set(_weak_topics(session))
    weak_topics.add(result.misconception_type)
    session.weak_topics = sorted(weak_topics)
    db.add(
        MisconceptionEvent(
            user_id=session.user_id,
            session_id=session.id,
            step_id=step.id,
            misconception_type=result.misconception_type,
            topic_key=(step.metadata_json or {}).get("skill_key") if isinstance(step.metadata_json, dict) else None,
            description_ar=result.feedback_ar,
            metadata_json={"step_key": step.step_key},
        )
    )


async def _update_skill_mastery(db: AsyncSession, session: InteractiveSession, step: InteractiveStep, correct: bool) -> None:
    metadata = step.metadata_json if isinstance(step.metadata_json, dict) else {}
    skill_key = metadata.get("skill_key") or step.step_key
    result = await db.execute(
        select(SkillMastery).where(SkillMastery.user_id == session.user_id, SkillMastery.skill_key == skill_key)
    )
    mastery = result.scalar_one_or_none()
    if mastery is None:
        mastery = SkillMastery(user_id=session.user_id, skill_key=skill_key, metadata_json={})
        db.add(mastery)
    mastery.attempts = (mastery.attempts or 0) + 1
    mastery.correct_attempts = mastery.correct_attempts or 0
    if correct:
        mastery.correct_attempts += 1
    mastery.mastery_score = round(mastery.correct_attempts / max(mastery.attempts, 1), 4)


def _next_pending_step(session: InteractiveSession) -> InteractiveStep | None:
    return next((step for step in session.steps if step.status == "pending"), None)


async def complete_session_if_done(db: AsyncSession, session: InteractiveSession) -> None:
    """Complete the session when all steps have been solved."""
    if all(step.status == "completed" for step in session.steps):
        summary = build_final_summary(session)
        session.status = "completed"
        session.final_answer = summary.final_answer
        session.summary_json = summary.model_dump()
        db.add(session)


async def submit_step_answer(
    db: AsyncSession,
    user: User,
    session_id: int,
    request: InteractiveAnswerSubmit,
) -> InteractiveAnswerResponse:
    """Validate one submitted answer and advance only on correctness."""
    session = await _get_owned_session(db, user.id, session_id)
    if session.status == "completed":
        summary = build_final_summary(session)
        return InteractiveAnswerResponse(
            session_id=session.id,
            step_id=0,
            is_correct=True,
            feedback_ar="هذه الجلسة مكتملة بالفعل.",
            current_step=None,
            next_step=None,
            session_status=session.status,
            final_summary=summary,
        )
    step = _current_step(session)
    if step is None:
        raise HTTPException(status_code=409, detail="No active step found for this session")
    if request.step_id is not None and request.step_id != step.id:
        raise HTTPException(status_code=409, detail="Answer the current step before moving forward")

    result = validate_step_answer(step, request.answer_text)
    answer = StudentStepAnswer(
        session_id=session.id,
        step_id=step.id,
        user_id=user.id,
        answer_text=request.answer_text,
        is_correct=result.is_correct,
        feedback_ar=result.feedback_ar,
        parsed_value=result.parsed_value,
        parsed_unit=result.parsed_unit,
        misconception_type=result.misconception_type,
        metadata_json={"step_key": step.step_key},
    )
    db.add(answer)
    await _update_skill_mastery(db, session, step, result.is_correct)

    if result.is_correct:
        step.status = "completed"
        next_step = _next_pending_step(session)
        if next_step:
            next_step.status = "current"
            session.current_step_index = next_step.step_index
        await complete_session_if_done(db, session)
    else:
        await _record_misconception(db, session=session, step=step, result=result)
        next_step = None

    await db.commit()
    session = await _get_owned_session(db, user.id, session.id)
    current = _current_step(session)
    final_summary = build_final_summary(session) if session.status == "completed" else None
    return InteractiveAnswerResponse(
        session_id=session.id,
        step_id=step.id,
        is_correct=result.is_correct,
        feedback_ar=result.feedback_ar,
        misconception_type=result.misconception_type,
        parsed_value=result.parsed_value,
        parsed_unit=result.parsed_unit,
        current_step=_step_response(current),
        next_step=_step_response(current) if result.is_correct else None,
        session_status=session.status,
        final_summary=final_summary,
    )


async def get_interactive_session(db: AsyncSession, user: User, session_id: int) -> InteractiveSessionResponse:
    return _session_response(await _get_owned_session(db, user.id, session_id))


async def list_interactive_sessions(
    db: AsyncSession,
    user: User,
    status: str | None = None,
    limit: int = 20,
) -> list[InteractiveSessionResponse]:
    stmt = (
        select(InteractiveSession)
        .options(selectinload(InteractiveSession.steps), selectinload(InteractiveSession.answers))
        .where(InteractiveSession.user_id == user.id)
        .order_by(InteractiveSession.updated_at.desc())
        .limit(limit)
    )
    if status:
        stmt = stmt.where(InteractiveSession.status == status)
    result = await db.execute(stmt)
    return [_session_response(session) for session in result.scalars().unique().all()]


async def get_step_hint(db: AsyncSession, user: User, session_id: int) -> InteractiveAnswerResponse:
    session = await _get_owned_session(db, user.id, session_id)
    step = _current_step(session)
    if step is None:
        summary = build_final_summary(session)
        return InteractiveAnswerResponse(
            session_id=session.id,
            step_id=0,
            is_correct=True,
            feedback_ar="لا توجد خطوة حالية؛ الجلسة مكتملة.",
            current_step=None,
            next_step=None,
            session_status=session.status,
            final_summary=summary,
        )
    return InteractiveAnswerResponse(
        session_id=session.id,
        step_id=step.id,
        is_correct=False,
        feedback_ar=step.hint_ar or "راجع القانون المناسب لهذه الخطوة.",
        current_step=_step_response(step),
        next_step=None,
        session_status=session.status,
    )


def build_final_summary(session: InteractiveSession) -> InteractiveSessionSummaryResponse:
    """Build the final sourced answer and follow-up actions."""
    plan = (session.metadata_json or {}).get("plan") if isinstance(session.metadata_json, dict) else {}
    final_answer = session.final_answer or plan.get("final_answer") or "لم تتوفر نتيجة نهائية."
    step_summary = [
        {
            "step_index": step.step_index,
            "step_key": step.step_key,
            "title_ar": step.title_ar,
            "status": step.status,
            "explanation_ar": step.explanation_ar,
        }
        for step in session.steps
    ]
    actions = _suggested_actions(session.id)
    return InteractiveSessionSummaryResponse(
        session_id=session.id,
        status="completed",
        final_answer=final_answer,
        step_summary=step_summary,
        sources=_source_refs(session.source_chunks),
        detected_weak_topics=_weak_topics(session),
        suggested_mini_quiz_action=actions["mini_quiz"],
        suggested_flashcard_generation_action=actions["flashcards"],
    )


async def finish_interactive_session(db: AsyncSession, user: User, session_id: int) -> InteractiveSessionSummaryResponse:
    """Finish the session and return the deterministic final summary."""
    session = await _get_owned_session(db, user.id, session_id)
    summary = build_final_summary(session)
    session.status = "completed"
    session.final_answer = summary.final_answer
    session.summary_json = summary.model_dump()
    await db.commit()
    return summary
