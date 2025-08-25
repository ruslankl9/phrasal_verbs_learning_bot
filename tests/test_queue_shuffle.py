from __future__ import annotations

import random

from srsbot.queue import build_daily_queue_view, Item


def test_bucket_shuffle_order() -> None:
    random.seed(123)
    learning = [Item(i, "learning") for i in range(1, 5)]
    reviews = [Item(i, "review") for i in range(100, 106)]
    new = [Item(i, "new") for i in range(200, 206)]
    out = build_daily_queue_view(learning, reviews, new, review_limit_per_day=6, daily_new_target=6)
    # Check sizes
    assert len(out) == len(learning) + 6 + 6
    # Check that bucket membership preserved
    l_ids = {it.card_id for it in learning}
    r_ids = {it.card_id for it in reviews}
    n_ids = {it.card_id for it in new}
    first = out[: len(learning)]
    mid = out[len(learning) : len(learning) + 6]
    last = out[len(learning) + 6 :]
    assert all(it.card_id in l_ids for it in first)
    assert all(it.card_id in r_ids for it in mid)
    assert all(it.card_id in n_ids for it in last)
    # Check that within-bucket order is not strictly original order most of the time
    assert [it.card_id for it in first] != [1, 2, 3, 4]
    assert [it.card_id for it in mid] != [100, 101, 102, 103, 104, 105]

