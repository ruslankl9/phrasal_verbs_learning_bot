from __future__ import annotations

"""Input validators for Settings inline UI."""

from typing import Tuple


def validate_int_in_range(text: str, lo: int, hi: int) -> Tuple[bool, str | None]:
    try:
        v = int(text.strip())
    except ValueError:
        return False, f"Invalid value. Expected an integer between {lo} and {hi}."
    if not (lo <= v <= hi):
        return False, f"Invalid value. Expected an integer between {lo} and {hi}."
    return True, None


def validate_hhmm(text: str) -> Tuple[bool, str | None]:
    s = text.strip()
    if len(s) != 5 or s[2] != ":" or not (s[:2].isdigit() and s[3:].isdigit()):
        return False, "Invalid time. Expected HH:MM (24h)."
    hh = int(s[:2])
    mm = int(s[3:])
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return False, "Invalid time. Hours 00–23 and minutes 00–59."
    return True, None


def validate_timezone(text: str) -> Tuple[bool, str | None]:
    # Optional: accept non-empty tokens with at least one slash
    s = text.strip()
    if "/" not in s or len(s) < 3:
        return False, "Invalid timezone. Expected format like Europe/Berlin."
    return True, None

