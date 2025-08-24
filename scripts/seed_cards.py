#!/usr/bin/env python3
"""Seed the SQLite database with cards from a CSV file.

CSV schema (header required):
phrasal,meaning_en,examples,tags,sense_uid,separable,intransitive

Usage:
    python scripts/seed_cards.py data/seed_cards.csv
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
from pathlib import Path
from typing import Any, Iterable

from srsbot.db import get_db, init_db


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path, help="Path to seed CSV file")
    args = parser.parse_args()

    await init_db()
    # Parse CSV with validation and dedupe by sense_uid
    cards: list[dict[str, Any]] = list(parse_seed_csv(args.csv_path))
    async with get_db() as db:
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
                    json.dumps(c["examples"], ensure_ascii=False, separators=(",", ":")),
                    ",".join(c.get("tags", [])),
                    c["sense_uid"],
                    1 if c.get("separable") else 0,
                    1 if c.get("intransitive") else 0,
                ),
            )
        await db.commit()
    print(f"Imported {len(cards)} cards into the database.")


def parse_seed_csv(path: Path) -> Iterable[dict[str, Any]]:
    """Yield validated card dicts from the seed CSV.

    Validates header order, JSON arrays in `examples`/`tags`, and boolean fields.
    Duplicates by sense_uid in the file are ignored.
    """
    required_header = [
        "phrasal",
        "meaning_en",
        "examples",
        "tags",
        "sense_uid",
        "separable",
        "intransitive",
    ]
    seen_sense: set[str] = set()
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        if header != required_header:
            raise SystemExit(
                f"Invalid header. Expected {required_header}, got {header}"
            )
        for i, row in enumerate(reader, start=2):
            phrasal = (row.get("phrasal") or "").strip()
            meaning_en = (row.get("meaning_en") or "").strip()
            if not phrasal or not meaning_en:
                raise SystemExit(f"Row {i}: empty phrasal or meaning_en")
            # JSON arrays
            try:
                ex = json.loads(row.get("examples") or "[]")
                if not (isinstance(ex, list) and 2 <= len(ex) <= 3 and all(isinstance(x, str) for x in ex)):
                    raise ValueError
            except Exception as exc:
                raise SystemExit(f"Row {i}: invalid examples JSON array: {row.get('examples')}. {exc}")
            try:
                tags = json.loads(row.get("tags") or "[]")
                if not (isinstance(tags, list) and all(isinstance(x, str) for x in tags)):
                    raise ValueError
            except Exception:
                raise SystemExit(f"Row {i}: invalid tags JSON array")
            sense_uid = (row.get("sense_uid") or "").strip()
            if not sense_uid:
                raise SystemExit(f"Row {i}: empty sense_uid")
            if sense_uid in seen_sense:
                # Skip duplicates in file
                continue
            seen_sense.add(sense_uid)
            # booleans
            sep = (row.get("separable") or "").strip().lower()
            intr = (row.get("intransitive") or "").strip().lower()
            if sep not in {"true", "false"} or intr not in {"true", "false"}:
                raise SystemExit(f"Row {i}: booleans must be true|false")
            yield {
                "phrasal": phrasal,
                "meaning_en": meaning_en,
                "examples": ex,
                "tags": tags,
                "sense_uid": sense_uid,
                "separable": sep == "true",
                "intransitive": intr == "true",
            }


if __name__ == "__main__":
    asyncio.run(main())
