from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from srsbot.db import get_db
from srsbot.keyboards import kb_back_to_menu
from srsbot.ui import SCREEN_STATS, show_screen


router = Router()


async def _build_stats_text(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    today_start = now.date().isoformat()
    week_ago = (now - timedelta(days=7)).date().isoformat()

    async with get_db() as db:
        cur = await db.execute(
            "SELECT COUNT(*), SUM(answer='good') FROM answers WHERE user_id=? AND date(ts)=?",
            (user_id, today_start),
        )
        row = await cur.fetchone()
        today_shown = int(row[0] or 0)
        today_good = int(row[1] or 0)

        cur = await db.execute(
            "SELECT COUNT(*), SUM(answer='good') FROM answers WHERE user_id=? AND date(ts)>=?",
            (user_id, week_ago),
        )
        row = await cur.fetchone()
        week_shown = int(row[0] or 0)
        week_good = int(row[1] or 0)

    today_acc = (today_good / today_shown) if today_shown else 0.0
    week_acc = (week_good / week_shown) if week_shown else 0.0
    return (
        "<b>Stats</b>\n"
        f"Today: shown {today_shown}, good {today_good}, accuracy {today_acc:.0%}\n"
        f"Week: shown {week_shown}, good {week_good}, accuracy {week_acc:.0%}"
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    assert message.from_user
    user_id = message.from_user.id
    await show_screen(
        bot=message.bot,
        user_id=user_id,
        text=await _build_stats_text(user_id),
        reply_markup=kb_back_to_menu(),
        screen_id=SCREEN_STATS,
    )


@router.callback_query(F.data == "ui:stats")
async def on_stats_open(cb: CallbackQuery) -> None:
    assert cb.from_user
    user_id = cb.from_user.id
    await show_screen(
        bot=cb.message.bot,  # type: ignore[union-attr]
        user_id=user_id,
        text=await _build_stats_text(user_id),
        reply_markup=kb_back_to_menu(),
        screen_id=SCREEN_STATS,
    )
    await cb.answer()
