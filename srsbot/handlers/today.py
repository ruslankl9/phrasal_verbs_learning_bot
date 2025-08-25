from __future__ import annotations

from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from srsbot.db import (
    get_db,
    init_db,
    init_or_get_day_state,
    increment_day_counters,
    update_day_state,
)
from srsbot.formatters import (
    format_round_complete,
    format_session_finished,
    html_card_message,
)
from srsbot.keyboards import round_end_keyboard, today_card_kb, kb_main_menu
from srsbot.models import Progress
from srsbot.session import store
from srsbot.srs import AnswerResult, on_answer
from srsbot.queue import build_round_queue, compute_daily_candidates
from srsbot.ui import SCREEN_TODAY, SCREEN_MENU, show_screen


router = Router()


@router.message(Command("today"))
async def cmd_today(message: Message) -> None:
    assert message.from_user
    user_id = message.from_user.id
    s = await store.get(user_id)
    await init_db()
    today = datetime.now(timezone.utc).date()
    ds = await init_or_get_day_state(user_id, today.isoformat())
    # Load config
    async with get_db() as db:
        cur = await db.execute(
            "SELECT daily_new_target, review_limit_per_day, pack_tags FROM user_config WHERE user_id=?",
            (user_id,),
        )
        row = await cur.fetchone()
    daily_new_target = int(row[0]) if row else 8
    review_limit = int(row[1]) if row else 35
    pack_tags = (row[2] if row else "daily").split(",")

    # If no active queue, build a round snapshot based on remaining capacities
    if not s.queue:
        review_remaining = max(0, review_limit - int(ds["served_review_count"]))
        new_remaining = max(0, daily_new_target - int(ds["shown_new_today"]))
        s.queue = await build_round_queue(
            user_id=user_id,
            today=today,
            pack_tags=pack_tags,
            review_remaining=review_remaining,
            new_remaining=new_remaining,
        )
        await update_day_state(
            user_id,
            today.isoformat(),
            round_card_ids_json="[" + ",".join(str(i) for i in s.queue) + "]",
        )

    if not s.queue:
        await show_screen(
            bot=message.bot,
            user_id=user_id,
            text="Nothing left for today 🎉",
            reply_markup=round_end_keyboard(),
            screen_id=SCREEN_TODAY,
        )
        return

    next_id = s.queue.pop(0)
    async with get_db() as db:
        cur = await db.execute(
            "SELECT phrasal, meaning_en, examples_json, tags FROM cards WHERE id=?",
            (next_id,),
        )
        row = await cur.fetchone()
        cur2 = await db.execute(
            "SELECT last_seen_at FROM progress WHERE user_id=? AND card_id=?",
            (user_id, next_id),
        )
        prow = await cur2.fetchone()
    if not row:
        await show_screen(
            bot=message.bot,
            user_id=user_id,
            text="Card not found.",
            reply_markup=kb_main_menu(),
            screen_id=SCREEN_MENU,
        )
        return
    # Determine if this is the first-ever show for this user
    first_time_ever = prow is None or prow[0] is None
    first_time_this_session = next_id not in s.shown_card_ids
    is_new_badge = first_time_ever and first_time_this_session
    s.shown_card_ids.add(next_id)
    tags_list = [t for t in str(row[3] or "").split(",") if t]
    await show_screen(
        bot=message.bot,
        user_id=user_id,
        text=html_card_message(row[0], row[1], row[2], is_new=is_new_badge, tags=tags_list),
        reply_markup=today_card_kb(next_id),
        screen_id=SCREEN_TODAY,
    )


