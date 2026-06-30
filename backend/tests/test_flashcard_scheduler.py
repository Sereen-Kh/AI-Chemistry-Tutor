from datetime import datetime, timezone

from app.services.flashcard_service import schedule_review_rating


def test_review_scheduler_again_requeues_soon_and_counts_lapse():
    reviewed_at = datetime(2026, 6, 28, 10, 0, tzinfo=timezone.utc)

    schedule = schedule_review_rating(
        "again",
        previous_interval_days=3,
        previous_ease_factor=2.5,
        previous_repetitions=2,
        previous_lapses=1,
        reviewed_at=reviewed_at,
    )

    assert schedule.status == "learning"
    assert schedule.interval_days == 0
    assert schedule.lapses == 2
    assert schedule.repetitions == 0
    assert schedule.due_at > reviewed_at


def test_review_scheduler_good_moves_card_to_review():
    reviewed_at = datetime(2026, 6, 28, 10, 0, tzinfo=timezone.utc)

    schedule = schedule_review_rating(
        "good",
        previous_interval_days=1,
        previous_ease_factor=2.5,
        previous_repetitions=1,
        reviewed_at=reviewed_at,
    )

    assert schedule.status == "review"
    assert schedule.interval_days == 3
    assert schedule.repetitions == 2
    assert schedule.due_at.date().isoformat() == "2026-07-01"


def test_review_scheduler_easy_can_master_card():
    reviewed_at = datetime(2026, 6, 28, 10, 0, tzinfo=timezone.utc)

    schedule = schedule_review_rating(
        "easy",
        previous_interval_days=4,
        previous_ease_factor=2.5,
        previous_repetitions=1,
        reviewed_at=reviewed_at,
    )

    assert schedule.status == "mastered"
    assert schedule.interval_days > 4
    assert schedule.ease_factor > 2.5
