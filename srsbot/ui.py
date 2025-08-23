from __future__ import annotations

"""Inline UI utilities: screen IDs and edit-or-replace rendering helper.

This module centralizes message cleanup so the chat always contains a single
active UI message for navigation screens.
"""

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup

from srsbot.db import get_ui_state, set_ui_state


# Screen identifiers
SCREEN_MENU = "menu"
SCREEN_TODAY = "today"
SCREEN_CONFIG = "config"
SCREEN_PACKS = "packs"
SCREEN_STATS = "stats"
SCREEN_SNOOZE = "snooze"


async def show_screen(
    bot: Bot,
    user_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None,
    screen_id: str,
) -> None:
    """Render a screen by editing previous UI message or replacing it.

    - If a previous `last_ui_message_id` exists, try to edit it in-place.
      If editing fails (e.g., content is identical or message is gone), delete
      and send a fresh one.
    - If no previous UI message, send a new one.
    Always update `last_ui_message_id` and `current_screen` in DB.
    """
    state = await get_ui_state(user_id)
    chat_id = user_id
    last_id = int(state["last_ui_message_id"]) if state and state["last_ui_message_id"] else None

    if last_id is not None:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=last_id,
                text=text,
                reply_markup=reply_markup,
            )
            await set_ui_state(user_id, last_ui_message_id=last_id, current_screen=screen_id)
            return
        except TelegramBadRequest:
            # Try to delete and re-send if edit is not possible
            try:
                await bot.delete_message(chat_id, last_id)
            except Exception:
                pass

    # Send a fresh message
    msg = await bot.send_message(chat_id, text, reply_markup=reply_markup)
    await set_ui_state(user_id, last_ui_message_id=msg.message_id, current_screen=screen_id)

