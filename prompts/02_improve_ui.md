**TASK: Add Inline Menu UI with Back Navigation, Emojis, and Message Cleanup**

You previously built a Telegram SRS bot (Python 3.11, aiogram v3, SQLite). Now improve UX by replacing most command typing with a **single inline menu**, navigable with buttons, including **Back** and message cleanup. Implement the following exactly:

## Goals

* Add a **Main Menu** (inline keyboard) invoked by **/menu** and **/help**.
* Menu items (with emojis):

  * **▶️ Today** — start/continue today’s rounds (must include a “Finish session” button on the Today screen).
  * **⚙️ Config** — change daily\_new\_target, review\_limit\_per\_day, push\_time, pack\_tags (existing UI remains; add Back).
  * **🧩 Packs** — toggle packs with **checkbox** behavior (green check when ON, gray/empty when OFF) + Back.
  * **📊 Stats** — show stats + Back.
  * **😴 Snooze** — snooze today’s notification + Back.
* **/pack** command must be removed entirely (UI handles packs).
* **Message cleanliness:** On every navigation action (opening a screen, toggling packs, returning Back), **do not append new messages** to the chat history. Prefer **editing the existing UI message** (`edit_message_text`) or, if necessary, **delete the previous UI message** and send a fresh one. The user should see a single “active” UI message at a time.
* **Packs toggling UX:** clicking a pack button **must toggle ON/OFF** (checkbox emoji update) **without** sending a new “New card pack set to…” message. Only the **inline button labels** update via message edit.
* **Today screen:** add an **inline “🏁 Finish session”** button that gracefully ends the current session (send a short summary, then return to Main Menu).

## UI / Navigation Details

### 1) Screens & Router

Introduce a simple inline-UI “router” with these screen IDs:

* `SCREEN_MENU` — main menu
* `SCREEN_TODAY` — today/round UI (card presentation)
* `SCREEN_CONFIG` — configuration
* `SCREEN_PACKS` — pack selection
* `SCREEN_STATS` — statistics
* `SCREEN_SNOOZE` — snooze settings

Maintain per-user UI state in DB or in-memory cache (prefer DB) to track:

* `last_ui_message_id` — the message we edit/delete for navigation
* `current_screen` — enum/string
* any screen-local cursor (e.g., pagination if needed)

### 2) Main Menu (invoked by /menu and /help)

* Command handlers `/menu` and `/help` must render the **same** main menu screen:

  * Title: `**Main Menu**`
  * Inline keyboard (two rows example):

    ```
    [▶️ Today] [⚙️ Config]
    [🧩 Packs] [📊 Stats]
    [😴 Snooze]
    ```
* Store/update `last_ui_message_id` so subsequent actions **edit this message** instead of adding a new one.

### 3) Today Screen (with Finish Session)

* When user taps **▶️ Today**, render current Today screen (as you already do for card flow).
* Add a persistent **“🏁 Finish session”** inline button on the Today UI.

  * On tap: finalize the session for the day (show a short summary of Good/Again, learned new, reviews done), then **navigate back to Main Menu** (replace the Today UI message with the menu via edit/delete).
* Ensure existing **card answer buttons** (Again/Good) still work **within the same message** (edit text/keyboard to show next card). Do not create new messages per card.
* If there are no cards to show: display “Nothing left for today 🎉” and a **Back** button to Main Menu.

### 4) Packs Screen (checkbox behavior, no extra messages)

* Render all available packs as inline buttons. Each button shows:

  * **Enabled**: `✅ <Pack Name> (N)`
  * **Disabled**: `☑️ <Pack Name> (N)`  (or use `⬜️` if preferred)
* On tap of a pack button: **toggle ON/OFF** and **re-render the same message** with updated checkmarks.

  * **Do not send a separate confirmation message.**
  * **Do not create a new message.** Only `edit_message_text` the existing one.
* Add a **“◀️ Back”** button that returns to Main Menu (again, via editing/deleting the current UI message).
* Remove the `/pack` command handler and any references; the only way to set packs is via this screen.

### 5) Config, Stats, Snooze Screens

* Each screen must include a **“◀️ Back”** button to the Main Menu.
* **Config**: keep existing UI/flow; when values change, update inline content in place.
* **Stats**: show today/week counters + Back; **edit** the same message on refresh.
* **Snooze**: offer a few preset options (e.g., +1h, +3h, +6h) as inline buttons + Back; update the UI in place.

### 6) Message Cleanup Policy

