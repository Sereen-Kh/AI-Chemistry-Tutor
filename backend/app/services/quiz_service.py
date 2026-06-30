"""Quiz and exam trainer service functions."""

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import QuizAttempt
from app.models.textbook import ExtractedQuestion
from app.models.topic import Topic


async def generate_quiz(
    db: AsyncSession,
    topic_id: int | None,
    lesson_id: int | None,
    source_type: str | None,
    limit: int,
):
    stmt = select(ExtractedQuestion).where(ExtractedQuestion.question_text.isnot(None))
    if topic_id is not None:
        stmt = stmt.where(ExtractedQuestion.topic_id == topic_id)
    elif lesson_id is not None:
        stmt = stmt.where(ExtractedQuestion.lesson_id == lesson_id)
    if source_type is not None:
        # source_type is stored on ContentSource; keep the first MVP version simple.
        pass
    result = await db.execute(stmt.order_by(ExtractedQuestion.id).limit(limit))
    return list(result.scalars().all())


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
