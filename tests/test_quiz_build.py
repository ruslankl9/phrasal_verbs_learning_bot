from __future__ import annotations

import random

from srsbot.handlers.quiz import build_quiz_items


def test_build_quiz_items_shapes_and_correct_index():
    # Prepare sample data
    cards = [
        (1, "look up", "to search for information"),
        (2, "run into", "to meet by chance"),
        (3, "get over", "to recover from"),
        (4, "put off", "to postpone"),
        (5, "bring up", "to mention"),
    ]
    meanings = [c[2] for c in cards] + [
        "to discard",
        "to acquire",
        "to remove",
        "to add",
    ]
    random.seed(42)
    items = build_quiz_items(cards, meanings, limit=4)
    assert len(items) <= 4
    for it in items:
        options = it["options"]
        correct = it["correct_meaning"]
        # At least 2 options, up to 4
        assert 2 <= len(options) <= 4
        # Correct should be present
        assert correct in options
        # Correct index should align
        assert options[it["correct_index"]] == correct
        # Distractors should be distinct and not include the correct one
        opts_wo_correct = [o for o in options if o != correct]
        assert len(opts_wo_correct) == len(set(opts_wo_correct))
