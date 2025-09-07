import asyncio

import pytest

from srsbot.db import init_db, get_explanation_cached, store_explanation


@pytest.mark.asyncio
async def test_explain_cache_store_and_get(tmp_path, monkeypatch):
    # Ensure DB initialized
    await init_db()

    card_id = 42
    assert await get_explanation_cached(card_id) is None

    content = "This is an explanation."
    await store_explanation(card_id, content)

    got = await get_explanation_cached(card_id)
    assert got == content

