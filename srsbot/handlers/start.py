from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..db import ensure_user_config


router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    assert message.from_user
    user_id = message.from_user.id
    await ensure_user_config(user_id)
    await message.answer(
        "Welcome! This bot helps you learn English phrasal verbs with a daily SRS session.\n"
        "Use /today to begin today’s session. Configure with /config."
    )

