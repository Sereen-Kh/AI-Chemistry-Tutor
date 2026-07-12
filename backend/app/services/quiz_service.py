"""Quiz and exam trainer service functions."""

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fastapi import HTTPException

from app.models.chemistry import Lesson
from app.models.assessment import QuizAttempt
from app.models.textbook import ContentSource, ExtractedQuestion, RagChunk
from app.models.topic import Topic
from app.services import ai_quiz_generator
from app.services.reviewed_curriculum_metadata import (
    ensure_reviewed_metadata_ready,
    evaluate_chunk_eligibility,
)


QUESTION_TYPE_ALIASES = {
    "mcq": "multiple_choice",
    "multiple_choice": "multiple_choice",
    "true_false": "true_false",
    "fill_blank": "short_answer",
    "short_answer": "short_answer",
    "calculation": "calculation",
    "equation_balancing": "equation_balancing",
}


QUIZ_NOT_READY_CODE = "LESSON_NOT_READY_FOR_QUIZ_GENERATION"


def _unique_ints(values: list[int] | None, extra: int | None = None) -> list[int]:
    result: list[int] = []
    for value in [*(values or []), extra]:
        if value is None:
            continue
        item = int(value)
        if item not in result:
            result.append(item)
    return result


def _metadata_dict(raw: object) -> dict:
    return dict(raw) if isinstance(raw, dict) else {}


def _chunk_quality(chunk: RagChunk) -> str:
    metadata = _metadata_dict(chunk.metadata_json)
    return str(metadata.get("quality_status") or "needs_review")


def _chunk_reviewed_version(chunk: RagChunk) -> str | None:
    metadata = _metadata_dict(chunk.metadata_json)
    value = metadata.get("reviewed_metadata_version")
    return str(value) if value else None


def _canonical_question_types(question_types: list[str] | None) -> set[str]:
    return {
        QUESTION_TYPE_ALIASES.get(str(question_type), str(question_type))
        for question_type in (question_types or [])
        if str(question_type).strip()
    }


def _question_type_matches(question: ExtractedQuestion, allowed_types: set[str]) -> bool:
    if not allowed_types:
        return True
    question_type = QUESTION_TYPE_ALIASES.get(question.question_type, question.question_type)
    return question_type in allowed_types


def _valid_question(question: ExtractedQuestion, allowed_types: set[str]) -> bool:
    if not _question_type_matches(question, allowed_types):
        return False
    if not (question.question_text or "").strip():
        return False
    if not (question.correct_answer or "").strip():
        return False
    if not question.lesson_id and not question.topic_id:
        return False
    if question.difficulty is None:
        return False
    question_type = QUESTION_TYPE_ALIASES.get(question.question_type, question.question_type)
    if question_type == "multiple_choice":
        options = question.options if isinstance(question.options, list) else list((question.options or {}).values())
        return len(options) >= 4 and question.correct_answer in [str(option) for option in options]
    if question_type == "true_false":
        return str(question.correct_answer).strip().lower() in {"true", "false", "صح", "خطأ"}
    if question_type in {"calculation", "equation_balancing"}:
        return bool((question.explanation or "").strip())
    return bool((question.explanation or "").strip())


async def _generated_source(db: AsyncSession) -> ContentSource:
    source = await db.scalar(
        select(ContentSource).where(
            ContentSource.source_type == "generated_quiz",
            ContentSource.title == "EduMind generated quiz fallback",
        )
    )
    if source is not None:
        return source
    source = ContentSource(
        source_type="generated_quiz",
        title="EduMind generated quiz fallback",
        grade="grade_12",
        subject="chemistry",
        status="ready",
        metadata_json={"generated_by": "quiz_service", "purpose": "cold_database_fallback"},
    )
    db.add(source)
    await db.flush()
    return source


async def _lesson_context(db: AsyncSession, lesson_id: int | None, topic_id: int | None) -> tuple[Lesson | None, Topic | None]:
    topic = await db.get(Topic, topic_id) if topic_id is not None else None
    lesson = None
    if lesson_id is not None:
        lesson = await db.scalar(
            select(Lesson)
            .where(Lesson.id == lesson_id)
            .options(selectinload(Lesson.topics), selectinload(Lesson.chapter))
        )
    elif topic is not None:
        lesson = await db.scalar(
            select(Lesson)
            .join(Lesson.topics)
            .where(Topic.id == topic.id)
            .options(selectinload(Lesson.topics), selectinload(Lesson.chapter))
        )
    return lesson, topic


