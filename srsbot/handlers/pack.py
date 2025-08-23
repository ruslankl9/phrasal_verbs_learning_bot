from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..db import get_db


router = Router()


@router.message(Command("pack"))
async def cmd_pack(message: Message) -> None:
    assert message.from_user
    user_id = message.from_user.id
    args = (message.text or "").split(maxsplit=1)
    if len(args) == 1:
        await message.answer("Usage: /pack <tag>[,<tag2>] (e.g., work or work,travel)")
        return
    tags = args[1].strip()
    async with get_db() as db:
        await db.execute(
            "UPDATE user_config SET pack_tags=? WHERE user_id=?", (tags, user_id)
        )
        await db.commit()
    await message.answer(f"New card pack set to: {tags}")

