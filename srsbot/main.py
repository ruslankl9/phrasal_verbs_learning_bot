from __future__ import annotations

import asyncio
from contextlib import suppress

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message

from .config import BOT_TOKEN
from .db import init_db
from .handlers import config as cfg_handler
from .handlers import help as help_handler
from .handlers import pack, packs, snooze, start, stats, today
from .scheduler import daily_tick


async def run_scheduler(bot: Bot) -> None:
    while True:
        await daily_tick(bot)
        await asyncio.sleep(60)


# Local router for simple, app-wide commands
router = Router()


# @router.message(Command("help"))
# async def cmd_help(message: Message) -> None:
#     await message.answer(
#         "Available commands:\n"
#         "/start — Intro and opt-in. Creates default config.\n"
#         "/today — Start or continue today’s session with Again/Good buttons.\n"
#         "/config — Configure daily_new_target (4–12), review_limit_per_day (20–60), push_time (HH:MM), pack_tags (comma-separated), intra_spacing_k.\n"
#         "/pack <tag> — Switch pack/tag filter for new cards (e.g., work, travel, daily).\n"
#         "/stats — Shows streak, new learned today, reviews done, accuracy (today/week), hardest tag.\n"
#         "/snooze — Snooze today’s notification by N hours (default 3h)."
#     )


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set. Please configure .env")

    await init_db()
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Built-in help
    dp.include_router(router)

    dp.include_router(start.router)
    dp.include_router(help_handler.router)
    dp.include_router(today.router)
    dp.include_router(cfg_handler.router)
    dp.include_router(pack.router)
    dp.include_router(packs.router)
    dp.include_router(stats.router)
    dp.include_router(snooze.router)

    # Background scheduler
    asyncio.create_task(run_scheduler(bot))

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        asyncio.run(main())
