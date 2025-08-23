# Phrasal Verbs SRS Telegram Bot

A minimal, production-ready Telegram bot to learn English phrasal verbs using a session-based spaced repetition system (Leitner-style) optimized for 1–2 daily sessions. Built with Python 3.11, aiogram v3, aiosqlite, and a simple daily scheduler.

## How It Works

- States: `learning` and `review`.
- Leitner Boxes and intervals (days): 1:1, 2:3, 3:7, 4:14, 5:30, 6:60, 7:120.
- Graduation: while `learning`, two Good answers in the same session promote to `review` Box 1 due tomorrow. `Again` requeues after `k` other cards (default 3).
- Reviews: `Good` increases box (cap 7) and schedules next review with ±15% jitter. `Again` moves the card back to `learning` and requeues after `k`.
- Daily queue priority: learning due → reviews due (capped, with overload rebalancing) → new (respecting pack tags and daily new target).
- Adaptive daily new target: starts at 8, +2 up to 12 if session accuracy ≥ 0.8, −2 down to 4 if < 0.6.
- Dynamic boost: every 5 consecutive Good in a session injects +1 new card (up to that day’s limit).

## Commands

- `/start` — Intro and opt-in. Creates default config.
- `/menu` — Open the inline Main Menu (Today, Settings, Stats, Snooze).
- `/today` — Start or continue today’s session with Again/Good buttons.
- `/settings` — Open Settings; edit Daily new cards, Review cap, Notification time, Packs, In-round spacing via inline UI with validation.
- `/stats` — Shows streak, new learned today, reviews done, accuracy (today/week).
- `/snooze` — Snooze today’s notification by N hours (default 3h) or open snooze screen.

## Setup

- Python: 3.11
- Install via Poetry (recommended):

```bash
poetry install
```

Or using pip:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment

Copy `.env.example` to `.env` and set values:

```
BOT_TOKEN=123456:ABC-DEF...
PUSH_TIME=09:00
TZ=Asia/Yerevan
```

## Running

Using Poetry:

```bash
poetry run python -m srsbot.main
```

Or via Makefile:

```bash
make run
```

## Database and Seeding

- The SQLite DB is stored in `data/bot.db` (auto-created).
- Seed at least 40 sample cards:

```bash
python scripts/seed_cards.py data/seed_cards.json
```

Export cards back to JSON for maintenance:

```bash
python scripts/export_cards.py data/seed_cards.json
```

## Lint/Format/Typecheck/Tests

```bash
make lint
make fmt
make typecheck
make test
```

## Docker

Build and run with Docker Compose:

```bash
docker compose up --build
```

The bot reads `.env` for the token and config.

## Menu Navigation

- Open the menu with `/menu` or `/help`.
- The bot keeps a single active UI message; navigating between screens edits that message (or replaces it) to keep chat history clean.
- Screens:
  - `▶️ Today`: study cards with Again/Good and a persistent `🏁 Finish session` button. When finished, you see a short summary and return to the menu.
  - `⚙️ Settings`: edit fields with per-item buttons; scalar values open an inline input screen with validation; `🧩 Active packs` lives here with checkbox toggles; Back returns cleanly.
  - `📊 Stats`: view today/week stats with Back.
  - `😴 Snooze`: quick +1h/+3h/+6h options with Back.

## License

MIT
