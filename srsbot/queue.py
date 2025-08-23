from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, Sequence

from srsbot.content import NewCard, select_new_cards
from srsbot.db import get_db


@dataclass(frozen=True)
class Item:
    card_id: int
    kind: str  # learning|review|new
    due_at: date | None = None


def rebalance_overdue(
    overdue: Sequence[Item],
    limit: int,
    today: date,
    days: int = 3,
) -> tuple[list[Item], list[tuple[int, date]]]:
    """Apply review cap and rebalance the remainder over next days.

    Returns (serve_today, rescheduled) where rescheduled is list of (card_id, new_due_date).
    """
    if len(overdue) <= limit:
        return list(overdue), []
    serve = list(overdue[:limit])
    remaining = overdue[limit:]
    rescheduled: list[tuple[int, date]] = []
    # Distribute evenly across next `days` days
    chunk = max(1, len(remaining) // days)
    d = 1
    i = 0
    for it in remaining:
        rescheduled.append((it.card_id, today + timedelta(days=d)))
        i += 1
        if i >= chunk and d < days:
            d += 1
            i = 0
    return serve, rescheduled


def build_daily_queue_view(
    learning_due: Sequence[Item],
    reviews_due: Sequence[Item],
    new_candidates: Sequence[Item],
    review_limit_per_day: int,
    daily_new_target: int,
) -> list[Item]:
    """Return ordered items for today's session: learning -> reviews -> new."""
    learning = list(learning_due)
    reviews = list(reviews_due[:review_limit_per_day])
    new = list(new_candidates[:daily_new_target])
    return learning + reviews + new


async def compute_daily_candidates(user_id: int, today: date) -> tuple[list[Item], list[Item], list[NewCard]]:
    """Compute learning due, reviews due (all), and new candidates (without limits)."""
    async with get_db() as db:
        # Learning due: any learning state for user
        cur = await db.execute(
            "SELECT card_id FROM progress WHERE user_id=? AND state='learning'",
            (user_id,),
        )
        learning_ids = [int(r[0]) for r in await cur.fetchall()]

        # Reviews due today or earlier
        cur = await db.execute(
            "SELECT card_id, due_at FROM progress WHERE user_id=? AND state='review' AND due_at<=date('now') ORDER BY due_at ASC",
            (user_id,),
        )
        reviews = [Item(int(r[0]), "review", today) for r in await cur.fetchall()]

        # New candidates: cards without progress for this user
        cur = await db.execute(
            """
            SELECT c.id, c.phrasal, c.sense_uid, c.tags FROM cards c
            LEFT JOIN progress p ON p.card_id=c.id AND p.user_id=?
            WHERE p.card_id IS NULL
            """,
            (user_id,),
        )
        new_rows = await cur.fetchall()
        new_candidates = [
            NewCard(id=int(r[0]), phrasal=str(r[1]), sense_uid=str(r[2]), tags=[t for t in (str(r[3] or "").split(",")) if t])
            for r in new_rows
        ]

    learning = [Item(cid, "learning") for cid in learning_ids]
    return learning, reviews, new_candidates


async def build_round_queue(
    user_id: int,
    today: date,
    pack_tags: list[str],
    review_remaining: int,
    new_remaining: int,
) -> list[int]:
    """Build a single round queue snapshot: learning -> limited reviews -> limited new."""
    learning, reviews_all, new_candidates = await compute_daily_candidates(user_id, today)
    reviews = list(reviews_all[: max(0, review_remaining)])
    picked_new = select_new_cards(new_candidates, pack_tags, limit=max(0, new_remaining))
    return [it.card_id for it in learning] + [it.card_id for it in reviews] + [c.id for c in picked_new]
