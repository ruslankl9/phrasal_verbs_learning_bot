from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from srsbot.db import get_db, get_ui_state, set_awaiting_input
from srsbot.keyboards import (
    kb_settings_input_back,
    kb_settings_list,
    kb_settings_packs,
)
from srsbot.ui import SCREEN_SETTINGS, show_screen
from srsbot.validators import validate_hhmm, validate_int_in_range


router = Router()


FIELD_META = {
    "daily_new_target": (
        "Daily new cards",
        "How many new cards to introduce per day. The bot adapts slightly based on your accuracy.",
        lambda s: validate_int_in_range(s, 4, 12),
    ),
    "review_limit_per_day": (
        "Daily review cap",
        "Max number of review cards per day to avoid overload; extra reviews are rebalanced to the next days.",
        lambda s: validate_int_in_range(s, 20, 60),
    ),
    "push_time": (
        "Notification time",
        "Daily reminder time in your local timezone.",
        validate_hhmm,
    ),
    "intra_spacing_k": (
        "In-round spacing",
        "How many other cards to show before repeating a missed card within the same round.",
        lambda s: validate_int_in_range(s, 1, 6),
    ),
    "quiz_question_limit": (
        "Quiz questions per session",
        "How many multiple-choice questions to include in one Quiz session (review cards only).",
        lambda s: validate_int_in_range(s, 5, 30),
    ),
}


def _fmt_settings_text(row: tuple[int, int, str, str, int, int]) -> str:
    daily_new, review_cap, push_time, pack_tags, k, quiz_limit = row
    packs_display = (
        ", ".join(t.strip().title() for t in pack_tags.split(",") if t.strip()) or "All"
    )
    return (
        "<b>Settings</b>\n"
        f"• Daily new cards: {daily_new}\n"
        f"• Daily review cap: {review_cap}\n"
        f"• Notification time: {push_time}\n"
        f"• Active packs: {packs_display}\n"
        f"• In-round spacing: {k}\n"
        f"• Quiz questions per session: {quiz_limit}"
    )


async def _load_settings_row(user_id: int) -> tuple[int, int, str, str, int, int]:
    async with get_db() as db:
        cur = await db.execute(
            "SELECT daily_new_target, review_limit_per_day, push_time, pack_tags, intra_spacing_k, quiz_question_limit FROM user_config WHERE user_id=?",
            (user_id,),
        )
        row = await cur.fetchone()
    if not row:
        return (8, 35, "09:00", "", 3, 10)
    return int(row[0]), int(row[1]), str(row[2]), str(row[3] or ""), int(row[4]), int(row[5] if row[5] is not None else 10)


async def show_settings(message_or_cb, user_id: int) -> None:
    row = await _load_settings_row(user_id)
    await show_screen(
        bot=message_or_cb.bot,
        user_id=user_id,
        text=_fmt_settings_text(row),
        reply_markup=kb_settings_list(),
        screen_id=SCREEN_SETTINGS,
    )


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    assert message.from_user
    await show_settings(message, message.from_user.id)


@router.callback_query(F.data == "ui:settings")
async def on_settings_open(cb: CallbackQuery) -> None:
    assert cb.from_user
    await set_awaiting_input(cb.from_user.id, None)
    await show_settings(cb.message, cb.from_user.id)  # type: ignore[arg-type]
    await cb.answer()


def _input_prompt(field: str, error: str | None = None) -> str:
    title, desc, _ = FIELD_META[field]
    lines = []
    if error:
        lines.append(f"❌ {error}")
        lines.append("")
    lines.append(f"<b>{title}</b>")
    lines.append(f"<i>{desc}</i>")
    lines.append("")
    lines.append("Please enter a new value:")
    return "\n".join(lines)


@router.callback_query(F.data.startswith("ui:settings.input:"))
async def on_open_input(cb: CallbackQuery) -> None:
    assert cb.from_user and cb.data
    user_id = cb.from_user.id
    # Ignore new actions if currently awaiting another input
    state = await get_ui_state(user_id)
    if state and state["awaiting_input_field"]:
        await cb.answer("Finish entering the value or tap Back.", show_alert=False)
        return
    _, _, field = cb.data.split(":", 2)
    if field not in FIELD_META:
        await cb.answer("Unsupported field.")
        return
    await set_awaiting_input(user_id, field)
    await show_screen(
        bot=cb.message.bot,  # type: ignore[union-attr]
        user_id=user_id,
        text=_input_prompt(field),
        reply_markup=kb_settings_input_back(),
        screen_id=SCREEN_SETTINGS,
    )
    await cb.answer()


