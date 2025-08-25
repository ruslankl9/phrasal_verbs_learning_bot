from __future__ import annotations

import json
import html
import re
from typing import Iterable


def escape_html(s: str) -> str:
    """Escape text for safe HTML rendering in Telegram."""
    return html.escape(s, quote=True)


def normalize_tag(s: str) -> str:
    """Normalize a tag to lowercase with non-word chars replaced by underscores."""
    tag = re.sub(r"[^a-z0-9_]+", "_", s.lower()).strip("_")
    return tag


def html_card_message(
    phrasal: str,
    meaning_en: str,
    examples_json: str,
    *,
    is_new: bool,
    tags: list[str],
) -> str:
    """Compose the HTML message body for a card.

    - Optional top-line badge "🆕" when is_new.
    - Bold phrasal, italic meaning.
    - Examples list with "- " bullets.
    - Tags as space-separated hashtags (#tag) built from provided tags.
    """
    examples: list[str] = []
    try:
        loaded = json.loads(examples_json)
        if isinstance(loaded, list):
            examples = [str(x) for x in loaded]
    except Exception:
        examples = []

    badge = "🆕\n" if is_new else ""
    tags_norm = [normalize_tag(t) for t in tags]
    tags_norm = [t for t in tags_norm if t]
    tags_line = "Tags: " + " ".join(f"#{t}" for t in tags_norm) if tags_norm else "Tags:"

    parts: list[str] = []
    if badge:
        parts.append(badge.rstrip("\n"))
    parts.append(f"<b>{escape_html(phrasal)}</b>")
    parts.append("")
    parts.append(f"<i>{escape_html(meaning_en)}</i>")
    parts.append("Examples:")
    for ex in examples:
        parts.append(f"- {escape_html(ex)}")
    parts.append("")
    parts.append(tags_line)
    return "\n".join(parts)


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