async def _lesson_ready_for_quiz(db: AsyncSession, lesson: Lesson) -> tuple[bool, str, str | None]:
    filters = [RagChunk.lesson_id == lesson.id]
    if lesson.page_start is not None and lesson.page_end is not None:
        filters.append(RagChunk.page_number.between(lesson.page_start, lesson.page_end))
    elif lesson.page_start is not None:
        filters.append(RagChunk.page_number == lesson.page_start)

    result = await db.execute(
        select(RagChunk)
        .where(
            or_(*filters),
            RagChunk.source_type.in_(("textbook", "solution_book")),
        )
        .order_by(RagChunk.page_number.asc().nulls_last(), RagChunk.chunk_index.asc())
        .limit(250)
    )
    chunks = list(result.scalars().all())
    if not chunks:
        return False, "missing_ready_content", None
    reviewed_metadata = ensure_reviewed_metadata_ready()
    decisions = [
        (
            chunk,
            evaluate_chunk_eligibility(
                chunk,
                reviewed_metadata,
                legacy=chunk.extraction_method != "reviewed_jsonl",
            ),
        )
        for chunk in chunks
    ]
    blocked = next((item for item in decisions if item[1].normalized_quality_status == "blocked"), None)
    if blocked:
        return False, "blocked", _chunk_reviewed_version(blocked[0])
    ready = next((item for item in decisions if item[1].student_generation_allowed), None)
    if ready is None:
        reviewable = next((item for item in decisions if item[1].rag_search_allowed), None)
        version_chunk = reviewable[0] if reviewable else chunks[0]
        status = reviewable[1].normalized_quality_status if reviewable else "missing_ready_content"
        return False, status, _chunk_reviewed_version(version_chunk)
    return True, "ready", _chunk_reviewed_version(ready[0])


async def _resolve_lessons_for_generation(
    db: AsyncSession,
    *,
    lesson_ids: list[int],
    topic_ids: list[int],
) -> list[Lesson]:
    lessons: list[Lesson] = []
    if lesson_ids:
        result = await db.execute(
            select(Lesson)
            .where(Lesson.id.in_(lesson_ids))
            .options(selectinload(Lesson.topics), selectinload(Lesson.chapter))
            .order_by(Lesson.order, Lesson.id)
        )
        lessons = list(result.scalars().unique().all())
        missing = set(lesson_ids) - {lesson.id for lesson in lessons}
        if missing:
            raise HTTPException(status_code=404, detail="لم يتم العثور على الدرس المحدد")

    if topic_ids:
        result = await db.execute(
            select(Lesson)
            .join(Lesson.topics)
            .where(Topic.id.in_(topic_ids))
            .options(selectinload(Lesson.topics), selectinload(Lesson.chapter))
            .order_by(Lesson.order, Lesson.id)
        )
        for lesson in result.scalars().unique().all():
            if lesson.id not in {item.id for item in lessons}:
                lessons.append(lesson)
    return lessons


async def _assert_lessons_ready_for_quiz(
    db: AsyncSession,
    *,
    lesson_ids: list[int],
    topic_ids: list[int],
) -> dict[int, str | None]:
    lessons = await _resolve_lessons_for_generation(db, lesson_ids=lesson_ids, topic_ids=topic_ids)
    if not lessons:
        raise HTTPException(status_code=422, detail="اختر درساً أو موضوعاً لتوليد الاختبار")

    reviewed_versions: dict[int, str | None] = {}
    for lesson in lessons:
        ready, status, version = await _lesson_ready_for_quiz(db, lesson)
        reviewed_versions[lesson.id] = version
        if not ready:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": QUIZ_NOT_READY_CODE,
                    "lesson_id": lesson.id,
                    "lesson_title": lesson.title_ar,
                    "quality_status": status,
                    "message": "توليد الاختبارات مسموح فقط للدروس المراجعة والجاهزة.",
                },
            )
    return reviewed_versions