@router.message()
async def on_text_input(message: Message) -> None:
    # Only capture if awaiting a settings value
    assert message.from_user
    user_id = message.from_user.id
    state = await get_ui_state(user_id)
    awaiting = state["awaiting_input_field"] if state else None
    if not awaiting:
        return
    field = str(awaiting)
    _, _, validator = FIELD_META.get(field, (None, None, None))
    if validator is None:
        # Unknown field; clear and show settings
        await set_awaiting_input(user_id, None)
        await show_settings(message, user_id)
        return
    ok, err = validator(message.text or "")
    if not ok:
        await show_screen(
            bot=message.bot,
            user_id=user_id,
            text=_input_prompt(field, error=err or "Invalid value."),
            reply_markup=kb_settings_input_back(),
            screen_id=SCREEN_SETTINGS,
        )
        return
    # Persist
    value = (message.text or "").strip()
    async with get_db() as db:
        await db.execute(
            f"UPDATE user_config SET {field}=? WHERE user_id=?",
            (value, user_id),
        )
        await db.commit()
    await set_awaiting_input(user_id, None)
    await show_settings(message, user_id)


@router.callback_query(F.data == "ui:settings.packs")
async def on_settings_packs_open(cb: CallbackQuery) -> None:
    assert cb.from_user
    user_id = cb.from_user.id
    # If awaiting input, block navigation except Back
    state = await get_ui_state(user_id)
    if state and state["awaiting_input_field"]:
        await cb.answer("Finish entering the value or tap Back.", show_alert=False)
        return
    # Build counts
    from collections import defaultdict
    from typing import Dict, Set

    async with get_db() as db:
        cur = await db.execute("SELECT phrasal, tags FROM cards")
        rows = await cur.fetchall()
        cur2 = await db.execute(
            "SELECT pack_tags FROM user_config WHERE user_id=?", (user_id,)
        )
        row2 = await cur2.fetchone()

    by_tag: Dict[str, Set[str]] = defaultdict(set)
    for r in rows:
        phrasal = str(r[0])
        for t in (x.strip().lower() for x in (r[1] or "").split(",") if x.strip()):
            by_tag[t].add(phrasal)
    counts = {t: len(s) for t, s in by_tag.items()}

    selected: set[str] = set(
        t.strip() for t in (row2[0] or "").split(",") if t.strip()
    ) if row2 else set()
    tags_sorted = sorted(counts.keys())
    packs_list = [(t, counts.get(t, 0)) for t in tags_sorted]
    # Reuse text from settings line
    text = "<b>Active packs</b>\nToggle packs on/off."
    from srsbot.keyboards import kb_settings_packs

    await show_screen(
        bot=cb.message.bot,  # type: ignore[union-attr]
        user_id=user_id,
        text=text,
        reply_markup=kb_settings_packs(packs_list, selected),
        screen_id=SCREEN_SETTINGS,
    )
    await cb.answer()


@router.callback_query(F.data.startswith("ui:settings.packs.toggle:"))
async def on_settings_packs_toggle(cb: CallbackQuery) -> None:
    assert cb.from_user and cb.data
    user_id = cb.from_user.id
    # If awaiting input, ignore toggles
    state = await get_ui_state(user_id)
    if state and state["awaiting_input_field"]:
        await cb.answer("Finish entering the value or tap Back.", show_alert=False)
        return
    _, _, tag = cb.data.split(":", 3)
    # Read current
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
    async with get_db() as db:
        await db.execute(
            "UPDATE user_config SET pack_tags=? WHERE user_id=?",
            (new_tags, user_id),
        )
        await db.commit()
    # Rebuild counts
    from collections import defaultdict
    from typing import Dict, Set

    async with get_db() as db:
        cur = await db.execute("SELECT phrasal, tags FROM cards")
        rows = await cur.fetchall()
    by_tag: Dict[str, Set[str]] = defaultdict(set)
    for r in rows:
        phrasal = str(r[0])
        for t in (x.strip().lower() for x in (r[1] or "").split(",") if x.strip()):
            by_tag[t].add(phrasal)
    counts = {t: len(s) for t, s in by_tag.items()}
    tags_sorted = sorted(counts.keys())
    packs_list = [(t, counts.get(t, 0)) for t in tags_sorted]
    # Re-render inline
    await cb.message.edit_text(
        "<b>Active packs</b>\nToggle packs on/off.",
        reply_markup=kb_settings_packs(packs_list, selected),
    )
    await cb.answer()


@router.callback_query(F.data == "ui:settings.packs.back")
async def on_settings_packs_back(cb: CallbackQuery) -> None:
    assert cb.from_user
    await show_settings(cb.message, cb.from_user.id)  # type: ignore[arg-type]
    await cb.answer()
