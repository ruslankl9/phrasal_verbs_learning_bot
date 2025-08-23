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
    "- /config: show current settings.\n"
    "  Example: /config daily_new_target=10 review_limit_per_day=40 pack_tags=work,travel\n"
    "- /pack tag[,tag2]: choose which tags to draw new cards from.\n"
    "- /stats: today/week accuracy and counts.\n"
    "- /snooze [hours]: delay today’s push (default 3h).\n\n"
    "Start now with /today. Happy learning!"
)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)
