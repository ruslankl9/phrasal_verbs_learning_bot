from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from srsbot.db import get_db


router = Router()


@router.message(Command("snooze"))
async def cmd_snooze(message: Message) -> None:
    assert message.from_user
    user_id = message.from_user.id
    parts = (message.text or "").split()
    hours = int(parts[1]) if len(parts) > 1 else 3
    until = datetime.now(timezone.utc) + timedelta(hours=hours)
    async with get_db() as db:
        await db.execute(
            "INSERT INTO user_state(user_id, snoozed_until) VALUES(?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET snoozed_until=excluded.snoozed_until",
            (user_id, until.isoformat()),
        )
        await db.commit()
    await message.answer(f"Snoozed for {hours} hour(s).")

