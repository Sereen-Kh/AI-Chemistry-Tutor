"""Flashcard API routes."""

from datetime import date
from inspect import signature

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id, require_admin
from app.database import get_async_db
from app.models.flashcard import Flashcard, FlashcardDeck, FlashcardProgress
from app.schemas.flashcards import (
    FlashcardCreateRequest,
    FlashcardDeckResponse,
    FlashcardDeckUpdateRequest,
    FlashcardDueResponse,
    FlashcardGenerateRequest,
    FlashcardProgressResponse,
    FlashcardProgressSummaryResponse,
    FlashcardResponse,
    FlashcardReviewRequest,
    FlashcardReviewResponse,
    FlashcardReviewSessionCreateRequest,
    FlashcardReviewSessionResponse,
    FlashcardReviewStateResponse,
    FlashcardUpdateRequest,
)
from app.services import flashcard_service

router = APIRouter(prefix="/flashcards", tags=["flashcards"])


def _review_response(card_id: int, progress: FlashcardProgress | None) -> FlashcardReviewStateResponse:
    if progress is None:
        return FlashcardReviewStateResponse(flashcard_id=card_id)
    return FlashcardReviewStateResponse(
        id=progress.id,
        user_id=progress.user_id,
        flashcard_id=progress.flashcard_id,
        status=progress.status or ("mastered" if progress.mastered else "new"),
        due_at=progress.due_at,
        last_reviewed_at=progress.last_reviewed_at or progress.last_reviewed,
        repetitions=progress.repetitions or progress.review_count,
        lapses=progress.lapses,
        ease_factor=progress.ease_factor,
        interval_days=progress.interval_days,
        mastered=progress.mastered,
        review_count=progress.review_count,
        next_review_at=progress.next_review_at,
        last_reviewed=progress.last_reviewed,
        created_at=getattr(progress, "created_at", None),
        updated_at=getattr(progress, "updated_at", None),
    )


def _card_response(card: Flashcard, progress: FlashcardProgress | None = None) -> FlashcardResponse:
    return FlashcardResponse(
        id=card.id,
        deck_id=getattr(card, "deck_id", None),
        unit_id=getattr(card, "unit_id", None),
        chapter_id=getattr(card, "chapter_id", None),
        lesson_id=getattr(card, "lesson_id", None),
        topic_id=getattr(card, "topic_id", None),
        card_type=getattr(card, "card_type", "term_definition"),
        difficulty=getattr(card, "difficulty", "medium"),
        front_ar=card.front_ar,
        back_ar=card.back_ar,
        front_text_ar=getattr(card, "front_text_ar", None) or card.front_ar,
        back_text_ar=getattr(card, "back_text_ar", None) or card.back_ar,
        hint_ar=getattr(card, "hint_ar", None),
        description_ar=getattr(card, "description_ar", "") or "تختبر هذه البطاقة فهماً كيميائياً من الدرس.",
        technical_description=getattr(card, "technical_description", "") or "",
        explanation_ar=getattr(card, "explanation_ar", "") or "",
        source_page_start=getattr(card, "source_page_start", None),
        source_page_end=getattr(card, "source_page_end", None),
        source_chunk_ids=getattr(card, "source_chunk_ids", None),
        tags=getattr(card, "tags", None),
        metadata_json=getattr(card, "metadata_json", None),
        created_by=card.created_by,
        created_at=card.created_at,
        updated_at=card.updated_at,
        review=_review_response(card.id, progress),
    )


def _deck_response(
    deck: FlashcardDeck,
    stats: dict[str, int],
    rows: list[tuple[Flashcard, FlashcardProgress | None]] | None = None,
) -> FlashcardDeckResponse:
    return FlashcardDeckResponse(
        id=deck.id,
        user_id=deck.user_id,
        title_ar=deck.title_ar,
        description_ar=deck.description_ar,
        scope_type=deck.scope_type,
        scope_id=deck.scope_id,
        status=deck.status,
        source=deck.source,
        total_cards=stats.get("total_cards", 0),
        due_cards=stats.get("due_cards", stats.get("due_today", 0)),
        new_cards=stats.get("new_cards", 0),
        learning_cards=stats.get("learning_cards", 0),
        mastered_cards=stats.get("mastered_cards", 0),
        overdue_cards=stats.get("overdue_cards", 0),
        mastery_percent=stats.get("mastery_percent", 0),
        cards=[_card_response(card, progress) for card, progress in (rows or [])],
        created_at=deck.created_at,
        updated_at=deck.updated_at,
    )


@router.get("", response_model=list[FlashcardResponse])
async def list_flashcards(topic_id: int | None = Query(default=None), db: AsyncSession = Depends(get_async_db)):
    return [_card_response(card) for card in await flashcard_service.list_flashcards(db, topic_id=topic_id)]


@router.post("", response_model=FlashcardResponse, status_code=201)
async def create_flashcard(
    request: FlashcardCreateRequest,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
):
    return _card_response(await flashcard_service.create_flashcard(db, request.model_dump()))