@router.callback_query(F.data == "ui:today")
async def on_today_from_menu(cb: CallbackQuery) -> None:
    # Open or continue today flow from the Main Menu
    assert cb.from_user
    user_id = cb.from_user.id
    s = await store.get(user_id)
    await init_db()
    today = datetime.now(timezone.utc).date()
    ds = await init_or_get_day_state(user_id, today.isoformat())
    # Load config
    async with get_db() as db:
        cur = await db.execute(
            "SELECT daily_new_target, review_limit_per_day, pack_tags FROM user_config WHERE user_id=?",
            (user_id,),
        )
        row = await cur.fetchone()
    daily_new_target = int(row[0]) if row else 8
    review_limit = int(row[1]) if row else 35
    pack_tags = (row[2] if row else "daily").split(",")

    if not s.queue:
        review_remaining = max(0, review_limit - int(ds["served_review_count"]))
        new_remaining = max(0, daily_new_target - int(ds["shown_new_today"]))
        s.queue = await build_round_queue(
            user_id=user_id,
            today=today,
            pack_tags=pack_tags,
            review_remaining=review_remaining,
            new_remaining=new_remaining,
        )
        await update_day_state(
            user_id,
            today.isoformat(),
            round_card_ids_json="[" + ",".join(str(i) for i in s.queue) + "]",
        )

    if not s.queue:
        await show_screen(
            bot=cb.message.bot,  # type: ignore[union-attr]
            user_id=user_id,
            text="Nothing left for today 🎉",
            reply_markup=round_end_keyboard(),
            screen_id=SCREEN_TODAY,
        )
        await cb.answer()
        return

    next_id = s.queue.pop(0)
    async with get_db() as db:
        cur = await db.execute(
            "SELECT phrasal, meaning_en, examples_json, tags FROM cards WHERE id=?",
            (next_id,),
        )
        row = await cur.fetchone()
        cur2 = await db.execute(
            "SELECT last_seen_at FROM progress WHERE user_id=? AND card_id=?",
            (user_id, next_id),
        )
        prow = await cur2.fetchone()
    if not row:
        await show_screen(
            bot=cb.message.bot,  # type: ignore[union-attr]
            user_id=user_id,
            text="Card not found.",
            reply_markup=kb_main_menu(),
            screen_id=SCREEN_MENU,
        )
        await cb.answer()
        return
    first_time_ever = prow is None or prow[0] is None
    first_time_this_session = next_id not in s.shown_card_ids
    is_new_badge = first_time_ever and first_time_this_session
    s.shown_card_ids.add(next_id)
    tags_list = [t for t in str(row[3] or "").split(",") if t]
    await show_screen(
        bot=cb.message.bot,  # type: ignore[union-attr]
        user_id=user_id,
        text=html_card_message(row[0], row[1], row[2], is_new=is_new_badge, tags=tags_list),
        reply_markup=today_card_kb(next_id),
        screen_id=SCREEN_TODAY,
    )
    await cb.answer()


