from __future__ import annotations

from collections import defaultdict
from typing import Dict, Set

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from srsbot.db import get_db
from srsbot.keyboards import kb_packs
from srsbot.ui import SCREEN_PACKS, show_screen


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


def _render_packs_text(current: set[str]) -> str:
    if not current:
        return "<b>Packs</b>\nSelect packs to include new cards from: All"
    return (
        "<b>Packs</b>\nSelect packs to include new cards from: "
        + ", ".join(sorted(current))
    )


@router.message(Command("packs"))
async def cmd_packs(message: Message) -> None:
    """Optional command to open Packs UI screen, rendered inline."""
    assert message.from_user
    user_id = message.from_user.id

    counts, total = await _load_pack_counts()
    if not counts:
        await message.answer("No packs found. Seed cards first (scripts/seed_cards.py).")
        return

    async with get_db() as db:
        cur = await db.execute(
            "SELECT pack_tags FROM user_config WHERE user_id=?", (user_id,)
        )
        row = await cur.fetchone()
    selected_set: set[str] = set(
        t.strip() for t in (row[0] or "").split(",") if t.strip()
    ) if row else set()

    tags_sorted = sorted(counts.keys())
    packs_list = [(t, counts.get(t, 0)) for t in tags_sorted]
    await show_screen(
        bot=message.bot,
        user_id=user_id,
        text=_render_packs_text(selected_set),
        reply_markup=kb_packs(packs_list, selected_set),
        screen_id=SCREEN_PACKS,
    )


@router.callback_query(F.data == "ui:packs")
async def on_packs_open(cb: CallbackQuery) -> None:
    assert cb.from_user
    user_id = cb.from_user.id

    counts, _ = await _load_pack_counts()
    async with get_db() as db:
        cur = await db.execute(
            "SELECT pack_tags FROM user_config WHERE user_id=?", (user_id,)
        )
        row = await cur.fetchone()
    selected_set: set[str] = set(
        t.strip() for t in (row[0] or "").split(",") if t.strip()
    ) if row else set()
    tags_sorted = sorted(counts.keys())
    packs_list = [(t, counts.get(t, 0)) for t in tags_sorted]
    await show_screen(
        bot=cb.message.bot,  # type: ignore[union-attr]
        user_id=user_id,
        text=_render_packs_text(selected_set),
        reply_markup=kb_packs(packs_list, selected_set),
        screen_id=SCREEN_PACKS,
    )
    await cb.answer()


@router.callback_query(F.data.startswith("ui:packs.toggle:"))
async def on_packs_toggle(cb: CallbackQuery) -> None:
    assert cb.from_user and cb.data
    user_id = cb.from_user.id
    _, _, tag = cb.data.split(":", 2)

    counts, _ = await _load_pack_counts()
    async with get_db() as db:
        cur = await db.execute(
            "SELECT pack_tags FROM user_config WHERE user_id=?", (user_id,)
        )
        row = await cur.fetchone()
        selected: set[str] = set(
            t.strip() for t in (row[0] or "").split(",") if t.strip()
        ) if row else set()
        if tag in selected:
            selected.remove(tag)
        else:
            selected.add(tag)
        new_tags = ",".join(sorted(selected))
        await db.execute(
            "UPDATE user_config SET pack_tags=? WHERE user_id=?",
            (new_tags, user_id),
        )
        await db.commit()

    tags_sorted = sorted(counts.keys())
    packs_list = [(t, counts.get(t, 0)) for t in tags_sorted]
    # Re-render in place
    await cb.message.edit_text(
        _render_packs_text(selected),
        reply_markup=kb_packs(packs_list, selected),
    )
    await cb.answer()
