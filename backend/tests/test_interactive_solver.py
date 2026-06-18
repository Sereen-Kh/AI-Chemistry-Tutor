"""Tests for the Guided Chemistry Problem-Solving Lab MVP."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models.user import User
from app.schemas.interactive_solver import InteractiveAnswerSubmit, InteractiveSessionCreate
from app.services import interactive_solver_service as solver

ORIGINAL_DYNAMIC_PLAN_GENERATOR = solver.generate_dynamic_solver_plan


def run_async(coro):
    return asyncio.run(coro)


@pytest.fixture()
def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async def init() -> async_sessionmaker[AsyncSession]:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return async_sessionmaker(engine, expire_on_commit=False)

    factory = run_async(init())
    yield factory
    run_async(engine.dispose())


@pytest.fixture(autouse=True)
def deterministic_context(monkeypatch: pytest.MonkeyPatch):
    async def fake_context(*_args, **_kwargs):
        return (
            [
                {
                    "chunk_id": 1,
                    "page_number": 7,
                    "source_type": "textbook",
                    "content_type": "definition",
                    "preview": "التركيز المولي C = n / V والتركيز الغرامي Cg = m / V.",
                    "similarity_score": 0.91,
                }
            ],
            {"rag_diagnostics": {"fixture": True}},
        )

    monkeypatch.setattr(solver, "retrieve_problem_context", fake_context)

    async def fake_dynamic_plan(*_args, **_kwargs):
        return None

    monkeypatch.setattr(solver, "generate_dynamic_solver_plan", fake_dynamic_plan)


async def _create_user(db: AsyncSession, *, email: str = "student@example.com") -> User:
    user = User(first_name="سارة", last_name="", email=email, hashed_password="hashed")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _start_session(db: AsyncSession, user: User):
    request = InteractiveSessionCreate(
        problem_text="محلول HCl حجمه 100 mL ويحتوي 3.65 g. احسب التركيز الغرامي والمولي.",
        source_types=["textbook", "solution_book"],
    )
    return await solver.start_interactive_session(db, user, request)


def test_starting_concentration_session_creates_steps(session_factory):
    async def scenario():
        async with session_factory() as db:
            user = await _create_user(db)
            response = await _start_session(db, user)
            assert response.problem_type == "concentration_calculation"
            assert response.status == "active"
            assert len(response.steps) == 7
            assert response.current_step is not None
            assert response.current_step.step_key == "identify_gram_concentration_formula"
            assert response.source_chunks[0].page_number == 7

    run_async(scenario())


def test_dynamic_plan_supports_general_chemistry_session(session_factory, monkeypatch: pytest.MonkeyPatch):
    async def fake_dynamic_plan(*_args, **_kwargs):
        return {
            "problem_type": "reaction_equation",
            "parsed": {"generated_by": "test"},
            "final_answer": "ينتج غاز الهيدروجين وملح كلوريد الزنك.",
            "steps": [
                {
                    "step_key": "identify_products",
                    "title_ar": "تحديد النواتج",
                    "prompt_ar": "ما نواتج تفاعل الزنك مع حمض كلور الماء؟",
                    "expected_answer_type": "keywords",
                    "expected_formula": None,
                    "expected_numeric": None,
                    "expected_unit": None,
                    "hint_ar": "المعدن مع الحمض يعطي ملحاً وغاز الهيدروجين.",
                    "explanation_ar": "ينتج كلوريد الزنك وغاز الهيدروجين.",
                    "metadata_json": {
                        "skill_key": "acid_metal_products",
                        "accepted_keywords": ["كلوريد الزنك", "الهيدروجين"],
                    },
                }
            ],
        }

    async def scenario():
        monkeypatch.setattr(solver, "generate_dynamic_solver_plan", fake_dynamic_plan)
        async with session_factory() as db:
            user = await _create_user(db)
            response = await solver.start_interactive_session(
                db,
                user,
                InteractiveSessionCreate(problem_text="ما نواتج تفاعل الزنك مع حمض كلور الماء؟"),
            )
            assert response.problem_type == "reaction_equation"
            assert len(response.steps) == 1
            result = await solver.submit_step_answer(
                db,
                user,
                response.id,
                InteractiveAnswerSubmit(answer_text="كلوريد الزنك وغاز الهيدروجين"),
            )
            assert result.is_correct is True
            assert result.session_status == "completed"

    run_async(scenario())


def test_dynamic_plan_generation_parses_structured_gemini_response(monkeypatch: pytest.MonkeyPatch):
    parsed_payload = solver.GeneratedSolverPlan(
        problem_type="reaction_equation",
        final_answer="Zn + 2HCl -> ZnCl2 + H2",
        steps=[
            solver.GeneratedSolverStep(
                step_key="write_reactants",
                title_ar="كتابة المتفاعلات",
                prompt_ar="اكتب صيغ المتفاعلات.",
                expected_answer_type="formula",
                expected_formula="Zn+HCl",
                formula_aliases=["Zn + HCl"],
                hint_ar="ابدأ بالزنك وحمض كلور الماء.",
                explanation_ar="المتفاعلان هما Zn و HCl.",
                skill_key="reaction_reactants",
            )
        ],
    )

    class FakeResponse:
        text = ""
        parsed = parsed_payload

    class FakeModels:
        def generate_content(self, **kwargs):
            assert kwargs["model"] == "gemini-test"
            assert "ما نواتج تفاعل الزنك" in kwargs["contents"]
            return FakeResponse()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(solver.settings, "gemini_api_key", "fake-key")
    monkeypatch.setattr(solver.settings, "google_api_key", "")
    monkeypatch.setattr(solver.settings, "gemini_tutor_generation_enabled", True)
    monkeypatch.setattr(solver.settings, "model_name", "gemini-test")
    monkeypatch.setattr(solver, "get_gemini_client", lambda: FakeClient())

    plan = run_async(
        ORIGINAL_DYNAMIC_PLAN_GENERATOR(
            "ما نواتج تفاعل الزنك مع حمض كلور الماء؟",
            source_chunks=[],
            problem_type="general_chemistry",
        )
    )

    assert plan is not None
    assert plan["problem_type"] == "reaction_equation"
    assert plan["parsed"]["generated_by"] == "gemini"
    assert plan["steps"][0]["expected_answer_type"] == "formula"
    assert "formula_aliases" in plan["steps"][0]["metadata_json"]


def test_correct_answer_advances_to_next_step(session_factory):
    async def scenario():
        async with session_factory() as db:
            user = await _create_user(db)
            session = await _start_session(db, user)
            result = await solver.submit_step_answer(
                db,
                user,
                session.id,
                InteractiveAnswerSubmit(answer_text="Cg = m / V"),
            )
            assert result.is_correct is True
            assert result.next_step is not None
            assert result.next_step.step_key == "convert_volume_ml_to_l"
            refreshed = await solver.get_interactive_session(db, user, session.id)
            assert refreshed.current_step is not None
            assert refreshed.current_step.step_key == "convert_volume_ml_to_l"

    run_async(scenario())


def test_wrong_answer_returns_feedback_and_does_not_advance(session_factory):
    async def scenario():
        async with session_factory() as db:
            user = await _create_user(db)
            session = await _start_session(db, user)
            result = await solver.submit_step_answer(
                db,
                user,
                session.id,
                InteractiveAnswerSubmit(answer_text="C = V / m"),
            )
            assert result.is_correct is False
            assert result.misconception_type == "wrong_formula"
            refreshed = await solver.get_interactive_session(db, user, session.id)
            assert refreshed.current_step is not None
            assert refreshed.current_step.step_key == "identify_gram_concentration_formula"

    run_async(scenario())


def test_ml_to_l_conversion_is_validated(session_factory):
    async def scenario():
        async with session_factory() as db:
            user = await _create_user(db)
            session = await _start_session(db, user)
            await solver.submit_step_answer(db, user, session.id, InteractiveAnswerSubmit(answer_text="Cg=m/V"))
            wrong = await solver.submit_step_answer(db, user, session.id, InteractiveAnswerSubmit(answer_text="100 mL"))
            assert wrong.is_correct is False
            assert wrong.misconception_type == "forgot_ml_to_l_conversion"
            correct = await solver.submit_step_answer(db, user, session.id, InteractiveAnswerSubmit(answer_text="0.1 L"))
            assert correct.is_correct is True
            assert correct.next_step is not None
            assert correct.next_step.step_key == "calculate_gram_concentration"

    run_async(scenario())


def test_final_session_completes_correctly(session_factory):
    async def scenario():
        async with session_factory() as db:
            user = await _create_user(db)
            session = await _start_session(db, user)
            answers = [
                "Cg=m/V",
                "0.1 L",
                "36.5 g/L",
                "36.5 g/mol",
                "0.1 mol",
                "1 mol/L",
                "Cg = 36.5 g/L و C = 1 mol/L",
            ]
            response = None
            for answer in answers:
                response = await solver.submit_step_answer(db, user, session.id, InteractiveAnswerSubmit(answer_text=answer))
            assert response is not None
            assert response.session_status == "completed"
            assert response.final_summary is not None
            assert "36.5" in response.final_summary.final_answer
            assert response.final_summary.suggested_mini_quiz_action["action"] == "generate_quiz"
            assert response.final_summary.suggested_flashcard_generation_action["action"] == "generate_flashcards"

    run_async(scenario())


def test_user_cannot_access_another_users_session(session_factory):
    async def scenario():
        async with session_factory() as db:
            owner = await _create_user(db, email="owner@example.com")
            other = await _create_user(db, email="other@example.com")
            session = await _start_session(db, owner)
            with pytest.raises(HTTPException) as exc_info:
                await solver.get_interactive_session(db, other, session.id)
            assert exc_info.value.status_code == 404

    run_async(scenario())
