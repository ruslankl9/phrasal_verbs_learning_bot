from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from srsbot.keyboards import kb_main_menu
from srsbot.ui import SCREEN_MENU, show_screen


router = Router()


def _menu_text() -> str:
    return "<b>Main Menu</b>"


@router.message(Command("menu"))
@router.message(Command("help"))
async def cmd_menu(message: Message) -> None:
    assert message.from_user
    user_id = message.from_user.id
    await show_screen(
        bot=message.bot,
        user_id=user_id,
        text=_menu_text(),
        reply_markup=kb_main_menu(),
        screen_id=SCREEN_MENU,
    )


@router.callback_query(F.data == "ui:menu")
async def on_menu(cb: CallbackQuery) -> None:
    assert cb.from_user
    user_id = cb.from_user.id
    await show_screen(
        bot=cb.message.bot,  # type: ignore[union-attr]
        user_id=user_id,
        text=_menu_text(),
        reply_markup=kb_main_menu(),
        screen_id=SCREEN_MENU,
    )
    await cb.answer()
