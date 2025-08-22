
# PROJECT BRIEF (Build from scratch): Telegram SRS Bot for Phrasal Verbs (Python, aiogram, SQLite)

You are an expert software engineer. Create a production-ready, minimal yet robust Telegram bot that helps users learn **English phrasal verbs** using a **session-based spaced repetition** system tailored for 1–2 daily study sessions (no second/minute learning timers). Implement clean architecture, type hints, docstrings, tests, and clear docs. Generate all files listed below.

### Tech & Constraints

* Language: **Python 3.11**
* Framework: **aiogram v3** (async/await)
* Storage: **SQLite** via **aiosqlite**
* Scheduling: daily push notifications via **APScheduler** (or an asyncio task + simple daily tick)
* Packaging: **poetry** (preferred) or **pip + requirements.txt**
* Deployment: **Dockerfile**, **docker-compose.yml**
* Lint/format: **ruff**, **black**, **mypy**
* Env: `.env` with `BOT_TOKEN`, optional `PUSH_TIME` (default `09:00`), `TZ` (default `Asia/Yerevan`)
* License: MIT

### Core Learning Model (Leitner-style with session repeats)

* Card states: `learning`, `review`
* Boxes & intervals (days):
  `1:1, 2:3, 3:7, 4:14, 5:30, 6:60, 7:120` (Box 0 is implicit “learning” in-session)
* **Graduation** from `learning` to `review` Box 1 after **2 Good** answers within the same session (answers separated by 2–4 other cards).
* In-session repeat: **Again** → requeue after `k=3` other cards (configurable).
* Between sessions:

  * **Good** on review → box +1 (cap 7), next due = today + interval(box) with jitter ±15%.
  * **Again** on review → move to `learning`, reset in-session counter.
* Avoid micro-intervals like 10s/60s/10m entirely.

### Daily Session Logic

* Queue priority: `learning due` → `review due (<= today)` → `new` (subject to daily new target).
* **Daily new target** default: 8 (adaptive):

  * After each session compute `accuracy = good / shown`.
  * If `accuracy ≥ 0.8` → increase daily new target by +2 (max 12).
  * If `accuracy < 0.6` → decrease by −2 (min 4).
* **Review limit per day**: default 35. If more are overdue, serve oldest first and **rebalance** the remainder over the next 2–3 days (do not zero intervals).
* Dynamic boost during session: every 5 consecutive **Good**, allow injecting +1 additional new card (up to that day’s new limit).

### Content & Cards

* Each card contains **one sense** only:

  * `phrasal`: e.g., `"bring up"`
  * `meaning_en`: concise (e.g., `"to mention a topic for discussion"`)
  * `examples`: 2–3 short EN sentences, JSON array
  * `tags`: array (e.g., `["work","meetings"]`)
  * `sense_uid`: unique per (phrasal + sense)
  * Optional flags: `separable`, `intransitive` (bool)
* Do **not** introduce multiple senses of the same phrasal verb on the same day.
* Provide a **seed dataset** JSON with **at least 40 sample cards** across tags `work`, `travel`, `daily` (include mixed separable/intransitive examples). Keep it realistic and B2-friendly. (I will expand later to 120–150.)

### Bot UX (Commands & Flow)

* `/start` — intro & “Begin today’s session”
* `/today` — start/continue today’s session. Shows one card at a time:

  ```
  bring up
  — to mention a topic for discussion
  Ex1: She brought up the budget issue at the meeting.
  Ex2: Don’t bring it up now, please.
  ```

  Inline buttons: **Again**, **Good**
* `/config` — set `daily_new_target` (4–12), `review_limit_per_day` (20–60), `push_time` (`HH:MM`), `pack_tags` (comma-separated)
* `/pack <tag>` — switch pack/tag filter for new cards (e.g., `work`, `travel`, `daily`)
* `/stats` — show: streak days, new learned today, reviews done, accuracy (today/week), hardest tag
* `/snooze` — snooze today’s notification by N hours (default 3h)
* Daily push at `push_time`: “You have X cards today: Y reviews + Z new. Start?”

### Data Model (SQLite)

* `cards(id INTEGER PK, phrasal TEXT, meaning_en TEXT, examples_json TEXT, tags TEXT, sense_uid TEXT UNIQUE, separable INTEGER, intransitive INTEGER)`

  * `tags` stored as comma-separated or JSON
* `progress(user_id INTEGER, card_id INTEGER, state TEXT CHECK(state IN ('learning','review')), box INTEGER, due_at DATE, lapses INTEGER DEFAULT 0, learning_good_count INTEGER DEFAULT 0, last_answer TEXT, last_seen_at DATETIME, PRIMARY KEY(user_id, card_id))`
* `user_config(user_id INTEGER PK, daily_new_target INTEGER DEFAULT 8, review_limit_per_day INTEGER DEFAULT 35, push_time TEXT DEFAULT '09:00', pack_tags TEXT DEFAULT 'daily', intra_spacing_k INTEGER DEFAULT 3)`
* Indices: `(user_id, due_at)`, `(user_id, state)`, `(sense_uid)`

### Scheduling & Timezone

* Respect `TZ` env (default `Asia/Yerevan`). Store `due_at` as dates; use local time for daily boundaries.
* Implement daily scheduler that enqueues a notification at `push_time` per user (store minimal per-user state to know who opted in; assume all users are opted in after `/start`).

