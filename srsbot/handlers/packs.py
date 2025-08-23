from __future__ import annotations

from collections import defaultdict
from typing import Dict, Set

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from srsbot.db import get_db


router = Router()


async def _load_pack_counts() -> tuple[Dict[str, int], int]:
    """Return (per-tag counts of unique phrasals, total unique phrasals)."""
    async with get_db() as db:
        cur = await db.execute("SELECT phrasal, tags FROM cards")
        rows = await cur.fetchall()

    by_tag: Dict[str, Set[str]] = defaultdict(set)
    all_phrasals: Set[str] = set()
    for r in rows:
        phrasal = str(r[0])
        all_phrasals.add(phrasal)
        tags_raw = (r[1] or "")
        for t in (x.strip().lower() for x in tags_raw.split(",") if x.strip()):
            by_tag[t].add(phrasal)

    counts = {t: len(s) for t, s in by_tag.items()}
    return counts, len(all_phrasals)


def _packs_keyboard(tags: list[str], counts: dict[str, int], total: int) -> InlineKeyboardMarkup:
    # Each button sets a single pack; include an "All" button
    buttons = []
    # Add an "All" option first
    buttons.append(
        [
            InlineKeyboardButton(text=f"All ({total})", callback_data="setpack:*")
        ]
    )
    # Then one row per tag
    for t in tags:
        n = counts.get(t, 0)
        buttons.append(
            [InlineKeyboardButton(text=f"{t} ({n})", callback_data=f"setpack:{t}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("packs"))
async def cmd_packs(message: Message) -> None:
    assert message.from_user
    user_id = message.from_user.id

    counts, total = await _load_pack_counts()
    if not counts:
        await message.answer(
            "No packs found. Seed cards first (scripts/seed_cards.py)."
        )
        return

    # Current selection
    async with get_db() as db:
        cur = await db.execute(
            "SELECT pack_tags FROM user_config WHERE user_id=?", (user_id,)
        )
        row = await cur.fetchone()
    current = (row[0] if row else "daily") or "All"

    # Sort tags alphabetically for predictable display
    tags_sorted = sorted(counts.keys())

    lines = [
        "Available packs (unique words):",
    ]
    for t in tags_sorted:
        lines.append(f"- {t}: {counts[t]} words")
    lines.append("")
    lines.append(f"Current pack filter: {current}")
    lines.append("Tap a pack below to set it. For multiple, use /pack tag1,tag2.")

    await message.answer(
        "\n".join(lines),
        reply_markup=_packs_keyboard(tags_sorted, counts, total),
    )


@router.callback_query(F.data.startswith("setpack:"))
async def on_setpack(cb: CallbackQuery) -> None:
    assert cb.from_user and cb.data
    user_id = cb.from_user.id
    _, payload = cb.data.split(":", 1)
    new_tags = "" if payload == "*" else payload
    async with get_db() as db:
        await db.execute(
            "UPDATE user_config SET pack_tags=? WHERE user_id=?", (new_tags, user_id)
        )
        await db.commit()
    label = "All" if new_tags == "" else new_tags
    await cb.answer()
    await cb.message.answer(f"New card pack set to: {label}")