@router.callback_query(F.data.startswith("ans:"))
async def on_ans(cb: CallbackQuery) -> None:
    assert cb.from_user and cb.data
    user_id = cb.from_user.id
    _, ans, card_id_s = cb.data.split(":", 2)
    card_id = int(card_id_s)

    async with get_db() as db:
        cur = await db.execute(
            "SELECT state, COALESCE(box,0), due_at, lapses, learning_good_count FROM progress WHERE user_id=? AND card_id=?",
            (user_id, card_id),
        )
        row = await cur.fetchone()
        if row:
            state, box, due_at, lapses, lgc = row
        else:
            state, box, due_at, lapses, lgc = ("learning", 0, None, 0, 0)

        p = Progress(
            user_id=user_id,
            card_id=card_id,
            state=state,
            box=int(box),
            due_at=None,
            lapses=int(lapses),
            learning_good_count=int(lgc),
            last_answer=None,
            last_seen_at=None,
        )

        today = datetime.now(timezone.utc).date()
        # intra-spacing k
        cur2 = await db.execute(
            "SELECT intra_spacing_k FROM user_config WHERE user_id=?", (user_id,)
        )
        row2 = await cur2.fetchone()
        k = int(row2[0]) if row2 else 3

        res: AnswerResult = on_answer(p, ans, today, k)

        # Update per-day counters on first serve of review/new
        # Track using seen sets stored in user_day_state JSON columns
        cur3 = await db.execute(
            "SELECT review_seen_ids_json, new_seen_ids_json FROM user_day_state WHERE user_id=? AND session_date=?",
            (user_id, today.isoformat()),
        )
        st = await cur3.fetchone()
        import json as _json
        review_seen = set(_json.loads(st[0] or "[]")) if st else set()
        new_seen = set(_json.loads(st[1] or "[]")) if st else set()
        add_review = 0
        add_new = 0
        if state == "review" and card_id not in review_seen:
            review_seen.add(card_id)
            add_review = 1
        if state == "learning" and int(box) == 0 and card_id not in new_seen:
            new_seen.add(card_id)
            add_new = 1
        if add_review or add_new:
            await db.execute(
                """
                UPDATE user_day_state
                SET served_review_count = served_review_count + ?,
                    shown_new_today = shown_new_today + ?,
                    review_seen_ids_json = ?,
                    new_seen_ids_json = ?
                WHERE user_id=? AND session_date=?
                """,
                (
                    add_review,
                    add_new,
                    _json.dumps(sorted(review_seen)),
                    _json.dumps(sorted(new_seen)),
                    user_id,
                    today.isoformat(),
                ),
            )

        # Upsert progress
        await db.execute(
            """
            INSERT INTO progress(user_id, card_id, state, box, due_at, lapses, learning_good_count, last_answer, last_seen_at)
            VALUES(?,?,?,?,?,?,?, ?, datetime('now'))
            ON CONFLICT(user_id, card_id) DO UPDATE SET
                state=excluded.state,
                box=excluded.box,
                due_at=excluded.due_at,
                lapses=excluded.lapses,
                learning_good_count=excluded.learning_good_count,
                last_answer=excluded.last_answer,
                last_seen_at=excluded.last_seen_at
            """,
            (
                user_id,
                card_id,
                res.progress.state,
                res.progress.box,
                res.progress.due_at.isoformat() if res.progress.due_at else None,
                res.progress.lapses,
                res.progress.learning_good_count,
                res.progress.last_answer,
            ),
        )

        # Log answer
        await db.execute(
            "INSERT INTO answers(user_id, card_id, answer, is_new, tags) VALUES(?,?,?,?,?)",
            (
                user_id,
                card_id,
                ans,
                1 if state == "learning" and box == 0 else 0,
                None,
            ),
        )
        await db.commit()

    s = await store.get(user_id)
    s.shown += 1
    if ans == "good":
        s.good += 1
        await increment_day_counters(user_id, today.isoformat(), good_delta=1)
        s.consecutive_good += 1
    else:
        await increment_day_counters(user_id, today.isoformat(), again_delta=1)
        s.consecutive_good = 0

    # Requeue if needed
    if res.requeue_after is not None:
        pos = min(res.requeue_after, len(s.queue))
        s.queue.insert(pos, card_id)

    # Dynamic boost: every 5 consecutive good -> inject one extra new id if available
    if s.consecutive_good > 0 and s.consecutive_good % 5 == 0:
        async with get_db() as db:
            cur = await db.execute(
                """
                SELECT c.id FROM cards c
                LEFT JOIN progress p ON p.card_id=c.id AND p.user_id=?
                WHERE p.card_id IS NULL
                LIMIT 1
                """,
                (user_id,),
            )
            row = await cur.fetchone()
            if row:
                s.queue.append(int(row[0]))

    print("queue:", s.queue)
    if not s.queue:
        # End of round: show completion UI with remaining counts in place
        async with get_db() as db:
            cur = await db.execute(
                "SELECT daily_new_target, review_limit_per_day, pack_tags FROM user_config WHERE user_id=?",
                (user_id,),
            )
            row = await cur.fetchone()
        daily_new_target = int(row[0]) if row else 8
        review_limit = int(row[1]) if row else 35
        pack_tags = (row[2] if row else "daily").split(",")
        # Remaining capacities
        async with get_db() as db:
            cur = await db.execute(
                "SELECT served_review_count, shown_new_today, good_today, again_today FROM user_day_state WHERE user_id=? AND session_date=?",
                (user_id, today.isoformat()),
            )
            ds = await cur.fetchone()
        served_reviews = int(ds[0]) if ds else 0
        shown_new = int(ds[1]) if ds else 0
        good_today = int(ds[2]) if ds else 0
        again_today = int(ds[3]) if ds else 0
        review_remaining = max(0, review_limit - served_reviews)
        new_remaining = max(0, daily_new_target - shown_new)
        # Candidates now
        learning_due, reviews_due_all, new_candidates = await compute_daily_candidates(
            user_id, today
        )
        # Apply remaining caps to compute remaining today
        remaining_learning = len(learning_due)
        remaining_reviews = min(len(reviews_due_all), review_remaining)
        # Filter new by tags and cap
        from srsbot.content import select_new_cards

        new_picked = select_new_cards(new_candidates, pack_tags, new_remaining)
        remaining_new = len(new_picked)

        # Show round complete in the same message
        await cb.message.edit_text(
            format_round_complete(
                good_today,
                again_today,
                remaining_learning,
                remaining_reviews,
                remaining_new,
            ),
            reply_markup=round_end_keyboard(),
        )
        await cb.answer()
        return

    # Show next card
    next_id = s.queue.pop(0)
    print("next_id:", next_id)
    async with get_db() as db:
        cur = await db.execute(
            "SELECT phrasal, meaning_en, examples_json, tags FROM cards WHERE id=?",
            (next_id,),
        )
        row = await cur.fetchone()
        cur2 = await db.execute(
            "SELECT last_seen_at FROM progress WHERE user_id=? AND card_id=?",
            (user_id, next_id),
        )
        prow = await cur2.fetchone()
    if row:
        first_time_ever = prow is None or prow[0] is None
        first_time_this_session = next_id not in s.shown_card_ids
        is_new_badge = first_time_ever and first_time_this_session
        s.shown_card_ids.add(next_id)
        tags_list = [t for t in str(row[3] or "").split(",") if t]
        await cb.message.edit_text(
            html_card_message(row[0], row[1], row[2], is_new=is_new_badge, tags=tags_list),
            reply_markup=today_card_kb(next_id),
        )
    await cb.answer()


