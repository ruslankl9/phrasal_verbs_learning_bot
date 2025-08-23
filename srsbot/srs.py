from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from srsbot.config import BOX_INTERVALS, JITTER_PCT
from srsbot.models import Answer, Progress


def next_due_for_box(box: int, base_date: date) -> date:
    """Return the next due date for a box with ±15% jitter.

    Box should be in 1..7. The base_date is the reference (usually today).
    """
    interval = BOX_INTERVALS.get(box, BOX_INTERVALS[7])
    jitter = int(round(interval * JITTER_PCT))
    delta = interval + random.randint(-jitter, jitter)
    delta = max(1, delta)
    return base_date + timedelta(days=delta)


@dataclass
class AnswerResult:
    progress: Progress
    requeue_after: Optional[int]  # k positions; None means not requeued for today


def on_answer(progress: Progress, answer: Answer, today: date, k: int = 3) -> AnswerResult:
    """Apply SRS rules for an answer and return updated progress and requeue hint.

    For learning:
      - Again: reset learning_good_count, requeue after k
      - Good: increment; if >=2 -> switch to review box 1, due tomorrow; else requeue after k

    For review:
      - Again: move to learning, reset counter, lapses +1, requeue after k
      - Good: bump box (cap 7), schedule next due via jitter
    """
    p = progress
    p.last_answer = answer

    if p.state == "learning":
        if answer == "again":
            p.learning_good_count = 0
            return AnswerResult(p, requeue_after=None)
        else:
            p.learning_good_count += 1
            if p.learning_good_count >= 2:
                p.state = "review"
                p.box = 1
                p.due_at = today + timedelta(days=1)
                p.learning_good_count = 0
                return AnswerResult(p, requeue_after=None)
            else:
                return AnswerResult(p, requeue_after=k)

    # review
    if answer == "again":
        p.state = "learning"
        p.learning_good_count = 0
        p.lapses += 1
        p.box = 0
        p.due_at = None
        return AnswerResult(p, requeue_after=None)
    else:
        p.box = min(p.box + 1, 7)
        p.due_at = next_due_for_box(p.box, today)
        return AnswerResult(p, requeue_after=None)

