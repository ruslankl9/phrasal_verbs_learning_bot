from __future__ import annotations

import random

from srsbot.formatters import format_quiz_summary_html
from srsbot.handlers.quiz import build_quiz_items


def test_quiz_flow_recording_and_summary_formatting():
    cards = [
        (1, "look up", "to search for information"),
        (2, "run into", "to meet by chance"),
        (3, "get over", "to recover from"),
        (4, "put off", "to postpone"),
    ]
    meanings = [c[2] for c in cards] + ["to remove", "to add", "to discard"]
    random.seed(7)
    items = build_quiz_items(cards, meanings, limit=4)

    # Simulate answering: correct for first two, wrong for last two
    for i, it in enumerate(items):
        ci = it["correct_index"]
        if i < 2:
            it["user_choice"] = ci
        else:
            # pick a wrong index (0..len-1 except ci)
            for alt in range(len(it["options"])):
                if alt != ci:
                    it["user_choice"] = alt
                    break

    html = format_quiz_summary_html(items)
    # Expect 2 correct out of 4
    assert "Correct: 2 / 4" in html
    # For a wrong question, shows ❌ chosen option and Correct answer line
    assert "❌" in html
    assert "(Correct answer:" in html
