#!/usr/bin/env python3
"""Export cards from SQLite to CSV.

Usage:
    python scripts/export_cards.py data/export_cards.csv
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
from pathlib import Path

from srsbot.db import get_db, init_db


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path, help="Output CSV path")
    args = parser.parse_args()

    await init_db()
    async with get_db() as db:
        cur = await db.execute(
            "SELECT phrasal, meaning_en, examples_json, tags, sense_uid, separable, intransitive FROM cards"
        )
        rows = await cur.fetchall()
    header = [
        "phrasal",
        "meaning_en",
        "examples",
        "tags",
        "sense_uid",
        "separable",
        "intransitive",
    ]
    rows_out = []
    for (
        phrasal,
        meaning_en,
        examples_json,
        tags,
        sense_uid,
        separable,
        intransitive,
    ) in rows:
        examples = json.loads(examples_json)
        tags_list = [t for t in (tags or "").split(",") if t]
        rows_out.append(
            (
                phrasal,
                meaning_en,
                json.dumps(examples, ensure_ascii=False, separators=(",", ":")),
                json.dumps(tags_list, ensure_ascii=False, separators=(",", ":")),
                sense_uid,
                "true" if separable else "false",
                "true" if intransitive else "false",
            )
        )
    with args.csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(header)
        writer.writerows(rows_out)
    print(f"Exported {len(rows_out)} cards to {args.csv_path}")


if __name__ == "__main__":
    asyncio.run(main())
