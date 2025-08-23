from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Optional

from aiogram import Bot

from srsbot.config import parse_push_time
from srsbot.db import get_db, update_last_notified


async def compute_counts(user_id: int) -> tuple[int, int]:
    """Return (reviews_due, new_available) for today."""
    async with get_db() as db:
        cur = await db.execute(
            "SELECT review_limit_per_day, daily_new_target FROM user_config WHERE user_id=?",
            (user_id,),
        )
        row = await cur.fetchone()
        review_limit = int(row[0]) if row else 35
        new_target = int(row[1]) if row else 8

        cur = await db.execute(
            "SELECT COUNT(*) FROM progress WHERE user_id=? AND state='review' AND due_at<=date('now')",
            (user_id,),
        )
        row = await cur.fetchone()
        reviews_due = min(int(row[0] or 0), review_limit)

        cur = await db.execute(
            "SELECT COUNT(*) FROM cards c LEFT JOIN progress p ON p.card_id=c.id AND p.user_id=? WHERE p.card_id IS NULL",
            (user_id,),
        )
        row = await cur.fetchone()
        new_avail = min(int(row[0] or 0), new_target)
    return reviews_due, new_avail


async def daily_tick(bot: Bot) -> None:
    """Run every minute; send push if time matches and not sent today or snoozed."""
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    async with get_db() as db:
        cur = await db.execute("SELECT user_id, push_time FROM user_config")
        users = await cur.fetchall()
    for row in users:
        user_id = int(row[0])
        push_t = parse_push_time(row[1])
        # Check last notified and snooze
        async with get_db() as db:
            cur = await db.execute(
                "SELECT last_notified_date, snoozed_until FROM user_state WHERE user_id=?",
                (user_id,),
            )
            st = await cur.fetchone()
        last_notified = (st[0] if st else None)
        snoozed_until = (st[1] if st else None)
        if snoozed_until and now < datetime.fromisoformat(snoozed_until):
            continue
        # Only once per day
        if last_notified == today:
            continue
        if now.hour == push_t.hour and now.minute == push_t.minute:
            reviews, new = await compute_counts(user_id)
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=f"You have {reviews + new} cards today: {reviews} reviews + {new} new. Start? (/today)",
                )
                await update_last_notified(user_id, now.date())
            except Exception:
                # Ignore send errors (e.g., bot not started by user)
                pass