@router.callback_query(F.data == "round:repeat")
async def on_round_repeat(cb: CallbackQuery) -> None:
    assert cb.from_user
    user_id = cb.from_user.id
    today = datetime.now(timezone.utc).date()
    # Load config and day state
    async with get_db() as db:
        cur = await db.execute(
            "SELECT daily_new_target, review_limit_per_day, pack_tags FROM user_config WHERE user_id=?",
            (user_id,),
        )
        row = await cur.fetchone()
        cur2 = await db.execute(
            "SELECT served_review_count, shown_new_today FROM user_day_state WHERE user_id=? AND session_date=?",
            (user_id, today.isoformat()),
        )
        ds = await cur2.fetchone()
    daily_new_target = int(row[0]) if row else 8
    review_limit = int(row[1]) if row else 35
    pack_tags = (row[2] if row else "daily").split(",")
    served_reviews = int(ds[0]) if ds else 0
    shown_new = int(ds[1]) if ds else 0
    review_remaining = max(0, review_limit - served_reviews)
    new_remaining = max(0, daily_new_target - shown_new)

    s = await store.get(user_id)
    s.queue = await build_round_queue(user_id, today, pack_tags, review_remaining, new_remaining)
    if not s.queue:
        await cb.message.edit_text(
            "Nothing left for today 🎉", reply_markup=round_end_keyboard()
        )
        await cb.answer()
        return
    # Increment round index
    async with get_db() as db:
        await db.execute(
            "UPDATE user_day_state SET round_index=round_index+1, round_card_ids_json=? WHERE user_id=? AND session_date=?",
            ("[" + ",".join(str(i) for i in s.queue) + "]", user_id, today.isoformat()),
        )
        await db.commit()
    # Show first card of new round
    next_id = s.queue.pop(0)
    async with get_db() as db:
        cur = await db.execute(
            "SELECT phrasal, meaning_en, examples_json, tags FROM cards WHERE id=?",
            (next_id,),
        )
        row = await cur.fetchone()
        cur2 = await db.execute(
            "SELECT last_seen_at FROM progress WHERE user_id=? AND card_id=?",
            (user_id, next_id),
        )
        prow = await cur2.fetchone()
    if not row:
        await cb.message.edit_text("Card not found.")
    else:
        first_time_ever = prow is None or prow[0] is None
        first_time_this_session = next_id not in s.shown_card_ids
        is_new_badge = first_time_ever and first_time_this_session
        s.shown_card_ids.add(next_id)
        tags_list = [t for t in str(row[3] or "").split(",") if t]
        await cb.message.edit_text(
            html_card_message(row[0], row[1], row[2], is_new=is_new_badge, tags=tags_list),
            reply_markup=today_card_kb(next_id),
        )
    await cb.answer()


@router.callback_query(F.data.in_({"round:finish", "ui:today.finish"}))
async def on_round_finish(cb: CallbackQuery) -> None:
    assert cb.from_user
    user_id = cb.from_user.id
    today = datetime.now(timezone.utc).date()
    async with get_db() as db:
        cur = await db.execute(
            "SELECT good_today, again_today, shown_new_today, served_review_count FROM user_day_state WHERE user_id=? AND session_date=?",
            (user_id, today.isoformat()),
        )
        ds = await cur.fetchone()
    good_today = int(ds[0]) if ds else 0
    again_today = int(ds[1]) if ds else 0
    learned_today = int(ds[2]) if ds else 0
    reviews_done = int(ds[3]) if ds else 0
    summary = format_session_finished(
        good_today, again_today, learned_today, reviews_done
    )
    # Show menu after finishing
    await show_screen(
        bot=cb.message.bot,  # type: ignore[union-attr]
        user_id=user_id,
        text=f"{summary}\n\n<b>Main Menu</b>",
        reply_markup=kb_main_menu(),
        screen_id=SCREEN_MENU,
    )
    await store.clear(user_id)
    await cb.answer()
