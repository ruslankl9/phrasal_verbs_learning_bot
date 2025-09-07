from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Final

from dotenv import load_dotenv


load_dotenv()

ROOT_DIR: Final[Path] = Path(__file__).resolve().parents[1]
DATA_DIR: Final[Path] = Path(os.getenv("DATA_DIR", str(ROOT_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH: Final[Path] = DATA_DIR / "bot.db"

BOT_TOKEN: Final[str] = os.getenv("BOT_TOKEN", "")
DEFAULT_PUSH_TIME: Final[str] = os.getenv("PUSH_TIME", "09:00")
DEFAULT_TZ: Final[str] = os.getenv("TZ", "Asia/Yerevan")

# Explain feature configuration
EXPLAIN_API_BASE: Final[str] = os.getenv("EXPLAIN_API_BASE", "")
EXPLAIN_API_KEY: Final[str] | None = os.getenv("EXPLAIN_API_KEY") or "no-key"
EXPLAIN_MODEL: Final[str] = os.getenv("EXPLAIN_MODEL", "gpt-4o-mini")
EXPLAIN_TIMEOUT_SECONDS: Final[int] = int(os.getenv("EXPLAIN_TIMEOUT_SECONDS", "30"))

# Leitner intervals in days for boxes 1..7
BOX_INTERVALS: Final[dict[int, int]] = {
    1: 1,
    2: 3,
    3: 7,
    4: 14,
    5: 30,
    6: 60,
    7: 120,
}

JITTER_PCT: Final[float] = 0.15


def parse_push_time(s: str | None) -> time:
    s = s or DEFAULT_PUSH_TIME
    hh, mm = s.split(":", 1)
    return time(hour=int(hh), minute=int(mm))


@dataclass(frozen=True)
class Today:
    today: date
    now: datetime
