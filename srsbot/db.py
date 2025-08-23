from __future__ import annotations

import contextlib
from datetime import date
from typing import AsyncIterator

import aiosqlite

from srsbot.config import DB_PATH

_SENTINEL = object()


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

            -- Per-day state for rounds and counters
            CREATE TABLE IF NOT EXISTS user_day_state (
                user_id INTEGER NOT NULL,
                session_date TEXT NOT NULL,
                round_index INTEGER NOT NULL DEFAULT 1,
                served_review_count INTEGER NOT NULL DEFAULT 0,
                shown_new_today INTEGER NOT NULL DEFAULT 0,
                good_today INTEGER NOT NULL DEFAULT 0,
                again_today INTEGER NOT NULL DEFAULT 0,
                round_card_ids_json TEXT,
                review_seen_ids_json TEXT,
                new_seen_ids_json TEXT,
                PRIMARY KEY (user_id, session_date)
            );
            CREATE INDEX IF NOT EXISTS ix_user_day_state_user_date ON user_day_state(user_id, session_date);

            -- UI state for inline navigation and message cleanup
            CREATE TABLE IF NOT EXISTS user_ui_state (
                user_id INTEGER PRIMARY KEY,
                last_ui_message_id INTEGER,
                current_screen TEXT,
                awaiting_input_field TEXT
            );
            """
        )
        await db.commit()
        # Migrations: add awaiting_input_field if missing
        try:
            await db.execute(
                "ALTER TABLE user_ui_state ADD COLUMN awaiting_input_field TEXT"
            )
            await db.commit()
        except Exception:
            pass


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


async def get_ui_state(user_id: int) -> aiosqlite.Row | None:
    """Return UI state row for a user if exists."""
    async with get_db() as db:
        cur = await db.execute(
            "SELECT user_id, last_ui_message_id, current_screen, awaiting_input_field FROM user_ui_state WHERE user_id=?",
            (user_id,),
        )
        return await cur.fetchone()


async def set_ui_state(
    user_id: int,
    last_ui_message_id: int | None = None,
    current_screen: str | None = None,
    awaiting_input_field: str | None | object = _SENTINEL,
) -> None:
    """Upsert UI state fields for the user."""
    # Read existing
    row = await get_ui_state(user_id)
    new_msg_id = last_ui_message_id if last_ui_message_id is not None else (
        int(row["last_ui_message_id"]) if row and row["last_ui_message_id"] is not None else None
    )
    new_screen = current_screen if current_screen is not None else (
        str(row["current_screen"]) if row and row["current_screen"] is not None else None
    )
    # Sentinel default means keep existing
    if awaiting_input_field is _SENTINEL:  # keep existing
        new_awaiting = row["awaiting_input_field"] if row else None
    else:
        new_awaiting = awaiting_input_field
    async with get_db() as db:
        await db.execute(
            "INSERT INTO user_ui_state(user_id, last_ui_message_id, current_screen, awaiting_input_field) VALUES(?,?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET last_ui_message_id=excluded.last_ui_message_id, current_screen=excluded.current_screen, awaiting_input_field=excluded.awaiting_input_field",
            (user_id, new_msg_id, new_screen, new_awaiting),
        )
        await db.commit()


async def clear_ui_message(user_id: int) -> None:
    """Clear stored UI message id for the user (screen unchanged)."""
    async with get_db() as db:
        await db.execute(
            "UPDATE user_ui_state SET last_ui_message_id=NULL WHERE user_id=?",
            (user_id,),
        )
        await db.commit()


async def set_awaiting_input(user_id: int, field: str | None) -> None:
    """Set or clear the awaiting input field in UI state."""
    await set_ui_state(user_id, awaiting_input_field=field)


async def get_day_state(user_id: int, session_date: str) -> aiosqlite.Row | None:
    async with get_db() as db:
        cur = await db.execute(
            "SELECT * FROM user_day_state WHERE user_id=? AND session_date=?",
            (user_id, session_date),
        )
        return await cur.fetchone()


async def init_or_get_day_state(user_id: int, session_date: str) -> aiosqlite.Row:
    async with get_db() as db:
        cur = await db.execute(
            "SELECT * FROM user_day_state WHERE user_id=? AND session_date=?",
            (user_id, session_date),
        )
        row = await cur.fetchone()
        if row is None:
            await db.execute(
                """
                INSERT INTO user_day_state(user_id, session_date, round_index, served_review_count, shown_new_today, good_today, again_today, round_card_ids_json, review_seen_ids_json, new_seen_ids_json)
                VALUES(?, ?, 1, 0, 0, 0, 0, NULL, '[]', '[]')
                """,
                (user_id, session_date),
            )
            await db.commit()
            cur = await db.execute(
                "SELECT * FROM user_day_state WHERE user_id=? AND session_date=?",
                (user_id, session_date),
            )
            row = await cur.fetchone()
        return row  # type: ignore[return-value]


async def update_day_state(
    user_id: int,
    session_date: str,
    **fields: object,
) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields.keys())
    vals = list(fields.values()) + [user_id, session_date]
    async with get_db() as db:
        await db.execute(
            f"UPDATE user_day_state SET {cols} WHERE user_id=? AND session_date=?",
            vals,
        )
        await db.commit()


async def increment_day_counters(
    user_id: int,
    session_date: str,
    good_delta: int = 0,
    again_delta: int = 0,
    review_served_delta: int = 0,
    new_shown_delta: int = 0,
) -> None:
    async with get_db() as db:
        await db.execute(
            """
            UPDATE user_day_state
            SET good_today = good_today + ?,
                again_today = again_today + ?,
                served_review_count = served_review_count + ?,
                shown_new_today = shown_new_today + ?
            WHERE user_id=? AND session_date=?
            """,
            (good_delta, again_delta, review_served_delta, new_shown_delta, user_id, session_date),
        )
        await db.commit()
