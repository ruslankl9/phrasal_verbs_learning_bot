import asyncio
from pathlib import Path

import pytest

from srsbot.db import init_db, get_explanation_cached, store_explanation



@pytest.mark.asyncio
async def test_explain_cache_store_and_get(tmp_path, monkeypatch):
    # Use a temp SQLite DB for isolation
    db_file: Path = tmp_path / "test.db"

    # Patch srsbot.db.DB_PATH so all DB operations go to the temp file
    import srsbot.db as dbmod

    monkeypatch.setattr(dbmod, "DB_PATH", db_file, raising=False)

    await init_db()

    try:
        card_id = 42
        assert await get_explanation_cached(card_id) is None

        content = "This is an explanation."
        await store_explanation(card_id, content)

        got = await get_explanation_cached(card_id)
        assert got == content
    finally:
        # Cleanup DB and WAL/SHM files explicitly (tmp_path also auto-cleans)
        wal = db_file.with_name(db_file.name + "-wal")
        shm = db_file.with_name(db_file.name + "-shm")
        for p in (wal, shm, db_file):
            try:
                p.unlink()
            except FileNotFoundError:
                pass
