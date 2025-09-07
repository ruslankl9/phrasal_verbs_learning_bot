from __future__ import annotations

import json
import html
import re
from typing import Iterable
import re


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


def build_card_prompt_text(
    phrasal: str,
    meaning_en: str,
    examples_json: str,
    *,
    tags: list[str] | None = None,
) -> str:
    """Build a concise, human-readable text for Explain prompt.

    Includes phrasal, meaning, and examples in simple HTML-compatible text.
    """
    examples: list[str] = []
    try:
        loaded = json.loads(examples_json)
        if isinstance(loaded, list):
            examples = [str(x) for x in loaded]
    except Exception:
        examples = []

    parts: list[str] = []
    parts.append(f"<b>{escape_html(phrasal)}</b>")
    parts.append(f"<i>{escape_html(meaning_en)}</i>")
    if examples:
        parts.append("Examples:")
        for ex in examples:
            parts.append(f"- {escape_html(ex)}")
    if tags:
        tags_norm = [normalize_tag(t) for t in tags]
        tags_norm = [t for t in tags_norm if t]
        if tags_norm:
            parts.append("Tags: " + " ".join(f"#{t}" for t in tags_norm))
    return "\n".join(parts)


def format_explain_loading_html() -> str:
    return "\n".join(
        [
            "<b>Explain</b>",
            "",
            "⏳ Loading an explanation... Please wait a moment.",
        ]
    )


def format_explain_error_html() -> str:
    return "\n".join(
        [
            "<b>Explain</b>",
            "",
            "❌ Sorry, we couldn’t load the explanation this time.",
            "Please try again later.",
        ]
    )


# ---- Markdown → Telegram HTML ---------------------------------------------

_CODE_BLOCK_RE = re.compile(r"```(\w+)?\n([\s\S]*?)\n```", re.MULTILINE)
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_STAR_RE = re.compile(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)")
_ITALIC_UNDER_RE = re.compile(r"_(.+?)_")
_STRIKE_RE = re.compile(r"~~(.+?)~~")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def markdown_to_html_telegram(md: str) -> str:
    """Convert a subset of Markdown to Telegram-compatible HTML.

    Supported:
    - Headings (# ..) → bold lines
    - Bold **text**
    - Italic *text* and _text_
    - Strike ~~text~~
    - Inline code `code`
    - Code blocks ```lang\ncode\n```
    - Links [text](url)
    Other content is preserved as text; groups are HTML-escaped.
    """
    if not md:
        return ""

    text = md.replace("\r\n", "\n").replace("\r", "\n")

    # Code blocks: replace with placeholders
    codeblocks: list[str] = []

    def _sub_codeblock(m: re.Match[str]) -> str:
        code = m.group(2)
        html_code = f"<pre><code>{escape_html(code)}</code></pre>"
        codeblocks.append(html_code)
        return f"{{CODEBLOCK_{len(codeblocks)-1}}}"

    text = _CODE_BLOCK_RE.sub(_sub_codeblock, text)

    # Inline code: replace with placeholders
    inline_codes: list[str] = []

    def _sub_inline_code(m: re.Match[str]) -> str:
        c = m.group(1)
        html_code = f"<code>{escape_html(c)}</code>"
        inline_codes.append(html_code)
        return f"{{CODE_{len(inline_codes)-1}}}"

    text = _INLINE_CODE_RE.sub(_sub_inline_code, text)

    # Links
    def _sub_link(m: re.Match[str]) -> str:
        label = escape_html(m.group(1))
        url = escape_html(m.group(2))
        return f"<a href=\"{url}\">{label}</a>"

    text = _LINK_RE.sub(_sub_link, text)

    # Headings → bold
    def _sub_heading(m: re.Match[str]) -> str:
        content = m.group(2).strip()
        return f"<b>{escape_html(content)}</b>"

    text = _HEADING_RE.sub(_sub_heading, text)

    # Bold, then italics, strike
    text = _BOLD_RE.sub(lambda m: f"<b>{escape_html(m.group(1))}</b>", text)
    text = _ITALIC_STAR_RE.sub(lambda m: f"<i>{escape_html(m.group(1))}</i>", text)
    text = _ITALIC_UNDER_RE.sub(lambda m: f"<i>{escape_html(m.group(1))}</i>", text)
    text = _STRIKE_RE.sub(lambda m: f"<s>{escape_html(m.group(1))}</s>", text)

    # Restore inline code and code blocks
    for i, html_snippet in enumerate(inline_codes):
        text = text.replace(f"{{CODE_{i}}}", html_snippet)
    for i, html_snippet in enumerate(codeblocks):
        text = text.replace(f"{{CODEBLOCK_{i}}}", html_snippet)

    return text


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
