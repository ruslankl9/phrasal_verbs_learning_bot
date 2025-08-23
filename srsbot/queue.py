from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, Sequence


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

