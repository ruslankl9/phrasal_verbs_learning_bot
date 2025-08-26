from __future__ import annotations

"""Quiz feature: multiple-choice practice over review-state cards.

This module provides router handlers and pure helpers to build quiz items.
"""

import json
import random
from typing import Dict, List, Tuple

from aiogram import F, Router
from aiogram.types import CallbackQuery

from srsbot.db import (
    get_db,
    get_quiz_state_json,
    set_quiz_state,
)
from srsbot.formatters import format_quiz_question_html, format_quiz_summary_html
from srsbot.keyboards import kb_main_menu, kb_quiz_question, kb_quiz_summary
from srsbot.ui import SCREEN_MENU, SCREEN_QUIZ, show_screen


router = Router()


def build_quiz_items(
    cards: List[Tuple[int, str, str]],
    global_meanings: List[str],
    limit: int,
) -> List[Dict]:
    """Build quiz items for given cards and meanings.

    cards: list of (card_id, phrasal, correct_meaning)
    global_meanings: meanings to sample distractors from (may include correct ones)
    limit: max number of questions
    """
    picked = cards[:]
    random.shuffle(picked)
    picked = picked[: max(0, limit)]

    # Prepare a de-duplicated pool of meanings
    pool = [m for m in dict.fromkeys(global_meanings)]  # preserve order, unique
    items: List[Dict] = []
    for card_id, phrasal, correct in picked:
        # Sample 3 unique distractors excluding the correct meaning
        distract_pool = [m for m in pool if m != correct]
        random.shuffle(distract_pool)
        distractors = []
        for m in distract_pool:
            if m not in distractors:
                distractors.append(m)
            if len(distractors) == 3:
                break
        options = [correct] + distractors
        # Ensure at least 2 options when pool is extremely small
        options = options[: max(2, min(4, len(options)))]
        random.shuffle(options)
        correct_index = options.index(correct)
        items.append(
            {
                "card_id": card_id,
                "phrasal": phrasal,
                "correct_meaning": correct,
                "options": options,
                "correct_index": correct_index,
                "user_choice": None,
            }
        )
    return items


async def _build_quiz_session(user_id: int) -> Tuple[str | None, str]:
    """Build a quiz session for the user.

    Returns (quiz_json_or_none, message_text). If no eligible cards, returns (None, info_message).
    """
    # Load eligible review cards and config
    async with get_db() as db:
        cur = await db.execute(
            "SELECT quiz_question_limit FROM user_config WHERE user_id=?",
            (user_id,),
        )
        row = await cur.fetchone()
        limit = int(row[0]) if row else 10

        cur2 = await db.execute(
            """
            SELECT p.card_id, c.phrasal, c.meaning_en
            FROM progress p JOIN cards c ON c.id=p.card_id
            WHERE p.user_id=? AND p.state='review'
            """,
            (user_id,),
        )
        cards = [(int(r[0]), str(r[1]), str(r[2])) for r in await cur2.fetchall()]

        cur3 = await db.execute("SELECT meaning_en FROM cards")
        meanings = [str(r[0]) for r in await cur3.fetchall()]

    if not cards:
        return None, "No review cards available for quiz today."

    items = build_quiz_items(cards, meanings, limit)
    state = {"questions": items, "current_q": 0}
    return json.dumps(state), ""


async def open_quiz(user_id: int, bot) -> None:
    quiz_json, msg = await _build_quiz_session(user_id)
    if quiz_json is None:
        await show_screen(
            bot=bot,
            user_id=user_id,
            text=msg,
            reply_markup=kb_main_menu(),
            screen_id=SCREEN_MENU,
        )
        return
    await set_quiz_state(user_id, quiz_json)
    await render_question(user_id, bot)