@router.get("/decks", response_model=list[FlashcardDeckResponse])
async def list_decks(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return [_deck_response(deck, stats) for deck, stats in await flashcard_service.list_decks(db, user_id)]


@router.post("/decks/generate", response_model=FlashcardDeckResponse, status_code=201)
async def generate_deck(
    request: FlashcardGenerateRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    if request.allow_needs_review or request.admin_review_approved:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "ADMIN_APPROVAL_REQUIRED_FOR_NEEDS_REVIEW_FLASHCARDS",
                "message": "توليد البطاقات من محتوى يحتاج مراجعة يتطلب موافقة مدير.",
            },
        )
    deck = await flashcard_service.generate_flashcard_deck(db, user_id, request)
    deck, rows, stats = await flashcard_service.get_deck(db, user_id, deck.id)
    return _deck_response(deck, stats, rows)


@router.post("/generate", response_model=list[FlashcardResponse], status_code=201)
async def generate_flashcards(
    request: FlashcardGenerateRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    if request.allow_needs_review or request.admin_review_approved:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "ADMIN_APPROVAL_REQUIRED_FOR_NEEDS_REVIEW_FLASHCARDS",
                "message": "توليد البطاقات من محتوى يحتاج مراجعة يتطلب موافقة مدير.",
            },
        )
    generate = flashcard_service.generate_flashcards
    if "user_id" in signature(generate).parameters:
        cards = await generate(db, request, user_id=user_id)
    else:
        cards = await generate(db, request)
    return [_card_response(card) for card in cards]


@router.get("/decks/{deck_id}", response_model=FlashcardDeckResponse)
async def get_deck(
    deck_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    deck, rows, stats = await flashcard_service.get_deck(db, user_id, deck_id)
    return _deck_response(deck, stats, rows)


@router.patch("/decks/{deck_id}", response_model=FlashcardDeckResponse)
async def update_deck(
    deck_id: int,
    request: FlashcardDeckUpdateRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    deck = await flashcard_service.update_deck(db, user_id, deck_id, request.model_dump(exclude_unset=True))
    stats = await flashcard_service.deck_stats(db, user_id, deck.id)
    return _deck_response(deck, stats)


@router.delete("/decks/{deck_id}", status_code=204)
async def delete_deck(
    deck_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    await flashcard_service.delete_deck(db, user_id, deck_id)
    return Response(status_code=204)


@router.get("/due", response_model=list[FlashcardDueResponse])
async def due_flashcards(
    limit: int = Query(default=30, ge=1, le=100),
    deck_id: int | None = Query(default=None),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    rows = (
        await flashcard_service.due_flashcards(db, user_id, limit=limit, deck_id=deck_id)
        if deck_id is not None
        else await flashcard_service.due_flashcards(db, user_id, limit)
    )
    return [
        FlashcardDueResponse(
            **_card_response(card, progress).model_dump(),
            mastered=progress.mastered if progress else False,
            review_count=progress.review_count if progress else 0,
            ease_factor=progress.ease_factor if progress else 2.5,
            interval_days=progress.interval_days if progress else 0,
            next_review_at=progress.next_review_at if progress else date.today(),
            last_reviewed=progress.last_reviewed if progress else None,
        )
        for card, progress in rows
    ]


@router.get("/progress", response_model=FlashcardProgressSummaryResponse)
async def progress_summary(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return FlashcardProgressSummaryResponse(**await flashcard_service.progress_summary(db, user_id))


@router.post("/review-sessions", response_model=FlashcardReviewSessionResponse, status_code=201)
async def create_review_session(
    request: FlashcardReviewSessionCreateRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    session = await flashcard_service.create_review_session(db, user_id, request.deck_id, request.limit)
    return FlashcardReviewSessionResponse(
        session_id=session["session_id"],
        deck_id=session["deck_id"],
        total_cards=len(session["rows"]),
        cards=[_card_response(card, progress) for card, progress in session["rows"]],
    )


@router.post("/{flashcard_id}/review", response_model=FlashcardReviewResponse)
async def review_flashcard(
    flashcard_id: int,
    request: FlashcardReviewRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    rating = request.rating or flashcard_service.quality_to_rating(request.quality)
    progress = await flashcard_service.review_flashcard(db, user_id, flashcard_id, rating)
    return FlashcardReviewResponse(
        card_id=flashcard_id,
        new_due_at=progress.due_at,
        status=progress.status,
        interval_days=progress.interval_days,
        ease_factor=progress.ease_factor,
        repetitions=progress.repetitions,
        lapses=progress.lapses,
    )


@router.patch("/{flashcard_id}", response_model=FlashcardResponse)
async def update_card(
    flashcard_id: int,
    request: FlashcardUpdateRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    card = await flashcard_service.update_card(db, user_id, flashcard_id, request.model_dump(exclude_unset=True))
    return _card_response(card)


@router.get("/{flashcard_id}", response_model=FlashcardResponse)
async def get_card(
    flashcard_id: int,
    _user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    card = await db.get(Flashcard, flashcard_id)
    if card is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="لم يتم العثور على البطاقة")
    return _card_response(card)