def _template_question_payloads(
    *,
    lesson: Lesson,
    topic: Topic | None,
    difficulty: int | None,
    question_types: set[str],
    count: int,
) -> list[dict]:
    lesson_title = lesson.title_ar
    topic_title = topic.title_ar if topic else lesson_title
    selected_types = list(question_types or {"multiple_choice", "true_false", "short_answer", "calculation"})
    payloads: list[dict] = []
    page_number = lesson.page_start
    for index in range(count):
        question_type = selected_types[index % len(selected_types)]
        if question_type == "multiple_choice":
            options = [
                f"يرتبط مباشرة بمفهوم {topic_title}",
                "تعريف غير مرتبط بالدرس",
                "خطوة حسابية بلا قانون مناسب",
                "ملاحظة مخبرية عشوائية",
            ]
            payloads.append(
                {
                    "question_text": f"أي عبارة تصف فكرة «{topic_title}» في درس «{lesson_title}»؟",
                    "question_type": "multiple_choice",
                    "options": options,
                    "correct_answer": options[0],
                    "explanation": f"الفكرة المطلوبة مأخوذة من درس {lesson_title}. راجع {topic_title} ثم اربط المصطلح بتعريفه أو تطبيقه في الكتاب.",
                }
            )
        elif question_type == "true_false":
            payloads.append(
                {
                    "question_text": f"صح أم خطأ: فهم «{topic_title}» يساعدك على حل أسئلة درس «{lesson_title}».",
                    "question_type": "true_false",
                    "options": ["صح", "خطأ"],
                    "correct_answer": "صح",
                    "explanation": f"هذا صحيح لأن أسئلة الدرس تعتمد على المفهوم الأساسي: {topic_title}.",
                }
            )
        elif question_type == "calculation":
            payloads.append(
                {
                    "question_text": f"اذكر خطوات حل مسألة كيميائية تعتمد على «{topic_title}».",
                    "question_type": "calculation",
                    "options": None,
                    "correct_answer": "تحديد المعطيات ثم اختيار القانون المناسب ثم التعويض والتحقق من الوحدة.",
                    "explanation": "في المسائل الحسابية ابدأ بالمعطيات، اكتب القانون، عوض القيم، ثم راجع وحدة الناتج وخطوات التحويل.",
                }
            )
        else:
            payloads.append(
                {
                    "question_text": f"اشرح باختصار مفهوم «{topic_title}» كما ورد في درس «{lesson_title}».",
                    "question_type": "short_answer",
                    "options": None,
                    "correct_answer": f"هو مفهوم رئيسي في درس {lesson_title} ويجب ربطه بالتعريف أو المثال الوارد في الكتاب.",
                    "explanation": f"الإجابة المقبولة تذكر معنى {topic_title} وتوضح علاقته بدرس {lesson_title}.",
                }
            )
        payloads[-1]["difficulty"] = difficulty or max(1, min(5, lesson.difficulty or 3))
        payloads[-1]["page_number"] = page_number
    return payloads


async def _save_template_questions(
    db: AsyncSession,
    *,
    lesson_id: int,
    topic_id: int | None,
    count: int,
    difficulty: int | None,
    question_types: set[str],
    reviewed_metadata_version: str | None = None,
) -> list[ExtractedQuestion]:
    lesson, topic = await _lesson_context(db, lesson_id, topic_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="لم يتم العثور على الدرس المحدد")
    if topic is None and lesson.topics:
        topic = lesson.topics[0]
    source = await _generated_source(db)
    questions = [
        ExtractedQuestion(
            source_id=source.id,
            chapter_id=lesson.chapter_id,
            lesson_id=lesson.id,
            topic_id=topic.id if topic else topic_id,
            page_number=payload["page_number"],
            question_text=payload["question_text"],
            question_type=payload["question_type"],
            options=payload["options"],
            correct_answer=payload["correct_answer"],
            explanation=payload["explanation"],
            answer_source="template_fallback",
            difficulty=payload["difficulty"],
            needs_review=True,
            metadata_json={
                "generated": True,
                "generator": "template_fallback",
                "quality_status": "ready",
                "reviewed_metadata_version": reviewed_metadata_version,
            },
        )
        for payload in _template_question_payloads(
            lesson=lesson,
            topic=topic,
            difficulty=difficulty,
            question_types=question_types,
            count=count,
        )
    ]
    db.add_all(questions)
    await db.commit()
    for question in questions:
        await db.refresh(question)
    return questions


