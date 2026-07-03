"""Flashcard deck generation and spaced-repetition service."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from math import ceil
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chemistry import Chapter, Lesson
from app.models.flashcard import Flashcard, FlashcardDeck, FlashcardProgress
from app.models.textbook import RagChunk
from app.models.topic import Topic
from app.schemas.flashcards import FlashcardGenerateRequest

SUPPORTED_CARD_TYPES = {
    "term_definition",
    "concept_explanation",
    "equation_law",
    "calculation",
    "experiment_result",
    "compare_contrast",
    "reaction_balancing",
    "safety_rule",
    "image_based",
}

LEGACY_CARD_TYPE_MAP = {
    "term": "term_definition",
    "definition": "term_definition",
    "formula": "equation_law",
    "reaction": "reaction_balancing",
    "comparison": "compare_contrast",
    "experiment": "experiment_result",
    "common_mistake": "concept_explanation",
}

CARD_TYPE_LABELS = {
    "term_definition": "مصطلح",
    "concept_explanation": "مفهوم",
    "equation_law": "قانون / معادلة",
    "calculation": "مسألة حسابية",
    "experiment_result": "تجربة واستنتاج",
    "compare_contrast": "مقارنة",
    "reaction_balancing": "موازنة معادلات",
    "safety_rule": "قاعدة أمان",
    "image_based": "بطاقة صورة",
}

GENERIC_BACK_PATTERNS = (
    "راجع الدرس",
    "راجع النص المصدر",
    "راجع مصدر",
    "راجع الكتاب",
    "راجع درس",
)


@dataclass
class ReviewSchedule:
    status: str
    due_at: datetime
    interval_days: int
    ease_factor: float
    repetitions: int
    lapses: int


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def normalize_card_type(value: str) -> str:
    normalized = LEGACY_CARD_TYPE_MAP.get(value, value)
    if normalized not in SUPPORTED_CARD_TYPES:
        return "concept_explanation"
    return normalized


def quality_to_rating(quality: int | None) -> str:
    if quality is None:
        return "good"
    if quality <= 1:
        return "again"
    if quality <= 3:
        return "hard"
    if quality == 4:
        return "good"
    return "easy"


def schedule_review_rating(
    rating: str,
    *,
    previous_interval_days: int = 0,
    previous_ease_factor: float = 2.5,
    previous_repetitions: int = 0,
    previous_lapses: int = 0,
    reviewed_at: datetime | None = None,
) -> ReviewSchedule:
    """Calculate a simple SM-2-inspired next review state."""

    reviewed_at = reviewed_at or now_utc()
    ease = max(1.3, previous_ease_factor)
    interval = max(0, previous_interval_days)
    repetitions = max(0, previous_repetitions)
    lapses = max(0, previous_lapses)

    if rating == "again":
        ease = max(1.3, ease - 0.25)
        lapses += 1
        repetitions = 0
        return ReviewSchedule(
            status="learning",
            due_at=reviewed_at + timedelta(minutes=20),
            interval_days=0,
            ease_factor=round(ease, 2),
            repetitions=repetitions,
            lapses=lapses,
        )

    if rating == "hard":
        ease = max(1.3, ease - 0.15)
        repetitions += 1
        interval = 1 if interval <= 1 else max(1, ceil(interval * 1.2))
        return ReviewSchedule(
            status="learning" if repetitions < 2 else "review",
            due_at=reviewed_at + timedelta(days=interval),
            interval_days=interval,
            ease_factor=round(ease, 2),
            repetitions=repetitions,
            lapses=lapses,
        )

    if rating == "easy":
        ease = min(3.2, ease + 0.15)
        repetitions += 1
        interval = 4 if interval <= 1 else ceil(interval * ease * 1.45)
        return ReviewSchedule(
            status="mastered" if repetitions >= 2 else "review",
            due_at=reviewed_at + timedelta(days=interval),
            interval_days=interval,
            ease_factor=round(ease, 2),
            repetitions=repetitions,
            lapses=lapses,
        )

    repetitions += 1
    if repetitions <= 1:
        interval = 1
    elif repetitions == 2:
        interval = 3
    else:
        interval = max(3, ceil(max(interval, 1) * ease))
    return ReviewSchedule(
        status="mastered" if repetitions >= 4 else "review",
        due_at=reviewed_at + timedelta(days=interval),
        interval_days=interval,
        ease_factor=round(ease, 2),
        repetitions=repetitions,
        lapses=lapses,
    )


def _clean_text(value: str | None, limit: int = 900) -> str:
    text = " ".join((value or "").split())
    return text[:limit].strip()


def _first_sentence(value: str | None, limit: int = 220) -> str:
    text = _clean_text(value, limit=1200)
    for separator in ("؟", ".", "!", "۔", "\n"):
        if separator in text:
            return text.split(separator, 1)[0][:limit].strip()
    return text[:limit].strip()


def _difficulty_from_lesson(lesson: Lesson, requested: str) -> str:
    if requested in {"easy", "medium", "hard"}:
        return requested
    if lesson.difficulty <= 1:
        return "easy"
    if lesson.difficulty >= 3:
        return "hard"
    return "medium"


def _topic_title(topic: Topic | None, lesson: Lesson) -> str:
    return topic.title_ar if topic else lesson.title_ar


def _is_generic_back(value: str | None) -> bool:
    text = _clean_text(value, limit=500)
    if len(text) < 18:
        return True
    return any(pattern in text for pattern in GENERIC_BACK_PATTERNS)


def _fallback_answer_by_type(card_type: str, topic_title: str, lesson: Lesson) -> str:
    lesson_title = lesson.title_ar
    page_label = (
        f"صفحات {lesson.page_start} - {lesson.page_end}"
        if lesson.page_start and lesson.page_end and lesson.page_end != lesson.page_start
        else f"صفحة {lesson.page_start}"
        if lesson.page_start
        else "مصدر الدرس"
    )
    answers = {
        "term_definition": (
            f"«{topic_title}» مفهوم أساسي في درس «{lesson_title}». اكتب تعريفه، ثم اربطه بمثال أو تطبيق من {page_label}."
        ),
        "concept_explanation": (
            f"الفكرة الأساسية في «{topic_title}» هي تفسير العلاقة الكيميائية داخل درس «{lesson_title}» مع ذكر سببها أو أثرها."
        ),
        "equation_law": (
            f"ابدأ بتحديد الكميات أو الرموز المرتبطة بـ «{topic_title}»، ثم اكتب العلاقة الكيميائية المناسبة واذكر وحدة القياس إن وجدت."
        ),
        "calculation": (
            f"خطوات الحل: استخرج المعطيات الخاصة بـ «{topic_title}»، اختر القانون المناسب، عوّض القيم، ثم تحقق من وحدة الناتج."
        ),
        "experiment_result": (
            f"في التجربة المرتبطة بـ «{topic_title}» ركّز على الملاحظة ثم الاستنتاج الكيميائي الذي يفسر سبب حدوثها."
        ),
        "compare_contrast": (
            f"قارن من حيث التعريف والخاصية أو السلوك الكيميائي، ثم اذكر مثالاً يوضح الفرق عن مفهوم قريب في درس «{lesson_title}»."
        ),
        "reaction_balancing": (
            "وازن المعادلة بمساواة عدد ذرات كل عنصر في طرفي المعادلة، وابدأ بالعناصر التي تظهر في مركب واحد في كل طرف."
        ),
        "safety_rule": (
            f"قاعدة الأمان هنا هي تحديد الخطر المرتبط بـ «{topic_title}» ثم اختيار التصرف المخبري الذي يقلل هذا الخطر."
        ),
        "image_based": (
            f"اقرأ العنوان والمحاور أو الرموز في الشكل، ثم اربطها بمفهوم «{topic_title}» داخل درس «{lesson_title}»."
        ),
    }
    return answers.get(card_type, answers["concept_explanation"])


def _hint_for_card(card_type: str, topic_title: str, lesson: Lesson, answer_text: str) -> str:
    if card_type == "calculation":
        return "ابدأ بكتابة المعطيات والوحدات قبل اختيار القانون."
    if card_type == "equation_law":
        return "ابحث عن الرموز أو العلاقة الرياضية المرتبطة بالمفهوم."
    if card_type == "compare_contrast":
        return "فكّر في خاصية واحدة تميز المفهوم عن مفهوم مشابه."
    if card_type == "reaction_balancing":
        return "عدّ ذرات كل عنصر في طرفي المعادلة قبل تغيير المعاملات."
    if card_type == "experiment_result":
        return "اربط الملاحظة بسببها الكيميائي وليس بوصف التجربة فقط."
    first_words = " ".join(_clean_text(answer_text, limit=160).split()[:8])
    return f"ركّز على الكلمة المفتاحية «{topic_title}» وفكّر في: {first_words}..."


def _lesson_metadata(lesson: Lesson, topic: Topic | None, chunk: RagChunk | None) -> dict:
    chapter = lesson.chapter
    unit = chapter.unit if chapter else None
    page_start = chunk.page_number if chunk and chunk.page_number else lesson.page_start
    page_end = chunk.page_number if chunk and chunk.page_number else lesson.page_end or lesson.page_start
    return {
        "unit_id": unit.id if unit else None,
        "unit_title_ar": unit.title_ar if unit else None,
        "chapter_id": chapter.id if chapter else None,
        "chapter_title_ar": chapter.title_ar if chapter else None,
        "lesson_id": lesson.id,
        "lesson_title_ar": lesson.title_ar,
        "topic_id": topic.id if topic else None,
        "topic_title_ar": topic.title_ar if topic else None,
        "source_page_start": page_start,
        "source_page_end": page_end,
        "source_chunk_ids": [chunk.id] if chunk else [],
        "source_type": chunk.source_type if chunk else "textbook",
        "content_type": chunk.content_type if chunk else "lesson",
    }


def _build_card_payload(
    *,
    lesson: Lesson,
    topic: Topic | None,
    chunk: RagChunk | None,
    card_type: str,
    difficulty: str,
    created_by: str,
) -> dict:
    metadata = _lesson_metadata(lesson, topic, chunk)
    topic_title = _topic_title(topic, lesson)
    source_text = _clean_text(chunk.content if chunk else lesson.content_ar, limit=900)
    fallback_answer = _fallback_answer_by_type(card_type, topic_title, lesson)
    answer_text = source_text if len(source_text) >= 35 else fallback_answer
    short_answer = _first_sentence(answer_text, limit=260) or answer_text[:260]
    page_label = (
        f"صفحة {metadata['source_page_start']}"
        if metadata["source_page_start"] and metadata["source_page_start"] == metadata["source_page_end"]
        else f"صفحات {metadata['source_page_start']} - {metadata['source_page_end']}"
        if metadata["source_page_start"] and metadata["source_page_end"]
        else "صفحات غير محددة"
    )

    front_by_type = {
        "term_definition": f"ما المقصود بـ «{topic_title}»؟",
        "concept_explanation": f"اشرح فكرة «{topic_title}» بأسلوبك.",
        "equation_law": f"ما القانون أو العلاقة الأساسية المرتبطة بـ «{topic_title}»؟",
        "calculation": f"مسألة قصيرة: كيف تستخدم فكرة «{topic_title}» في حل تمرين كيميائي؟",
        "experiment_result": f"ما الملاحظة أو الاستنتاج المرتبط بتجربة «{topic_title}»؟",
        "compare_contrast": f"قارن بين «{topic_title}» ومفهوم قريب منه في الدرس.",
        "reaction_balancing": f"كيف تراجع موازنة المعادلات المرتبطة بـ «{topic_title}»؟",
        "safety_rule": f"ما قاعدة الأمان التي يجب تذكرها عند دراسة «{topic_title}»؟",
        "image_based": f"ما الذي يجب الانتباه إليه في الشكل أو الجدول المرتبط بـ «{topic_title}»؟",
    }
    description_by_type = {
        "term_definition": f"تختبر هذه البطاقة فهمك لتعريف {topic_title}.",
        "concept_explanation": f"تساعدك هذه البطاقة على شرح مفهوم {topic_title} وربطه بالدرس.",
        "equation_law": f"تراجع هذه البطاقة القانون أو العلاقة المرتبطة بـ {topic_title}.",
        "calculation": f"مسألة قصيرة على تطبيق {topic_title} في الحسابات الكيميائية.",
        "experiment_result": f"تربط هذه البطاقة بين خطوات التجربة والملاحظة والاستنتاج.",
        "compare_contrast": f"تساعدك هذه البطاقة على تمييز {topic_title} عن مفاهيم مشابهة.",
        "reaction_balancing": "تدربك هذه البطاقة على التفكير في موازنة المعادلات الكيميائية.",
        "safety_rule": "تذكرك هذه البطاقة بقاعدة أمان مخبرية مرتبطة بالمفهوم.",
        "image_based": "تساعدك هذه البطاقة على قراءة الأشكال والجداول من الكتاب.",
    }

    front = front_by_type[card_type]
    back = short_answer if card_type != "calculation" else f"ابدأ بتحديد المعطيات والقانون المناسب. النتيجة/الفكرة من المصدر: {short_answer}"
    if _is_generic_back(back):
        back = fallback_answer
    explanation = answer_text
    if _is_generic_back(explanation):
        explanation = fallback_answer
    hint = _hint_for_card(card_type, topic_title, lesson, explanation)
    technical_description = (
        f"{CARD_TYPE_LABELS[card_type]} card. Source: "
        f"{metadata.get('unit_title_ar') or 'وحدة غير محددة'} > "
        f"{metadata.get('lesson_title_ar')} > "
        f"{metadata.get('topic_title_ar') or 'كل موضوعات الدرس'}. "
        f"{page_label}. Generated from {'RAG chunk ' + str(chunk.id) if chunk else 'lesson metadata'}."
    )

    return {
        "unit_id": metadata["unit_id"],
        "chapter_id": metadata["chapter_id"],
        "lesson_id": metadata["lesson_id"],
        "topic_id": metadata["topic_id"],
        "card_type": card_type,
        "difficulty": difficulty,
        "front_ar": front,
        "back_ar": back,
        "front_text_ar": front,
        "back_text_ar": back,
        "hint_ar": hint,
        "description_ar": description_by_type[card_type],
        "technical_description": technical_description,
        "explanation_ar": explanation,
        "source_page_start": metadata["source_page_start"],
        "source_page_end": metadata["source_page_end"],
        "source_chunk_ids": metadata["source_chunk_ids"],
        "tags": [card_type, f"lesson:{lesson.id}", *( [f"topic:{topic.id}"] if topic else [] )],
        "metadata_json": metadata,
        "created_by": created_by,
    }


def _validate_card_payload(payload: dict) -> list[str]:
    errors: list[str] = []
    if not _clean_text(payload.get("front_ar")):
        errors.append("واجهة البطاقة فارغة")
    if not _clean_text(payload.get("back_ar")):
        errors.append("إجابة البطاقة فارغة")
    if _is_generic_back(payload.get("back_ar")):
        errors.append("إجابة البطاقة عامة وغير مفيدة")
    if not _clean_text(payload.get("hint_ar")):
        errors.append("تلميح البطاقة غير متوفر")
    if not _clean_text(payload.get("explanation_ar")):
        errors.append("شرح البطاقة غير متوفر")
    if not payload.get("lesson_id"):
        errors.append("لا يوجد درس مرتبط بالبطاقة")
    if not payload.get("card_type"):
        errors.append("نوع البطاقة غير محدد")
    if not _clean_text(payload.get("description_ar")):
        errors.append("وصف البطاقة غير متوفر")
    if not _clean_text(payload.get("technical_description")):
        errors.append("الوصف التقني غير متوفر")
    return errors


async def list_flashcards(db: AsyncSession, topic_id: int | None = None) -> list[Flashcard]:
    stmt = select(Flashcard)
    if topic_id is not None:
        stmt = stmt.where(Flashcard.topic_id == topic_id)
    result = await db.execute(stmt.order_by(Flashcard.id))
    return list(result.scalars().all())


async def create_flashcard(db: AsyncSession, data: dict) -> Flashcard:
    data.setdefault("front_text_ar", data.get("front_ar"))
    data.setdefault("back_text_ar", data.get("back_ar"))
    card = Flashcard(**data)
    db.add(card)
    await db.commit()
    await db.refresh(card)
    return card


async def _load_lessons_for_request(db: AsyncSession, request: FlashcardGenerateRequest) -> list[Lesson]:
    lesson_ids = list(dict.fromkeys(request.lesson_ids))
    if request.lesson_id and request.lesson_id not in lesson_ids:
        lesson_ids.append(request.lesson_id)

    if request.scope_type == "topic" and request.topic_ids:
        result = await db.execute(
            select(Lesson)
            .join(Lesson.topics)
            .where(Topic.id.in_(request.topic_ids))
            .options(
                selectinload(Lesson.topics),
                selectinload(Lesson.chapter).selectinload(Chapter.unit),
            )
            .order_by(Lesson.order, Lesson.id)
        )
        return list(dict.fromkeys(result.scalars().all()))

    if request.scope_type == "unit" and request.unit_ids:
        result = await db.execute(
            select(Lesson)
            .join(Lesson.chapter)
            .where(Chapter.unit_id.in_(request.unit_ids))
            .options(
                selectinload(Lesson.topics),
                selectinload(Lesson.chapter).selectinload(Chapter.unit),
            )
            .order_by(Chapter.order, Lesson.order, Lesson.id)
        )
        return list(result.scalars().all())

    if not lesson_ids and request.topic_id:
        result = await db.execute(
            select(Lesson)
            .join(Lesson.topics)
            .where(Topic.id == request.topic_id)
            .options(
                selectinload(Lesson.topics),
                selectinload(Lesson.chapter).selectinload(Chapter.unit),
            )
            .order_by(Lesson.order, Lesson.id)
        )
        lessons = list(result.scalars().all())
        if lessons:
            return lessons

    if not lesson_ids:
        raise HTTPException(status_code=422, detail="اختر درساً واحداً على الأقل")

    result = await db.execute(
        select(Lesson)
        .where(Lesson.id.in_(lesson_ids))
        .options(
            selectinload(Lesson.topics),
            selectinload(Lesson.chapter).selectinload(Chapter.unit),
        )
        .order_by(Lesson.order, Lesson.id)
    )
    lessons = list(result.scalars().all())
    if not lessons:
        raise HTTPException(status_code=404, detail="لم يتم العثور على الدروس المحددة")
    return lessons


async def _chunks_for_lesson(
    db: AsyncSession,
    lesson: Lesson,
    topic_ids: list[int],
    limit: int,
) -> list[RagChunk]:
    filters = [RagChunk.lesson_id == lesson.id]
    lesson_topic_ids = [topic.id for topic in lesson.topics]
    selected_topic_ids = [topic_id for topic_id in topic_ids if topic_id in lesson_topic_ids]
    if selected_topic_ids:
        filters.append(RagChunk.topic_id.in_(selected_topic_ids))
    result = await db.execute(
        select(RagChunk)
        .where(
            and_(*filters),
            RagChunk.content_type.in_(
                ("definition", "formula", "equation", "result", "note", "text", "experiment", "example")
            ),
            RagChunk.source_type.in_(("textbook", "solution_book")),
        )
        .order_by(RagChunk.page_number.asc().nulls_last(), RagChunk.chunk_index.asc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def generate_flashcard_deck(
    db: AsyncSession,
    user_id: int,
    request: FlashcardGenerateRequest,
) -> FlashcardDeck:
    card_types = [normalize_card_type(card_type) for card_type in request.card_types]
    card_types = [card_type for card_type, _ in dict.fromkeys((card_type, None) for card_type in card_types)]
    if not card_types:
        raise HTTPException(status_code=422, detail="اختر نوع بطاقة واحداً على الأقل")

    lessons = await _load_lessons_for_request(db, request)
    first_lesson = lessons[0]
    scope_id = request.scope_id
    if not scope_id and len(lessons) == 1:
        scope_id = str(first_lesson.id)
    title = request.title_ar or (
        f"بطاقات {first_lesson.title_ar}" if len(lessons) == 1 else f"بطاقات مراجعة {len(lessons)} دروس"
    )
    description = request.description_ar or (
        f"مجموعة بطاقات ذكية من الكتاب مرتبطة بـ {len(lessons)} درس، مع مصادر ووصف لكل بطاقة."
    )
    deck = FlashcardDeck(
        user_id=user_id,
        title_ar=title,
        description_ar=description,
        scope_type=request.scope_type,
        scope_id=scope_id,
        status="active",
        source="book_rag" if not request.source_text else "ai_generated",
    )
    db.add(deck)
    await db.flush()

    cards: list[Flashcard] = []
    validation_errors: list[str] = []
    for lesson in lessons:
        lesson_topics = [topic for topic in lesson.topics if not request.topic_ids or topic.id in request.topic_ids]
        if not lesson_topics:
            lesson_topics = list(lesson.topics) or [None]
        chunks = await _chunks_for_lesson(db, lesson, request.topic_ids, max(request.cards_per_lesson * 3, 6))
        if request.source_text and len(lessons) == 1:
            chunks = []
        source_items: list[tuple[Topic | None, RagChunk | None]] = []
        for index in range(max(request.cards_per_lesson, len(card_types))):
            topic = lesson_topics[index % len(lesson_topics)]
            chunk = chunks[index % len(chunks)] if chunks else None
            source_items.append((topic, chunk))

        for index in range(request.cards_per_lesson):
            card_type = card_types[index % len(card_types)]
            topic, chunk = source_items[index % len(source_items)]
            payload = _build_card_payload(
                lesson=lesson,
                topic=topic,
                chunk=chunk,
                card_type=card_type,
                difficulty=_difficulty_from_lesson(lesson, request.difficulty),
                created_by=request.created_by,
            )
            if request.source_text and len(lessons) == 1:
                source_back = _back_from_source_text(request.source_text)
                if _is_generic_back(source_back):
                    source_back = _fallback_answer_by_type(card_type, _topic_title(topic, lesson), lesson)
                payload["back_ar"] = source_back
                payload["back_text_ar"] = payload["back_ar"]
                payload["explanation_ar"] = payload["back_ar"]
                payload["hint_ar"] = _hint_for_card(card_type, _topic_title(topic, lesson), lesson, payload["back_ar"])
                payload["technical_description"] += " Generated from provided source_text."
            errors = _validate_card_payload(payload)
            if errors:
                validation_errors.extend(errors)
                continue
            cards.append(Flashcard(deck_id=deck.id, **payload))

    if not cards:
        await db.rollback()
        detail = "تعذر توليد البطاقات، حاول مرة أخرى"
        if validation_errors:
            detail = "؛ ".join(validation_errors[:4])
        raise HTTPException(status_code=422, detail=detail)

    db.add_all(cards)
    await db.flush()
    for card in cards:
        db.add(
            FlashcardProgress(
                user_id=user_id,
                flashcard_id=card.id,
                status="new",
                due_at=now_utc(),
                next_review_at=date.today(),
                ease_factor=2.5,
            )
        )
    await db.commit()
    await db.refresh(deck)
    return deck


def _back_from_source_text(source_text: str) -> str:
    snippets = [line.strip() for line in source_text.splitlines() if line.strip()]
    return _clean_text(" ".join(snippets), limit=700)


async def generate_flashcards(
    db: AsyncSession,
    request: FlashcardGenerateRequest,
    user_id: int | None = None,
) -> list[Flashcard]:
    """Legacy endpoint helper returning generated cards directly."""

    deck = await generate_flashcard_deck(db, user_id or 1, request)
    result = await db.execute(select(Flashcard).where(Flashcard.deck_id == deck.id).order_by(Flashcard.id))
    return list(result.scalars().all())


async def _progress_map(db: AsyncSession, user_id: int, card_ids: list[int]) -> dict[int, FlashcardProgress]:
    if not card_ids:
        return {}
    result = await db.execute(
        select(FlashcardProgress).where(
            FlashcardProgress.user_id == user_id,
            FlashcardProgress.flashcard_id.in_(card_ids),
        )
    )
    return {progress.flashcard_id: progress for progress in result.scalars().all()}


async def deck_stats(db: AsyncSession, user_id: int, deck_id: int | None = None) -> dict[str, int]:
    now = now_utc()
    today_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    stmt = (
        select(Flashcard.id, FlashcardProgress.status, FlashcardProgress.due_at)
        .outerjoin(
            FlashcardProgress,
            (FlashcardProgress.flashcard_id == Flashcard.id) & (FlashcardProgress.user_id == user_id),
        )
        .outerjoin(FlashcardDeck, FlashcardDeck.id == Flashcard.deck_id)
        .where(or_(FlashcardDeck.user_id == user_id, Flashcard.deck_id.is_(None)))
    )
    if deck_id is not None:
        stmt = stmt.where(Flashcard.deck_id == deck_id)
    result = await db.execute(stmt)
    rows = list(result.all())
    total = len(rows)
    statuses = Counter((row.status or "new") for row in rows)
    due_today = 0
    overdue = 0
    for _, status, due_at in rows:
        if status == "mastered":
            continue
        if due_at is None:
            due_today += 1
            continue
        if due_at <= now:
            due_today += 1
        if due_at < today_start:
            overdue += 1
    mastered = statuses.get("mastered", 0)
    return {
        "total_cards": total,
        "due_cards": due_today,
        "due_today": due_today,
        "new_cards": statuses.get("new", 0),
        "learning_cards": statuses.get("learning", 0) + statuses.get("review", 0),
        "mastered_cards": mastered,
        "overdue_cards": overdue,
        "mastery_percent": round((mastered / total) * 100) if total else 0,
    }


async def list_decks(db: AsyncSession, user_id: int) -> list[tuple[FlashcardDeck, dict[str, int]]]:
    result = await db.execute(
        select(FlashcardDeck)
        .where(FlashcardDeck.user_id == user_id, FlashcardDeck.status != "archived")
        .order_by(FlashcardDeck.updated_at.desc(), FlashcardDeck.id.desc())
    )
    decks = list(result.scalars().all())
    return [(deck, await deck_stats(db, user_id, deck.id)) for deck in decks]


async def get_deck(db: AsyncSession, user_id: int, deck_id: int) -> tuple[FlashcardDeck, list[tuple[Flashcard, FlashcardProgress | None]], dict[str, int]]:
    deck = await db.scalar(select(FlashcardDeck).where(FlashcardDeck.id == deck_id, FlashcardDeck.user_id == user_id))
    if deck is None:
        raise HTTPException(status_code=404, detail="لم يتم العثور على مجموعة البطاقات")
    result = await db.execute(select(Flashcard).where(Flashcard.deck_id == deck.id).order_by(Flashcard.id))
    cards = list(result.scalars().all())
    progress_by_card = await _progress_map(db, user_id, [card.id for card in cards])
    stats = await deck_stats(db, user_id, deck.id)
    return deck, [(card, progress_by_card.get(card.id)) for card in cards], stats


async def update_deck(db: AsyncSession, user_id: int, deck_id: int, data: dict) -> FlashcardDeck:
    deck = await db.scalar(select(FlashcardDeck).where(FlashcardDeck.id == deck_id, FlashcardDeck.user_id == user_id))
    if deck is None:
        raise HTTPException(status_code=404, detail="لم يتم العثور على مجموعة البطاقات")
    for key, value in data.items():
        if value is not None and hasattr(deck, key):
            setattr(deck, key, value)
    await db.commit()
    await db.refresh(deck)
    return deck


async def delete_deck(db: AsyncSession, user_id: int, deck_id: int) -> None:
    deck = await db.scalar(select(FlashcardDeck).where(FlashcardDeck.id == deck_id, FlashcardDeck.user_id == user_id))
    if deck is None:
        raise HTTPException(status_code=404, detail="لم يتم العثور على مجموعة البطاقات")
    await db.delete(deck)
    await db.commit()


async def update_card(db: AsyncSession, user_id: int, card_id: int, data: dict) -> Flashcard:
    card = await db.scalar(
        select(Flashcard)
        .outerjoin(FlashcardDeck, FlashcardDeck.id == Flashcard.deck_id)
        .where(Flashcard.id == card_id, or_(FlashcardDeck.user_id == user_id, Flashcard.deck_id.is_(None)))
    )
    if card is None:
        raise HTTPException(status_code=404, detail="لم يتم العثور على البطاقة")
    for key, value in data.items():
        if value is not None and hasattr(card, key):
            setattr(card, key, value)
    if data.get("front_text_ar"):
        card.front_ar = data["front_text_ar"]
    if data.get("back_text_ar"):
        card.back_ar = data["back_text_ar"]
    await db.commit()
    await db.refresh(card)
    return card


async def due_flashcards(
    db: AsyncSession,
    user_id: int,
    limit: int = 30,
    deck_id: int | None = None,
) -> list[tuple[Flashcard, FlashcardProgress | None]]:
    current = now_utc()
    stmt = (
        select(Flashcard, FlashcardProgress)
        .outerjoin(
            FlashcardProgress,
            (FlashcardProgress.flashcard_id == Flashcard.id) & (FlashcardProgress.user_id == user_id),
        )
        .outerjoin(FlashcardDeck, FlashcardDeck.id == Flashcard.deck_id)
        .where(
            or_(FlashcardDeck.user_id == user_id, Flashcard.deck_id.is_(None)),
            or_(
                FlashcardProgress.id.is_(None),
                and_(
                    FlashcardProgress.status.notin_(("mastered", "suspended")),
                    or_(
                        FlashcardProgress.status == "new",
                        FlashcardProgress.due_at.is_(None),
                        FlashcardProgress.due_at <= current,
                        FlashcardProgress.next_review_at <= date.today(),
                    ),
                ),
            ),
        )
        .order_by(FlashcardProgress.due_at.asc().nulls_first(), Flashcard.id.asc())
        .limit(limit)
    )
    if deck_id is not None:
        stmt = stmt.where(Flashcard.deck_id == deck_id)
    result = await db.execute(stmt)
    return list(result.all())


async def review_flashcard(db: AsyncSession, user_id: int, flashcard_id: int, rating: str) -> FlashcardProgress:
    card = await db.scalar(
        select(Flashcard)
        .outerjoin(FlashcardDeck, FlashcardDeck.id == Flashcard.deck_id)
        .where(Flashcard.id == flashcard_id, or_(FlashcardDeck.user_id == user_id, Flashcard.deck_id.is_(None)))
    )
    if card is None:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    result = await db.execute(
        select(FlashcardProgress).where(
            FlashcardProgress.user_id == user_id,
            FlashcardProgress.flashcard_id == flashcard_id,
        )
    )
    progress = result.scalar_one_or_none()
    if progress is None:
        progress = FlashcardProgress(user_id=user_id, flashcard_id=flashcard_id, status="new")
        db.add(progress)

    reviewed_at = now_utc()
    schedule = schedule_review_rating(
        rating,
        previous_interval_days=progress.interval_days,
        previous_ease_factor=progress.ease_factor,
        previous_repetitions=progress.repetitions or progress.review_count,
        previous_lapses=progress.lapses,
        reviewed_at=reviewed_at,
    )
    progress.review_count += 1
    progress.mastered = schedule.status == "mastered"
    progress.status = schedule.status
    progress.interval_days = schedule.interval_days
    progress.ease_factor = schedule.ease_factor
    progress.repetitions = schedule.repetitions
    progress.lapses = schedule.lapses
    progress.due_at = schedule.due_at
    progress.next_review_at = schedule.due_at.date()
    progress.last_reviewed = reviewed_at
    progress.last_reviewed_at = reviewed_at
    await db.commit()
    await db.refresh(progress)
    return progress


async def progress_summary(db: AsyncSession, user_id: int) -> dict[str, int]:
    stats = await deck_stats(db, user_id)
    return {
        "total_cards": stats["total_cards"],
        "due_today": stats["due_today"],
        "new_cards": stats["new_cards"],
        "learning_cards": stats["learning_cards"],
        "mastered_cards": stats["mastered_cards"],
        "overdue_cards": stats["overdue_cards"],
        "mastery_percent": stats["mastery_percent"],
    }


async def create_review_session(
    db: AsyncSession,
    user_id: int,
    deck_id: int | None,
    limit: int,
) -> dict:
    rows = await due_flashcards(db, user_id, limit=limit, deck_id=deck_id)
    return {
        "session_id": f"review_{uuid4().hex[:12]}",
        "deck_id": deck_id,
        "rows": rows,
    }
