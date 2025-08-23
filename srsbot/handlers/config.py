from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..db import get_db


router = Router()


@router.message(Command("config"))
async def cmd_config(message: Message) -> None:
    assert message.from_user
    user_id = message.from_user.id
    text = (message.text or "").strip()
    # Usage examples:
    # /config daily_new_target=10 review_limit_per_day=40 push_time=08:30 pack_tags=work,travel intra_spacing_k=3
    parts = text.split()[1:]
    updates = {}
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1)
            updates[k.strip()] = v.strip()
    if updates:
        # Validate bounds
        if "daily_new_target" in updates:
            v = max(4, min(12, int(updates["daily_new_target"])))
            updates["daily_new_target"] = v
        if "review_limit_per_day" in updates:
            v = max(20, min(60, int(updates["review_limit_per_day"])))
            updates["review_limit_per_day"] = v
        if "intra_spacing_k" in updates:
            v = max(1, min(8, int(updates["intra_spacing_k"])))
            updates["intra_spacing_k"] = v

        sets = ", ".join(f"{k}=?" for k in updates.keys())
        async with get_db() as db:
            await db.execute(
                f"UPDATE user_config SET {sets} WHERE user_id=?",
                (*updates.values(), user_id),
            )
            await db.commit()
        await message.answer("Config updated.")
        return

    # Show current config
    async with get_db() as db:
        cur = await db.execute(
            "SELECT daily_new_target, review_limit_per_day, push_time, pack_tags, intra_spacing_k"
            " FROM user_config WHERE user_id=?",
            (user_id,),
        )
        row = await cur.fetchone()
    if not row:
        await message.answer("No config found. Use /start first.")
        return
    await message.answer(
        "Your config:\n"
        f"daily_new_target: {row[0]}\n"
        f"review_limit_per_day: {row[1]}\n"
        f"push_time: {row[2]}\n"
        f"pack_tags: {row[3]}\n"
        f"intra_spacing_k: {row[4]}\n"
        "\nUpdate with: /config key=value ..."
    )

