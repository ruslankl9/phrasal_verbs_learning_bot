from __future__ import annotations

from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from ..db import get_db, init_db
from ..formatters import render_card
from ..keyboards import answer_kb
from ..models import Progress
from ..session import store
from ..srs import AnswerResult, on_answer


router = Router()


@router.message(Command("today"))
async def cmd_today(message: Message) -> None:
    assert message.from_user
    user_id = message.from_user.id
    s = await store.get(user_id)
    if not s.queue:
        # Build a simple queue from DB: learning due, reviews due today, then some new
        await init_db()
        async with get_db() as db:
            # learning due
            cur = await db.execute(
                "SELECT card_id FROM progress WHERE user_id=? AND state='learning'",
                (user_id,),
            )
            learning = [r[0] for r in await cur.fetchall()]

            # reviews due (<= today)
            cur = await db.execute(
                "SELECT card_id FROM progress WHERE user_id=? AND state='review' AND due_at<=date('now') ORDER BY due_at ASC",
                (user_id,),
            )
            reviews = [r[0] for r in await cur.fetchall()]

            # config
            cur = await db.execute(
                "SELECT daily_new_target, review_limit_per_day, pack_tags FROM user_config WHERE user_id=?",
                (user_id,),
            )
            row = await cur.fetchone()
            daily_new_target = int(row[0]) if row else 8
            review_limit = int(row[1]) if row else 35
            pack_tags = (row[2] if row else "daily").split(",")

            # limit reviews and add new cards from packs
            reviews = reviews[:review_limit]
            # new candidates: cards without progress for this user
            cur = await db.execute(
                """
                SELECT c.id FROM cards c
                LEFT JOIN progress p ON p.card_id=c.id AND p.user_id=?
                WHERE p.card_id IS NULL
                """,
                (user_id,),
            )
            new_all = [r[0] for r in await cur.fetchall()]

            # Filter by pack tags
            filtered_new: list[int] = []
            seen_phrasal: set[str] = set()
            seen_sense: set[str] = set()
            tagset = {t.strip().lower() for t in pack_tags if t.strip()}
            if tagset:
                for cid in new_all:
                    cur = await db.execute(
                        "SELECT tags, phrasal, sense_uid FROM cards WHERE id=?", (cid,)
                    )
                    row = await cur.fetchone()
                    tags = (row[0] or "").lower().split(",")
                    phrasal = str(row[1])
                    sense_uid = str(row[2])
                    if any(t in tagset for t in tags):
                        if phrasal in seen_phrasal or sense_uid in seen_sense:
                            continue
                        seen_phrasal.add(phrasal)
                        seen_sense.add(sense_uid)
                        filtered_new.append(cid)
            else:
                # No tag filter, still avoid duplicates per phrasal/sense
                for cid in new_all:
                    cur = await db.execute(
                        "SELECT phrasal, sense_uid FROM cards WHERE id=?", (cid,)
                    )
                    row = await cur.fetchone()
                    phrasal = str(row[0])
                    sense_uid = str(row[1])
                    if phrasal in seen_phrasal or sense_uid in seen_sense:
                        continue
                    seen_phrasal.add(phrasal)
                    seen_sense.add(sense_uid)
                    filtered_new.append(cid)

            new = filtered_new[:daily_new_target]
            s.queue = learning + reviews + new

    if not s.queue:
        await message.answer("You have nothing scheduled today. Enjoy your day!")
        return

    next_id = s.queue.pop(0)
    async with get_db() as db:
        cur = await db.execute(
            "SELECT phrasal, meaning_en, examples_json FROM cards WHERE id=?",
            (next_id,),
        )
        row = await cur.fetchone()
    if not row:
        await message.answer("Card not found.")
        return
    await message.answer(render_card(row[0], row[1], row[2]), reply_markup=answer_kb(next_id))


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
        s.consecutive_good += 1
    else:
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

    if not s.queue:
        # Adjust daily_new_target by accuracy
        accuracy = (s.good / s.shown) if s.shown > 0 else 0.0
        async with get_db() as db:
            cur = await db.execute(
                "SELECT daily_new_target FROM user_config WHERE user_id=?", (user_id,)
            )
            row = await cur.fetchone()
            dnt = int(row[0]) if row else 8
            if accuracy >= 0.8:
                dnt = min(12, dnt + 2)
            elif accuracy < 0.6:
                dnt = max(4, dnt - 2)
            await db.execute(
                "UPDATE user_config SET daily_new_target=? WHERE user_id=?", (dnt, user_id)
            )
            await db.commit()
        await cb.message.answer(
            f"Session complete. Accuracy: {accuracy:.0%}. Daily new target is now {dnt}."
        )
        await store.clear(user_id)
        await cb.answer()
        return

    # Show next card
    next_id = s.queue.pop(0)
    async with get_db() as db:
        cur = await db.execute(
            "SELECT phrasal, meaning_en, examples_json FROM cards WHERE id=?",
            (next_id,),
        )
        row = await cur.fetchone()
    if row:
        await cb.message.edit_text(
            render_card(row[0], row[1], row[2]), reply_markup=answer_kb(next_id)
        )
    await cb.answer()
