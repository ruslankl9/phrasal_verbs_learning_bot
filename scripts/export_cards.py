#!/usr/bin/env python3
"""Export cards from SQLite to JSON.

Usage:
    python scripts/export_cards.py data/seed_cards.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from srsbot.db import get_db, init_db


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("json_path", type=Path, help="Output JSON path")
    args = parser.parse_args()

    await init_db()
    async with get_db() as db:
        cur = await db.execute(
            "SELECT phrasal, meaning_en, examples_json, tags, sense_uid, separable, intransitive FROM cards"
        )
        rows = await cur.fetchall()
    out = []
    for (
        phrasal,
        meaning_en,
        examples_json,
        tags,
        sense_uid,
        separable,
        intransitive,
    ) in rows:
        out.append(
            {
                "phrasal": phrasal,
                "meaning_en": meaning_en,
                "examples": json.loads(examples_json),
                "tags": tags.split(",") if tags else [],
                "sense_uid": sense_uid,
                "separable": bool(separable),
                "intransitive": bool(intransitive),
            }
        )
    args.json_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Exported {len(out)} cards to {args.json_path}")


if __name__ == "__main__":
    asyncio.run(main())