* Define a helper `ui.show_screen(user_id, screen, text, keyboard)` that:

  * If `last_ui_message_id` exists: try `edit_message_text`; if `MessageNotModified` or incompatible, **delete** and send a new message; update `last_ui_message_id`.
  * If no `last_ui_message_id`: send a new message; store `last_ui_message_id`.
* All screen transitions (including Back and pack toggles) must route through this helper.
* Answer callbacks for cards (Again/Good) should continue to **edit the same message** to show the next card or round completion UI.

## Technical Implementation

### Files to Modify

* `srsbot/handlers/start.py`

  * Ensure `/help` calls the same entry point as `/menu`.
* `srsbot/handlers/menu.py` (new)

  * Implement `/menu` and `/help`, render Main Menu via `ui.show_screen`.
* `srsbot/handlers/today.py`

  * Add **Finish session** inline button; callback `ui:today.finish`.
  * On finish, compute summary, then show Main Menu via `ui.show_screen`.
  * Ensure card flow still edits the same message; no stray messages.
* `srsbot/handlers/packs.py`

  * Replace any text-based confirms with **inline toggle updates** only.
  * Callback data: `ui:packs.toggle:<pack_id>`, `ui:packs.back`.
  * On toggle, update user’s pack selection and **re-render** the same message.
* `srsbot/handlers/config.py`, `srsbot/handlers/stats.py`, `srsbot/handlers/snooze.py`

  * Add **Back** button with callbacks `ui:config.back`, `ui:stats.back`, `ui:snooze.back` → navigate to Main Menu with `ui.show_screen`.
  * For any changes (e.g., config updates), **edit** in place (avoid new messages).
* `srsbot/keyboards.py`

  * New builders:

    * `kb_main_menu()`
    * `kb_today(answer_buttons=True, finish_button=True, back_to_menu=False)` (for card + finish button)
    * `kb_packs(packs, selected_set)` (renders checkboxes)
    * `kb_config_back()`, `kb_stats_back()`, `kb_snooze_back()`
    * `kb_back_to_menu()`
* `srsbot/ui.py` (new)

  * `show_screen(user_id, screen_id, text, reply_markup)` to centralize edit-or-delete-and-send logic and manage `last_ui_message_id`.
  * Helpers to render titles/body for each screen (string builders using `formatters.py`).
* `srsbot/db.py`

  * Add/update per-user UI state storage:

    * `user_ui_state(user_id INTEGER PK, last_ui_message_id INTEGER, current_screen TEXT)`
  * CRUD helpers: `get_ui_state`, `set_ui_state`, `clear_ui_message`.
* Remove `/pack` from routing and codebase.

### Callback Data Conventions

Use explicit prefixes for clarity:

* Main Menu: `ui:menu`
* Today: `ui:today.finish`, `ui:today.back` (if needed)
* Packs: `ui:packs.toggle:<pack_id>`, `ui:packs.back`
* Config: `ui:config.*`, `ui:config.back`
* Stats: `ui:stats.back`
* Snooze: `ui:snooze.<option>`, `ui:snooze.back`

### Emojis (consistent usage)

* Menu: `▶️ Today`, `⚙️ Config`, `🧩 Packs`, `📊 Stats`, `😴 Snooze`
* Back: `◀️ Back`
* Finish session (Today): `🏁 Finish session`
* Packs checkboxes: **Enabled**=`✅`, **Disabled**=`☑️` (or `⬜️` if rendering better)

## Acceptance Criteria

1. Typing `/menu` or `/help` opens the **Main Menu**. The bot maintains **one active UI message**; navigating between screens **edits** the same message or deletes & re-sends, never spamming chat.
2. **Today** screen shows card UI with **🏁 Finish session** button that ends the session and returns to the **Main Menu** with a short summary.
3. **Packs** screen displays each pack as a checkbox button with count. Tapping a pack **toggles** its state and **updates the same message** (no extra confirmation messages). A **◀️ Back** button returns to Main Menu.
4. The **/pack command is removed** (not registered, no handler). Pack selection fully works via the Packs UI.
5. **Config**, **Stats**, and **Snooze** screens each include a **◀️ Back** button; all changes and displays happen via inline **message edits**, not new messages.
6. Navigation between any screens **does not leave residual messages** in chat history. Only the active UI message remains visible at each step.
7. Existing SRS functionality (cards, rounds, caps, rebalancing) continues to work unchanged.

Keep code typed (mypy), formatted (black/ruff), with docstrings for new helpers, and update **README.md** with a short “Menu Navigation” section (how to open the menu, meaning of buttons, and the cleanup behavior).