### Business Rules (Important)

* **Rebalancing overload:** if overdue reviews > `review_limit_per_day`, serve `review_limit_per_day` oldest today; reschedule remaining evenly across the next 2–3 days (preserve box; just shift `due_at`).
* **Jitter**: when scheduling review intervals, apply ±15% random jitter to avoid clumping.
* **New selection**: honor `pack_tags`; never pick two cards with the same `sense_uid` on the same day.
* **In-session requeue after Again**: place card after `k` other cards (use `intra_spacing_k`).
* Track `streak`: increment if the user completes at least one card today.

### Repository Layout

```
.
├── README.md
├── LICENSE
├── pyproject.toml            # or requirements.txt if not using poetry
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── scripts/
│   ├── seed_cards.py         # imports seed JSON into SQLite
│   └── export_cards.py       # export cards to JSON (for maintenance)
├── data/
│   ├── seed_cards.json       # >= 40 sample cards across tags
│   └── bot.db                # created on first run (ignored in git)
├── srsbot/
│   ├── __init__.py
│   ├── config.py             # env loading, constants, intervals, jitter
│   ├── db.py                 # aiosqlite helpers, migrations/bootstrap
│   ├── models.py             # dataclasses / TypedDicts for entities
│   ├── scheduler.py          # daily push logic
│   ├── srs.py                # box logic, next due computation, rebalancing
│   ├── queue.py              # build daily queue (learning→review→new)
│   ├── content.py            # selection of new cards honoring tags/senses
│   ├── formatters.py         # message rendering for a card
│   ├── keyboards.py          # inline keyboards (Again/Good)
│   ├── handlers/
│   │   ├── start.py
│   │   ├── today.py
│   │   ├── config.py
│   │   ├── pack.py
│   │   ├── stats.py
│   │   └── snooze.py
│   └── main.py               # aiogram app bootstrap
└── tests/
    ├── test_srs.py           # graduation, box bumps, again behavior
    ├── test_queue.py         # daily queue assembly & overload balancing
    ├── test_content.py       # new selection rules (tags, sense_uid)
    └── conftest.py
```

### Key Implementation Details

* `srs.next_due_for_box(box:int, base_date:date) -> date` applies jitter ±15%.
* `srs.on_answer(progress, answer, today)` implements:

  * If `learning`:

    * `Again` → `learning_good_count=0`, requeue after `k`.
    * `Good` → `learning_good_count += 1`; if >=2 → switch to `review` Box 1, `due_at = today + 1 day`; else requeue after `k`.
  * If `review`:

    * `Again` → move to `learning`, `learning_good_count=0`, `lapses += 1`, requeue after `k`.
    * `Good` → `box = min(box+1, 7)`, `due_at = next_due_for_box(box)`.
* `queue.build_daily_queue(user, today)`:

  1. `learning_due` now,
  2. `reviews_due` up to end-of-day (apply cap & rebalance remainder),
  3. `new_candidates` (avoid same `sense_uid`, honor `pack_tags`, up to adaptive `daily_new_target`).
* After session: compute `accuracy`, adapt `daily_new_target` (4..12).
* `/stats` aggregates today & week metrics from `progress` and simple per-user stats table or on-the-fly queries.

### Seed Data (sample format in `data/seed_cards.json`)

Provide >= 40 entries like:

```json
[
  {
    "phrasal": "bring up",
    "meaning_en": "to mention a topic for discussion",
    "examples": [
      "She brought up the budget issue at the meeting.",
      "Don't bring it up now, please."
    ],
    "tags": ["work", "meetings"],
    "sense_uid": "bring_up__mention",
    "separable": true,
    "intransitive": false
  },
  {
    "phrasal": "get over",
    "meaning_en": "to recover from an illness or disappointment",
    "examples": [
      "It took him months to get over the flu.",
      "She still hasn't gotten over the breakup."
    ],
    "tags": ["daily", "health"],
    "sense_uid": "get_over__recover",
    "separable": false,
    "intransitive": true
  }
]
```

### README.md (must include)

* Project overview
* How the SRS works (the session model and boxes)
* Setup (Python version, poetry/pip install)
* `.env` config with examples
* How to run locally (`make run` / `python -m srsbot.main`)
* How to seed the DB (`python scripts/seed_cards.py data/seed_cards.json`)
* Docker usage (`docker-compose up`)
* Commands reference
* Notes about data model & how to extend the card set

### Makefile Targets

* `make install` (deps)
* `make lint` (ruff + black check + mypy)
* `make test`
* `make run`
* `make seed`
* `make docker` / `make up`

### Tests (pytest)

* `test_srs.py`:

  * graduation after 2 Good in learning
  * Again on review → back to learning
  * Good on review → box increment and jittered due
* `test_queue.py`:

  * correct priority order
  * capping/rebalancing of excessive reviews
  * in-session requeue after Again respects spacing `k`
* `test_content.py`:

  * no two cards with the same `sense_uid` in a day
  * `pack_tags` honored

### Deliverables & Quality

* Fully runnable code (no TODOs).
* Clean, typed, documented.
* Sensible error handling and logging.
* MIT **LICENSE** included.

Generate the entire repository with all files, ready to `make install && make run`.

### Considerations
Don't enter into .venv directory as it only contains python virtual environment.
