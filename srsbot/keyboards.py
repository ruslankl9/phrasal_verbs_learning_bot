from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def answer_kb(card_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Again", callback_data=f"ans:again:{card_id}"),
                InlineKeyboardButton(text="Good", callback_data=f"ans:good:{card_id}"),
            ]
        ]
    )

