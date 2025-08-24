#!/usr/bin/env python3
from __future__ import annotations
from sqlite3 import Row
from typing import Iterable

"""Build a single-line, comma-separated known list of phrasals and sense_uids.

Usage:
    python scripts/build_known_list.py --out data/known_phrasals.txt
"""

import argparse
import asyncio
from pathlib import Path

from srsbot.db import get_db, init_db


def build_known_line(rows: Iterable[Row]) -> list[str]:
    """Return single-line, comma-separated lowercase list from inputs.

    Duplicates removed, order sorted for determinism.
    """
    items: set[str] = set()
    for row in rows:
        phrasals = row[0].strip().lower()
        sense_uids = row[1].strip().lower()

        items.add(f"{phrasals}({sense_uids})")

    return sorted(items)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path, help="Output path for known list")
    args = parser.parse_args()

    await init_db()
    async with get_db() as db:
        cur = await db.execute("SELECT phrasal, sense_uid FROM cards")
        rows = await cur.fetchall()
    items = build_known_line(rows)
    content = ",".join(items)
    args.out.write_text(content, encoding="utf-8")
    print(f"Wrote known list with {len(items)} items to {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