async def render_question(user_id: int, bot) -> None:
    data_s = await get_quiz_state_json(user_id)
    if not data_s:
        # No active quiz; go back to menu
        await show_screen(bot=bot, user_id=user_id, text="<b>Main Menu</b>", reply_markup=kb_main_menu(), screen_id=SCREEN_MENU)
        return
    state = json.loads(data_s)
    qidx = int(state.get("current_q", 0))
    questions = state.get("questions", [])
    if qidx >= len(questions):
        # Nothing to show; render summary instead
        await render_summary(user_id, bot)
        return
    q = questions[qidx]
    opts = [str(x) for x in q.get("options", [])]
    text = format_quiz_question_html(q.get("phrasal", ""), opts)
    await show_screen(
        bot=bot,
        user_id=user_id,
        text=text,
        reply_markup=kb_quiz_question(qidx, len(opts)),
        screen_id=SCREEN_QUIZ,
    )


async def render_summary(user_id: int, bot) -> None:
    data_s = await get_quiz_state_json(user_id)
    if not data_s:
        await show_screen(bot=bot, user_id=user_id, text="<b>Main Menu</b>", reply_markup=kb_main_menu(), screen_id=SCREEN_MENU)
        return
    state = json.loads(data_s)
    items = state.get("questions", [])
    text = format_quiz_summary_html(items)
    await show_screen(
        bot=bot,
        user_id=user_id,
        text=text,
        reply_markup=kb_quiz_summary(),
        screen_id=SCREEN_QUIZ,
    )


@router.callback_query(F.data == "ui:quiz")
async def on_quiz_open(cb: CallbackQuery) -> None:
    assert cb.from_user
    await open_quiz(cb.from_user.id, cb.message.bot)  # type: ignore[union-attr]
    await cb.answer()


@router.callback_query(F.data.startswith("ui:quiz.answer:"))
async def on_quiz_answer(cb: CallbackQuery) -> None:
    assert cb.from_user and cb.data
    user_id = cb.from_user.id
    _, _, rest = cb.data.split(":", 2)
    parts = rest.split(":")
    if len(parts) != 2:
        await cb.answer()
        return
    qidx = int(parts[0])
    optidx = int(parts[1])

    data_s = await get_quiz_state_json(user_id)
    if not data_s:
        await cb.answer("No active quiz.")
        return
    state = json.loads(data_s)
    cur = int(state.get("current_q", 0))
    questions: List[Dict] = state.get("questions", [])
    if qidx != cur or qidx >= len(questions):
        await cb.answer("This question is no longer active", show_alert=False)
        return
    # Record choice
    questions[qidx]["user_choice"] = optidx
    state["current_q"] = cur + 1
    await set_quiz_state(user_id, json.dumps(state))
    # Next
    if state["current_q"] < len(questions):
        await render_question(user_id, cb.message.bot)  # type: ignore[union-attr]
    else:
        await render_summary(user_id, cb.message.bot)  # type: ignore[union-attr]
    await cb.answer()


@router.callback_query(F.data == "ui:quiz.again")
async def on_quiz_again(cb: CallbackQuery) -> None:
    assert cb.from_user
    user_id = cb.from_user.id
    quiz_json, msg = await _build_quiz_session(user_id)
    if quiz_json is None:
        await show_screen(
            bot=cb.message.bot,  # type: ignore[union-attr]
            user_id=user_id,
            text=msg,
            reply_markup=kb_main_menu(),
            screen_id=SCREEN_MENU,
        )
        await cb.answer()
        return
    await set_quiz_state(user_id, quiz_json)
    await render_question(user_id, cb.message.bot)  # type: ignore[union-attr]
    await cb.answer()


@router.callback_query(F.data == "ui:quiz.back")
async def on_quiz_back(cb: CallbackQuery) -> None:
    assert cb.from_user
    user_id = cb.from_user.id
    # Clear and return to menu
    await set_quiz_state(user_id, None)
    await show_screen(
        bot=cb.message.bot,  # type: ignore[union-attr]
        user_id=user_id,
        text="<b>Main Menu</b>",
        reply_markup=kb_main_menu(),
        screen_id=SCREEN_MENU,
    )
    await cb.answer()
