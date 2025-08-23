from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from srsbot.db import get_db
from srsbot.keyboards import kb_back_to_menu, kb_snooze_options
from srsbot.ui import SCREEN_SNOOZE, show_screen


router = Router()


def _snooze_text(prefix: str | None = None) -> str:
    base = "<b>Snooze</b>\nChoose how long to snooze today’s notification:"
    return f"{prefix}\n\n{base}" if prefix else base


@router.message(Command("snooze"))
async def cmd_snooze(message: Message) -> None:
    assert message.from_user
    user_id = message.from_user.id
    await show_screen(
        bot=message.bot,
        user_id=user_id,
        text=_snooze_text(),
        reply_markup=kb_snooze_options(),
        screen_id=SCREEN_SNOOZE,
    )


@router.callback_query(F.data == "ui:snooze")
async def on_snooze_open(cb: CallbackQuery) -> None:
    assert cb.from_user
    user_id = cb.from_user.id
    await show_screen(
        bot=cb.message.bot,  # type: ignore[union-attr]
        user_id=user_id,
        text=_snooze_text(),
        reply_markup=kb_snooze_options(),
        screen_id=SCREEN_SNOOZE,
    )
    await cb.answer()


@router.callback_query(F.data.startswith("ui:snooze.set:"))
async def on_snooze_set(cb: CallbackQuery) -> None:
    assert cb.from_user and cb.data
    user_id = cb.from_user.id
    _, _, hours_s = cb.data.split(":", 2)
    hours = int(hours_s)
    until = datetime.now(timezone.utc) + timedelta(hours=hours)
    async with get_db() as db:
        await db.execute(
            "INSERT INTO user_state(user_id, snoozed_until) VALUES(?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET snoozed_until=excluded.snoozed_until",
            (user_id, until.isoformat()),
        )
        await db.commit()
    # Refresh UI in place with confirmation
    await cb.message.edit_text(
        _snooze_text(prefix=f"Snoozed for {hours} hour(s)."),
        reply_markup=kb_snooze_options(),
    )
    await cb.answer()
