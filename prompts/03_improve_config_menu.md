**TASK: Redesign “Config” into “Settings” with Per-Field Buttons, Inline Input Prompts, Validation, and Clean UI**

You previously added an inline Main Menu and round flow. Now improve the **settings UX**:

## Goals

* Rename **Config** to **Settings** everywhere (commands, screen titles, callbacks, code files).
* Replace the `/config key=value` flow with a **button-driven Settings screen**:

  * Each setting has its **own inline button** with a **friendly name** (not raw variable names).
  * Tapping a setting opens an **inline “value input” screen** that:

    * Asks the user to enter a new value with:

      * **Bold field name** (e.g., `**Daily new cards**`)
      * *Italic short description* of what it does.
    * Shows a **◀️ Back** button to return to the Settings list.
    * Validates user input; if invalid, shows an **error** (concise), then **re-shows** the same input screen (bold field name, italic description, and Back), keeping the UI clean.
  * On success, updates the setting and returns to the Settings list with updated values.
* **Move pack selection into Settings**: remove the Packs entry from the Main Menu. Inside Settings, provide an **“Active packs”** subsection with the existing **checkbox toggle UI** (green check when ON, gray/empty when OFF). Toggling packs updates the same message (no extra confirmation messages), includes a **Back** to Settings.
* Maintain **clean UI**: **edit** the single active UI message (`edit_message_text`) for all screens; on screen changes use edit, or delete+send and update `last_ui_message_id`. Do not append new bot messages during navigation. (User’s raw text messages cannot be deleted; that’s fine.)
* Remove `/config` command entirely (replace with `/settings` if needed, or rely on **/menu**).

## Settings to Expose (friendly labels + validation)

Use these defaults and validations:

1. **Daily new cards** (`user_config.daily_new_target`, int 4–12)
   *How many new cards to introduce per day. The bot adapts slightly based on your accuracy.*

   * Validator: integer in \[4, 12]

2. **Daily review cap** (`user_config.review_limit_per_day`, int 20–60)
   *Max number of review cards per day to avoid overload; extra reviews are rebalanced to the next days.*

   * Validator: integer in \[20, 60]

3. **Notification time** (`user_config.push_time`, `HH:MM` 24h)
   *Daily reminder time in your local timezone.*

   * Validator: strict `^\d{2}:\d{2}$`, 00≤HH≤23, 00≤MM≤59

4. **Active packs** (moved from Main Menu)
   *Choose which topic packs to draw new cards from. Toggle multiple packs on/off.*

   * UI: checkbox buttons with counts and a **◀️ Back** to Settings.
   * No text input here.

5. **In-round spacing** (`user_config.intra_spacing_k`, int 1–6)
   *How many other cards to show before repeating a missed card within the same round.*

   * Validator: integer in \[1, 6]

(If `TZ` is user-editable: add **Timezone** (`user_config.tz`, IANA string). Optional: validate against `pytz/zoneinfo`. If not, skip.)

## Screens & Navigation

* **Main Menu** (already exists): replace **⚙️ Config** with **⚙️ Settings**. Remove **🧩 Packs**. Menu becomes:

  * `▶️ Today` · `⚙️ Settings` · `📊 Stats` · `😴 Snooze`

* **Settings list screen** (title `**Settings**`): show current values in a readable way, e.g.:

  ```
  **Settings**
  • Daily new cards: 8
  • Daily review cap: 35
  • Notification time: 09:00
  • Active packs: Work, Travel
  • In-round spacing: 3
  ```

  Inline buttons (each on its own row):

  * `🆕 Daily new cards`
  * `🔁 Daily review cap`
  * `⏰ Notification time`
  * `🧩 Active packs`   (opens packs checkbox UI)
  * `↔️ In-round spacing`
  * `◀️ Back` (to Main Menu)

* **Value input screen** (for each editable scalar):

  * Text format:

    ```
    **<Friendly Field Name>**
    *<Short purpose description>*

    Please enter a new value:
    ```
  * If previous attempt failed:

    * Prepend a single-line error like:
      `❌ Invalid value. Expected an integer between 4 and 12.`
    * Then re-show the same bold/italic prompt and Back button.
  * Inline buttons:

    * `◀️ Back` (to Settings)

* **Active packs screen**:

  * Checkbox buttons as before:

    * Enabled: `✅ <Pack Name> (N)`
    * Disabled: `☑️ <Pack Name> (N)` (or `⬜️`)
  * No extra “New pack set to…” message on toggle; only re-render the same message.
  * `◀️ Back` (to Settings)

## State Management

* Add/update `user_ui_state` to support **pending input** for a specific setting:

  * `current_screen`, `last_ui_message_id`, and:
  * `awaiting_input_field` (nullable: one of `daily_new_target`, `review_limit_per_day`, `push_time`, `intra_spacing_k`, `tz` if used)