async def generate_quiz(
    db: AsyncSession,
    topic_id: int | None = None,
    lesson_id: int | None = None,
    topic_ids: list[int] | None = None,
    lesson_ids: list[int] | None = None,
    source_type: str | None = None,
    limit: int = 5,
    *,
    difficulty: int | None = None,
    question_types: list[str] | None = None,
    user_id: int = 0,
):
    selected_lesson_ids = _unique_ints(lesson_ids, lesson_id)
    selected_topic_ids = _unique_ints(topic_ids, topic_id)
    reviewed_versions = await _assert_lessons_ready_for_quiz(
        db,
        lesson_ids=selected_lesson_ids,
        topic_ids=selected_topic_ids,
    )

    allowed_types = _canonical_question_types(question_types)
    stmt = select(ExtractedQuestion).where(ExtractedQuestion.question_text.isnot(None))
    filters = []
    if selected_topic_ids:
        filters.append(ExtractedQuestion.topic_id.in_(selected_topic_ids))
    if selected_lesson_ids:
        filters.append(ExtractedQuestion.lesson_id.in_(selected_lesson_ids))
    if filters:
        stmt = stmt.where(or_(*filters))
    if difficulty is not None:
        stmt = stmt.where(ExtractedQuestion.difficulty == difficulty)
    if source_type is not None:
        # source_type is stored on ContentSource; keep the first MVP version simple.
        pass
    result = await db.execute(stmt.order_by(ExtractedQuestion.id).limit(max(limit * 3, limit)))
    existing = [question for question in result.scalars().all() if _valid_question(question, allowed_types)]
    if len(existing) >= limit:
        return existing[:limit], False, "database"

    generated: list[ExtractedQuestion] = []
    for current_topic_id in selected_topic_ids:
        if len(existing) + len(generated) >= limit:
            break
        try:
            ai_questions = await ai_quiz_generator.generate_questions_for_topic(
                db,
                topic_id=current_topic_id,
                user_id=user_id,
                num_questions=limit - len(existing) - len(generated),
            )
            generated.extend([question for question in ai_questions if _valid_question(question, allowed_types)])
        except Exception:
            await db.rollback()

    remaining = limit - len(existing) - len(generated)
    if remaining > 0:
        lessons = await _resolve_lessons_for_generation(
            db,
            lesson_ids=selected_lesson_ids,
            topic_ids=selected_topic_ids,
        )
        for index in range(remaining):
            lesson = lessons[index % len(lessons)]
            selected_topic_id = selected_topic_ids[0] if selected_topic_ids else None
            generated.extend(
                await _save_template_questions(
                    db,
                    lesson_id=lesson.id,
                    topic_id=selected_topic_id,
                    count=1,
                    difficulty=difficulty,
                    question_types=allowed_types,
                    reviewed_metadata_version=reviewed_versions.get(lesson.id),
                )
            )

    questions = [question for question in [*existing, *generated] if _valid_question(question, allowed_types)]
    if not questions:
        raise HTTPException(status_code=503, detail="لا توجد أسئلة كافية لهذا الدرس حالياً")
    source = "database" if not generated else "ai_or_template_fallback"
    return questions[:limit], bool(generated), source


async def submit_quiz(db: AsyncSession, user_id: int, topic_id: int | None, answers: dict[str, str]) -> QuizAttempt:
    question_ids = []
    for qid in answers.keys():
        try:
            question_ids.append(int(qid))
        except ValueError:
            pass

    score = 0
    total = len(answers)
    weak_topics = {}

    resolved_topic_id = topic_id
    if question_ids:
        # Fetch questions to grade
        result = await db.execute(
            select(ExtractedQuestion).where(ExtractedQuestion.id.in_(question_ids))
        )
        questions = result.scalars().all()
        q_map = {str(q.id): q for q in questions}
        if resolved_topic_id is None:
            resolved_topic_id = next((question.topic_id for question in questions if question.topic_id), None)
        if resolved_topic_id is None:
            lesson_id_for_topic = next((question.lesson_id for question in questions if question.lesson_id), None)
            if lesson_id_for_topic is not None:
                lesson = await db.scalar(
                    select(Lesson)
                    .where(Lesson.id == lesson_id_for_topic)
                    .options(selectinload(Lesson.topics))
                )
                if lesson and lesson.topics:
                    resolved_topic_id = lesson.topics[0].id

        for qid_str, user_ans in answers.items():
            question = q_map.get(qid_str)
            if question:
                correct = question.correct_answer or ""
                # Simple exact match for MVP, or we can use AI service for fuzzy matching later
                if user_ans.strip().lower() == correct.strip().lower():
                    score += 1
                else:
                    topic_str = str(question.topic_id or resolved_topic_id or "unknown")
                    weak_topics[topic_str] = weak_topics.get(topic_str, 0) + 1
    if resolved_topic_id is None:
        raise HTTPException(status_code=422, detail="لا يمكن حفظ محاولة الاختبار دون موضوع مرتبط")

    attempt = QuizAttempt(
        user_id=user_id,
        topic_id=resolved_topic_id,
        answers=answers,
        score=score,
        total=total,
        weak_topics=weak_topics
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)
    return attempt


async def list_attempts(db: AsyncSession, user_id: int) -> list[QuizAttempt]:
    result = await db.execute(
        select(QuizAttempt).where(QuizAttempt.user_id == user_id).order_by(desc(QuizAttempt.completed_at))
    )
    return list(result.scalars().all())


async def recommendations(db: AsyncSession) -> list[dict]:
    result = await db.execute(select(Topic).order_by(Topic.difficulty.desc(), Topic.order).limit(5))
    return [
        {"topic_id": topic.id, "title_ar": topic.title_ar, "reason": "راجع هذا الموضوع لتحسين التقدم.", "priority": index + 1}
        for index, topic in enumerate(result.scalars().all())
    ]
