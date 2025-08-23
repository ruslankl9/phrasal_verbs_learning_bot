from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message


router = Router()


HELP_TEXT = (
    "Learn English phrasal verbs with short daily SRS sessions.\n\n"
    "Basics:\n"
    "- /start: Initialize and see intro.\n"
    "- /today: Start or continue today’s session. Each card shows the phrasal verb, meaning, and examples with buttons: Again / Good.\n"
    "- Again: see the card again later in the session. Good: promote/schedule it further.\n\n"
    "How reviews work:\n"
    "- Queue order: learning due → reviews due today → new (limited).\n"
    "- Promotion: 2× Good in learning → move to Box 1 (due tomorrow).\n"
    "- Review Good: box +1 (max 7) with a jittered next date.\n"
    "- Review Again: back to learning; you’ll see it again this session.\n\n"
    "Daily pacing:\n"
    "- Daily new target adapts by accuracy (4–12).\n"
    "- Dynamic boost: every 5 consecutive Good may inject +1 new.\n\n"
    "Configuration:\n"
    "- /config: show or update settings. Example:\n"
    "  /config daily_new_target=10 review_limit_per_day=40 pack_tags=work,travel\n"
    "- /pack tag[,tag2]: quick way to set pack_tags for new cards.\n"
    "- /stats: today/week accuracy and counts.\n"
    "- /snooze [hours]: delay today’s push (default 3h).\n\n"
    "Config parameters:\n"
    "- daily_new_target: number of new cards introduced per day (4–12).\n"
    "- review_limit_per_day: maximum reviews served per day (20–60).\n"
    "- push_time: daily notification time in HH:MM (local timezone).\n"
    "- pack_tags: comma-separated tags used to pick new cards (e.g., work,travel,daily).\n"
    "- intra_spacing_k: how many other cards to wait before seeing a card again after Again/learning (default 3).\n\n"
    "Start now with /today. Happy learning!"
)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)