* When `awaiting_input_field` is set, capture the **next incoming text** from this user as the candidate value for that field; **validate**, then:

  * If valid: persist to `user_config`, clear `awaiting_input_field`, and return to **Settings** screen (edit same message).
  * If invalid: re-render **the same input screen** with an error line, keeping Back button.
* Make sure callback handlers **ignore** pack toggles or other callbacks while `awaiting_input_field` is set (except Back). Either reject with a small ephemeral alert (answerCallbackQuery) or allow Back to cancel input mode.

## Validation Helpers

Create a small validator module (e.g., `srsbot/validators.py`) with:

```python
def validate_int_in_range(text: str, lo: int, hi: int) -> tuple[bool, str | None]:
    ...
def validate_hhmm(text: str) -> tuple[bool, str | None]:
    ...
def validate_timezone(text: str) -> tuple[bool, str | None]:  # optional
    ...
```

Return `(ok, error_message)` where `error_message` is concise and human-readable.

## Callback/Data Conventions

* Settings list: `ui:settings`
* Open scalar inputs:

  * `ui:settings.input:daily_new_target`
  * `ui:settings.input:review_limit_per_day`
  * `ui:settings.input:push_time`
  * `ui:settings.input:intra_spacing_k`
  * (optional) `ui:settings.input:tz`
* Packs subsection:

  * `ui:settings.packs` (open)
  * `ui:settings.packs.toggle:<pack_id>`
  * `ui:settings.back` (Back to Main Menu)
  * `ui:settings.packs.back` (Back to Settings)
* Remove `/config` command; add `/settings` command that routes to `ui:settings` (and keep **/menu**).

## Files to Modify / Add

* **Routing & Handlers**

  * `srsbot/handlers/menu.py`: rename “Config” to “Settings”; remove Packs from Main Menu.
  * `srsbot/handlers/settings.py` (new, split from old config):

    * `show_settings(user_id, edit=True)` → renders list with friendly names and current values.
    * `open_input(user_id, field)` → sets `awaiting_input_field` and renders the input screen.
    * `handle_text_input(message)` → if `awaiting_input_field` set:

      * validate via `validators.py`
      * on success, save to `user_config`, clear awaiting flag, show updated Settings list
      * on failure, re-render same input screen with error line.
    * Packs subsection handlers:

      * open packs, toggle packs with checkbox, back to Settings.
  * Remove `/config` handler entirely; add `/settings` → Settings list.
* **Keyboards**

  * `srsbot/keyboards.py`:

    * `kb_settings_list(...)`
    * `kb_settings_back()` (to Main Menu)
    * `kb_settings_input_back()` (Back from input screen to Settings)
    * `kb_settings_packs(packs, selected_set)` (checkbox UI)
* **UI Helper**

  * `srsbot/ui.py`: add helpers for rendering Settings list, input screens, and clean edit/delete message logic (`show_screen` already exists).
* **DB / State**

  * `srsbot/db.py`:

    * Extend `user_ui_state` to include `awaiting_input_field TEXT NULL`.
    * CRUD to set/clear it.
* **Validators**

  * `srsbot/validators.py` with functions listed above.

## Copy & Text (examples)

* **Settings list title:** `**Settings**`
* **Input prompt (Daily new cards):**

  ```
  **Daily new cards**
  *How many new cards to introduce per day. The bot adapts slightly based on your accuracy.*

  Please enter a new value:
  ```
* **On invalid value:**

  ```
  ❌ Invalid value. Expected an integer between 4 and 12.

  **Daily new cards**
  *How many new cards to introduce per day. The bot adapts slightly based on your accuracy.*

  Please enter a new value:
  ```
* Keep prompts short, consistent, and polished.

## Acceptance Criteria

1. Main Menu shows **⚙️ Settings** instead of Config; **Packs** is **removed** from Main Menu. `/config` is removed; `/settings` (optional) opens Settings list; `/menu` and `/help` still work.
2. Settings list renders **friendly names** and current values. Each field opens a **value input** screen with **bold field name**, *italic description*, an instruction to enter a new value, and a **◀️ Back** button.
3. On text input:

   * Valid input → update stored config and return to the Settings list (same UI message edited).
   * Invalid input → show a concise error line and **re-show** the same input screen (bold name + italic description + Back).
4. **Active packs** selection is now inside **Settings**. Toggling packs updates **the same message** (checkbox behavior), **no extra messages** are sent; has a **◀️ Back** to Settings.
5. The bot maintains **one active UI message** for navigation. Screen changes **edit** or delete+send, updating `last_ui_message_id`. No extra bot messages are appended during screen navigation. (User text inputs remain, as expected.)
6. Existing SRS features (rounds, Today flow with Finish Session, Stats, Snooze) continue to function unchanged.

Keep the code typed (mypy), formatted (ruff/black), with docstrings for new helpers, and update **README.md** (“Settings” section) describing the new UI, validation, and how to change each field.
