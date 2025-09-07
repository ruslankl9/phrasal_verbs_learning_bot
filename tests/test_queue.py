from __future__ import annotations

from datetime import date

from srsbot.queue import Item, build_daily_queue_view, rebalance_overdue


def test_build_daily_queue_view_order():
    today = date(2024, 1, 1)
    learning = [Item(1, "learning"), Item(2, "learning")]
    reviews = [Item(3, "review", today), Item(4, "review", today)]
    new = [Item(5, "new"), Item(6, "new")]
    items = build_daily_queue_view(learning, reviews, new, 1, 1)
    assert sorted([i.card_id for i in items]) == [1, 2, 3, 5]


def test_rebalance_overdue():
    today = date(2024, 1, 1)
    overdue = [Item(i, "review", today) for i in range(10)]
    serve, res = rebalance_overdue(overdue, limit=4, today=today, days=2)
    assert [i.card_id for i in serve] == [0, 1, 2, 3]
    # Ensure rescheduled across next two days
    days = {d for _, d in res}
    assert days == {date(2024, 1, 2), date(2024, 1, 3)}

