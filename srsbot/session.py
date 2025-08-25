from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class SessionData:
    queue: List[int] = field(default_factory=list)
    shown: int = 0
    good: int = 0
    consecutive_good: int = 0
    shown_card_ids: Set[int] = field(default_factory=set)


class SessionStore:
    def __init__(self) -> None:
        self._data: Dict[int, SessionData] = {}
        self._lock = asyncio.Lock()

    async def get(self, user_id: int) -> SessionData:
        async with self._lock:
            return self._data.setdefault(user_id, SessionData())

    async def clear(self, user_id: int) -> None:
        async with self._lock:
            self._data.pop(user_id, None)


store = SessionStore()
