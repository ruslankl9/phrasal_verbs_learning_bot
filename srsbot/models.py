from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal, Optional

State = Literal["learning", "review"]
Answer = Literal["again", "good"]


@dataclass
class Card:
    id: int
    phrasal: str
    meaning_en: str
    examples_json: str
    tags: str
    sense_uid: str
    separable: bool
    intransitive: bool


@dataclass
class Progress:
    user_id: int
    card_id: int
    state: State
    box: int
    due_at: Optional[date]
    lapses: int
    learning_good_count: int
    last_answer: Optional[Answer]
    last_seen_at: Optional[datetime]


@dataclass
class UserConfig:
    user_id: int
    daily_new_target: int
    review_limit_per_day: int
    push_time: str
    pack_tags: str
    intra_spacing_k: int

