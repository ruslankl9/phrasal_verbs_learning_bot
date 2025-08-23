from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def kb_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="▶️ Today", callback_data="ui:today"),
                InlineKeyboardButton(text="⚙️ Config", callback_data="ui:config"),
            ],
            [
                InlineKeyboardButton(text="🧩 Packs", callback_data="ui:packs"),
                InlineKeyboardButton(text="📊 Stats", callback_data="ui:stats"),
            ],
            [InlineKeyboardButton(text="😴 Snooze", callback_data="ui:snooze")],
        ]
    )


def answer_kb(card_id: int) -> InlineKeyboardMarkup:
    """Legacy answer keyboard for a card (Again/Good)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Again", callback_data=f"ans:again:{card_id}"),
                InlineKeyboardButton(text="Good", callback_data=f"ans:good:{card_id}"),
            ]
        ]
    )


def today_card_kb(card_id: int) -> InlineKeyboardMarkup:
    """Answer keyboard with persistent Finish button for Today screen."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Again", callback_data=f"ans:again:{card_id}"),
                InlineKeyboardButton(text="Good", callback_data=f"ans:good:{card_id}"),
            ],
            [InlineKeyboardButton(text="🏁 Finish session", callback_data="ui:today.finish")],
        ]
    )


def round_end_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔁 Repeat round", callback_data="round:repeat"),
                InlineKeyboardButton(text="🏁 Finish session", callback_data="ui:today.finish"),
            ],
            [InlineKeyboardButton(text="◀️ Back", callback_data="ui:menu")],
        ]
    )


def kb_back_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="◀️ Back", callback_data="ui:menu")]]
    )


def kb_packs(packs: list[tuple[str, int]], selected: set[str]) -> InlineKeyboardMarkup:
    rows = []
    for tag, n in packs:
        enabled = tag in selected
        mark = "✅" if enabled else "☑️"
        rows.append(
            [InlineKeyboardButton(text=f"{mark} {tag} ({n})", callback_data=f"ui:packs.toggle:{tag}")]
        )
    rows.append([InlineKeyboardButton(text="◀️ Back", callback_data="ui:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_snooze_options(options: list[int] = [1, 3, 6]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text=f"+{h}h", callback_data=f"ui:snooze.set:{h}")
            for h in options
        ]
    ]
    rows.append([InlineKeyboardButton(text="◀️ Back", callback_data="ui:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
