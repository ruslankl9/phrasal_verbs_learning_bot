from __future__ import annotations

from srsbot.content import NewCard, select_new_cards


def test_select_new_cards_tags_and_uniqueness():
    candidates = [
        NewCard(1, "bring up", "bring_up__mention", ["work", "meetings"]),
        NewCard(2, "bring up", "bring_up__raise_child", ["daily"]),
        NewCard(3, "get over", "get_over__recover", ["daily", "health"]),
        NewCard(4, "check in", "check_in__register", ["travel"]),
    ]

    picked = select_new_cards(candidates, ["work", "travel"], limit=3)
    # Should pick at most one sense of "bring up" and include travel/work only
    assert {c.id for c in picked}.issubset({1, 4})
    assert len(picked) <= 2

