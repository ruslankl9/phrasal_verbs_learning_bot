from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Sequence


@dataclass(frozen=True)
class NewCard:
    id: int
    phrasal: str
    sense_uid: str
    tags: list[str]


def select_new_cards(
    candidates: Sequence[NewCard],
    pack_tags: list[str],
    limit: int,
) -> list[NewCard]:
    """Select new cards honoring pack tags and uniqueness per phrasal/sense.

    - Only cards that have any overlap with pack_tags.
    - Do not introduce multiple senses of the same phrasal on the same day.
    - Do not duplicate sense_uid.
    """
    if limit == 0:
        return []

    tagset = {t.strip().lower() for t in pack_tags if t.strip()}
    seen_phrasal: set[str] = set()
    seen_sense: set[str] = set()
    picked: list[NewCard] = []

    for i in random.sample(range(len(candidates)), k=len(candidates)):
        c = candidates[i]
        if len(tagset) > 0:
            if not any(t in tagset for t in (t.lower() for t in c.tags)):
                continue
        # No duplicates per phrasal or sense
        if c.phrasal in seen_phrasal or c.sense_uid in seen_sense:
            continue
        seen_phrasal.add(c.phrasal)
        seen_sense.add(c.sense_uid)
        picked.append(c)
        if len(picked) >= limit:
            break
    return picked
