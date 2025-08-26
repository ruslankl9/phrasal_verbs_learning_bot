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


# ---- Quiz formatters -------------------------------------------------------

def format_quiz_question_html(phrasal: str, options: list[str]) -> str:
    """Render a single quiz question in HTML.

    Displays the phrasal verb in bold, a prompt line, and four numbered options.
    If fewer than four options are provided, renders only available ones.
    """
    opts_lines: list[str] = []
    for i, opt in enumerate(options[:4], start=1):
        opts_lines.append(f"{i}) {escape_html(opt)}")
    parts = [
        f"<b>{escape_html(phrasal)}</b>",
        "",
        "Choose the correct meaning:",
        *opts_lines,
    ]
    return "\n".join(parts)


def format_quiz_summary_html(items: list[dict]) -> str:
    """Render quiz summary with overall score and per-question breakdown.

    Each item dict is expected to contain:
    - phrasal: str
    - options: list[str]
    - correct_index: int
    - user_choice: int | None
    """
    total = len(items)
    correct = sum(1 for it in items if it.get("user_choice") == it.get("correct_index"))
    lines: list[str] = [
        "Quiz summary",
        f"Correct: {correct} / {total}",
    ]
    for idx, it in enumerate(items, start=1):
        phrasal = str(it.get("phrasal", ""))
        opts: list[str] = [str(x) for x in it.get("options", [])]
        ci = int(it.get("correct_index", 0))
        uc = it.get("user_choice")
        correct_text = opts[ci] if 0 <= ci < len(opts) else ""
        lines.append("")
        lines.append(f"{idx}) <b>{escape_html(phrasal)}</b>")
        if uc == ci:
            lines.append(f"✅ <b>{escape_html(correct_text)}</b>")
        else:
            if uc is not None and 0 <= uc < len(opts):
                lines.append(f"❌ {escape_html(opts[uc])}")
            else:
                lines.append("❌")
            lines.append(f"(Correct answer: <b>{escape_html(correct_text)}</b>)")
    return "\n".join(lines)
