from __future__ import annotations

import contextlib
from datetime import date
from typing import AsyncIterator

import aiosqlite

from .config import DB_PATH


@contextlib.asynccontextmanager
async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    db = await aiosqlite.connect(DB_PATH.as_posix())
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def init_db() -> None:
    async with get_db() as db:
        await db.executescript(
            """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY,
                phrasal TEXT NOT NULL,
                meaning_en TEXT NOT NULL,
                examples_json TEXT NOT NULL,
                tags TEXT,
                sense_uid TEXT UNIQUE NOT NULL,
                separable INTEGER NOT NULL DEFAULT 0,
                intransitive INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS progress (
                user_id INTEGER NOT NULL,
                card_id INTEGER NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('learning','review')),
                box INTEGER NOT NULL DEFAULT 0,
                due_at DATE,
                lapses INTEGER NOT NULL DEFAULT 0,
                learning_good_count INTEGER NOT NULL DEFAULT 0,
                last_answer TEXT,
                last_seen_at DATETIME,
                PRIMARY KEY(user_id, card_id)
            );

            CREATE INDEX IF NOT EXISTS idx_progress_user_due ON progress(user_id, due_at);
            CREATE INDEX IF NOT EXISTS idx_progress_user_state ON progress(user_id, state);

            CREATE TABLE IF NOT EXISTS user_config (
                user_id INTEGER PRIMARY KEY,
                daily_new_target INTEGER NOT NULL DEFAULT 8,
                review_limit_per_day INTEGER NOT NULL DEFAULT 35,
                push_time TEXT NOT NULL DEFAULT '09:00',
                pack_tags TEXT NOT NULL DEFAULT 'daily',
                intra_spacing_k INTEGER NOT NULL DEFAULT 3
            );

            -- Additional lightweight state for scheduling and stats
            CREATE TABLE IF NOT EXISTS user_state (
                user_id INTEGER PRIMARY KEY,
                last_notified_date DATE,
                snoozed_until DATETIME,
                streak_days INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS answers (
                user_id INTEGER NOT NULL,
                card_id INTEGER NOT NULL,
                answer TEXT NOT NULL CHECK(answer IN ('again','good')),
                ts DATETIME NOT NULL DEFAULT (datetime('now')),
                is_new INTEGER NOT NULL DEFAULT 0,
                tags TEXT
            );
            """
        )
        await db.commit()


async def ensure_user_config(user_id: int) -> None:
    async with get_db() as db:
        cur = await db.execute("SELECT 1 FROM user_config WHERE user_id=?", (user_id,))
        if await cur.fetchone() is None:
            await db.execute("INSERT INTO user_config(user_id) VALUES (?)", (user_id,))
            await db.execute("INSERT OR IGNORE INTO user_state(user_id) VALUES (?)", (user_id,))
            await db.commit()


async def get_push_time(user_id: int) -> str:
    async with get_db() as db:
        cur = await db.execute("SELECT push_time FROM user_config WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        return row[0] if row else "09:00"


async def update_last_notified(user_id: int, d: date) -> None:
    async with get_db() as db:
        await db.execute(
            "UPDATE user_state SET last_notified_date=? WHERE user_id=?", (d.isoformat(), user_id)
        )
        await db.commit()

