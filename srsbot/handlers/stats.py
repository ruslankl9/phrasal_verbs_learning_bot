from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..db import get_db


router = Router()


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    assert message.from_user
    user_id = message.from_user.id
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
    await message.answer(
        "Stats:\n"
        f"Today: shown {today_shown}, good {today_good}, accuracy {today_acc:.0%}\n"
        f"Week: shown {week_shown}, good {week_good}, accuracy {week_acc:.0%}"
    )

