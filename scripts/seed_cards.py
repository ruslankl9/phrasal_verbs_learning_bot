#!/usr/bin/env python3
"""Seed the SQLite database with cards from a JSON file.

Usage:
    python scripts/seed_cards.py data/seed_cards.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from srsbot.db import get_db, init_db


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("json_path", type=Path, help="Path to seed JSON file")
    args = parser.parse_args()

    await init_db()
    async with get_db() as db:
        with args.json_path.open("r", encoding="utf-8") as f:
            cards: list[dict[str, Any]] = json.load(f)
        for c in cards:
            await db.execute(
                """
                INSERT OR IGNORE INTO cards
                (phrasal, meaning_en, examples_json, tags, sense_uid, separable, intransitive)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    c["phrasal"],
                    c["meaning_en"],
                    json.dumps(c["examples"], ensure_ascii=False),
                    ",".join(c.get("tags", [])),
                    c["sense_uid"],
                    1 if c.get("separable") else 0,
                    1 if c.get("intransitive") else 0,
                ),
            )
        await db.commit()
    print(f"Imported {len(cards)} cards into the database.")


if __name__ == "__main__":
    asyncio.run(main())

