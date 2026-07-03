"""Quiz and exam trainer service functions."""

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fastapi import HTTPException

from app.models.chemistry import Lesson
from app.models.assessment import QuizAttempt
from app.models.textbook import ContentSource, ExtractedQuestion
from app.models.topic import Topic
from app.services import ai_quiz_generator


QUESTION_TYPE_ALIASES = {
    "mcq": "multiple_choice",
    "multiple_choice": "multiple_choice",
    "true_false": "true_false",
    "fill_blank": "short_answer",
    "short_answer": "short_answer",
    "calculation": "calculation",
    "equation_balancing": "equation_balancing",
}


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
) -> list[ExtractedQuestion]:
    lesson, topic = await _lesson_context(db, lesson_id, topic_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="لم يتم العثور على الدرس المحدد")
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
            metadata_json={"generated": True, "generator": "template_fallback"},
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
    source_type: str | None = None,
    limit: int = 5,
    *,
    difficulty: int | None = None,
    question_types: list[str] | None = None,
    user_id: int = 0,
):
    allowed_types = _canonical_question_types(question_types)
    stmt = select(ExtractedQuestion).where(ExtractedQuestion.question_text.isnot(None))
    if topic_id is not None:
        stmt = stmt.where(ExtractedQuestion.topic_id == topic_id)
    elif lesson_id is not None:
        stmt = stmt.where(ExtractedQuestion.lesson_id == lesson_id)
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
    if topic_id is not None and len(existing) < limit:
        try:
            ai_questions = await ai_quiz_generator.generate_questions_for_topic(
                db,
                topic_id=topic_id,
                user_id=user_id,
                num_questions=limit - len(existing),
            )
            generated.extend([question for question in ai_questions if _valid_question(question, allowed_types)])
        except Exception:
            await db.rollback()

    remaining = limit - len(existing) - len(generated)
    if remaining > 0:
        if lesson_id is None and topic_id is None:
            raise HTTPException(status_code=422, detail="اختر درساً أو موضوعاً لتوليد الاختبار")
        lesson, _topic = await _lesson_context(db, lesson_id, topic_id)
        if lesson is None:
            raise HTTPException(status_code=404, detail="لم يتم العثور على الدرس المحدد")
        generated.extend(
            await _save_template_questions(
                db,
                lesson_id=lesson.id,
                topic_id=topic_id,
                count=remaining,
                difficulty=difficulty,
                question_types=allowed_types,
            )
        )

    questions = [question for question in [*existing, *generated] if _valid_question(question, allowed_types)]
    if not questions:
        raise HTTPException(status_code=503, detail="لا توجد أسئلة كافية لهذا الدرس حالياً")
    source = "database" if not generated else "ai_or_template_fallback"
    return questions[:limit], bool(generated), source


async def submit_quiz(db: AsyncSession, user_id: int, topic_id: int, answers: dict[str, str]) -> QuizAttempt:
    question_ids = []
    for qid in answers.keys():
        try:
            question_ids.append(int(qid))
        except ValueError:
            pass

    score = 0
    total = len(answers)
    weak_topics = {}

    if question_ids:
        # Fetch questions to grade
        result = await db.execute(
            select(ExtractedQuestion).where(ExtractedQuestion.id.in_(question_ids))
        )
        questions = result.scalars().all()
        q_map = {str(q.id): q for q in questions}

        for qid_str, user_ans in answers.items():
            question = q_map.get(qid_str)
            if question:
                correct = question.correct_answer or ""
                # Simple exact match for MVP, or we can use AI service for fuzzy matching later
                if user_ans.strip().lower() == correct.strip().lower():
                    score += 1
                else:
                    topic_str = str(question.topic_id) if question.topic_id else "unknown"
                    weak_topics[topic_str] = weak_topics.get(topic_str, 0) + 1

    attempt = QuizAttempt(
        user_id=user_id,
        topic_id=topic_id,
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
