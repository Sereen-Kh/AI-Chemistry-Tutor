"""Small, student-owned learning context for tutor prompt personalization."""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import QuizAttempt
from app.models.chemistry import Lesson, LessonProgress
from app.models.interactive_solver import MisconceptionEvent, SkillMastery
from app.models.student_profile import StudentProfile
from app.models.topic import Topic
from app.models.user_progress import UserProgress


MEMORY_MAX_CHARS = 1200
_SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class LearningMemoryContext:
    enabled: bool
    prompt_text: str = ""
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def applied(self) -> bool:
        return self.enabled and bool(self.prompt_text)

    def diagnostics(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "applied": self.applied,
            "counts": dict(self.counts),
        }


def _clean(value: object, *, limit: int = 160) -> str:
    return _SPACE_RE.sub(" ", str(value or "")).strip()[:limit]


def _bounded_lines(lines: list[str], max_chars: int = MEMORY_MAX_CHARS) -> str:
    selected: list[str] = []
    used = 0
    for line in lines:
        clean_line = _clean(line, limit=320)
        if not clean_line:
            continue
        extra = len(clean_line) + (1 if selected else 0)
        if used + extra > max_chars:
            break
        selected.append(clean_line)
        used += extra
    return "\n".join(selected)


async def build_learning_memory_context(
    db: AsyncSession,
    *,
    user_id: int,
    enabled: bool = True,
    current_lesson_id: int | None = None,
) -> LearningMemoryContext:
    """Build deterministic learning context without reading prior chat text."""
    if not enabled:
        return LearningMemoryContext(enabled=False)

    profile = await db.scalar(select(StudentProfile).where(StudentProfile.user_id == user_id))
    if profile is not None and not profile.learning_memory_enabled:
        return LearningMemoryContext(enabled=False)

    current_lesson_title = None
    if current_lesson_id is not None:
        current_lesson_title = await db.scalar(
            select(Lesson.title_ar).where(Lesson.id == current_lesson_id)
        )

    lesson_rows = (
        await db.execute(
            select(LessonProgress.status, Lesson.title_ar)
            .join(Lesson, Lesson.id == LessonProgress.lesson_id)
            .where(LessonProgress.user_id == user_id)
            .order_by(LessonProgress.id.desc())
            .limit(3)
        )
    ).all()
    weak_topic_rows = (
        await db.execute(
            select(Topic.title_ar, UserProgress.best_quiz_score, UserProgress.quizzes_completed)
            .join(Topic, Topic.id == UserProgress.topic_id)
            .where(UserProgress.user_id == user_id, UserProgress.quizzes_completed > 0)
            .order_by(UserProgress.best_quiz_score.asc(), UserProgress.id.asc())
            .limit(3)
        )
    ).all()
    misconception_rows = (
        await db.execute(
            select(MisconceptionEvent.misconception_type, MisconceptionEvent.topic_key)
            .where(MisconceptionEvent.user_id == user_id)
            .order_by(MisconceptionEvent.id.desc())
            .limit(3)
        )
    ).all()
    mastery_rows = (
        await db.execute(
            select(SkillMastery.skill_key, SkillMastery.mastery_score, SkillMastery.attempts)
            .where(SkillMastery.user_id == user_id, SkillMastery.attempts > 0)
            .order_by(SkillMastery.mastery_score.asc(), SkillMastery.id.asc())
            .limit(3)
        )
    ).all()
    quiz_rows = (
        await db.execute(
            select(QuizAttempt.score, QuizAttempt.total)
            .where(QuizAttempt.user_id == user_id, QuizAttempt.total > 0)
            .order_by(QuizAttempt.completed_at.desc(), QuizAttempt.id.desc())
            .limit(3)
        )
    ).all()

    counts = {
        "current_lesson": int(current_lesson_title is not None),
        "recent_lessons": len(lesson_rows),
        "weak_topics": len(weak_topic_rows),
        "misconceptions": len(misconception_rows),
        "skills": len(mastery_rows),
        "quiz_attempts": len(quiz_rows),
    }
    lines: list[str] = []

    if current_lesson_title:
        lines.append(f"سياق الدرس الحالي: {_clean(current_lesson_title, limit=100)}.")

    if profile is not None:
        preferences = [
            _clean(profile.teaching_level, limit=30),
            _clean(profile.explanation_method, limit=40),
        ]
        lines.append(f"تفضيلات الشرح: {', '.join(item for item in preferences if item)}.")
        interests = [_clean(item, limit=30) for item in (profile.student_interests or [])[:3]]
        if interests:
            lines.append(f"اهتمامات اختيارية للأمثلة فقط: {', '.join(interests)}.")
        goal = _clean(profile.goals, limit=180)
        if goal:
            lines.append(f"هدف تعلم معلن: {goal}.")

    if lesson_rows:
        lessons = "; ".join(f"{_clean(title, limit=80)} ({_clean(status, limit=24)})" for status, title in lesson_rows)
        lines.append(f"دروس حديثة: {lessons}.")
    if weak_topic_rows:
        weak_topics = "; ".join(
            f"{_clean(title, limit=70)}: {round(float(score))}%"
            for title, score, _attempts in weak_topic_rows
        )
        lines.append(f"موضوعات ضعيفة مبنية على محاولات اختبار: {weak_topics}.")
    if misconception_rows:
        misconceptions = "; ".join(
            ": ".join(part for part in (_clean(kind, limit=60), _clean(topic, limit=60)) if part)
            for kind, topic in misconception_rows
        )
        lines.append(f"مفاهيم خاطئة حديثة: {misconceptions}.")
    if mastery_rows:
        skills = "; ".join(
            f"{_clean(skill, limit=70)}: {round(float(score) * 100)}%"
            for skill, score, _attempts in mastery_rows
        )
        lines.append(f"مهارات تحتاج دعماً: {skills}.")
    if quiz_rows:
        percentages = [round((float(score) / float(total)) * 100) for score, total in quiz_rows]
        lines.append(f"متوسط آخر محاولات الاختبار: {round(sum(percentages) / len(percentages))}%.")

    if lines:
        lines.insert(
            0,
            "ذاكرة تعلم منظمة للتخصيص فقط. لا تغيّر الحقائق أو الإجابة الصحيحة أو ترتيب الاسترجاع أو الاستشهادات.",
        )
    prompt_text = _bounded_lines(lines)
    return LearningMemoryContext(enabled=True, prompt_text=prompt_text, counts=counts)


def append_learning_memory(system_prompt: str, memory: LearningMemoryContext) -> str:
    if not memory.applied:
        return system_prompt
    return f"{system_prompt}\n\n{memory.prompt_text}"
