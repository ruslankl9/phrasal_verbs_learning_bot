from __future__ import annotations

import json
from typing import Iterable


def render_card(phrasal: str, meaning_en: str, examples_json: str) -> str:
    examples: list[str] = []
    try:
        examples = list(json.loads(examples_json))
    except Exception:
        pass
    lines = [phrasal, f"— {meaning_en}"]
    for i, ex in enumerate(examples[:3], start=1):
        lines.append(f"Ex{i}: {ex}")
    return "\n".join(lines)


def format_round_complete(
    good: int,
    again: int,
    remaining_learning: int,
    remaining_reviews: int,
    remaining_new: int,
) -> str:
    lines = [
        "✅ Round complete!",
        f"Done this round: {good + again} answers (Good: {good}, Again: {again}).",
        f"Remaining today: {remaining_learning} learning • {remaining_reviews} reviews due • {remaining_new} new available",
    ]
    return "\n".join(lines)


def format_session_finished(
    good_total: int,
    again_total: int,
    learned_today: int,
    reviews_done: int,
) -> str:
    lines = [
        "🎯 Session finished.",
        f"Today: Good {good_total} / Again {again_total} • New learned: {learned_today} • Reviews done: {reviews_done}",
        "See you tomorrow!",
    ]
    return "\n".join(lines)
