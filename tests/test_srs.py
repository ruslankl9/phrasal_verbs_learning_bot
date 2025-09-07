from __future__ import annotations

from datetime import date, timedelta

from srsbot.models import Progress
from srsbot.srs import next_due_for_box, on_answer


def make_progress(state: str = "learning", box: int = 0) -> Progress:
    return Progress(
        user_id=1,
        card_id=1,
        state=state,  # type: ignore[arg-type]
        box=box,
        due_at=None,
        lapses=0,
        learning_good_count=0,
        last_answer=None,
        last_seen_at=None,
    )


def test_next_due_for_box_jitter():
    base = date(2024, 1, 1)
    d = next_due_for_box(3, base)
    assert d >= base + timedelta(days=1)


def test_learning_again_requeues():
    p = make_progress("learning", 0)
    res = on_answer(p, "again", date(2024, 1, 1), k=3)
    # Current behavior: do not requeue on 'again' in learning
    assert res.requeue_after is None
    assert p.learning_good_count == 0


def test_learning_promotes_after_two_good():
    p = make_progress("learning", 0)
    today = date(2024, 1, 1)
    res1 = on_answer(p, "good", today, k=3)
    assert res1.requeue_after == 3
    res2 = on_answer(p, "good", today, k=3)
    assert res2.requeue_after is None
    assert p.state == "review"
    assert p.box == 1
    assert p.due_at == today + timedelta(days=1)


def test_review_good_bumps_box():
    p = make_progress("review", 2)
    today = date(2024, 1, 1)
    res = on_answer(p, "good", today, k=3)
    assert p.box == 3
    assert res.requeue_after is None
    assert p.due_at and p.due_at >= today + timedelta(days=1)


def test_review_again_to_learning():
    p = make_progress("review", 2)
    res = on_answer(p, "again", date(2024, 1, 1), k=2)
    assert p.state == "learning"
    assert p.box == 0
    assert p.lapses == 1
    # Current behavior: do not requeue on 'again' from review
    assert res.requeue_after is None
