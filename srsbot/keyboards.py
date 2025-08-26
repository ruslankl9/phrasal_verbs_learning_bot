from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def kb_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="▶️ Today", callback_data="ui:today"),
                InlineKeyboardButton(text="⚙️ Settings", callback_data="ui:settings"),
            ],
            [
                InlineKeyboardButton(text="📝 Quiz", callback_data="ui:quiz"),
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
    rows.append([InlineKeyboardButton(text="◀️ Back", callback_data="ui:settings.packs.back")])
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


def kb_settings_list() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🆕 Daily new cards", callback_data="ui:settings.input:daily_new_target")],
            [InlineKeyboardButton(text="🔁 Daily review cap", callback_data="ui:settings.input:review_limit_per_day")],
            [InlineKeyboardButton(text="⏰ Notification time", callback_data="ui:settings.input:push_time")],
            [InlineKeyboardButton(text="🧩 Active packs", callback_data="ui:settings.packs")],
            [InlineKeyboardButton(text="↔️ In-round spacing", callback_data="ui:settings.input:intra_spacing_k")],
            [InlineKeyboardButton(text="📝 Quiz questions per session", callback_data="ui:settings.input:quiz_question_limit")],
            [InlineKeyboardButton(text="◀️ Back", callback_data="ui:menu")],
        ]
    )


def kb_settings_input_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="◀️ Back", callback_data="ui:settings")]]
    )


def kb_settings_packs(packs: list[tuple[str, int]], selected: set[str]) -> InlineKeyboardMarkup:
    rows = []
    for tag, n in packs:
        enabled = tag in selected
        mark = "✅" if enabled else "☑️"
        rows.append(
            [InlineKeyboardButton(text=f"{mark} {tag} ({n})", callback_data=f"ui:settings.packs.toggle:{tag}")]
        )
    rows.append([InlineKeyboardButton(text="◀️ Back", callback_data="ui:settings.packs.back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_quiz_question(qidx: int, n_options: int) -> InlineKeyboardMarkup:
    """Keyboard with 1-4 options for a quiz question and Back button.

    Buttons callback data carry the chosen index.
    """
    digits = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
    row = [
        InlineKeyboardButton(text=digits[i], callback_data=f"ui:quiz.answer:{qidx}:{i}")
        for i in range(min(max(2, n_options), 4))
    ]
    rows = [row, [InlineKeyboardButton(text="◀️ Back", callback_data="ui:quiz.back")]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_quiz_summary() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Take quiz again", callback_data="ui:quiz.again")],
            [InlineKeyboardButton(text="◀️ Back to menu", callback_data="ui:menu")],
        ]
    )
