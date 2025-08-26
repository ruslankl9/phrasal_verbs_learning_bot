from __future__ import annotations

import asyncio
from contextlib import suppress

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message

from srsbot.config import BOT_TOKEN
from srsbot.db import init_db
from srsbot.handlers import menu, packs, settings, snooze, start, stats, today, quiz
from srsbot.scheduler import daily_tick


async def run_scheduler(bot: Bot) -> None:
    while True:
        await daily_tick(bot)
        await asyncio.sleep(60)


# Local router for simple, app-wide commands
router = Router()


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set. Please configure .env")

    await init_db()
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Built-in help
    dp.include_router(router)

    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(today.router)
    dp.include_router(settings.router)
    dp.include_router(packs.router)
    dp.include_router(stats.router)
    dp.include_router(snooze.router)
    dp.include_router(quiz.router)

    # Background scheduler
    asyncio.create_task(run_scheduler(bot))

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        asyncio.run(main())
